# Implementation Plan: Mixamo API Pivot

## Phase 1: API Client Foundation & Authentication
- [ ] Task: Create `MixamoAPIClient` class with basic authentication logic.
    - [ ] Write tests for `MixamoAPIClient` initializing with a token from `mixamo_token.txt`.
    - [ ] Implement `MixamoAPIClient` to read token and handle basic headers (`Authorization`, `X-Api-Key`).
- [ ] Task: Implement API Request Wrapper with Retries.
    - [ ] Write tests for API request retries using `tenacity`.
    - [ ] Implement a robust request wrapper in `MixamoAPIClient` to handle rate limits and transient errors.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: API Client Foundation & Authentication' (Protocol in workflow.md)

## Phase 2: Character Management & Animation Catalog
- [ ] Task: Implement Character Upload via API.
    - [ ] Write tests for uploading an FBX and retrieving a `character_id`.
    - [ ] Implement `upload_character` in `MixamoAPIClient`.
- [ ] Task: Implement Local Animation Catalog Caching.
    - [ ] Write tests for fetching the animation list and saving it to `animations_catalog.json`.
    - [ ] Implement `fetch_animation_catalog` with local JSON caching.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Character Management & Animation Catalog' (Protocol in workflow.md)

## Phase 3: Export & Multi-threaded Downloads
- [ ] Task: Implement Animation Export and Status Monitoring.
    - [ ] Write tests for triggering an export and polling for completion.
    - [ ] Implement `export_animation` and `monitor_export_progress`.
- [ ] Task: Implement Multi-threaded Download Queue.
    - [ ] Write tests for concurrent downloads using `ThreadPoolExecutor`.
    - [ ] Implement `download_animations` using multi-threading and reporting progress.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Export & Multi-threaded Downloads' (Protocol in workflow.md)

## Phase 4: Integration & UI Enhancements
- [ ] Task: Refactor `MixamoBot` to use `MixamoAPIClient`.
    - [ ] Write integration tests for `MixamoBot` performing a full flow (Upload -> Catalog -> Download) via API.
    - [ ] Update `MixamoBot` internal methods to delegate to `MixamoAPIClient`.
- [ ] Task: Update GUI for API Status and Metrics.
    - [ ] Write tests for UI components reflecting API token validity and download progress.
    - [ ] Implement UI updates in `cli/ui.py` for real-time API feedback.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Integration & UI Enhancements' (Protocol in workflow.md)
