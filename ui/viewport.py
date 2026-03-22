from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
import trimesh
import pyrender
import numpy as np
from typing import Dict, Optional, Any

class PyrenderWidget(QLabel):
    """
    A PySide6 widget that renders a trimesh.Scene using Pyrender 
    and displays it using a QLabel for maximum compatibility.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene: Optional[trimesh.Scene] = None
        self.renderer: Optional[pyrender.OffscreenRenderer] = None
        self.pyrender_scene: Optional[pyrender.Scene] = None
        self.camera: Optional[pyrender.PerspectiveCamera] = None
        self.camera_node: Optional[pyrender.Node] = None
        self._node_map: Dict[str, pyrender.Node] = {}
        
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(400, 400)
        self.setStyleSheet("background-color: #CCCCCC; border: 1px solid #999999;")

    def set_scene(self, trimesh_scene: trimesh.Scene):
        """Sets the trimesh scene to be rendered."""
        self.scene = trimesh_scene
        self.pyrender_scene = pyrender.Scene(bg_color=[0.8, 0.8, 0.8])
        self._node_map = {}

        for node_name in self.scene.graph.nodes:
            transform, geometry_name = self.scene.graph.get(node_name)
            if geometry_name is not None:
                mesh = self.scene.geometry[geometry_name]
                if isinstance(mesh, trimesh.Trimesh):
                    pr_mesh = pyrender.Mesh.from_trimesh(mesh)
                    pr_node = self.pyrender_scene.add(pr_mesh, pose=transform, name=node_name)
                    self._node_map[node_name] = pr_node
        
        for node_name in self.scene.graph.nodes:
            if node_name not in self._node_map:
                transform, _ = self.scene.graph.get(node_name)
                pr_node = pyrender.Node(name=node_name, matrix=transform)
                self.pyrender_scene.add_node(pr_node)
                self._node_map[node_name] = pr_node

        center = self.scene.centroid
        extents = self.scene.extents
        max_extent = np.max(extents) if extents.size > 0 else 1.0
        dist = max_extent * 3.0
        
        camera_pose = np.eye(4)
        camera_pose[:3, 3] = center + [0, 0, dist]
        
        self.camera = pyrender.PerspectiveCamera(yfov=np.pi / 3.0, aspectRatio=1.0, zfar=dist * 10.0)
        self.camera_node = self.pyrender_scene.add(self.camera, pose=camera_pose)
            
        self.pyrender_scene.add(pyrender.PointLight(color=[1.0, 1.0, 1.0], intensity=dist * 100), pose=camera_pose)
        self.pyrender_scene.add(pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=10.0), pose=camera_pose)
            
        self.render_frame()

    def update_scene_transforms(self):
        """Updates pyrender nodes from trimesh scene graph."""
        if not self.scene or not self.pyrender_scene:
            return
        for node_name in self.scene.graph.nodes:
            if node_name in self._node_map:
                transform, _ = self.scene.graph.get(node_name)
                self.pyrender_scene.set_pose(self._node_map[node_name], pose=transform)

    def resizeEvent(self, event):
        """Handles widget resize."""
        size = event.size()
        w, h = size.width(), size.height()
        if w > 0 and h > 0:
            if self.renderer:
                self.renderer.delete()
            self.renderer = pyrender.OffscreenRenderer(w, h)
            if self.camera:
                self.camera.aspectRatio = float(w) / float(h)
            self.render_frame()
        super().resizeEvent(event)

    def render_frame(self):
        """Triggers a re-render and updates the label's pixmap."""
        if not self.pyrender_scene or not self.renderer:
            return
            
        try:
            self.update_scene_transforms()
            color, _ = self.renderer.render(self.pyrender_scene)
            
            if not color.flags['C_CONTIGUOUS']:
                color = np.ascontiguousarray(color)
                
            height, width, _ = color.shape
            img = QImage(color.data, width, height, QImage.Format_RGB888)
            self.setPixmap(QPixmap.fromImage(img))
        except Exception as e:
            print(f"Render error: {e}")

    def update(self):
        """Overrides update() to call render_frame()."""
        self.render_frame()
        super().update()

    def cleanup(self):
        """Cleans up resources."""
        if self.renderer:
            self.renderer.delete()
            self.renderer = None
