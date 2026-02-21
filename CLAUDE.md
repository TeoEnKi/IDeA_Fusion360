# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Tutorial Overlay for Autodesk Fusion 360 — an add-in that provides step-by-step interactive tutorials with animated cursor guidance and real 3D viewport interaction. Packaged as a `.bundle` for the Autodesk App Store.

## Architecture

**Python backend** (`FusionTutorialOverlay.py` + `core/` modules) communicates with a **vanilla JS/HTML frontend** (`palette/`) through Fusion 360's palette bridge — no HTTP server, no external dependencies. No build system, linter, or test framework — the add-in runs directly as Python + HTML/JS.

### Communication Bridge
- **JS -> Python:** `window.adsk.fusionSendData('cycleEvent', JSON.stringify(data))`
- **Python -> JS:** `palette.sendInfoToHTML('response', JSON.stringify(data))`
- All data passes as JSON strings. No REST endpoints or WebSockets.

### Key Modules

**Python backend:**
- **`FusionTutorialOverlay.py`** — Entry point (~1200 lines). Registers toolbar commands, creates the HTML palette, routes bridge messages to action handlers via `PaletteHTMLEventHandler.notify()`. Contains **inline** `TutorialManager` and `FusionActionsRunner` classes that are used at runtime.
- **`core/completion_detector.py`** — Monitors Fusion API events (commandStarting, commandTerminated) to detect step completion. Fires `completionEvent` messages to JS for QC check toggling. Contains `COMMAND_MAP` for mapping Fusion command IDs to event types.
- **`core/context_detector.py`** — Detects current workspace/environment (toolbar tab is primary signal, active sketch is secondary).
- **`core/context_poller.py`** — Polls context periodically during redirect steps and after non-blocking context warnings; fires `contextResolved` when the user switches to the correct environment.
- **`core/consent_manager.py`** — Manages user consent for AI-guided redirect help (ON/ASK/OFF modes), persists preference to disk.
- **`core/redirect_templates.py`** — Generates redirect step data (animated instructions for switching workspaces/environments).
- **`core/assets.py`** — `AssetManager` class for base64 data URL conversion with caching. **Not connected** — inline `base64.b64encode` is used instead.
- **`core/tutorial_manager.py`** — More structured `TutorialManager` with validation. **Not connected** — the inline class in `FusionTutorialOverlay.py` is used at runtime.
- **`core/fusion_actions.py`** — More structured `FusionActionsRunner`. **Not connected** — the inline class in `FusionTutorialOverlay.py` is used at runtime.

**JavaScript frontend (no module bundler — all globals on `window.*`, loaded in dependency order):**
- **`palette/static/js/main.js`** — Bridge initialization, message routing, standalone test mode (IIFE pattern).
- **`palette/static/js/stepper.js`** — Step navigation controller (Next/Previous/GoToStep), redirect mode management.
- **`palette/static/js/consentDialog.js`** — First-run consent dialog for AI guidance preference.
- **`palette/static/js/renderers/`** — Strategy pattern: `BaseRenderer` → `AnimatedRenderer`, `StaticRenderer`, `RedirectRenderer`.

**Data files:**
- **`assets/UI Images/Solid/Solid_UIComponents.json`** and **`assets/UI Images/Sketch/Sketch_UIComponents.json`** — Per-environment UI component position maps (toolbar groups, environment tabs, navigation bar). Loaded by `BaseRenderer` at init. Each has corresponding screenshot PNGs (`Solid_0.png`..`Solid_2.png`, `Sketch_0.png`..`Sketch_3.png`) where the `imageIndex` field selects which screenshot to display (e.g., 0=base, 1=Create expanded, 2=Modify expanded).
- **`test_data/mug_tutorial.json`** — Test tutorial (`mug_v2`, 10 steps). Used for both Fusion testing and standalone browser testing.

### Data Flow
```
Tutorial JSON → Python TutorialManager → Bridge → JS Stepper/Renderer → DOM
User Action → JS Bridge Event → Python Handler → Fusion API → Result back to JS
Fusion API Event → CompletionDetector → Bridge completionEvent → JS QC update
```

### Bridge Message Reference

**JS → Python actions** (sent via `fusionSendData`):
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

**Python → JS response types** (sent via `sendInfoToHTML`):
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

### Context Warnings
Context warnings are **non-blocking** — navigation always proceeds even if the user is in the wrong environment. A dismissible `#warningFooter` appears with configurable type (`warning`/`error`/`info`), optional action button with callback, and auto-dismiss after 5 seconds or when the context poller detects the user has switched to the correct environment.

### QC Completion Detection
Tutorial steps can include `qcChecks` with an `expectedCommand` field matching a Fusion 360 command ID (e.g., `"expectedCommand": "SketchLine"`). The completion detector monitors Fusion API events and sends `completionEvent` messages to JS.

**Three-tier matching in JS:**
1. **Primary:** `data-expected-command` attribute on QC list item matches `event.additionalInfo.commandId` directly.
2. **Secondary:** `eventToCommandMap` maps feature event types (e.g., `extrude_created`) to the command IDs that produce them (e.g., `Extrude`).
3. **Fallback:** Text-based matching for items without `expectedCommand` (e.g., item text contains "fillet" and event is `fillet_created`).

**Visual states:** `pending` (empty circle) → `checking` (filled circle, pulsing) → `completed` (checkmark).

Sketch tools (SketchLine, Sketch3PointArc, etc.) don't create timeline items — `TimelineEventHandler` fires `command_terminated` events for these so JS can still complete checks. Feature tools (Extrude, Fillet, Revolve) DO create timeline items and emit specific event types like `extrude_created`. For `command_terminated` events, JS completes one QC check at a time for progressive feedback.

### Target Resolution System
`BaseRenderer.resolveTarget(path)` is the single unified system for resolving dot-separated target paths (e.g., `"toolbar.create.extrude"`) to positions in the UI component maps. Both `visualStep.highlights` and cursor animations in `AnimatedRenderer` use this same system. Resolution uses a 9-strategy cascade: direct lookup → stripped segments → progressive path shortening → wildcard matching → camelCase conversion → substring match → browser fallback → bare segment. Targets starting with `canvas.*` or `dialog.*` return null (these are viewport/dialog references, not toolbar targets).

## Development Workflow

### Quick UI iteration (no Fusion 360 needed)
Start a local HTTP server from the `Contents/` directory and open the palette in a browser:
```bash
cd FusionTutorialOverlay.bundle/Contents
python -m http.server 8000
# Open http://localhost:8000/palette/tutorial_palette.html
```
The palette auto-detects the missing Fusion bridge and enters standalone mode, loading `test_data/mug_tutorial.json`. Opening the HTML file directly via `file://` will hit CORS errors and fall back to inline placeholder data.

### Full testing in Fusion 360
1. Copy `FusionTutorialOverlay.bundle` to `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns`
2. In Fusion: Tools > Add-Ins > enable "FusionTutorialOverlay" > Run
3. Button appears in Tools > Utilities panel
4. Python errors: View > Python Console
5. JS errors: F12 (Qt WebEngine DevTools)
6. Debug log: `FusionTutorialOverlay.bundle/Contents/debug.log`

**After editing files in the repo, you must re-copy the bundle to the AddIns directory** for changes to take effect in Fusion. There is no sync script.

### Tutorial JSON format
Test tutorials live in `test_data/`. The current test tutorial is `mug_tutorial.json` (tutorialId: `mug_v2`, 10 steps). The tutorial ID is hard-coded in `_handle_ready()` — changing which tutorial loads requires editing that method.

**Step fields:**
- `stepId`, `stepNumber`, `title` — Step identification
- `instruction` — Primary instruction text
- `detailedText` — Secondary explanation text
- `tips` — Array of tip strings or `{symbol, text}` objects
- `qcChecks` — Array of `{text, expectedCommand}` for completion detection
- `warnings` — Array of `{symbol, text}` for step warnings
- `uiAnimations` — Array of animation directives (see animation types below)
- `fusionActions` — Array of Fusion API actions (only `highlight.body` and `prompt.selectEntity` are implemented; other types like `ui.openWorkspace` are defined in JSON but are no-ops)
- `requires` — Context requirements (`{workspace, environment}`)
- `visualStep` — `{image, highlights[], caption, useNavbar}` for UI reference images with positioned highlight overlays; highlights can use `component` references resolved via the UIComponents JSON files
- `expandedContent` — `{whyThisMatters, tips, dimensions, parameters, referenceImage, nextSteps, skillsLearned}`
- `captureViewport` — Boolean; auto-captures Fusion viewport screenshot on step load (read-only; does not control the camera)

**Animation types:** `move`, `click`, `drag`, `pause`, `highlight`, `tooltip`, `arrow`. Coordinates in `move`/`click`/`drag` are percentages (0–100) relative to the animation area. `highlight`/`tooltip`/`arrow` use `target` strings (e.g., `"toolbar.create.extrude"`) resolved via `BaseRenderer.resolveTarget()`.

## Important Conventions

- **Python handlers must be retained** in the `_handlers` list to prevent garbage collection by Fusion's API. `CompletionDetector` manages its own internal `_handlers` list separately.
- **Optional modules degrade gracefully** — core tutorial playback works even if context detection or completion detection fails to load.
- **Assets are base64 data URLs** — viewport screenshots and images are encoded at runtime, never served via HTTP.
- **Fusion destroys palettes on workspace switch** — the add-in recreates them as needed.
- **JS must wait for `window.adsk`** before calling bridge methods (`waitForBridge()` in main.js).
- **Duplicate classes exist** — `TutorialManager` and `FusionActionsRunner` have inline versions in `FusionTutorialOverlay.py` (used at runtime) and more structured versions in `core/` (not yet connected). Edits to the `core/` versions have no effect on runtime behavior.
- Python: `snake_case` functions, `PascalCase` classes, `UPPER_SNAKE_CASE` constants.
- JavaScript: `camelCase` functions/variables, `PascalCase` classes.
- QC feedback uses symbols (checkmark, warning, stop) rather than colors for accessibility.
- **`Fusion360_AI_Tutorial_Software_ArchitecturePlan.md` describes target state**, not always current behavior (e.g., it says `warnings` field was removed from the schema, but the code still renders it).
