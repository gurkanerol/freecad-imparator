"""
FreeCAD Imparator - FreeCAD to OBJ Headless Exporter
Author: gurkanerol
Email: gurkanerol@gmail.com

This script runs in a background FreeCAD Python environment. It parses a FreeCAD
(.fcstd) document, extracts the assembly hierarchy, recalculates absolute global
placements, and exports all 3D mesh and part geometry into a clean OBJ format,
along with a companion JSON file representing the original assembly structure.

All status output goes to stderr so that the caller can capture it independently
from any FreeCAD internal stdout noise.
"""

import sys
import os
import json
import zipfile
import xml.etree.ElementTree as ET


def log(msg):
    """Write a status line to stderr (visible in Blender's system console)."""
    print(msg, file=sys.stderr, flush=True)


# Argument structure: python fcstd_to_obj.py <input_fcstd> <output_obj> <deflection> <scale> [lib_path]
if len(sys.argv) < 5:
    log("Error: Missing arguments.")
    log("Usage: python fcstd_to_obj.py <input_fcstd> <output_obj> <deflection> <scale> [lib_path]")
    sys.exit(1)

input_fcstd = sys.argv[1]
output_obj  = sys.argv[2]

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
        sys.path.insert(0, lib_path)

# Try to import FreeCAD modules
try:
    import FreeCAD
    import Part      # noqa: F401  (used implicitly through Shape)
    import Mesh      # noqa: F401
    import MeshPart
except ImportError as e:
    log(f"Error: Could not import FreeCAD modules.")
    log(f"  sys.path = {sys.path}")
    log(f"  {e}")
    sys.exit(2)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_container_obj(obj):
    """Return True if the object acts as a group/assembly container."""
    if hasattr(obj, "Group"):
        return True
    return obj.TypeId in ["App::Part", "PartDesign::Body"] or \
           "Group" in obj.TypeId or "Assembly" in obj.TypeId


def get_global_placement(obj):
    """Return the object's global placement, falling back to local Placement."""
    if hasattr(obj, "getGlobalPlacement"):
        try:
            return obj.getGlobalPlacement()
        except Exception:
            pass
    if hasattr(obj, "Placement"):
        return obj.Placement
    return None


def get_gui_properties(fcstd_path):
    """Parse GuiDocument.xml inside the .fcstd ZIP to extract per-object
    color, transparency, and visibility. Returns a dict keyed by object name."""
    props = {}
    try:
        with zipfile.ZipFile(fcstd_path, 'r') as z:
            if 'GuiDocument.xml' not in z.namelist():
                return props
            xml_content = z.read('GuiDocument.xml')
            root = ET.fromstring(xml_content)
            for view_obj in root.findall(".//ViewProvider"):
                name = view_obj.get('name')

                # --- color ---
                r, g, b = 0.8, 0.8, 0.8
                shape_color_prop = view_obj.find(".//Property[@name='ShapeColor']/PropertyColor")
                if shape_color_prop is not None:
                    try:
                        val = int(shape_color_prop.get('value'))
                        r = ((val >> 24) & 0xFF) / 255.0
                        g = ((val >> 16) & 0xFF) / 255.0
                        b = ((val >>  8) & 0xFF) / 255.0
                    except Exception:
                        pass

                # --- transparency ---
                transparency = 0.0
                trans_prop = view_obj.find(".//Property[@name='Transparency']/Integer")
                if trans_prop is not None:
                    try:
                        transparency = int(trans_prop.get('value')) / 100.0
                    except Exception:
                        pass

                # --- visibility ---
                visibility = True
                vis_prop = view_obj.find(".//Property[@name='Visibility']/Bool")
                if vis_prop is not None:
                    visibility = vis_prop.get('value') == 'true'

                props[name] = {
                    "color": [r, g, b],
                    "transparency": transparency,
                    "visibility": visibility,
                }
    except Exception as e:
        log(f"Warning: Could not read GuiDocument.xml: {e}")
    return props


def find_parent_name(obj):
    """Return the Name of the first direct Group container of obj, or None."""
    for dep in obj.InList:
        if hasattr(dep, "Group") and obj in dep.Group:
            return dep.Name
    return None


def find_parent_container(obj):
    """Return the first direct Group container object, or None."""
    for dep in obj.InList:
        if hasattr(dep, "Group") and obj in dep.Group and is_container_obj(dep):
            return dep
    return None


# ---------------------------------------------------------------------------
# Load document
# ---------------------------------------------------------------------------

log(f"FreeCAD version: {FreeCAD.Version()}")
log(f"Loading document: {input_fcstd}")

try:
    doc = FreeCAD.openDocument(input_fcstd)
except Exception as e:
    log(f"Error opening FreeCAD file: {e}")
    sys.exit(3)

gui_props = get_gui_properties(input_fcstd)

# ---------------------------------------------------------------------------
# Determine root objects to export (leaf shapes/meshes, not consumed by others)
# ---------------------------------------------------------------------------

log("Analyzing geometry objects...")
SKIP_TYPE_FRAGMENTS = ["App::Line", "App::Plane", "App::Point", "App::Origin"]

objs_to_export = []
for obj in doc.Objects:
    if not (hasattr(obj, "Shape") or hasattr(obj, "Mesh")):
        continue
    if is_container_obj(obj):
        continue
    if any(t in obj.TypeId for t in SKIP_TYPE_FRAGMENTS):
        continue
    # Skip if another shape/mesh depends on this one (intermediate history step)
    is_consumed = any(
        (hasattr(dep, "Shape") or hasattr(dep, "Mesh")) and not is_container_obj(dep)
        for dep in obj.InList
    )
    if not is_consumed:
        objs_to_export.append(obj)

if not objs_to_export:
    log("Warning: No root 3D shapes or meshes found in the document to export.")
    sys.exit(0)

log(f"Found {len(objs_to_export)} final root objects for export:")
for o in objs_to_export:
    log(f"  - {o.Name} ({o.TypeId})")

# ---------------------------------------------------------------------------
# Collect all needed container ancestors (for hierarchy reconstruction)
# ---------------------------------------------------------------------------

needed_containers = set()

def mark_ancestors_needed(child_obj):
    for dep in child_obj.InList:
        if hasattr(dep, "Group") and child_obj in dep.Group:
            needed_containers.add(dep.Name)
            mark_ancestors_needed(dep)

for obj in objs_to_export:
    mark_ancestors_needed(obj)

# Include ancestors of hidden leaf objects too
for obj in doc.Objects:
    vp = gui_props.get(obj.Name)
    if vp is not None and not vp["visibility"]:
        if (hasattr(obj, "Shape") or hasattr(obj, "Mesh")) and not is_container_obj(obj):
            mark_ancestors_needed(obj)

# ---------------------------------------------------------------------------
# Build hierarchy JSON data
# ---------------------------------------------------------------------------

log("Extracting document assembly hierarchy...")
containers_json = []
meshes_json = []

for obj in doc.Objects:
    vp = gui_props.get(obj.Name)
    is_hidden = vp is not None and not vp["visibility"]

    if obj in objs_to_export:
        parent_name = find_parent_name(obj)

        # Color: use linked object's color if this object has none
        color_info = gui_props.get(obj.Name)
        if color_info is None and hasattr(obj, "LinkedObject") and obj.LinkedObject:
            color_info = gui_props.get(obj.LinkedObject.Name)

        obj_color = color_info["color"] if color_info else [0.8, 0.8, 0.8]
        obj_trans  = color_info["transparency"] if color_info else 0.0

        meshes_json.append({
            "name":        obj.Name,
            "label":       obj.Label,
            "parent_name": parent_name,
            "color":       obj_color,
            "transparency": obj_trans,
            "hidden":      is_hidden,
        })

    elif is_container_obj(obj) and obj.Name in needed_containers:
        if obj.TypeId == "App::Origin" or obj.Name == "Origin":
            continue

        parent_name = find_parent_name(obj)
        gp = get_global_placement(obj) or FreeCAD.Placement()

        pos = [gp.Base.x * global_scale,
               gp.Base.y * global_scale,
               gp.Base.z * global_scale]
        # Blender quaternion order: w, x, y, z
        rot = [gp.Rotation.Q[3],
               gp.Rotation.Q[0],
               gp.Rotation.Q[1],
               gp.Rotation.Q[2]]

        containers_json.append({
            "name":        obj.Name,
            "label":       obj.Label,
            "parent_name": parent_name,
            "position":    pos,
            "rotation":    rot,
            "hidden":      is_hidden,
        })

# Save JSON sidecar
json_path = output_obj + ".json"
try:
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({"containers": containers_json, "meshes": meshes_json}, f, indent=2)
    log(f"Exported assembly hierarchy to: {json_path}")
except Exception as e:
    log(f"Warning: Could not save hierarchy JSON: {e}")

# ---------------------------------------------------------------------------
# Tessellate Part shapes into temporary Mesh features
# ---------------------------------------------------------------------------

# temp_features: (feat, is_temporary) tuples
# is_temporary=True means we created it and must remove it afterwards
export_entries = []  # list of (mesh_feature, is_temp)

for obj in objs_to_export:
    parent_container = find_parent_container(obj)
    parent_gp = get_global_placement(parent_container) if parent_container else None

    if hasattr(obj, "Shape") and obj.Shape:
        try:
            log(f"Tessellating '{obj.Name}' with deflection={deflection}...")
            mesh_data = MeshPart.meshFromShape(Shape=obj.Shape, LinearDeflection=deflection)
            if parent_gp is not None:
                mesh_data.transform(parent_gp.Matrix)
            temp_name = f"TempMesh_{obj.Name}"
            temp_feat = doc.addObject("Mesh::Feature", temp_name)
            temp_feat.Mesh  = mesh_data
            temp_feat.Label = obj.Label
            export_entries.append((temp_feat, True))
        except Exception as e:
            log(f"Error tessellating shape '{obj.Name}': {e}")
            export_entries.append((obj, False))

    elif hasattr(obj, "Mesh") and obj.Mesh:
        if parent_gp is not None:
            # Must duplicate to avoid mutating the original mesh
            temp_name = f"TempMesh_{obj.Name}"
            temp_feat = doc.addObject("Mesh::Feature", temp_name)
            mesh_data = obj.Mesh.copy()
            mesh_data.transform(parent_gp.Matrix)
            temp_feat.Mesh = mesh_data
            export_entries.append((temp_feat, True))
        else:
            export_entries.append((obj, False))

# ---------------------------------------------------------------------------
# Write OBJ file (batched writes for performance)
# ---------------------------------------------------------------------------

log(f"Exporting {len(export_entries)} features to OBJ: {output_obj}")
try:
    lines = ["# Exported by FreeCAD Imparator\n"]
    vertex_offset = 1
    for feat, _is_temp in export_entries:
        lines.append(f"o {feat.Name}\n")
        mesh = feat.Mesh
        s = global_scale
        for v in mesh.Points:
            lines.append(f"v {v.x * s:.6f} {v.y * s:.6f} {v.z * s:.6f}\n")
        for facet in mesh.Facets:
            p = facet.PointIndices
            lines.append(f"f {p[0]+vertex_offset} {p[1]+vertex_offset} {p[2]+vertex_offset}\n")
        vertex_offset += mesh.CountPoints

    with open(output_obj, 'w', encoding='utf-8') as out_f:
        out_f.writelines(lines)
    log("OBJ export completed successfully.")
except Exception as e:
    log(f"Error exporting OBJ: {e}")
    # Clean up temp features before aborting
    for feat, is_temp in export_entries:
        if is_temp:
            try:
                doc.removeObject(feat.Name)
            except Exception:
                pass
    sys.exit(4)

# ---------------------------------------------------------------------------
# Clean up temporary mesh features
# ---------------------------------------------------------------------------

log("Cleaning up temporary tessellation features...")
for feat, is_temp in export_entries:
    if is_temp:
        try:
            doc.removeObject(feat.Name)
        except Exception as e:
            log(f"Warning: Could not remove temp object '{feat.Name}': {e}")

# ---------------------------------------------------------------------------
# Close document to release all FreeCAD memory
# ---------------------------------------------------------------------------

try:
    FreeCAD.closeDocument(doc.Name)
    log("FreeCAD document closed.")
except Exception as e:
    log(f"Warning: Could not close FreeCAD document: {e}")

log("FreeCAD export process finished.")
sys.exit(0)
