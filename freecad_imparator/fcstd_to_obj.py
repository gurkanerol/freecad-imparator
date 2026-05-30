"""
FreeCAD Imparator - FreeCAD to OBJ Headless Exporter
Author: gurkanerol
Email: gurkanerol@gmail.com

This script runs in a background FreeCAD Python environment. It parses a FreeCAD
(.fcstd) document, extracts the assembly hierarchy, recalculates absolute global
placements, and exports all 3D mesh and part geometry into a clean OBJ format,
along with a companion JSON file representing the original assembly structure.
"""

import sys
import os
import json
import zipfile
import xml.etree.ElementTree as ET

# Argument structure: python fcstd_to_obj.py <input_fcstd> <output_obj> <deflection> <scale> [lib_path]
if len(sys.argv) < 5:
    print("Error: Missing arguments.")
    print("Usage: python fcstd_to_obj.py <input_fcstd> <output_obj> <deflection> <scale> [lib_path]")
    sys.exit(1)

input_fcstd = sys.argv[1]
output_obj = sys.argv[2]
try:
    deflection = float(sys.argv[3])
except ValueError:
    deflection = 0.1

try:
    global_scale = float(sys.argv[4])
except ValueError:
    global_scale = 0.001

if len(sys.argv) >= 6:
    lib_path = sys.argv[5]
    if lib_path and lib_path not in sys.path:
        sys.path.append(lib_path)

# Try to import FreeCAD modules
try:
    import FreeCAD
    import Part
    import Mesh
    import MeshPart
except ImportError as e:
    print(f"Error: Could not import FreeCAD modules. sys.path is: {sys.path}")
    print(e)
    sys.exit(2)

def is_container_obj(obj):
    if hasattr(obj, "Group"):
        return True
    if obj.TypeId in ["App::Part", "PartDesign::Body"] or "Group" in obj.TypeId or "Assembly" in obj.TypeId:
        return True
    return False

def get_global_placement(obj):
    if hasattr(obj, "getGlobalPlacement"):
        try:
            return obj.getGlobalPlacement()
        except Exception:
            pass
    if hasattr(obj, "Placement"):
        return obj.Placement
    return None

def get_gui_properties(fcstd_path):
    """Parse GuiDocument.xml to extract color, transparency, and visibility."""
    props = {}
    try:
        with zipfile.ZipFile(fcstd_path, 'r') as z:
            if 'GuiDocument.xml' in z.namelist():
                xml_content = z.read('GuiDocument.xml')
                root = ET.fromstring(xml_content)
                for view_obj in root.findall(".//ViewProvider"):
                    name = view_obj.get('name')
                    r, g, b = 0.8, 0.8, 0.8
                    shape_color_prop = view_obj.find(".//Property[@name='ShapeColor']/PropertyColor")
                    if shape_color_prop is not None:
                        val = int(shape_color_prop.get('value'))
                        r = ((val >> 24) & 0xFF) / 255.0
                        g = ((val >> 16) & 0xFF) / 255.0
                        b = ((val >> 8) & 0xFF) / 255.0
                    
                    transparency = 0.0
                    trans_prop = view_obj.find(".//Property[@name='Transparency']/Integer")
                    if trans_prop is not None:
                        try:
                            transparency = int(trans_prop.get('value')) / 100.0
                        except:
                            pass
                            
                    visibility = True
                    vis_prop = view_obj.find(".//Property[@name='Visibility']/Bool")
                    if vis_prop is not None:
                        visibility = vis_prop.get('value') == 'true'
                    
                    props[name] = {"color": [r, g, b], "transparency": transparency, "visibility": visibility}
    except Exception as e:
        print(f"Error reading GuiDocument.xml: {e}")
    return props

print(f"FreeCAD version: {FreeCAD.Version()}")
print(f"Loading document: {input_fcstd}")

try:
    doc = FreeCAD.openDocument(input_fcstd)
except Exception as e:
    print(f"Error opening FreeCAD file: {e}")
    sys.exit(3)

# Parse GUI metadata first for visibility checks
gui_props = get_gui_properties(input_fcstd)

print("Analyzing geometry objects...")
objs_to_export = []
for obj in doc.Objects:
    # We want physical shapes or meshes, but not group containers
    if (hasattr(obj, "Shape") or hasattr(obj, "Mesh")) and not is_container_obj(obj):
        # Exclude construction/helper elements
        if any(t in obj.TypeId for t in ["App::Line", "App::Plane", "App::Point", "App::Origin"]):
            continue
            
        # Filter: Exclude intermediate shapes in the CAD history.
        is_consumed = False
        for dep in obj.InList:
            if (hasattr(dep, "Shape") or hasattr(dep, "Mesh")) and not is_container_obj(dep):
                is_consumed = True
                break
        if not is_consumed:
            objs_to_export.append(obj)

if not objs_to_export:
    print("Warning: No root 3D shapes or meshes found in the document to export.")
    sys.exit(0)

print(f"Found {len(objs_to_export)} final root objects for export:")
for o in objs_to_export:
    print(f" - {o.Name} ({o.TypeId})")

# Determine which containers are actually needed (ancestors of all exported meshes, visible or hidden)
needed_containers = set()

def mark_ancestors_needed(child_obj):
    for dep in child_obj.InList:
        if hasattr(dep, "Group") and child_obj in dep.Group:
            needed_containers.add(dep.Name)
            mark_ancestors_needed(dep)

for obj in objs_to_export:
    mark_ancestors_needed(obj)

# Also mark ancestors of hidden objects so their folder structure is preserved
for obj in doc.Objects:
    vp = gui_props.get(obj.Name)
    if vp is not None and not vp["visibility"]:
        if (hasattr(obj, "Shape") or hasattr(obj, "Mesh")) and not is_container_obj(obj):
            mark_ancestors_needed(obj)

# Extract assembly and parent-child hierarchy
print("Extracting document assembly hierarchy...")
containers_json = []
meshes_json = []

for obj in doc.Objects:
    vp = gui_props.get(obj.Name)
    is_hidden = False
    if vp is not None and not vp["visibility"]:
        is_hidden = True

    if obj in objs_to_export:
        # Leaf mesh object
        parent_name = None
        for dep in obj.InList:
            if hasattr(dep, "Group") and obj in dep.Group:
                parent_name = dep.Name
                break
        
        # Look up color and transparency (fallback to LinkedObject if link color is not set)
        color_info = gui_props.get(obj.Name)
        if color_info is None and hasattr(obj, "LinkedObject") and obj.LinkedObject:
            color_info = gui_props.get(obj.LinkedObject.Name)
            
        if color_info:
            obj_color = color_info["color"]
            obj_trans = color_info["transparency"]
        else:
            obj_color = [0.8, 0.8, 0.8]
            obj_trans = 0.0
        
        meshes_json.append({
            "name": obj.Name,
            "label": obj.Label,
            "parent_name": parent_name,
            "color": obj_color,
            "transparency": obj_trans,
            "hidden": is_hidden
        })
    else:
        # Check if it acts as a group container AND is actually needed
        if is_container_obj(obj) and obj.Name in needed_containers:
            # Ignore standard/default "Origin" container
            if obj.TypeId == "App::Origin" or obj.Name == "Origin":
                continue
                
            parent_name = None
            for dep in obj.InList:
                if hasattr(dep, "Group") and obj in dep.Group:
                    parent_name = dep.Name
                    break
            
            gp = get_global_placement(obj)
            if gp is None:
                gp = FreeCAD.Placement()

            # Scale mm to meters for Blender
            pos = [gp.Base.x * global_scale, gp.Base.y * global_scale, gp.Base.z * global_scale]
            rot = [gp.Rotation.Q[3], gp.Rotation.Q[0], gp.Rotation.Q[1], gp.Rotation.Q[2]] # w, x, y, z
            
            containers_json.append({
                "name": obj.Name,
                "label": obj.Label,
                "parent_name": parent_name,
                "position": pos,
                "rotation": rot,
                "hidden": is_hidden
            })

# Save JSON sidecar metadata
hierarchy_data = {
    "containers": containers_json,
    "meshes": meshes_json
}

json_path = output_obj + ".json"
try:
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(hierarchy_data, f, indent=4)
    print(f"Exported assembly hierarchy to: {json_path}")
except Exception as e:
    print(f"Error saving hierarchy JSON: {e}")

# Triangulate Part shapes into temporary Mesh features using the target deflection
export_features = []
temp_mesh_features = []

for obj in objs_to_export:
    if hasattr(obj, "Shape") and obj.Shape:
        try:
            print(f"Tessellating shape '{obj.Name}' with deflection={deflection}...")
            mesh_data = MeshPart.meshFromShape(Shape=obj.Shape, LinearDeflection=deflection)
            
            # Bake the parent container's global placement into the mesh geometry
            parent_gp = None
            for dep in obj.InList:
                if hasattr(dep, "Group") and obj in dep.Group and is_container_obj(dep):
                    parent_gp = get_global_placement(dep)
                    break
            
            if parent_gp is not None:
                mesh_data.transform(parent_gp.Matrix)
            
            # Create temporary feature in document to hold the mesh data
            temp_name = f"TempMesh_{obj.Name}"
            temp_feat = doc.addObject("Mesh::Feature", temp_name)
            temp_feat.Mesh = mesh_data
            temp_feat.Label = obj.Label # Keep the friendly user label
            
            export_features.append(temp_feat)
            temp_mesh_features.append(temp_feat)
        except Exception as e:
            print(f"Error tessellating shape '{obj.Name}': {e}")
            export_features.append(obj)
    elif hasattr(obj, "Mesh") and obj.Mesh:
        # For existing meshes, we should also export them relative to their parent!
        # But we can't transform the original, so we duplicate it into a temp mesh!
        parent_gp = None
        for dep in obj.InList:
            if hasattr(dep, "Group") and obj in dep.Group and is_container_obj(dep):
                parent_gp = get_global_placement(dep)
                break
        
        if parent_gp is not None:
            temp_name = f"TempMesh_{obj.Name}"
            temp_feat = doc.addObject("Mesh::Feature", temp_name)
            mesh_data = obj.Mesh.copy()
            mesh_data.transform(parent_gp.Matrix)
            temp_feat.Mesh = mesh_data
            export_features.append(temp_feat)
            temp_mesh_features.append(temp_feat)
        else:
            export_features.append(obj)

# Export all collected features to OBJ with separated objects
print(f"Exporting {len(export_features)} features to OBJ: {output_obj}")
try:
    with open(output_obj, 'w', encoding='utf-8') as out_f:
        out_f.write("# Exported by FreeCAD Imparator\n")
        vertex_offset = 1
        for feat in export_features:
            # Write object name tag to separate them in Blender
            out_f.write(f"o {feat.Name}\n")
            mesh = feat.Mesh
            # Write vertices (scaled mm to meters)
            for v in mesh.Points:
                out_f.write(f"v {v.x * global_scale} {v.y * global_scale} {v.z * global_scale}\n")
            # Write faces (using 1-based indexing relative to the whole file)
            for facet in mesh.Facets:
                i1 = facet.PointIndices[0] + vertex_offset
                i2 = facet.PointIndices[1] + vertex_offset
                i3 = facet.PointIndices[2] + vertex_offset
                out_f.write(f"f {i1} {i2} {i3}\n")
            # Increment the vertex offset for the next object
            vertex_offset += mesh.CountPoints
    print("Export completed successfully.")
except Exception as e:
    print(f"Error exporting objects to OBJ: {e}")
    for temp_feat in temp_mesh_features:
        try:
            doc.removeObject(temp_feat.Name)
        except:
            pass
    sys.exit(4)

# Clean up temporary mesh features
print("Cleaning up temporary tessellation features...")
for temp_feat in temp_mesh_features:
    try:
        doc.removeObject(temp_feat.Name)
    except Exception as e:
        print(f"Error removing temp object {temp_feat.Name}: {e}")

# Close document to free memory
try:
    FreeCAD.closeDocument(doc.Name)
    print("FreeCAD document closed.")
except Exception as e:
    print(f"Error closing document: {e}")

print("FreeCAD export process finished.")
sys.exit(0)
