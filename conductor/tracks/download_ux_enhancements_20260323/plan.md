# Implementation Plan: Download Enhancements (UX & Filename Safety)

This plan covers the implementation of progress tracking (ETA/Counter) and filename collision handling for the Mixamo download process.

## Objective
Improve the user experience by providing accurate progress feedback and preventing data loss from duplicate animation names.

## Key Files
- `bot/mixamo_bot.py`: Core download logic.
- `main.py`: CLI display logic.

## Implementation Steps

### 1. Progress Feedback (TRACK 1)
- **Modify `MixamoBot.download_animations`**:
  - Add a progress tracking mechanism.
  - Track start time and calculate duration for each download.
  - Compute average time per download to provide an estimated time remaining.
- **Modify `main.py`**:
  - Integrate the new progress info into the `rich.progress` bar.
  - Display the "index/total" counter in the task description.

### 2. Filename Collision Handling (TRACK 2)
- **Modify `MixamoBot.download_animations`**:
  - Implement a check for existing files before calling `download.save_as()`.
  - If a file exists, increment a counter and append it to the filename (e.g., `model_anim_1.fbx`).
  - Repeat until a unique filename is found.

## Verification & Testing
- Run a batch download of 5 animations.
- Verify the terminal shows "1/5", "2/5", etc., with a dynamic ETA.
- Mock or find two animations with the same name and verify both are saved as separate files.
