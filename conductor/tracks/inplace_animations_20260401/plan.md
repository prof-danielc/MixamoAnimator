# Implementation Plan: In-Place Animations Support

## Phase 1: Research and API Verification [checkpoint: 7a6a5aa]
Research and verify the "in-place" parameter in the Mixamo API requests to ensure correct implementation.

- [x] Task: Verify the Mixamo API's handling of the `inplace` parameter by manually inspecting a network request if possible, or by cross-referencing `Research/mixamo_API_code.js` logic with current `MixamoAPIClient` behavior. 12ada4e
- [x] Task: Conductor - User Manual Verification 'Phase 1: Research and API Verification' (Protocol in workflow.md)

## Phase 2: Update MixamoAPIClient
Implement the `inplace` parameter in the core API client.

- [ ] Task: Write Tests for `MixamoAPIClient.export_animation` and `_process_single_animation` to support the `inplace` flag.
- [ ] Task: Update `MixamoAPIClient.export_animation` to accept an `inplace` boolean and inject it into the `gms_hash` (or preferences) in the payload.
- [ ] Task: Update `MixamoAPIClient._process_single_animation` and `download_animations` to handle the `inplace` flag and the new filename suffix.
- [ ] Task: Verify tests pass for `MixamoAPIClient` changes.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Update MixamoAPIClient' (Protocol in workflow.md)

## Phase 3: Update CLI (main.py)
Expose the "in-place" option to the user via the command-line interface.

- [ ] Task: Write Tests for `main.py` CLI arguments.
- [ ] Task: Add `--inplace` flag to `main.py` using `argparse`.
- [ ] Task: Ensure the `inplace` flag is passed through to the `MixamoAPIClient`.
- [ ] Task: Verify tests pass for CLI changes.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Update CLI (main.py)' (Protocol in workflow.md)

## Phase 4: Final Integration and Verification
Perform a complete end-to-end test of the new feature.

- [ ] Task: Perform a manual end-to-end download test with `--inplace` and verify the resulting FBX file (check in-place motion and filename).
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Final Integration and Verification' (Protocol in workflow.md)
