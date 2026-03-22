# Plan: Resolve Semantic Animation Names and Fix PySide6 DLL Error

## Objective
To allow users to specify semantic animation names (e.g., 'walk', 'run') instead of full file paths, and to resolve the `ImportError: DLL load failed` when importing PySide6 on Windows.

## Key Files
- `main.py`: Update argument parsing and animation file resolution.
- `ui/main_window.py`: Ensure compatibility with the resolved animation paths.
- `requirements.txt`: Update PySide6 dependencies if needed.
- `conductor/product.md`: Document the new animation naming convention.

## Implementation Steps

### Phase 1: Semantic Animation Name Mapping
1.  **Modify `main.py`**:
    -   In `parse_args()`, add an optional `--animations_dir` argument (default: `./animations`).
    -   Update the help text for `--animation_name` to reflect it's a name, not a path.
    -   In `main()`, implement a resolution function `resolve_animation_path(animations_dir, animation_name)`:
        -   It will search for files named `<animation_name>.fbx` (case-insensitive) in the specified directory.
        -   If found, it returns the full path.
        -   If not found, it should provide a helpful error message listing available animations in that folder.
    -   Update the file existence check for `animation_name` to use this resolved path.
2.  **Update `ui/main_window.py`**:
    -   The `MainWindow` already takes `animation_path`, so no structural changes are needed, but ensuring it correctly handles potentially missing files with better UI feedback is a plus.
3.  **Update Project Documentation**:
    -   Update `conductor/product.md` to reflect the change in parameters.

### Phase 2: Fix PySide6 DLL Load Error
1.  **Troubleshoot Environment**:
    -   Create a small script `check_pyside6.py` to diagnose the DLL issue.
    -   Try forcing a re-installation of PySide6 with `pip install --upgrade --force-reinstall PySide6`.
2.  **Update `requirements.txt`**:
    -   Consider pinning `PySide6` to a specific version (e.g., `PySide6==6.5.2`) if the latest version is problematic in the current environment.
3.  **Visual C++ Redistributable**:
    -   Advise the user to ensure they have the latest Microsoft Visual C++ Redistributable installed, as PySide6 depends on it.

## Verification & Testing
1.  **Manual Verification**:
    -   Create a sample `animations/` folder.
    -   Put `crush_dummy_UE4_skinned.fbx` in it (as it has animations).
    -   Run `python main.py --model_name crush_dummy_UE4_skinned.fbx --animation_name crush_dummy_UE4_skinned` and verify it loads.
2.  **Unit Tests**:
    -   Update `tests/test_main.py` to test the new argument parsing and path resolution logic.
