"""Main entry point for MixamoAnimator."""

import argparse
import sys
import os
import glob
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow


def resolve_animation_path(animations_dir, animation_name):
    """Resolves a semantic animation name to a file path.

    Args:
        animations_dir (str): The directory to search for animations.
        animation_name (str): The semantic name of the animation (e.g., 'walk').

    Returns:
        str: The full path to the animation file if found, None otherwise.
    """
    if not os.path.exists(animations_dir):
        return None

    # Search for common 3D formats
    extensions = ['*.fbx', '*.obj', '*.glb', '*.gltf']
    for ext in extensions:
        # Exact match (case-insensitive)
        pattern = os.path.join(animations_dir, f"{animation_name}{ext[1:]}")
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
        
        # Case-insensitive search using glob if exact match fails
        all_files = glob.glob(os.path.join(animations_dir, ext))
        for file in all_files:
            base = os.path.splitext(os.path.basename(file))[0].lower()
            if base == animation_name.lower():
                return file
                
    return None


def parse_args():
    """Parses command-line arguments for MixamoAnimator.

    Returns:
        argparse.Namespace: The parsed arguments.
    """
    parser = argparse.ArgumentParser(description="MixamoAnimator: Map Mixamo animations to 3D models.")
    parser.add_argument("--model_name", required=True, help="The name or path of the 3D model file (.fbx, .glb, .gltf).")
    parser.add_argument("--animation_name", required=True, help="The semantic name of the animation (e.g., 'walk', 'run').")
    parser.add_argument("--animations_dir", default="./animations", help="The directory where Mixamo animations are stored.")
    return parser.parse_args()


def main():
    """Main function for MixamoAnimator."""
    args = parse_args()
    
    # Check if model exists
    model_path = args.model_name
    if not os.path.exists(model_path):
        # Try looking in project root if it's just a name
        if os.path.exists(os.path.join(".", args.model_name)):
            model_path = os.path.join(".", args.model_name)
        else:
            print(f"Error: Model file not found: {args.model_name}")
            sys.exit(1)

    # Resolve animation name to path
    animation_path = resolve_animation_path(args.animations_dir, args.animation_name)
    if not animation_path:
        # Fallback: check if animation_name is actually a path that exists
        if os.path.exists(args.animation_name):
            animation_path = args.animation_name
        else:
            print(f"Error: Could not resolve animation '{args.animation_name}' in '{args.animations_dir}'.")
            if os.path.exists(args.animations_dir):
                available = [os.path.splitext(f)[0] for f in os.listdir(args.animations_dir) if f.lower().endswith('.fbx')]
                if available:
                    print(f"Available animations: {', '.join(available)}")
            sys.exit(1)

    print(f"Loading model: {model_path}")
    print(f"Loading animation: {animation_path}")

    app = QApplication(sys.argv)
    
    try:
        window = MainWindow(model_path, animation_path)
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"An error occurred during application startup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
