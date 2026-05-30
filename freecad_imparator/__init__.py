"""
FreeCAD Imparator - Blender Addon
Author: gurkanerol
Email: gurkanerol@gmail.com

This Blender addon provides a robust, one-click solution for importing FreeCAD
(.fcstd) files directly into Blender. It preserves the exact assembly hierarchy,
perfectly maps FreeCAD's internal coordinates to Blender's Z-Up metric system,
cleans up generated triangles into smooth BMesh N-gons, and allows for quick
reloads of the FreeCAD geometry without losing the Blender scene setup.
"""

import os
import sys
import time
import tempfile
import subprocess
import bpy
from bpy.props import StringProperty, BoolProperty, FloatProperty, CollectionProperty, IntProperty, EnumProperty
from bpy.types import AddonPreferences, Operator, Panel, PropertyGroup
from bpy_extras.io_utils import ImportHelper

bl_info = {
    "name": "FreeCAD Imparator",
    "author": "gurkanerol (2026 Edition)",
    "version": (2026, 5, 35),
    "blender": (4, 2, 0),
    "description": "Robust import of FreeCAD (.fcstd) models with individual reload, deflection control, and deep purge.",
    "category": "Import-Export",
    "location": "File > Import > FreeCAD (.fcstd) or Sidebar Tab 'FreeCAD'",
}

# --- UTILITIES ---

def get_default_freecad_path():
    """Determine a sensible default path for the FreeCAD Python/Cmd executable based on OS."""
    plat = sys.platform
    if plat.startswith("darwin"):
        # macOS typical bundle path
        path = "/Applications/FreeCAD.app/Contents/Resources/bin/python"
        if os.path.exists(path):
            return path
        # Fallback to standard app location
        path_alt = "/Applications/FreeCAD.app/Contents/MacOS/FreeCAD"
        if os.path.exists(path_alt):
            return path_alt
    elif plat.startswith("win32"):
        # Windows typical installation paths
        common_paths = [
            r"C:\Program Files\FreeCAD\bin\python.exe",
            r"C:\Program Files\FreeCAD 0.22\bin\python.exe",
            r"C:\Program Files\FreeCAD 0.21\bin\python.exe",
            r"C:\Program Files\FreeCAD\bin\FreeCADCmd.exe",
        ]
        for p in common_paths:
            if os.path.exists(p):
                return p
    else:
        # Linux typical commands
        for cmd in ["freecadcmd", "python3"]:
            if shutil.which(cmd):
                return cmd
    return ""

def get_freecad_lib_path(freecad_path):
    """Derive the library directory where FreeCAD.so or FreeCAD.pyd resides."""
    if not freecad_path:
        return ""
    dirname = os.path.dirname(freecad_path)
    # macOS App Bundle structure: Contents/Resources/bin/python -> Contents/Resources/lib
    if "Resources/bin" in freecad_path:
        lib_path = os.path.join(os.path.dirname(dirname), "lib")
        if os.path.exists(lib_path):
            return lib_path
    # Windows/Linux structure: FreeCAD/bin/python.exe -> FreeCAD/lib
    lib_path = os.path.join(os.path.dirname(dirname), "lib")
    if os.path.exists(lib_path):
        return lib_path
    return ""

def import_obj_file(filepath):
    """Import an OBJ file into Blender, supporting modern and legacy APIs."""
    # Modern fast C++ importer (Blender 4.0+)
    if hasattr(bpy.ops.wm, "obj_import"):
        try:
            # We use Y-forward, Z-up to exactly match FreeCAD's native coordinate space
            bpy.ops.wm.obj_import(filepath=filepath, forward_axis='Y', up_axis='Z')
            return True
        except Exception as e:
            print(f"FreeCAD Imparator | Modern obj_import failed: {e}")

    # Legacy python-based importer
    if hasattr(bpy.ops.import_scene, "obj"):
        try:
            bpy.ops.import_scene.obj(filepath=filepath, axis_forward='Y', axis_up='Z')
            return True
        except Exception as e:
            print(f"FreeCAD Imparator | Legacy obj import failed: {e}")

    return False

def delete_import_collection(collection_name):
    """Recursively delete all objects and child collections inside a collection."""
    coll = bpy.data.collections.get(collection_name)
    if not coll:
        return

    # Gather all objects in this collection hierarchy
    obs_to_delete = list(coll.all_objects)
    for obj in obs_to_delete:
        try:
            bpy.data.objects.remove(obj, do_unlink=True)
        except Exception as e:
            print(f"FreeCAD Imparator | Error removing object {obj.name}: {e}")

    # Helper function to recursively delete child collections
    def purge_collections(c):
        for child in list(c.children):
            purge_collections(child)
            try:
                bpy.data.collections.remove(child)
            except Exception as e:
                print(f"FreeCAD Imparator | Error removing collection {child.name}: {e}")

    purge_collections(coll)

    # Finally, remove the main collection
    try:
        bpy.data.collections.remove(coll)
    except Exception as e:
        print(f"FreeCAD Imparator | Error removing root collection {coll.name}: {e}")

def clean_imported_meshes(objects):
    """Convert imported triangulated meshes into clean N-gon/BMesh geometry."""
    import bmesh
    for obj in objects:
        if obj.type == 'MESH':
            me = obj.data
            bm = bmesh.new()
            bm.from_mesh(me)
            
            # Recalculate normals to be consistent
            try:
                bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            except Exception as e:
                print(f"FreeCAD Imparator | Normal recalc failed: {e}")
                
            # Dissolve coplanar edges to recreate original flat polygons
            try:
                # angle_limit in radians: 0.0017 radians is approx 0.1 degrees
                bmesh.ops.dissolve_limit(
                    bm,
                    angle_limit=0.0017,
                    verts=bm.verts,
                    edges=bm.edges,
                    delimit={'MATERIAL'}
                )
            except Exception as e:
                print(f"FreeCAD Imparator | BMesh dissolve limit failed: {e}")
                
            bm.to_mesh(me)
            bm.free()
            me.update()

def reconstruct_hierarchy(json_path, imported_obs, import_coll):
    """Reconstruct the FreeCAD assembly hierarchy using Empty parent objects."""
    import json
    if not os.path.exists(json_path):
        return
        
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"FreeCAD Imparator | Error reading hierarchy JSON: {e}")
        return

    containers = data.get("containers", [])
    meshes = data.get("meshes", [])
    
    if not containers and not meshes:
        return

    # Create hidden collection if needed
    has_hidden = any(c.get("hidden", False) for c in containers) or any(m.get("hidden", False) for m in meshes)
    hidden_coll = None
    if has_hidden:
        hidden_coll = bpy.data.collections.new("Hidden Geometry")
        import_coll.children.link(hidden_coll)

    # Helper to clean mesh names (e.g. TempMesh_Box.001 -> Box)
    def get_clean_name(name):
        if name.startswith("TempMesh_"):
            name = name[len("TempMesh_"):]
        if "." in name:
            parts = name.split(".")
            if parts[-1].isdigit():
                name = ".".join(parts[:-1])
        return name

    # 1. Create Empties for all containers
    created_empties = {}
    for c in containers:
        c_name = c["name"]
        c_label = c["label"]
        pos = c["position"]
        rot = c["rotation"]
        
        # Create Empty
        empty = bpy.data.objects.new(c_label, None)
        empty.empty_display_type = 'PLAIN_AXES'
        empty.empty_display_size = 0.5 # Suitable for metric scaled import
        empty.rotation_mode = 'QUATERNION'
        
        # Apply global placement (keeping unit system consistent with meshes)
        empty.location = (pos[0], pos[1], pos[2])
        empty.rotation_quaternion = (rot[0], rot[1], rot[2], rot[3])
        
        # Store FreeCAD internal name for reference
        empty["freecad_name"] = c_name
        
        # Link to the collection
        is_hidden = c.get("hidden", False)
        target_coll = hidden_coll if (is_hidden and hidden_coll) else import_coll
        target_coll.objects.link(empty)
        created_empties[c_name] = empty

    # Force a scene update so that every Empty gets its matrix_world correctly evaluated before parenting
    bpy.context.view_layer.update()

    # 2. Establish hierarchy between containers
    for c in containers:
        c_name = c["name"]
        parent_name = c["parent_name"]
        if parent_name and parent_name in created_empties:
            empty = created_empties[c_name]
            parent_empty = created_empties[parent_name]
            
            # Parent it keeping global transform
            empty.parent = parent_empty
            empty.matrix_parent_inverse = parent_empty.matrix_world.inverted()

    # 3. Map imported mesh objects by their clean name
    mesh_map = {}
    for obj in imported_obs:
        if obj.type == 'MESH':
            clean_name = get_clean_name(obj.name)
            mesh_map[clean_name] = obj
            
            # Rename the Blender mesh object to its nice user Label from FreeCAD and apply colors
            for m in meshes:
                if m["name"] == clean_name:
                    obj.name = m["label"]
                    
                    is_hidden = m.get("hidden", False)
                    if is_hidden and hidden_coll:
                        if obj.name in import_coll.objects:
                            import_coll.objects.unlink(obj)
                        hidden_coll.objects.link(obj)
                    
                    # Apply Material Color and Transparency
                    color = m.get("color", [0.8, 0.8, 0.8])
                    transparency = m.get("transparency", 0.0)
                    mat_name = f"FC_Mat_{m['name']}"
                    mat = bpy.data.materials.get(mat_name)
                    if not mat:
                        mat = bpy.data.materials.new(name=mat_name)
                        mat.use_nodes = True
                        bsdf = mat.node_tree.nodes.get("Principled BSDF")
                        if bsdf:
                            bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
                            if transparency > 0.0:
                                if "Alpha" in bsdf.inputs:
                                    bsdf.inputs["Alpha"].default_value = 1.0 - transparency
                                if hasattr(mat, "blend_method"):
                                    mat.blend_method = 'BLEND'
                                if hasattr(mat, "shadow_method"):
                                    mat.shadow_method = 'HASHED'
                            else:
                                if "Alpha" in bsdf.inputs:
                                    bsdf.inputs["Alpha"].default_value = 1.0
                                if hasattr(mat, "blend_method"):
                                    mat.blend_method = 'OPAQUE'
                                if hasattr(mat, "shadow_method"):
                                    mat.shadow_method = 'OPAQUE'
                    
                    if len(obj.data.materials) == 0:
                        obj.data.materials.append(mat)
                    else:
                        obj.data.materials[0] = mat
                        
                    break
    # 4. Parent meshes to their containers
    for m in meshes:
        mesh_name = m["name"]
        parent_name = m["parent_name"]
        if parent_name and parent_name in created_empties:
            mesh_obj = mesh_map.get(mesh_name)
            if mesh_obj:
                parent_empty = created_empties[parent_name]
                
                # Parent it keeping global transform
                mesh_obj.parent = parent_empty
                mesh_obj.matrix_parent_inverse = parent_empty.matrix_world.inverted()
                
    # Final scene update
    bpy.context.view_layer.update()

# --- PROPERTY GROUP ---

class FreeCADImportItem(PropertyGroup):
    """Represents a single FreeCAD file imported into Blender."""
    name: StringProperty(name="Name", default="FreeCAD Model")
    filepath: StringProperty(name="Filepath", subtype='FILE_PATH')
    collection_name: StringProperty(name="Collection Name")
    import_time: StringProperty(name="Import Time")
    deflection: FloatProperty(name="Deflection", default=0.1, min=0.001, max=10.0, description="Tessellation linear deflection (mm)")
    scale: EnumProperty(
        name="Scale",
        description="Select the import scale mapping",
        items=[
            ("1.0", "1:1 (Raw/Huge)", "1 mm in FreeCAD = 1 m in Blender"),
            ("0.1", "1:10", "10x smaller"),
            ("0.02", "1:50", "50x smaller"),
            ("0.01", "1:100 (Centimeters)", "100x smaller"),
            ("0.001", "1:1000 (Real Metric)", "1 mm in FreeCAD = 0.001 m in Blender"),
        ],
        default="0.001"
    )
    clean_ngons: BoolProperty(name="Clean N-Gons", default=True, description="Dissolve coplanar triangles into clean N-gons")

# --- ADDON PREFERENCES ---

class FreeCADAddonPreferences(AddonPreferences):
    bl_idname = __name__

    freecad_path: StringProperty(
        name="FreeCAD Python Path",
        description="Path to FreeCAD's internal Python executable or FreeCADCmd binary",
        default=get_default_freecad_path(),
        subtype='FILE_PATH'
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="- System Configuration -", icon='SETTINGS')
        
        box = layout.box()
        box.prop(self, "freecad_path")
        
        lib_path = get_freecad_lib_path(self.freecad_path)
        if lib_path:
            box.label(text=f"Detected Library Directory: {lib_path}", icon='INFO')
        else:
            box.label(text="Could not auto-detect FreeCAD library directory. Make sure path is correct.", icon='ERROR')

        # Validity warning
        if not self.freecad_path or not os.path.exists(self.freecad_path):
            box.label(text="Warning: FreeCAD executable path is invalid or empty!", icon='ERROR')

# --- OPERATORS ---

class FCSTD_OT_import(Operator, ImportHelper):
    """Select and import a FreeCAD file (.fcstd)"""
    bl_idname = "import_scene.fcstd"
    bl_label = "Import FreeCAD"
    bl_options = {"REGISTER", "UNDO"}
    filename_ext = ".fcstd"

    filter_glob: StringProperty(
        default="*.fcstd",
        options={"HIDDEN"},
    )

    deflection: FloatProperty(
        name="Mesh Quality (Deflection)",
        description="Linear deflection value for triangulation. Smaller is higher quality",
        default=0.1,
        min=0.001,
        max=5.0,
        subtype='DISTANCE'
    )

    scale: EnumProperty(
        name="Scale",
        description="Select the import scale mapping",
        items=[
            ("1.0", "1:1 (Raw/Huge)", "1 mm in FreeCAD = 1 m in Blender"),
            ("0.1", "1:10", "10x smaller"),
            ("0.02", "1:50", "50x smaller"),
            ("0.01", "1:100 (Centimeters)", "100x smaller"),
            ("0.001", "1:1000 (Real Metric)", "1 mm in FreeCAD = 0.001 m in Blender"),
        ],
        default="0.001"
    )

    clean_ngons: BoolProperty(
        name="Clean N-Gons (BMesh)",
        description="Dissolve coplanar triangles into clean flat N-gons (BMesh)",
        default=True
    )

    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences
        freecad_bin = prefs.freecad_path
        
        if not freecad_bin or not os.path.exists(freecad_bin):
            self.report({'ERROR'}, "FreeCAD path is not configured. Please set it in addon preferences.")
            return {'CANCELLED'}

        lib_path = get_freecad_lib_path(freecad_bin)
        
        # Temp OBJ output file
        temp_dir = tempfile.gettempdir()
        temp_obj = os.path.join(temp_dir, f"fcstd_import_{int(time.time())}.obj")

        # Find the exporter script
        addon_dir = os.path.dirname(__file__)
        exporter_script = os.path.join(addon_dir, "fcstd_to_obj.py")

        if not os.path.exists(exporter_script):
            self.report({'ERROR'}, f"Exporter helper script not found at: {exporter_script}")
            return {'CANCELLED'}

        # Prepare subprocess call
        cmd = [
            freecad_bin,
            exporter_script,
            self.filepath,
            temp_obj,
            str(self.deflection),
            str(self.scale),
        ]
        if lib_path:
            cmd.append(lib_path)

        # Setup sandbox environment variables to prevent permission crashes
        env = os.environ.copy()
        env["FREECAD_USER_HOME"] = temp_dir
        env["FREECAD_USER_DATA"] = temp_dir
        env["FREECAD_USER_TEMP"] = temp_dir

        self.report({'INFO'}, "Running FreeCAD to process geometry...")
        print(f"FreeCAD Imparator | Spawning subprocess: {' '.join(cmd)}")
        
        try:
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                check=False
            )
            print("--- FreeCAD Subprocess Output ---")
            print(process.stdout)
            print("--- FreeCAD Subprocess Errors ---")
            print(process.stderr)
            
            if process.returncode != 0:
                err_msg = process.stderr.strip() if process.stderr else "Unknown error"
                self.report({'ERROR'}, f"FreeCAD export failed: {err_msg[:200]}")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to run FreeCAD: {e}")
            return {'CANCELLED'}

        if not os.path.exists(temp_obj) or os.path.getsize(temp_obj) == 0:
            self.report({'ERROR'}, "FreeCAD did not generate a valid OBJ file.")
            return {'CANCELLED'}

        # Track currently existing objects to isolate imported ones
        old_objects = set(bpy.data.objects.keys())
        
        # Perform OBJ import
        self.report({'INFO'}, "Importing geometry into Blender...")
        import_success = import_obj_file(temp_obj)
        
        # Clean up temporary file
        try:
            os.remove(temp_obj)
            mtl_file = temp_obj.replace(".obj", ".mtl")
            if os.path.exists(mtl_file):
                os.remove(mtl_file)
        except Exception as e:
            print(f"FreeCAD Imparator | Error deleting temp files: {e}")

        if not import_success:
            self.report({'ERROR'}, "Blender failed to import the generated OBJ file.")
            return {'CANCELLED'}

        # Find newly imported objects
        new_objects = set(bpy.data.objects.keys())
        imported_obs = [bpy.data.objects[name] for name in (new_objects - old_objects)]

        if not imported_obs:
            self.report({'WARNING'}, "Imported successfully, but no new 3D objects were found.")
            return {'FINISHED'}

        # Clean up triangulation (convert to clean N-gons / BMesh)
        if self.clean_ngons:
            self.report({'INFO'}, "Converting geometry to clean BMesh N-gons...")
            clean_imported_meshes(imported_obs)

        # Create collection setup
        filename = os.path.basename(self.filepath)
        coll_name = f"FCSTD - {filename.split('.')[0]}"
        
        # Ensure unique collection name
        counter = 1
        original_coll_name = coll_name
        while bpy.data.collections.get(coll_name):
            coll_name = f"{original_coll_name}.{counter:03d}"
            counter += 1

        # Parent main collection
        main_coll_name = "FreeCAD Imported Data"
        main_coll = bpy.data.collections.get(main_coll_name)
        if not main_coll:
            main_coll = bpy.data.collections.new(main_coll_name)
            context.scene.collection.children.link(main_coll)

        import_coll = bpy.data.collections.new(coll_name)
        main_coll.children.link(import_coll)

        # Move imported objects to new collection
        for obj in imported_obs:
            if obj.name not in import_coll.objects:
                import_coll.objects.link(obj)
            for col in list(obj.users_collection):
                if col != import_coll:
                    col.objects.unlink(obj)

        # Reconstruct assembly hierarchy
        json_path = temp_obj + ".json"
        if os.path.exists(json_path):
            self.report({'INFO'}, "Reconstructing FreeCAD assembly hierarchy...")
            reconstruct_hierarchy(json_path, imported_obs, import_coll)
            try:
                os.remove(json_path)
            except Exception as e:
                print(f"Error removing temp JSON: {e}")

        # Add item to freecad_imports list
        item = context.scene.freecad_imports.add()
        item.name = filename
        item.filepath = self.filepath
        item.collection_name = coll_name
        item.deflection = self.deflection
        item.scale = self.scale
        item.clean_ngons = self.clean_ngons
        item.import_time = time.strftime("%Y-%m-%d %H:%M:%S")

        # Auto-configure scene units to millimeters so values feel natural
        scene = context.scene
        if scene.unit_settings.system == 'NONE' or scene.unit_settings.length_unit == 'METERS':
            scene.unit_settings.system = 'METRIC'
            scene.unit_settings.length_unit = 'MILLIMETERS'
            scene.unit_settings.scale_length = 0.001
            self.report({'INFO'}, f"Scene units set to Millimeters (metric).")

        self.report({'INFO'}, f"Successfully imported: {filename}")
        return {'FINISHED'}

class FCSTD_OT_reload(Operator):
    """Reload and update a specific FreeCAD import."""
    bl_idname = "import_scene.fcstd_reload"
    bl_label = "Reload Import"
    bl_options = {"REGISTER", "UNDO"}

    import_index: IntProperty()

    def execute(self, context):
        imports = context.scene.freecad_imports
        if self.import_index < 0 or self.import_index >= len(imports):
            self.report({'ERROR'}, "Invalid import item selection.")
            return {'CANCELLED'}

        item = imports[self.import_index]
        filepath = item.filepath
        collection_name = item.collection_name
        deflection = item.deflection
        scale = getattr(item, "scale", "0.001")
        if isinstance(scale, float):
            scale = str(scale)

        if not os.path.exists(filepath):
            self.report({'ERROR'}, f"FreeCAD source file not found at: {filepath}")
            return {'CANCELLED'}

        prefs = context.preferences.addons[__name__].preferences
        freecad_bin = prefs.freecad_path
        if not freecad_bin or not os.path.exists(freecad_bin):
            self.report({'ERROR'}, "FreeCAD executable path is not configured correctly.")
            return {'CANCELLED'}

        lib_path = get_freecad_lib_path(freecad_bin)
        temp_dir = tempfile.gettempdir()
        temp_obj = os.path.join(temp_dir, f"fcstd_reload_{int(time.time())}.obj")

        addon_dir = os.path.dirname(__file__)
        exporter_script = os.path.join(addon_dir, "fcstd_to_obj.py")

        cmd = [
            freecad_bin,
            exporter_script,
            filepath,
            temp_obj,
            str(deflection),
            str(scale),
        ]
        if lib_path:
            cmd.append(lib_path)

        env = os.environ.copy()
        env["FREECAD_USER_HOME"] = temp_dir
        env["FREECAD_USER_DATA"] = temp_dir
        env["FREECAD_USER_TEMP"] = temp_dir

        self.report({'INFO'}, f"Exporting fresh geometry for: {item.name}...")
        
        try:
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                check=False
            )
            if process.returncode != 0:
                err_msg = process.stderr.strip() if process.stderr else "Unknown error"
                self.report({'ERROR'}, f"FreeCAD export failed: {err_msg[:200]}")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Subprocess error: {e}")
            return {'CANCELLED'}

        if not os.path.exists(temp_obj) or os.path.getsize(temp_obj) == 0:
            self.report({'ERROR'}, "FreeCAD failed to produce reload geometry.")
            return {'CANCELLED'}

        # --- UPDATE BLENDER SCENE ---
        # 1. Delete old objects in target collection
        coll = bpy.data.collections.get(collection_name)
        if coll:
            obs_to_delete = list(coll.all_objects)
            for obj in obs_to_delete:
                try:
                    bpy.data.objects.remove(obj, do_unlink=True)
                except Exception as e:
                    print(f"Error removing old object: {e}")
        else:
            # Recreate collection if missing
            coll = bpy.data.collections.new(collection_name)
            main_coll = bpy.data.collections.get("FreeCAD Imported Data")
            if not main_coll:
                main_coll = bpy.data.collections.new("FreeCAD Imported Data")
                context.scene.collection.children.link(main_coll)
            main_coll.children.link(coll)

        # 2. Track new objects during import
        old_objects = set(bpy.data.objects.keys())
        import_success = import_obj_file(temp_obj)

        # Cleanup temp file
        try:
            os.remove(temp_obj)
            mtl_file = temp_obj.replace(".obj", ".mtl")
            if os.path.exists(mtl_file):
                os.remove(mtl_file)
        except Exception as e:
            print(f"Error deleting temp files: {e}")

        if not import_success:
            self.report({'ERROR'}, "Failed to import reload geometry into Blender.")
            return {'CANCELLED'}

        new_objects = set(bpy.data.objects.keys())
        imported_obs = [bpy.data.objects[name] for name in (new_objects - old_objects)]

        # Clean up triangulation (convert to clean N-gons / BMesh)
        if item.clean_ngons:
            self.report({'INFO'}, "Converting geometry to clean BMesh N-gons...")
            clean_imported_meshes(imported_obs)

        # 3. Move newly imported objects to the target collection
        for obj in imported_obs:
            if obj.name not in coll.objects:
                coll.objects.link(obj)
            for col in list(obj.users_collection):
                if col != coll:
                    col.objects.unlink(obj)

        # Reconstruct assembly hierarchy
        json_path = temp_obj + ".json"
        if os.path.exists(json_path):
            self.report({'INFO'}, "Reconstructing FreeCAD assembly hierarchy...")
            reconstruct_hierarchy(json_path, imported_obs, coll)
            try:
                os.remove(json_path)
            except Exception as e:
                print(f"Error removing temp JSON: {e}")

        # Update metadata timestamp
        item.import_time = time.strftime("%Y-%m-%d %H:%M:%S")

        self.report({'INFO'}, f"Successfully reloaded: {item.name}")
        return {'FINISHED'}

class FCSTD_OT_delete(Operator):
    """Delete a FreeCAD import, purging its collection and objects."""
    bl_idname = "import_scene.fcstd_delete"
    bl_label = "Delete Import"
    bl_options = {"REGISTER", "UNDO"}

    import_index: IntProperty()

    def execute(self, context):
        imports = context.scene.freecad_imports
        if self.import_index < 0 or self.import_index >= len(imports):
            self.report({'ERROR'}, "Invalid delete index.")
            return {'CANCELLED'}

        item = imports[self.import_index]
        
        # Recursively delete the import's collection and objects
        delete_import_collection(item.collection_name)
        
        # Remove from tracking list
        name = item.name
        imports.remove(self.import_index)
        
        self.report({'INFO'}, f"Deleted import and purged hierarchy for: {name}")
        return {'FINISHED'}

class FCSTD_OT_select_objects(Operator):
    """Select all objects belonging to this FreeCAD import."""
    bl_idname = "import_scene.fcstd_select"
    bl_label = "Select Objects"
    bl_options = {"REGISTER", "UNDO"}

    import_index: IntProperty()

    def execute(self, context):
        imports = context.scene.freecad_imports
        if self.import_index < 0 or self.import_index >= len(imports):
            return {'CANCELLED'}

        item = imports[self.import_index]
        coll = bpy.data.collections.get(item.collection_name)
        
        if not coll:
            self.report({'WARNING'}, f"Collection '{item.collection_name}' not found.")
            return {'CANCELLED'}

        # Deselect all first
        bpy.ops.object.select_all(action='DESELECT')
        
        # Select all objects in the collection
        count = 0
        for obj in coll.all_objects:
            obj.select_set(True)
            count += 1

        if count > 0:
            # Set active object to first found mesh
            for obj in coll.all_objects:
                context.view_layer.objects.active = obj
                break
            self.report({'INFO'}, f"Selected {count} objects belonging to '{item.name}'.")
        else:
            self.report({'WARNING'}, "No objects found in this import to select.")
            
        return {'FINISHED'}

class FCSTD_OT_deep_purge(Operator):
    """Purge all unused data blocks recursively."""
    bl_idname = "import_scene.fcstd_deep_purge"
    bl_label = "Purge Unused Data"
    bl_description = "Recursively clean up orphaned meshes, materials, and textures"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        purged_total = 0
        for i in range(3):
            # Run orphans purge three times to resolve recursive references
            res = bpy.ops.outliner.orphans_purge(
                do_local_ids=True,
                do_linked_ids=True,
                do_recursive=True
            )
            if 'FINISHED' in res:
                purged_total += 1
        self.report({'INFO'}, "Deep purge completed successfully.")
        return {'FINISHED'}

class FCSTD_OT_smooth(Operator):
    """Set Shade Smooth by Angle for meshes."""
    bl_idname = "import_scene.fcstd_smooth"
    bl_label = "Smooth"
    bl_description = "Shade smooth by angle (Auto Smooth) all meshes in the scene or selected"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # Find meshes to smooth
        meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        # If nothing is selected, smooth all meshes in all imported FreeCAD collections
        if not meshes:
            for item in context.scene.freecad_imports:
                coll = bpy.data.collections.get(item.collection_name)
                if coll:
                    for obj in coll.all_objects:
                        if obj.type == 'MESH' and obj not in meshes:
                            meshes.append(obj)

        if not meshes:
            self.report({'WARNING'}, "No meshes found to smooth. Please select meshes or import a model first.")
            return {'CANCELLED'}

        # Store selection to restore later
        active_obj = context.active_object
        old_selected = list(context.selected_objects)

        # Deselect all
        bpy.ops.object.select_all(action='DESELECT')

        count = 0
        for obj in meshes:
            obj.select_set(True)
            context.view_layer.objects.active = obj
            
            # Apply shade smooth by angle
            try:
                bpy.ops.object.shade_smooth_by_angle()
                count += 1
            except Exception:
                try:
                    bpy.ops.object.shade_smooth()
                    obj.data.use_auto_smooth = True
                    obj.data.auto_smooth_angle = 0.523599 # 30 deg
                    count += 1
                except Exception:
                    pass

        # Restore selection
        bpy.ops.object.select_all(action='DESELECT')
        for obj in old_selected:
            try:
                obj.select_set(True)
            except:
                pass
        context.view_layer.objects.active = active_obj

        self.report({'INFO'}, f"Applied Auto Smooth to {count} objects.")
        return {'FINISHED'}

# --- UI PANEL ---

class FCSTD_PT_panel(Panel):
    """Sidebar Panel for FreeCAD Imparator."""
    bl_label = "FreeCAD Imparator"
    bl_idname = "FCSTD_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FreeCAD'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        imports = scene.freecad_imports

        # Warning if path is invalid
        prefs = context.preferences.addons[__name__].preferences
        fc_bin = prefs.freecad_path
        if not fc_bin or not os.path.exists(fc_bin):
            box = layout.box()
            box.alert = True
            box.label(text="FreeCAD path invalid!", icon='ERROR')
            box.label(text="Please configure in Addon Preferences.")
            return

        # Import main button (matching image styling)
        row_import = layout.row()
        row_import.scale_y = 1.8
        row_import.operator("import_scene.fcstd", text="IMPORT NEW FCSTD", icon='IMPORT')

        layout.separator()
        
        # Tool row (Smooth & Purge side-by-side matching image inside a box)
        box_tools = layout.box()
        row_tools = box_tools.row(align=True)
        row_tools.scale_y = 1.4
        row_tools.operator("import_scene.fcstd_smooth", text="Smooth", icon='MOD_BEVEL')
        row_tools.operator("import_scene.fcstd_deep_purge", text="Purge", icon='TRASH')

        layout.separator()
        layout.separator()

        # Section header
        layout.label(text="Imported FreeCAD Files:", icon='CUBE')

        # List of imports
        if len(imports) > 0:
            for idx, item in enumerate(imports):
                box = layout.box()
                
                # Header row with name and delete button
                row = box.row(align=True)
                row.label(text=item.name, icon='FILE_3D')
                
                # Check if collection still exists in data
                coll_exists = bpy.data.collections.get(item.collection_name) is not None
                if not coll_exists:
                    row.label(text="[Missing Coll]", icon='WARNING')
                
                op_del = row.operator("import_scene.fcstd_delete", text="", icon='TRASH')
                op_del.import_index = idx
                
                # File path tooltip
                box.label(text=f"Time: {item.import_time}", icon='TIME')
                
                # Controls box for reload options
                ctrl_box = box.column(align=True)
                
                # Top Row: BMesh and Actions
                row_top = ctrl_box.row(align=True)
                row_top.prop(item, "clean_ngons", text="BMesh")
                op_sel = row_top.operator("import_scene.fcstd_select", text="", icon='RESTRICT_SELECT_OFF')
                op_sel.import_index = idx
                op_rel = row_top.operator("import_scene.fcstd_reload", text="", icon='FILE_REFRESH')
                op_rel.import_index = idx
                
                # Bottom Row: Quality and Scale
                row_bot = ctrl_box.row(align=True)
                row_bot.prop(item, "deflection", text="Quality")
                row_bot.prop(item, "scale", text="Scale")
        else:
            # Match the empty state image
            layout.label(text="No FCSTD files in scene.", icon='INFO')

# --- MENU INTEGRATION ---

def menu_func_import(self, context):
    self.layout.operator(FCSTD_OT_import.bl_idname, text="FreeCAD (.fcstd)", icon='FILE_3D')


# --- REGISTRATION ---

classes = (
    FreeCADImportItem,
    FreeCADAddonPreferences,
    FCSTD_OT_import,
    FCSTD_OT_reload,
    FCSTD_OT_delete,
    FCSTD_OT_select_objects,
    FCSTD_OT_deep_purge,
    FCSTD_OT_smooth,
    FCSTD_PT_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.Scene.freecad_imports = CollectionProperty(type=FreeCADImportItem)
    bpy.types.Scene.freecad_import_index = IntProperty(name="Active Import Index", default=0)

def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    
    # Clean up scene properties
    del bpy.types.Scene.freecad_imports
    del bpy.types.Scene.freecad_import_index

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
