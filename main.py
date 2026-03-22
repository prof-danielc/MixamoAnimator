"""Main entry point for MixamoAnimator."""

import argparse
import sys
import os
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow


def parse_args():
    """Parses command-line arguments for MixamoAnimator.

    Returns:
        argparse.Namespace: The parsed arguments.
    """
    parser = argparse.ArgumentParser(description="MixamoAnimator: Map Mixamo animations to FBX models.")
    parser.add_argument("--model_name", required=True, help="The name of the FBX model file.")
    parser.add_argument("--animation_name", required=True, help="The name of the animation file.")
    return parser.parse_args()


def main():
    """Main function for MixamoAnimator."""
    args = parse_args()
    
    # Check if files exist
    if not os.path.exists(args.model_name):
        print(f"Error: Model file not found: {args.model_name}")
        sys.exit(1)
    if not os.path.exists(args.animation_name):
        print(f"Error: Animation file not found: {args.animation_name}")
        sys.exit(1)

    app = QApplication(sys.argv)
    
    try:
        window = MainWindow(args.model_name, args.animation_name)
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"An error occurred during application startup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
