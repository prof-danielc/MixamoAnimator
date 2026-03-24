# Plan: Support FBX Loading and GLB Fallback

Fix the `NotImplementedError: file_type 'fbx' not supported` from `trimesh` and improve the robustness of FBX/GLTF loading.

## Objective
The application fails to load FBX files if the `assimp` system library is missing or improperly configured. This plan introduces a more robust dependency check, provides an automatic fallback to `.glb` or `.gltf` files if they exist, and fixes missing dependencies in `requirements.txt`.

## Key Files & Context
- `loaders/fbx_loader.py`: Core logic for loading models and animations.
- `requirements.txt`: Project dependencies.
- `main.py`: Entry point for resolving file paths.

## Implementation Steps

### 1. Update Dependencies
- Add `pygltflib` to `requirements.txt`.
- Ensure `pyassimp` is correctly versioned.

### 2. Refactor `loaders/fbx_loader.py`
- **Consolidate Imports**: Remove redundant imports in the middle of the file.
- **Robust Dependency Check**:
  - Update `ASSIMP_AVAILABLE` to check if `trimesh` actually has `fbx` in its `available_formats()`.
  - Provide more descriptive error messages in `_check_dependencies`.
- **Implement Fallback Mechanism**:
  - In `load_model` and `load_animation`, if the requested file is `.fbx` and it fails to load (due to missing dependency or `NotImplementedError`), look for a `.glb` or `.gltf` file with the same base name in the same directory.
  - If a fallback file is found, print a warning and load it instead.
  - This is particularly useful for the `crush_dummy_UE4_skinned` model which already has both versions.

### 3. Improve `main.py`
- Add a check at startup to warn if FBX support is missing but an FBX file was requested.

### 4. Update Tests
- Add a test case for the GLB fallback mechanism.
- Ensure tests don't fail silently if files are missing.

## Verification & Testing
- Run `python check_fbx.py` (after creating it) to verify the environment.
- Run `pytest tests/test_fbx_loader.py`.
- Manually test the application with `--model_name crush_dummy_UE4_skinned.fbx` and verify it falls back to `.glb` if FBX support is missing.
- Verify `Running.fbx` still errors out if no GLB is found (but with a better message).
