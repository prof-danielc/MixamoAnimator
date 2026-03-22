import os
from typing import Dict, Any, List, Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QListWidget, QLabel, QFrame
)
from ui.viewport import PyrenderWidget
from ui.playback_engine import PlaybackEngine
from mapping.rig_mapper import RigMapper
from loaders.fbx_loader import FBXLoader, MixamoAnimationLoader

class MainWindow(QMainWindow):
    """
    Main application window for MixamoAnimator.
    """

    def __init__(self, model_path: str, animation_path: str):
        """
        Initializes the MainWindow.

        Args:
            model_path: Path to the FBX model file.
            animation_path: Path to the Mixamo animation FBX file.
        """
        super().__init__()
        self.setWindowTitle("MixamoAnimator")
        self.resize(1200, 800)

        self.model_loader = FBXLoader()
        self.animation_loader = MixamoAnimationLoader()
        
        # Load model
        self.scene = self.model_loader.load_model(model_path)
        
        # Load animation
        self.animation_result = self.animation_loader.load_animation(animation_path)
        self.animations = self.animation_result.get("animations", [])
        self.animation_scene = self.animation_result.get("scene")
        
        # Initialize RigMapper with target bone names
        target_bone_names = list(self.scene.graph.nodes)
        self.rig_mapper = RigMapper(target_bone_names)
        
        # Initialize PlaybackEngine
        self.playback_engine = PlaybackEngine()
        
        self._setup_ui()
        self._connect_signals()
        
        # Initial population
        self._populate_animations()
        
        # Set initial duration if animation exists
        if self.animations:
            duration = 0.0
            for anim in self.animations:
                if hasattr(anim, 'times') and len(anim.times) > 0:
                    duration = max(duration, anim.times[-1])
            self.playback_engine.set_duration(duration)

    def _setup_ui(self):
        """Sets up the user interface layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left Panel: Animation List and Controls
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.StyledPanel)
        left_layout = QVBoxLayout(left_panel)
        left_panel.setFixedWidth(300)

        left_layout.addWidget(QLabel("Available Animations"))
        self.animation_list = QListWidget()
        left_layout.addWidget(self.animation_list)

        # Playback Controls
        controls_group = QWidget()
        controls_layout = QHBoxLayout(controls_group)
        
        self.play_button = QPushButton("Play")
        self.pause_button = QPushButton("Pause")
        self.reset_button = QPushButton("Reset")
        
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.pause_button)
        controls_layout.addWidget(self.reset_button)
        
        left_layout.addWidget(controls_group)
        
        main_layout.addWidget(left_panel)

        # Right Panel: Viewport
        self.viewport = PyrenderWidget()
        self.viewport.set_scene(self.scene)
        main_layout.addWidget(self.viewport, stretch=1)

    def _connect_signals(self):
        """Connects UI signals to slots."""
        self.play_button.clicked.connect(self.playback_engine.play)
        self.pause_button.clicked.connect(self.playback_engine.pause)
        self.reset_button.clicked.connect(self.playback_engine.reset)
        
        self.playback_engine.time_changed.connect(self._on_time_changed)
        self.animation_list.currentRowChanged.connect(self._on_animation_selected)

    def _populate_animations(self):
        """Populates the animation list widget."""
        self.animation_list.clear()
        if not self.animations:
            # If no animations found in the file, maybe use the file name as a placeholder
            file_name = os.path.basename(self.animation_result.get("file_path", "Unknown"))
            self.animation_list.addItem(file_name)
        else:
            for i, anim in enumerate(self.animations):
                name = getattr(anim, 'name', f"Animation {i+1}")
                self.animation_list.addItem(name)
        
        if self.animation_list.count() > 0:
            self.animation_list.setCurrentRow(0)

    def _on_animation_selected(self, index: int):
        """Handles animation selection change."""
        if self.animations and 0 <= index < len(self.animations):
            anim = self.animations[index]
            if hasattr(anim, 'times') and len(anim.times) > 0:
                self.playback_engine.set_duration(anim.times[-1])
            else:
                self.playback_engine.set_duration(0.0)
            self.playback_engine.reset()

    def _on_time_changed(self, current_time: float):
        """Updates the scene based on the current playback time."""
        if not self.animations:
            return

        selected_idx = self.animation_list.currentRow()
        if 0 <= selected_idx < len(self.animations):
            anim = self.animations[selected_idx]
            
            # Sample animation at current_time
            # trimesh.animation.Animation.interpolate(time) returns a dict of node transforms
            if hasattr(anim, 'interpolate'):
                try:
                    animation_data = anim.interpolate(current_time)
                    self.rig_mapper.apply_to_scene(self.scene, animation_data)
                    self.viewport.update()
                except Exception as e:
                    # Log error once to avoid flooding
                    if not hasattr(self, '_last_anim_error') or self._last_anim_error != str(e):
                        print(f"Animation interpolation error: {e}")
                        self._last_anim_error = str(e)

    def closeEvent(self, event):
        """Cleans up resources on window close."""
        self.viewport.cleanup()
        super().closeEvent(event)
