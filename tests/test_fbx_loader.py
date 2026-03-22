import pytest
import os
import trimesh
import numpy as np
from loaders.fbx_loader import FBXLoader, MixamoAnimationLoader, ASSIMP_AVAILABLE, DependencyError

@pytest.fixture
def loader():
    return FBXLoader()

@pytest.fixture
def animation_loader():
    return MixamoAnimationLoader()

@pytest.fixture
def sample_fbx_path():
    # Use the existing sample file in the project root
    return "crush_dummy_UE4_skinned.fbx"

def test_load_model_not_found(loader):
    with pytest.raises(FileNotFoundError):
        loader.load_model("non_existent.fbx")

def test_dependency_error_when_assimp_missing(loader, sample_fbx_path):
    if ASSIMP_AVAILABLE:
        pytest.skip("Assimp is available, cannot test DependencyError")
    
    if not os.path.exists(sample_fbx_path):
        pytest.skip("Sample FBX file not found for testing")

    with pytest.raises(DependencyError) as excinfo:
        loader.load_model(sample_fbx_path)
    assert "assimp" in str(excinfo.value).lower()

def test_load_model_success(loader, sample_fbx_path):
    if not os.path.exists(sample_fbx_path):
        pytest.skip("Sample FBX file not found for testing")
    
    if not ASSIMP_AVAILABLE:
        pytest.skip("Skipping success test as assimp is missing")

    try:
        scene = loader.load_model(sample_fbx_path)
        assert isinstance(scene, trimesh.Scene)
        assert len(scene.geometry) > 0
    except Exception as e:
        pytest.fail(f"FBX loading failed: {e}")

def test_process_mesh_data(loader, sample_fbx_path):
    if not os.path.exists(sample_fbx_path):
        pytest.skip("Sample FBX file not found for testing")
    
    if not ASSIMP_AVAILABLE:
        pytest.skip("Skipping mesh processing test as assimp is missing")
    
    try:
        scene = loader.load_model(sample_fbx_path)
        vertices, faces = loader.process_mesh_data(scene)
        assert isinstance(vertices, np.ndarray)
        assert isinstance(faces, np.ndarray)
        assert vertices.shape[1] == 3
        assert faces.shape[1] == 3
    except Exception as e:
        pytest.fail(f"Mesh processing failed: {e}")

def test_load_animation_success(animation_loader, sample_fbx_path):
    if not os.path.exists(sample_fbx_path):
        pytest.skip("Sample FBX file not found for testing")
    
    if not ASSIMP_AVAILABLE:
        pytest.skip("Skipping animation success test as assimp is missing")

    try:
        data = animation_loader.load_animation(sample_fbx_path)
        assert "scene" in data
        assert "animations" in data
        assert isinstance(data["scene"], trimesh.Scene)
    except Exception as e:
        pytest.fail(f"Animation loading failed: {e}")
