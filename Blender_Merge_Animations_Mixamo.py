'''
Blender script to merge multiple Mixamo FBX animations into a single GLB file with NLA tracks.
- Place all your Mixamo FBX files in the specified FBX_FOLDER.
- The script imports a master T-pose skeleton, then iteratively imports each animation FBX,
extracts the action, and pushes it into the master armature's NLA stack.
- It also includes a function to fix missing textures by searching the specified TEX_FOLDER.
- Finally, it exports the combined result as a GLB file with all animations intact.


USAGE:
1. Update the FBX_FOLDER, TEX_FOLDER, MASTER_FILE, and EXPORT_FILE variables as
    needed.
'''


import bpy
import os
import builtins
from collections import defaultdict
import re

# =============================
# CONFIG
# =============================
FBX_FOLDER = r"C:\Users\Daniel\Downloads\MixamoAnimator\downloads"
TEX_FOLDER = r"C:\Users\Daniel\Downloads\MixamoAnimator\downloads\textures"
MASTER_FILE = "Tpose.fbx"
EXPORT_FILE = "MergedAnimations.glb"

# =============================
# FIX MISSING TEXTURES
# Equivalent to: File > External Data > Find Missing Files
# Searches the FBX folder and all subfolders for any textures
# that Blender couldn't locate automatically on import.
# =============================
def find_missing_textures(search_folder):
    # ── Build file map: lowercase filename → absolute path ──
    file_map = {}
    for root, dirs, files in os.walk(search_folder):
        for fname in files:
            file_map[fname.lower()] = os.path.join(root, fname)

    log(f"Files on disk: {len(file_map)}")

    # ── Collect all missing images ──
    missing = [
        img for img in bpy.data.images
        if img.source == 'FILE' and not img.has_data
    ]

    if not missing:
        log("No missing textures")
        return

    log(f"Missing: {len(missing)}")

    def resolve(img):
        # Strip Blender duplicate suffix: "name.tga.003" → "name.tga"
        clean = re.sub(r'\.\d{3}$', '', img.name).lower()

        return (
            file_map.get(clean)           or   # exact:          name.tga
            file_map.get(clean + '.png')  or   # double ext:     name.tga.png ← YOUR CASE
            file_map.get(clean + '.jpg')  or   # double ext jpg: name.tga.jpg
            file_map.get(clean + '.jpeg') or
            None
        )

    # ── Fix + deduplicate in one pass ──
    # Keep track of canonical image per clean name
    canonical = {}   # clean_name → image datablock

    for img in sorted(missing, key=lambda x: x.name):
        clean = re.sub(r'\.\d{3}$', '', img.name)

        # If canonical already resolved, just remap this duplicate
        if clean in canonical:
            _remap_material_nodes(img, canonical[clean])
            if img.users == 0:
                bpy.data.images.remove(img)
            continue

        found = resolve(img)
        if found:
            img.filepath = found
            img.reload()
            canonical[clean] = img
            log(f"  FIXED: '{img.name}'  →  {found}")
        else:
            log(f"  NOT FOUND: '{img.name}'")

    log(f"Resolved: {len(canonical)} unique textures")


def _remap_material_nodes(old_img, new_img):
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image == old_img:
                node.image = new_img
        
# =============================
# LOGGER
# =============================
def log(*args):
    builtins.print("[MERGE]", *args)

# =============================
# PATCH BLENDER FBX LIGHT BUG
# =============================
def patch_fbx_light_bug():
    try:
        from io_scene_fbx import import_fbx
        original = import_fbx.blen_read_light
        def patched(*args, **kwargs):
            try:
                return original(*args, **kwargs)
            except:
                return None
        import_fbx.blen_read_light = patched
        log("FBX importer patched")
    except Exception as e:
        log("Patch failed:", e)

patch_fbx_light_bug()

# =============================
# NAME EXTRACTION
# =============================
def extract_base_name(filename):
    """Extract NAME from 'NAME_NUMBER_TEXT.fbx' pattern."""
    stem = os.path.splitext(filename)[0]   # strip .fbx
    parts = stem.split("_")
    return parts[0] if parts else stem     # take everything before first underscore

def build_action_name(base_name, counts):
    """Return 'Name' for the first occurrence, 'Name 2', 'Name 3'... for subsequent ones."""
    counts[base_name] += 1
    n = counts[base_name]
    return base_name if n == 1 else f"{base_name} {n}"

# =============================
# IMPORT HELPER
# =============================
def import_fbx(filepath):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=filepath)
    after = set(bpy.context.scene.objects)
    return list(after - before)

# =============================
# CLEAN SCENE
# =============================
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
log("Scene cleared")

# =============================
# IMPORT MASTER SKELETON
# =============================
master_path = os.path.join(FBX_FOLDER, MASTER_FILE)
objs = import_fbx(master_path)
master_armature = next(o for o in objs if o.type == "ARMATURE")
master_meshes = [o for o in objs if o.type == "MESH"]
log("Master armature:", master_armature.name)

master_armature.animation_data_create()

import bpy
import os

print("\n" + "="*60)
print("IMAGE DIAGNOSTIC")
print("="*60)

for img in bpy.data.images:
    abs_path = bpy.path.abspath(img.filepath)
    print(f"\nName      : {img.name}")
    print(f"Source    : {img.source}")
    print(f"has_data  : {img.has_data}")
    print(f"filepath  : {img.filepath}")
    print(f"abs_path  : {abs_path}")
    print(f"file exists on disk : {os.path.isfile(abs_path)}")
    print(f"packed    : {img.packed_file is not None}")

# Fix missing textures in the model
find_missing_textures(TEX_FOLDER) 

print("\n" + "="*60)
print("IMAGE DIAGNOSTIC")
print("="*60)

for img in bpy.data.images:
    abs_path = bpy.path.abspath(img.filepath)
    print(f"\nName      : {img.name}")
    print(f"Source    : {img.source}")
    print(f"has_data  : {img.has_data}")
    print(f"filepath  : {img.filepath}")
    print(f"abs_path  : {abs_path}")
    print(f"file exists on disk : {os.path.isfile(abs_path)}")
    print(f"packed    : {img.packed_file is not None}")

# =============================
# PROCESS ANIMATIONS
# =============================
name_counts = defaultdict(int)  # tracks how many times each base name has been seen

for file in sorted(os.listdir(FBX_FOLDER)):
    if not file.endswith(".fbx"):
        continue
    if file == MASTER_FILE:
        continue

    filepath = os.path.join(FBX_FOLDER, file)
    log("Importing:", file)
    imported = import_fbx(filepath)

    anim_armature = next(
        (o for o in imported if o.type == "ARMATURE"), None
    )

    if anim_armature is None:
        log("No armature found in:", file)
        continue
    if not anim_armature.animation_data:
        log("No animation data in:", file)
        continue

    action = anim_armature.animation_data.action
    if action is None:
        log("No action in:", file)
        continue

    # Build a clean, deduplicated action name
    base_name = extract_base_name(file)
    action_name = build_action_name(base_name, name_counts)
    action.name = action_name
    log("Pushing action into NLA:", action_name)

    master_armature.animation_data.action = action

    nla_tracks = master_armature.animation_data.nla_tracks
    track = nla_tracks.new()
    track.name = action_name
    strip = track.strips.new(
        action_name,
        int(action.frame_range[0]),
        action
    )
    master_armature.animation_data.action = None

    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)

log("All animations merged into NLA")

# =============================
# EXPORT
# =============================
export_path = os.path.join(FBX_FOLDER, EXPORT_FILE)
bpy.ops.object.select_all(action='DESELECT')
master_armature.select_set(True)
for mesh in master_meshes:
    mesh.select_set(True)
bpy.context.view_layer.objects.active = master_armature

# fix textures (again) before exporting
find_missing_textures(TEX_FOLDER)

bpy.ops.export_scene.gltf(
    filepath              = export_path,
    use_selection         = True,
    export_format         = 'GLB',
    export_animations     = True,
    export_nla_strips     = True,
    export_animation_mode = 'NLA_TRACKS',
    export_optimize_animation_size = False,
)

'''
bpy.ops.export_scene.fbx(
    filepath=export_path,
    use_selection=True,
    bake_anim=True,
    bake_anim_use_all_actions=True
)
'''

log("Exported:", export_path)