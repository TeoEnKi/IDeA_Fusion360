# Software Architecture: Fusion 360 AI Tutorial Plugin

## 1. Architecture Overview

The Fusion 360 AI Tutorial Plugin is a **local-only** Autodesk Fusion 360 add-in. A Python backend communicates with a vanilla JS/HTML frontend through Fusion 360's built-in palette bridge. There is no cloud backend, no external API, no HTTP server, and no external dependencies. All tutorial data is bundled as local JSON files and all assets are served as base64 data URLs.

---

## 2. System Components

### Fusion 360 Host
- Provides the palette (embedded Chromium) for the HTML/JS frontend
- Exposes Python API for toolbar commands, viewport control, timeline monitoring, and entity selection
- Manages add-in lifecycle (`run`/`stop`) and palette creation/destruction
- Destroys palettes on workspace switch; the add-in recreates them as needed

### Python Backend (`FusionTutorialOverlay.py` + `core/`)
- Registers toolbar commands and creates the HTML palette
- Manages tutorial state and step navigation (`TutorialManager`)
- Routes bridge messages from JS to action handlers
- Executes Fusion API actions — camera orientation, entity highlighting, viewport capture (`FusionActionsRunner`)
- Monitors Fusion events for completion detection (`CompletionDetector`)
- Detects workspace/environment context and polls for changes (`ContextDetector`, `ContextPoller`)
- Manages user consent preferences (`ConsentManager`)
- Generates redirect step animations for environment switching (`RedirectTemplateLibrary`)

### JS/HTML Frontend (`palette/`)
- Bridge initialization and message routing (`main.js`)
- Step navigation control with redirect mode management (`stepper.js`)
- First-run consent dialog (`consentDialog.js`)
- Step rendering via strategy pattern: `BaseRenderer` → `AnimatedRenderer`, `StaticRenderer`, `RedirectRenderer`
- QC checklist management with three-tier event matching
- Warning footer for non-blocking context mismatch alerts

---

## 3. Module Map

### Python Modules

| Module | Status | Description |
|---|---|---|
| `FusionTutorialOverlay.py` | **Active** | Entry point. Registers toolbar commands, creates palette, routes bridge messages. Contains **inline** `TutorialManager` and `FusionActionsRunner` classes used at runtime. |
| `core/completion_detector.py` | **Active** | Monitors Fusion API events (commandStarting, commandTerminated, timeline changes) to detect step completion. Contains `COMMAND_MAP` for mapping Fusion command IDs to event types. |
| `core/context_detector.py` | **Active** | Detects current workspace/environment (toolbar tab is primary signal, active sketch is secondary). |
| `core/context_poller.py` | **Active** | Polls context periodically during redirect steps and after context warnings; fires `contextResolved` when the user switches to the correct environment. |
| `core/consent_manager.py` | **Active** | Manages user consent for AI-guided redirect help (ON/ASK/OFF modes), persists preference to disk. |
| `core/redirect_templates.py` | **Active** | Generates redirect step data (animated instructions for switching workspaces/environments). |
| `core/assets.py` | **Not integrated** | `AssetManager` class for base64 data URL conversion with caching. Entry point uses inline `base64.b64encode` instead. |
| `core/tutorial_manager.py` | **Not integrated** | More structured `TutorialManager` replacement with validation. The inline class in the entry point is used at runtime. |
| `core/fusion_actions.py` | **Not integrated** | More structured `FusionActionsRunner` replacement. The inline class in the entry point is used at runtime. |

### JavaScript Modules

| Module | Description |
|---|---|
| `palette/static/js/main.js` | Bridge initialization, message routing, standalone test mode (IIFE pattern). |
| `palette/static/js/stepper.js` | Step navigation controller (Next/Previous/GoToStep), redirect mode management. |
| `palette/static/js/consentDialog.js` | First-run consent dialog for AI guidance preference. |
| `palette/static/js/renderers/BaseRenderer.js` | Base class — renders step info, visual steps, expanded content, QC checks, warnings. Loads `Fusion360_SolidNavbar.json` for component position resolution. |
| `palette/static/js/renderers/AnimatedRenderer.js` | Extends BaseRenderer — cursor animations (move, click, drag, pause, highlight, tooltip, arrow, focusCamera). Contains hardcoded `FULL_UI_POSITIONS` map for animation target resolution. |
| `palette/static/js/renderers/StaticRenderer.js` | Extends BaseRenderer — static step rendering without animations. |
| `palette/static/js/renderers/RedirectRenderer.js` | Renders redirect/environment-switch guidance overlays. |

### Data Files

| File | Description |
|---|---|
| `core/Fusion360_SolidNavbar.json` | UI component position map (toolbar groups, environment tabs, browser items, ViewCube). Used by `BaseRenderer.resolveHighlights` for visual step highlights. |
| `test_data/mug_tutorial.json` | Test tutorial (`mug_v2`, 10 steps). Used for both Fusion testing and standalone browser testing. |
| `assets/UI Images/` | UI reference images (Fusion 360 toolbar screenshots) used by visual steps and animation overlays. |

---

## 4. Data Flow

### Tutorial Load
```
Palette ready → JS sends "ready" → Python loads JSON file →
TutorialManager.load_from_file() → sends "tutorialLoaded" + step data →
JS Stepper.loadStep() → Renderer.render() → DOM
```

### Step Navigation
```
User clicks Next/Prev → JS sends "next"/"prev" → Python checks context requirements →
sends "contextWarning" if mismatch (non-blocking) → TutorialManager.next_step() →
executes fusionActions (camera, highlights) → auto-captures viewport if requested →
sends "updateStep" + step data → JS renders new step
```

### Completion Detection
```
User performs action in Fusion → Fusion API event fires →
CompletionDetector handles commandStarting/commandTerminated/timeline events →
maps to CompletionEvent → sends "completionEvent" to JS →
JS matches event to QC checklist items (three-tier: expectedCommand, eventToCommandMap, text fallback) →
updates visual state: pending → checking → completed
```

### Context Redirect
```
Step has "requires" field → Python detects context mismatch →
sends non-blocking "contextWarning" → starts ContextPoller →
user switches environment → poller detects match →
sends "contextResolved" → JS dismisses warning footer
```

---

## 5. Communication Protocol

All communication passes through Fusion 360's palette bridge as JSON strings. There are **no REST endpoints, WebSockets, or HTTP servers**.

- **JS → Python:** `window.adsk.fusionSendData('cycleEvent', JSON.stringify(data))`
- **Python → JS:** `palette.sendInfoToHTML('response', JSON.stringify(data))`

### JS → Python Actions

| Action | Description |
|---|---|
| `ready` | Palette loaded, request initial tutorial |
| `loadTutorial` | Load a specific tutorial by ID |
| `next` | Navigate to next step |
| `prev` | Navigate to previous step |
| `goToStep` | Navigate to a specific step index |
| `getConsent` | Query current consent/guidance mode |
| `setConsent` | Set consent mode (ON/ASK/OFF) |
| `showRedirectHelp` | User wants redirect guidance |
| `skipRedirectHelp` | User declined redirect guidance |
| `skipRedirect` | Skip active redirect animation |
| `captureViewport` | Capture viewport as screenshot |
| `checkQCConditions` | Check QC conditions against design state |
| `getDesignState` | Query current design state |
| `resetTracking` | Reset completion tracking for new step |

### Python → JS Response Types

| Action | Description |
|---|---|
| `tutorialLoaded` | Tutorial loaded with first step data |
| `updateStep` | Step data after navigation |
| `error` | Error message |
| `assets` | Preloaded asset data URLs |
| `consentRequired` | First-run consent dialog trigger |
| `consentSet` | Consent mode acknowledgment |
| `contextWarning` | Non-blocking environment mismatch warning |
| `contextResolved` | Environment now matches — dismiss warning |
| `askRedirect` | Ask user about redirect guidance |
| `redirectStep` | Redirect step animation data |
| `redirectComplete` | Redirect resolved, auto-advance |
| `redirectSkipped` | Redirect was skipped |
| `completionEvent` | QC completion event from Fusion API |
| `viewportCaptured` | Viewport screenshot as base64 data URL |
| `qcResults` | QC condition check results |
| `designState` | Current design state snapshot |

---

## 6. Key Architectural Patterns

### Strategy Pattern (Renderers)
`BaseRenderer` defines the rendering interface. `AnimatedRenderer`, `StaticRenderer`, and `RedirectRenderer` extend it with specialized behavior. The `Stepper` holds a reference to the active renderer and delegates `render()` calls.

### Handler Retention
Python event handlers must be stored in the global `_handlers` list to prevent garbage collection by Fusion's API. Without this, handlers are silently collected and events stop firing.

### Graceful Degradation
Core modules (`core/`) are imported with error handling. If any module fails to load, basic tutorial playback (navigation, rendering, step display) continues to work. The `CORE_MODULES_LOADED` flag gates optional features like completion detection, context warnings, and redirect guidance.

### Non-Blocking Context Warnings
Context mismatches produce a dismissible `#warningFooter` with configurable type (`warning`/`error`/`info`), optional action button with callback, and auto-dismiss after 5 seconds. Navigation always proceeds regardless of context match.

### Base64 Data URLs
Viewport screenshots and images are encoded as base64 data URLs at runtime. This avoids file:// CORS restrictions in Qt WebEngine and eliminates the need for an HTTP server.

### Dual Position Resolution
Two independent systems resolve UI element positions:
1. **`Fusion360_SolidNavbar.json`** — loaded by `BaseRenderer.resolveHighlights()` for visual step highlight overlays on the navbar image.
2. **`FULL_UI_POSITIONS` map** — hardcoded in `AnimatedRenderer.resolveAnimationTarget()` for cursor animation positioning on the full UI screenshot.

### Progressive QC Feedback
QC check items transition through visual states: `pending` (empty circle) → `checking` (filled circle, pulsing) → `completed` (checkmark). For `command_terminated` events (sketch tools that don't create timeline items), only one item completes at a time for progressive feedback. Feature events (extrude, fillet, etc.) can complete multiple matching items.

---

## 7. Future — Cloud Integration (Milestone 4)

Per the PRD, Milestone 4 envisions replacing local test tutorial data with AI-generated manifests. This would involve:

- A cloud backend (API gateway) accepting screenshots and prompts
- An orchestration layer (e.g., n8n) running AI model workflows
- AI models generating tutorial manifests and optional CAD geometry
- Object storage for generated assets
- A `cloud_client.py` module in the plugin for job creation, polling, and manifest download

**This architecture does not currently exist.** The current system is entirely local. Cloud integration is future work that would extend (not replace) the existing local playback architecture — the plugin would still use the same palette bridge, renderers, and step navigation; only the tutorial data source would change from local JSON files to cloud-generated manifests.
