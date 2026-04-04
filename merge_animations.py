"""
merge_animations.py
====================
Merges multiple Mixamo FBX animation files onto a single master skeleton,
fixes missing textures, and exports the result as a GLB file with one
named clip per NLA track.

Runs via Blender in background (headless) mode — no bpy pip package needed.

Requirements:
    - Blender 3.x or 4.x installed on your machine

Usage:
    python merge_animations.py
    python merge_animations.py --folder "C:/path/to/fbx" --tex "C:/path/to/textures" --master Tpose.fbx --save-as gltf --output Out.glb
"""

import os
import sys
import subprocess
import tempfile
import argparse
from pathlib import Path

# ============================================================
# CONFIG  —  edit these or use the CLI flags below
# ============================================================
DEFAULT_FBX_FOLDER  = r"C:\Users\Daniel\Downloads\MixamoAnimator\downloads"
DEFAULT_TEX_FOLDER  = r"C:\Users\Daniel\Downloads\MixamoAnimator\downloads\textures"
DEFAULT_MASTER_FILE = "Tpose.fbx"
DEFAULT_EXPORT_FILES = {
    "gltf": "MergedAnimations.glb",
    "fbx": "MergedAnimations.fbx",
    "save_as_mainfile": "MergedAnimations.blend",
}

# Common Blender install locations (checked in order).
# Add your own path at the top if Blender lives somewhere else.
BLENDER_SEARCH_PATHS = [
    # Windows
    r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
    # macOS
    "/Applications/Blender.app/Contents/MacOS/Blender",
    # Linux
    "/usr/bin/blender",
    "/usr/local/bin/blender",
    "/snap/bin/blender",
]


def find_latest_blender_install() -> str | None:
    """Return the newest Blender executable from common install roots."""
    install_roots = [
        Path(r"C:\Program Files\Blender Foundation"),
        Path(r"C:\Program Files"),
    ]
    blender_dirs = []

    for root in install_roots:
        if not root.is_dir():
            continue
        for child in root.iterdir():
            if not child.is_dir() or not child.name.lower().startswith("blender"):
                continue
            exe_path = child / "blender.exe"
            if exe_path.is_file():
                blender_dirs.append((child.name.lower(), str(exe_path)))

    if not blender_dirs:
        return None

    blender_dirs.sort(reverse=True)
    return blender_dirs[0][1]

# ============================================================
# THE BLENDER SCRIPT (embedded as a string, written to a
# temporary file and executed by Blender in --background mode)
# ============================================================
BLENDER_SCRIPT = r'''
import bpy
import os
import re
import sys
import builtins
from collections import defaultdict

# ── Args injected by the launcher via "--" separator ─────────
argv      = sys.argv
separator = argv.index("--") + 1
fbx_folder  = argv[separator]
tex_folder  = argv[separator + 1]
master_file = argv[separator + 2]
export_file = argv[separator + 3]
save_as     = argv[separator + 4].lower()

master_path = os.path.join(fbx_folder, master_file)
export_path = os.path.join(fbx_folder, export_file)

# ── Logger ────────────────────────────────────────────────────
def log(*args):
    builtins.print("[MERGE]", *args)

# ── Patch Blender FBX light bug ───────────────────────────────
def patch_fbx_light_bug():
    try:
        from io_scene_fbx import import_fbx
        original = import_fbx.blen_read_light
        def patched(*args, **kwargs):
            try:
                return original(*args, **kwargs)
            except Exception:
                return None
        import_fbx.blen_read_light = patched
        log("FBX importer patched")
    except Exception as e:
        log("Patch skipped:", e)

patch_fbx_light_bug()

# ── Texture fixing ────────────────────────────────────────────
def _build_file_map(search_folder):
    file_map = {}
    for root, _, files in os.walk(search_folder):
        for fname in files:
            file_map[fname.lower()] = os.path.join(root, fname)
    return file_map

def _resolve_image(img, file_map):
    clean = re.sub(r'\.\d{3}$', '', img.name).lower()
    return (
        file_map.get(clean)            or
        file_map.get(clean + '.png')   or
        file_map.get(clean + '.jpg')   or
        file_map.get(clean + '.jpeg')  or
        None
    )

def _remap_material_nodes(old_img, new_img):
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image == old_img:
                node.image = new_img

def find_missing_textures(search_folder):
    file_map = _build_file_map(search_folder)
    log(f"Texture search: {len(file_map)} files found under '{search_folder}'")

    missing = [
        img for img in bpy.data.images
        if img.source == 'FILE' and not img.has_data
    ]

    if not missing:
        log("No missing textures — nothing to fix")
        return

    log(f"Missing textures: {len(missing)}")

    canonical = {}

    for img in sorted(missing, key=lambda x: x.name):
        clean = re.sub(r'\.\d{3}$', '', img.name)

        if clean in canonical:
            _remap_material_nodes(img, canonical[clean])
            if img.users == 0:
                bpy.data.images.remove(img)
            continue

        found = _resolve_image(img, file_map)
        if found:
            img.filepath = found
            img.reload()
            canonical[clean] = img
            log(f"  FIXED   : '{img.name}'  →  {found}")
        else:
            log(f"  MISSING : '{img.name}' — not found under search folder")

    log(f"Resolved: {len(canonical)} unique texture(s)")

def diagnose_images():
    print("\n" + "=" * 60)
    print("IMAGE DIAGNOSTIC")
    print("=" * 60)
    for img in bpy.data.images:
        abs_path = bpy.path.abspath(img.filepath)
        print(
            f"\n  Name      : {img.name}\n"
            f"  Source    : {img.source}\n"
            f"  has_data  : {img.has_data}\n"
            f"  filepath  : {img.filepath}\n"
            f"  abs_path  : {abs_path}\n"
            f"  on disk   : {os.path.isfile(abs_path)}\n"
            f"  packed    : {img.packed_file is not None}"
        )
    print("=" * 60 + "\n")

# ── Name helpers ──────────────────────────────────────────────
def extract_base_name(filename):
    stem  = os.path.splitext(filename)[0]
    parts = stem.split("_")
    return parts[0] if parts else stem

def build_action_name(base_name, counts):
    counts[base_name] += 1
    n = counts[base_name]
    return base_name if n == 1 else f"{base_name} {n}"

# ── Import helper ─────────────────────────────────────────────
def import_fbx(filepath):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=filepath)
    after  = set(bpy.context.scene.objects)
    return list(after - before)

# ── Clear scene ───────────────────────────────────────────────
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete()
log("Scene cleared")

# ── Import master skeleton ────────────────────────────────────
objs = import_fbx(master_path)
master_armature = next(o for o in objs if o.type == "ARMATURE")
master_meshes   = [o for o in objs if o.type == "MESH"]
log("Master armature:", master_armature.name)
master_armature.animation_data_create()

# ── Fix textures after master import ─────────────────────────
diagnose_images()
find_missing_textures(tex_folder)
diagnose_images()

# ── Process each animation FBX ────────────────────────────────
name_counts = defaultdict(int)

for file in sorted(os.listdir(fbx_folder)):
    if not file.endswith(".fbx"):
        continue
    if file == master_file:
        continue

    filepath = os.path.join(fbx_folder, file)
    log("Importing:", file)
    imported = import_fbx(filepath)

    anim_armature = next((o for o in imported if o.type == "ARMATURE"), None)

    if anim_armature is None:
        log("  ✗ No armature found — skipping")
        continue
    if not anim_armature.animation_data:
        log("  ✗ No animation data — skipping")
        continue

    action = anim_armature.animation_data.action
    if action is None:
        log("  ✗ No action — skipping")
        continue

    base_name   = extract_base_name(file)
    action_name = build_action_name(base_name, name_counts)
    action.name = action_name
    log("  ✓ Pushing into NLA as:", action_name)

    master_armature.animation_data.action = action

    nla_tracks = master_armature.animation_data.nla_tracks
    track       = nla_tracks.new()
    track.name  = action_name
    track.strips.new(action_name, int(action.frame_range[0]), action)

    master_armature.animation_data.action = None

    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)

log("All animations merged into NLA")

# ── Fix textures again before export ─────────────────────────
find_missing_textures(tex_folder)

# ── Export ────────────────────────────────────────────────────
bpy.ops.object.select_all(action="DESELECT")
master_armature.select_set(True)
for mesh in master_meshes:
    mesh.select_set(True)
bpy.context.view_layer.objects.active = master_armature

if save_as == "gltf":
    bpy.ops.export_scene.gltf(
        filepath                       = export_path,
        use_selection                  = True,
        export_format                  = "GLB",
        export_animations              = True,
        export_nla_strips              = True,
        export_animation_mode          = "NLA_TRACKS",
        export_optimize_animation_size = False,
    )
elif save_as == "fbx":
    bpy.ops.export_scene.fbx(
        filepath=export_path,
        use_selection=True,
        bake_anim=True,
        bake_anim_use_all_actions=True,
    )
elif save_as == "save_as_mainfile":
    bpy.ops.wm.save_as_mainfile(filepath=export_path)
else:
    raise ValueError(f"Unsupported save mode: {save_as}")

log("Exported:", export_path)
'''

# ============================================================
# HELPERS
# ============================================================

def find_blender() -> str:
    """Return the path to the Blender executable, or raise."""
    # 1. Honour a BLENDER_PATH environment variable if set
    env = os.environ.get("BLENDER_PATH")
    if env and os.path.isfile(env):
        return env

    # 2. Prefer the newest Blender installation in standard locations
    latest_install = find_latest_blender_install()
    if latest_install:
        return latest_install

    # 3. Try well-known install paths
    for path in BLENDER_SEARCH_PATHS:
        if os.path.isfile(path):
            return path

    # 4. Try PATH (works on Linux/macOS when installed via package manager)
    for candidate in ("blender", "blender3", "blender4"):
        result = subprocess.run(
            ["where" if sys.platform == "win32" else "which", candidate],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            found = result.stdout.strip().splitlines()[0]
            if os.path.isfile(found):
                return found

    raise FileNotFoundError(
        "Blender executable not found.\n"
        "Either add it to PATH, set the BLENDER_PATH environment variable,\n"
        "or add its location to BLENDER_SEARCH_PATHS at the top of this script."
    )


def run_merge(
    fbx_folder: str,
    tex_folder: str,
    master_file: str,
    export_file: str,
    save_as: str,
):
    blender_exe = find_blender()
    print(f"[LAUNCHER] Using Blender : {blender_exe}")
    print(f"[LAUNCHER] FBX folder   : {fbx_folder}")
    print(f"[LAUNCHER] Tex folder   : {tex_folder}")
    print(f"[LAUNCHER] Master file  : {master_file}")
    print(f"[LAUNCHER] Export file  : {export_file}")
    print(f"[LAUNCHER] Save mode    : {save_as}")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(BLENDER_SCRIPT)
        tmp_path = tmp.name

    try:
        cmd = [
            blender_exe,
            "--background",       # no UI
            "--python", tmp_path, # our embedded script
            "--",                 # everything after this is passed to the script
            fbx_folder,
            tex_folder,
            master_file,
            export_file,
            save_as,
        ]

        print("[LAUNCHER] Running Blender in background mode …\n")
        result = subprocess.run(cmd, text=True)

        if result.returncode != 0:
            print(f"\n[LAUNCHER] Blender exited with code {result.returncode}.")
            sys.exit(result.returncode)
        else:
            export_path = os.path.join(fbx_folder, export_file)
            print(f"\n[LAUNCHER] Done! Output: {export_path}")
    finally:
        os.unlink(tmp_path)


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge Mixamo FBX animations and export them from Blender."
    )
    parser.add_argument(
        "--folder",
        default=DEFAULT_FBX_FOLDER,
        help="Folder containing all FBX files",
    )
    parser.add_argument(
        "--tex",
        default=DEFAULT_TEX_FOLDER,
        help="Folder to search for missing textures (searched recursively)",
    )
    parser.add_argument(
        "--master",
        default=DEFAULT_MASTER_FILE,
        help="Master T-pose FBX filename (default: Tpose.fbx)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output filename (default depends on --save-as)",
    )
    parser.add_argument(
        "--save-as",
        choices=tuple(DEFAULT_EXPORT_FILES),
        default="gltf",
        help="Blender export mode: gltf, fbx, or save_as_mainfile (default: gltf)",
    )
    args = parser.parse_args()

    export_file = args.output or DEFAULT_EXPORT_FILES[args.save_as]

    run_merge(
        fbx_folder  = args.folder,
        tex_folder  = args.tex,
        master_file = args.master,
        export_file = export_file,
        save_as     = args.save_as,
    )
