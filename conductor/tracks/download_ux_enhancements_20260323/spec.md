# Specification: Download UX Enhancements

Implement ETA and progress counter for animation downloads.

## Functional Requirements
- Display an incrementing counter for each download (e.g., "1/100", "2/100").
- Calculate and display an ETA based on the average time taken for completed downloads in the current session.
- Extrapolate the remaining time based on the average download duration.

## Technical Details
- Update `MixamoBot.download_animations` to support progress callbacks or internal status updates.
- Update `main.py` to use the progress counter in the terminal.
- Use `rich.progress` to handle the display logic.
