import trimesh
import numpy as np
import os
from typing import Dict, Any, Optional, Tuple

# Dependency checks
FBX_SDK_AVAILABLE = False
try:
    import fbx
    FBX_SDK_AVAILABLE = True
except:
    pass

ASSIMP_AVAILABLE = False
try:
    import pyassimp
    from pyassimp import helper
    helper.search_library()
    ASSIMP_AVAILABLE = True
except:
    pass

class DependencyError(Exception):
    """Exception raised when a required environment dependency is missing."""
    pass

class FBXLoader:
    """
    Loader for FBX models using trimesh.
    Note: FBX support in trimesh requires the pyassimp backend and the assimp library.
    """

    def __init__(self):
        """Initializes the FBXLoader."""
        pass

    def _check_dependencies(self):
        """Checks if required dependencies are available."""
        if not ASSIMP_AVAILABLE:
            raise DependencyError(
                "FBX loading requires the 'assimp' library and 'pyassimp' Python package. "
                "Please ensure assimp is installed on your system (e.g., 'brew install assimp' "
                "on macOS or 'sudo apt-get install libassimp-dev' on Linux)."
            )
        
        if not FBX_SDK_AVAILABLE:
            # We log a warning or handle it if FBX SDK is strictly required for some features
            # For now, we just note its absence as it's preferred for native processing
            pass

    def load_model(self, file_path: str) -> trimesh.Scene:
        """
        Loads an FBX model from the specified file path.

        Args:
            file_path: The path to the FBX file.

        Returns:
            trimesh.Scene: The loaded scene containing the model.

        Raises:
            FileNotFoundError: If the file does not exist.
            DependencyError: If required dependencies are missing.
            ValueError: If the file format is not supported or loading fails.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"FBX file not found: {file_path}")

        self._check_dependencies()

        try:
            # trimesh.load uses assimp for FBX if available.
            scene = trimesh.load(file_path, file_type='fbx')
            
            if isinstance(scene, trimesh.Trimesh):
                # Wrap single mesh in a scene for consistency
                scene = trimesh.Scene(scene)
                
            return scene
        except Exception as e:
            raise ValueError(f"Failed to load FBX model: {str(e)}")

    def process_mesh_data(self, scene: trimesh.Scene) -> Tuple[np.ndarray, np.ndarray]:
        """
        Processes mesh data from a scene to extract vertices and faces.

        Args:
            scene: The trimesh Scene to process.

        Returns:
            Tuple[np.ndarray, np.ndarray]: A tuple containing (vertices, faces).
        """
        # Concatenate all meshes in the scene into a single mesh for processing
        mesh = scene.dump(concatenate=True)
        if isinstance(mesh, trimesh.Scene):
             # Handle cases where dump might return a scene if concatenation fails
             vertices = []
             faces = []
             current_offset = 0
             for m in scene.geometry.values():
                 if not hasattr(m, 'vertices') or not hasattr(m, 'faces'):
                     continue
                 vertices.append(m.vertices)
                 faces.append(m.faces + current_offset)
                 current_offset += len(m.vertices)
             
             if not vertices:
                 return np.array([]), np.array([])
                 
             return np.vstack(vertices), np.vstack(faces)
        
        return mesh.vertices, mesh.faces

class MixamoAnimationLoader(FBXLoader):
    """
    Specialized loader for Mixamo animations from FBX files.
    """

    def load_animation(self, file_path: str) -> Dict[str, Any]:
        """
        Loads animation data from a Mixamo FBX file.

        Args:
            file_path: The path to the Mixamo FBX file.

        Returns:
            Dict[str, Any]: A dictionary containing animation data.

        Raises:
            FileNotFoundError: If the file does not exist.
            DependencyError: If required dependencies are missing.
            ValueError: If the file format is not supported or loading fails.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Animation file not found: {file_path}")

        self._check_dependencies()

        try:
            scene = trimesh.load(file_path, file_type='fbx')
            
            # trimesh stores animations in scene.graph.animations or similar depending on version/backend
            animations = getattr(scene, 'animations', [])
            
            return {
                "scene": scene,
                "animations": animations,
                "file_path": file_path
            }
        except Exception as e:
            raise ValueError(f"Failed to load Mixamo animation: {str(e)}")
