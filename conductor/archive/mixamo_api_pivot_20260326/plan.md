# Implementation Plan: Mixamo API Pivot

## Phase 1: API Client Foundation & Authentication [checkpoint: cae385b]
- [x] Task: Create `MixamoAPIClient` class with basic authentication logic. d375e53
    - [x] Write tests for `MixamoAPIClient` initializing with a token from `mixamo_token.txt`.
    - [x] Implement `MixamoAPIClient` to read token and handle basic headers (`Authorization`, `X-Api-Key`).
- [x] Task: Implement API Request Wrapper with Retries. eb00b3f
    - [x] Write tests for API request retries using `tenacity`.
    - [x] Implement a robust request wrapper in `MixamoAPIClient` to handle rate limits and transient errors.
- [x] Task: Conductor - User Manual Verification 'Phase 1: API Client Foundation & Authentication' (Protocol in workflow.md)

## Phase 2: Character Management & Animation Catalog [checkpoint: cd0e8ea]
- [x] Task: Implement Character Upload via API. cf8327a
    - [x] Write tests for uploading an FBX and retrieving a `character_id`.
    - [x] Implement `upload_character` in `MixamoAPIClient`.
- [x] Task: Implement Local Animation Catalog Caching. f137f43
    - [x] Write tests for fetching the animation list and saving it to `animations_catalog.json`.
    - [x] Implement `fetch_animation_catalog` with local JSON caching.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Character Management & Animation Catalog' (Protocol in workflow.md)

## Phase 3: Export & Multi-threaded Downloads [checkpoint: 2c8e209]
- [x] Task: Implement Animation Export and Status Monitoring. b30b005
    - [x] Write tests for triggering an export and polling for completion.
    - [x] Implement `export_animation` and `monitor_export_progress`.
- [x] Task: Implement Multi-threaded Download Queue. fa20d16
    - [x] Write tests for concurrent downloads using `ThreadPoolExecutor`.
    - [x] Implement `download_animations` using multi-threading and reporting progress.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Export & Multi-threaded Downloads' (Protocol in workflow.md)

## Phase 4: Integration & UI Enhancements [checkpoint: bb3e77c]
- [x] Task: Refactor `MixamoBot` to use `MixamoAPIClient`. b4d4499
    - [x] Write integration tests for `MixamoBot` performing a full flow (Upload -> Catalog -> Download) via API.
    - [x] Update `MixamoBot` internal methods to delegate to `MixamoAPIClient`.
- [x] Task: Update GUI for API Status and Metrics. 9e4d93a
    - [x] Write tests for UI components reflecting API token validity and download progress.
    - [x] Implement UI updates in `cli/ui.py` for real-time API feedback.
- [x] Task: Conductor - User Manual Verification 'Phase 4: Integration & UI Enhancements' (Protocol in workflow.md)

