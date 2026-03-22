import trimesh
import pyrender
import numpy as np
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from typing import Dict, Optional, Any

class PyrenderWidget(QOpenGLWidget):
    """
    A PySide6 widget that renders a trimesh.Scene using Pyrender.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene: Optional[trimesh.Scene] = None
        self.renderer: Optional[pyrender.OffscreenRenderer] = None
        self.pyrender_scene: Optional[pyrender.Scene] = None
        self.camera: Optional[pyrender.PerspectiveCamera] = None
        self.camera_node: Optional[pyrender.Node] = None
        self._node_map: Dict[str, pyrender.Node] = {}

    def set_scene(self, trimesh_scene: trimesh.Scene):
        """
        Sets the trimesh scene to be rendered.

        Args:
            trimesh_scene: The trimesh.Scene to render.
        """
        self.scene = trimesh_scene
        
        # Create pyrender scene from trimesh scene
        self.pyrender_scene = pyrender.Scene.from_trimesh_scene(self.scene)
        
        # Map trimesh nodes to pyrender nodes for fast updates
        self._node_map = {}
        for node in self.pyrender_scene.nodes:
            if node.name:
                self._node_map[node.name] = node

        # Add a camera if not present
        if not self.pyrender_scene.main_camera_node:
            self.camera = pyrender.PerspectiveCamera(yfov=np.pi / 3.0, aspectRatio=1.0)
            camera_pose = np.eye(4)
            camera_pose[:3, 3] = [0, 0, 5]
            self.camera_node = self.pyrender_scene.add(self.camera, pose=camera_pose)
            
        # Add light if not present
        if len(self.pyrender_scene.light_nodes) == 0:
            light = pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=2.0)
            self.pyrender_scene.add(light, pose=np.eye(4))
            
        self.update()

    def update_scene_transforms(self):
        """
        Updates the pyrender scene nodes' poses from the trimesh scene graph.
        """
        if not self.scene or not self.pyrender_scene:
            return
            
        for node_name in self.scene.graph.nodes:
            if node_name in self._node_map:
                transform, _ = self.scene.graph.get(node_name)
                self.pyrender_scene.set_pose(self._node_map[node_name], pose=transform)

    def initializeGL(self):
        """Initializes OpenGL state."""
        pass

    def resizeGL(self, w, h):
        """Handles widget resize events."""
        if self.renderer:
            self.renderer.delete()
        if w > 0 and h > 0:
            self.renderer = pyrender.OffscreenRenderer(w, h)
            if self.camera:
                self.camera.aspectRatio = float(w) / float(h)

    def paintGL(self):
        """Renders the scene."""
        if not self.pyrender_scene or not self.renderer:
            return
            
        try:
            self.update_scene_transforms()
            
            # Render the scene
            color, _ = self.renderer.render(self.pyrender_scene)
            
            # Create a QImage from the color buffer.
            # Pyrender returns an RGB array.
            height, width, _ = color.shape
            # We use the ndarray directly; QImage will not own the memory.
            # Since this is synchronous, it's safe.
            img = QImage(color.data, width, height, QImage.Format_RGB888)
            
            painter = QPainter(self)
            # Draw the image scaled to the widget size
            painter.drawImage(self.rect(), img)
            painter.end()
        except Exception as e:
            # Avoid flooding the console with errors during playback
            if not hasattr(self, '_last_error') or self._last_error != str(e):
                print(f"Render error: {e}")
                self._last_error = str(e)

    def cleanup(self):
        """Cleans up pyrender resources."""
        if self.renderer:
            self.renderer.delete()
            self.renderer = None
