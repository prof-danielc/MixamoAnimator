import sys
import os
import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ui.main_window import MainWindow
import trimesh

# Create a single QApplication instance for all tests
@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

@pytest.fixture
def mock_loaders():
    with patch('ui.main_window.FBXLoader') as mock_fbx, \
         patch('ui.main_window.MixamoAnimationLoader') as mock_anim, \
         patch('ui.main_window.PyrenderWidget') as mock_viewport:
        
        # Setup mock scene
        mock_scene = MagicMock(spec=trimesh.Scene)
        mock_scene.graph = MagicMock()
        mock_scene.graph.nodes = ['bone1', 'bone2']
        mock_fbx.return_value.load_model.return_value = mock_scene
        
        # Setup mock animation
        mock_anim_obj = MagicMock()
        mock_anim_obj.times = [0.0, 1.0]
        mock_anim_obj.name = "TestAnim"
        mock_anim.return_value.load_animation.return_value = {
            "animations": [mock_anim_obj],
            "scene": MagicMock(),
            "file_path": "dummy.fbx"
        }
        
        yield mock_fbx, mock_anim, mock_viewport

def test_main_window_init(qapp, mock_loaders):
    """Tests that the MainWindow initializes correctly with mocked loaders."""
    window = MainWindow("model.fbx", "anim.fbx")
    
    assert window.windowTitle() == "MixamoAnimator"
    assert window.animation_list.count() == 1
    assert window.animation_list.item(0).text() == "TestAnim"
    
    # Check if viewport is created
    assert window.viewport is not None
    
    # Check buttons
    assert window.play_button.text() == "Play"
    assert window.pause_button.text() == "Pause"
    assert window.reset_button.text() == "Reset"
    
    window.close()

def test_playback_controls(qapp, mock_loaders):
    """Tests that playback control buttons are connected to the PlaybackEngine."""
    window = MainWindow("model.fbx", "anim.fbx")
    
    # Mock playback engine
    window.playback_engine = MagicMock()
    
    # Re-connect signals to the mock
    window.play_button.clicked.disconnect()
    window.play_button.clicked.connect(window.playback_engine.play)
    window.pause_button.clicked.disconnect()
    window.pause_button.clicked.connect(window.playback_engine.pause)
    window.reset_button.clicked.disconnect()
    window.reset_button.clicked.connect(window.playback_engine.reset)
    
    window.play_button.click()
    window.playback_engine.play.assert_called_once()
    
    window.pause_button.click()
    window.playback_engine.pause.assert_called_once()
    
    window.reset_button.click()
    window.playback_engine.reset.assert_called_once()
    
    window.close()

def test_animation_selection(qapp, mock_loaders):
    """Tests that selecting an animation from the list updates the playback engine."""
    mock_fbx, mock_anim_loader, mock_viewport = mock_loaders
    
    # Setup multiple animations
    anim1 = MagicMock()
    anim1.times = [0.0, 1.0]
    anim1.name = "Anim1"
    
    anim2 = MagicMock()
    anim2.times = [0.0, 2.0]
    anim2.name = "Anim2"
    
    mock_anim_loader.return_value.load_animation.return_value = {
        "animations": [anim1, anim2],
        "scene": MagicMock(),
        "file_path": "dummy.fbx"
    }
    
    window = MainWindow("model.fbx", "anim.fbx")
    
    assert window.animation_list.count() == 2
    assert window.animation_list.item(0).text() == "Anim1"
    assert window.animation_list.item(1).text() == "Anim2"
    
    # Select second animation
    window.animation_list.setCurrentRow(1)
    
    # Check if duration was updated in playback engine
    assert window.playback_engine.duration == 2.0
    
    window.close()

def test_time_changed_updates_scene(qapp, mock_loaders):
    """Tests that the scene is updated when the playback engine time changes."""
    mock_fbx, mock_anim_loader, mock_viewport = mock_loaders
    
    anim1 = MagicMock()
    anim1.times = [0.0, 1.0]
    anim1.name = "Anim1"
    anim1.interpolate.return_value = {"bone1": [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]}
    
    mock_anim_loader.return_value.load_animation.return_value = {
        "animations": [anim1],
        "scene": MagicMock(),
        "file_path": "dummy.fbx"
    }
    
    window = MainWindow("model.fbx", "anim.fbx")
    
    # Mock rig_mapper
    window.rig_mapper = MagicMock()
    
    # Trigger time change
    window.playback_engine.time_changed.emit(0.5)
    
    # Verify rig_mapper.apply_to_scene was called
    window.rig_mapper.apply_to_scene.assert_called_once()
    
    # Verify viewport update was called
    window.viewport.update.assert_called()
    
    window.close()
