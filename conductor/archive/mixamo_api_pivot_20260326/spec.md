# Track Spec: Mixamo API Pivot (20260326)

## Overview
This track involves a significant architectural pivot: replacing the Playwright-based web crawling and downloading mechanism with a more robust and efficient direct integration using the Mixamo API. The existing `MixamoBot` class will be refactored to prioritize API-driven interactions, with Playwright retained primarily as a fallback or for session management.

## Functional Requirements
- **API Client Implementation**: Integrate logic from `mixamo_harvester.py` into `MixamoBot` to handle authentication, product listing, character export, and file downloads.
- **Manual Authentication**: Use a `mixamo_token.txt` file for the Mixamo Bearer Token, with `session.json` as a fallback.
- **Custom Character Uploads**: Ensure that user-provided FBX models are uploaded to Mixamo to obtain a valid `character_id` for subsequent animation exports.
- **Multi-threaded Downloads**: Implement `ThreadPoolExecutor` (as seen in `mixamo_harvester.py`) to handle concurrent animation downloads and status monitoring.
- **Local Animation Catalog**: Implement a local JSON caching mechanism for the Mixamo animation catalog (ids vs names) to reduce API overhead.
- **Enhanced GUI**:
    - Display API status (Token Validity).
    - Provide real-time feedback on Mixamo export job progress.
    - Show download metrics (speed, percentage) for each animation in the queue.

## Non-Functional Requirements
- **Robustness**: Implement exponential backoff and retries (via `tenacity`) for all API calls to handle rate limits and transient network issues.
- **Performance**: Significant reduction in time to fetch and download animations compared to Playwright-based scraping.

## Acceptance Criteria
- `MixamoBot` successfully authenticates using a Bearer Token from `mixamo_token.txt`.
- Custom characters are uploaded, and their `character_id` is retrieved via the API.
- Animations are exported and downloaded concurrently using the Mixamo API.
- The UI accurately reflects API status and download progress.
- Local catalog cache is created and used for faster lookups.

## Out of Scope
- Full removal of Playwright (kept for legacy support/login fallback).
- Support for "MotionPacks" (animations with multiple sub-animations) unless easily implementable.
