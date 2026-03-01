# Cloud Tutorial Loader Implementation (2026-03-01)

## Scope Implemented
- Switched plugin tutorial bootstrap to unauthenticated cloud fetch:
  - `GET https://narwhjorl.app.n8n.cloud/webhook/get-latest-tutorial`
- Removed local tutorial fallback behavior from plugin tutorial flow and standalone palette mode.
- Kept existing bridge render/update contracts (`tutorialLoaded`, `error`, `updateStep`) intact.
- Preserved app-level behavior outside tutorial bootstrap path.

## Code Changes

### 1) New service
- Added `FusionTutorialOverlay.bundle/Contents/core/tutorial_plugin_service.py`
  - `WEBHOOK_URL` constant
  - `fetch_latest_tutorial(timeout_seconds=15)`
  - Uses stdlib `urllib.request` + `json`
  - Normalized error outputs:
    - timeout
    - network/URL errors
    - non-2xx responses
    - invalid JSON

### 2) Backend bootstrap wiring
- Updated `FusionTutorialOverlay.bundle/Contents/FusionTutorialOverlay.py`
  - Imports `fetch_latest_tutorial`
  - `_handle_ready()` now loads latest cloud tutorial
  - Added `_handle_load_latest_tutorial()`:
    - fetch from webhook
    - validate top-level object + non-empty `steps[]`
    - initialize inline `TutorialManager` from memory via `load_tutorial(data)`
    - keep initial context normalization, fusion actions, viewport capture, mismatch feedback
  - `loadTutorial` bridge action is now explicit legacy-disabled error in cloud-only mode

### 3) Frontend behavior
- Updated `FusionTutorialOverlay.bundle/Contents/palette/static/js/main.js`
  - Removed automatic `ready` retry loop
  - Removed automatic standalone tutorial fallback
  - Bridge missing now shows blocking error state
  - Retry button sends single manual `ready` request
  - Standalone helper functions now show blocking error only

## Validation Performed
- Python syntax check:
  - `python -m py_compile FusionTutorialOverlay.bundle/Contents/FusionTutorialOverlay.py FusionTutorialOverlay.bundle/Contents/core/tutorial_plugin_service.py`
- Static scan confirms no auth/session/token additions in plugin path.

## Notes
- Runtime now depends on webhook availability for tutorial bootstrap.
- Local `test_data/` files remain in repo as fixtures/reference but are not bootstrap fallbacks.
