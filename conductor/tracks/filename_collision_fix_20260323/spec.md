# Specification: Filename Collision Fix

Handle animations with identical names to prevent overwriting files.

## Functional Requirements
- When saving a downloaded animation, check if a file with the same name already exists in the output directory.
- If a collision is detected, append a suffix (e.g., `_1`, `_2`) to the animation name part of the filename.
- Ensure all copies of animations sharing the same name are preserved.

## Technical Details
- Update `MixamoBot.download_animations` to include collision detection logic.
- Use a while loop to find the next available filename if necessary.
