import pytest
import numpy as np
import trimesh
from mapping.rig_mapper import RigMapper

@pytest.fixture
def target_bones():
    return ["Hips", "Spine", "Neck", "Head", "L_Arm", "R_Arm", "L_Leg", "R_Leg"]

@pytest.fixture
def mapper(target_bones):
    return RigMapper(target_bones)

def test_auto_map(mapper):
    mapping = mapper.get_mapping()
    # Check some basic mappings
    assert mapping.get("mixamorig:Hips") == "Hips"
    assert mapping.get("mixamorig:Spine") == "Spine"
    assert mapping.get("mixamorig:Neck") == "Neck"
    assert mapping.get("mixamorig:Head") == "Head"
    
    # Check if it handles partial matches (e.g., "Arm" in "L_Arm")
    assert mapping.get("mixamorig:LeftArm") == "L_Arm"
    assert mapping.get("mixamorig:RightArm") == "R_Arm"

def test_set_custom_mapping(mapper):
    # Add a new bone to target bones to test custom mapping
    mapper.target_bone_names.append("Custom_Hips_Name")
    custom_mapping = {"mixamorig:Hips": "Custom_Hips_Name"}
    mapper.set_custom_mapping(custom_mapping)
    assert mapper.get_mapping()["mixamorig:Hips"] == "Custom_Hips_Name"

def test_retarget_animation(mapper):
    # Create some dummy animation data
    animation_data = {
        "mixamorig:Hips": np.eye(4),
        "mixamorig:Spine": np.eye(4) * 2.0
    }
    
    retargeted = mapper.retarget_animation(animation_data)
    
    assert "Hips" in retargeted
    assert "Spine" in retargeted
    assert np.array_equal(retargeted["Hips"], np.eye(4))
    assert np.array_equal(retargeted["Spine"], np.eye(4) * 2.0)

def test_apply_to_scene(mapper):
    # Create a simple scene with some nodes
    scene = trimesh.Scene()
    # trimesh.Scene.graph.update(node, matrix, parent)
    scene.graph.update("Hips", matrix=np.eye(4))
    scene.graph.update("Spine", matrix=np.eye(4))
    
    animation_data = {
        "mixamorig:Hips": np.eye(4) * 3.0,
        "mixamorig:Spine": np.eye(4) * 4.0
    }
    
    mapper.apply_to_scene(scene, animation_data)
    
    # Verify that the scene graph was updated
    # scene.graph.get returns (matrix, parent)
    hips_matrix, _ = scene.graph.get("Hips")
    spine_matrix, _ = scene.graph.get("Spine")
    
    assert np.array_equal(hips_matrix, np.eye(4) * 3.0)
    assert np.array_equal(spine_matrix, np.eye(4) * 4.0)

def test_rig_agnostic_mapping():
    # Test with a completely different naming convention
    target_bones = ["Bip01_Pelvis", "Bip01_Spine", "Bip01_Neck", "Bip01_Head"]
    mapper = RigMapper(target_bones)
    
    # My current heuristic might fail here if it only looks for "hips"
    # Mixamo "Hips" -> "Pelvis" is a common mapping but not handled by simple substring
    
    # Let's see what it maps
    mapping = mapper.get_mapping()
    assert mapping.get("mixamorig:Spine") == "Bip01_Spine"
    assert mapping.get("mixamorig:Neck") == "Bip01_Neck"
    assert mapping.get("mixamorig:Head") == "Bip01_Head"
    
    # We can manually set the Hips mapping
    mapper.set_custom_mapping({"mixamorig:Hips": "Bip01_Pelvis"})
    assert mapper.get_mapping()["mixamorig:Hips"] == "Bip01_Pelvis"
