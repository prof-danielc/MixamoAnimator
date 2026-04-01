# Specification: In-Place Animations Support

## Overview
This track adds support for "in-place" animations when downloading from Mixamo. This feature is useful for game development where root motion is handled separately, as it forces the animation to stay at the origin (e.g., a "Run Forward" animation becomes a "Run in Place" animation).

## Functional Requirements
- **CLI Argument:** Add a new `--inplace` boolean flag to `main.py`.
- **API Integration:**
    - Update `MixamoAPIClient` to accept an `inplace` parameter in its download and export methods.
    - Inject `"inplace": true` (or `false`) into the `gms_hash` object sent to the Mixamo `animations/export` endpoint.
- **File Naming:**
    - If `--inplace` is active, the downloaded file should include an `_inplace` suffix.
    - Format: `{anim_name}_inplace_{anim_id}_{character_id}_{skin_suffix}.fbx`
- **Scope:**
    - The flag is global for the current session (applies to all animations in a batch).
    - GUI support is out of scope for this track (CLI only).

## Technical Details (Research Findings)
- Inspection of `Research/mixamo_API_code.js` confirms that `inplace` is a boolean property within the `gms_hash` payload for "Motion" types.
- The parameter must be set at the individual clip/gms_hash level.

## Acceptance Criteria
- [ ] `main.py --model_path ... --inplace` successfully downloads animations with root motion locked to the origin.
- [ ] Resulting filenames correctly contain the `_inplace` suffix.
- [ ] The `MixamoAPIClient` correctly handles the `inplace` flag for both single and concurrent downloads.

## Out of Scope
- GUI checkbox for "in-place" animations.
- Per-animation "in-place" selection (global flag only).
