# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Tutorial Overlay for Autodesk Fusion 360 — an add-in that provides step-by-step interactive tutorials with animated cursor guidance and real 3D viewport interaction. Packaged as a `.bundle` for the Autodesk App Store.

## Architecture

**Python backend** (`FusionTutorialOverlay.py` + `core/` modules) communicates with a **vanilla JS/HTML frontend** (`palette/`) through Fusion 360's palette bridge — no HTTP server, no external dependencies.

### Communication Bridge
- **JS -> Python:** `window.adsk.fusionSendData('cycleEvent', JSON.stringify(data))`
- **Python -> JS:** `palette.sendInfoToHTML('response', JSON.stringify(data))`
- All data passes as JSON strings. No REST endpoints or WebSockets.

### Key Modules
- **`FusionTutorialOverlay.py`** — Entry point. Registers toolbar commands, creates the HTML palette, routes bridge messages to action handlers.
- **`core/tutorial_manager.py`** — Loads/validates tutorial JSON, manages step state.
- **`core/completion_detector.py`** — Monitors Fusion API events (timeline, sketch, command) to detect step completion. Fires `completionEvent` messages to JS for QC check toggling.
- **`core/context_detector.py`** — Detects current workspace/environment (toolbar tab is primary signal, active sketch is secondary).
- **`core/context_poller.py`** — Polls context periodically during redirect steps and after non-blocking context warnings; fires `contextResolved` when the user switches to the correct environment.
- **`core/consent_manager.py`** — Manages user consent for AI-guided redirect help (ON/ASK/OFF modes), persists preference to disk.
- **`core/redirect_templates.py`** — Generates redirect step data (animated instructions for switching workspaces/environments).
- **`core/fusion_actions.py`** — Wraps Fusion 360 API calls (camera, selection, highlighting).
- **`palette/static/js/main.js`** — Bridge initialization, message routing (IIFE pattern).
- **`palette/static/js/stepper.js`** — Step navigation controller (Next/Previous).
- **`palette/static/js/consentDialog.js`** — First-run consent dialog for AI guidance preference.
- **`palette/static/js/renderers/`** — Strategy pattern: `BaseRenderer` -> `AnimatedRenderer`, `StaticRenderer`, `RedirectRenderer`.

### Data Flow
```
Tutorial JSON -> Python TutorialManager -> Bridge -> JS Stepper/Renderer -> DOM
User Action -> JS Bridge Event -> Python Handler -> Fusion API -> Result back to JS
```

### Context Warnings
Context warnings are **non-blocking** — navigation always proceeds even if the user is in the wrong environment. A dismissible warning footer appears and auto-dismisses after 5 seconds or when the context poller detects the user has switched to the correct environment.

### QC Completion Detection
Tutorial steps can include `qcChecks` with an `expectedCommand` field matching a Fusion 360 command ID (e.g., `"expectedCommand": "SketchLine"`). The completion detector monitors Fusion API events and sends `completionEvent` messages to JS. Sketch tools (SketchLine, Sketch3PointArc, etc.) emit `command_terminated` events; feature tools (Extrude, Fillet) emit specific events like `extrude_created`. JS completes one QC check at a time for progressive feedback.

## Development Workflow

There is **no build system, linter, or test framework**. The add-in runs directly as Python + HTML/JS.

### Quick UI iteration (no Fusion 360 needed)
Open `FusionTutorialOverlay.bundle/Contents/palette/tutorial_palette.html` in a browser. It auto-detects the missing Fusion bridge and enters standalone mode: `main.js` fetches `test_data/mug_tutorial.json` via `fetch()`; falls back to inline placeholder data on CORS error (use a local HTTP server for full testing).

### Full testing in Fusion 360
1. Copy `FusionTutorialOverlay.bundle` to `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns`
2. In Fusion: Tools > Add-Ins > enable "FusionTutorialOverlay" > Run
3. Button appears in Tools > Utilities panel
4. Python errors: View > Python Console
5. JS errors: F12 (Qt WebEngine DevTools)
6. Debug log: `FusionTutorialOverlay.bundle/Contents/debug.log`

### Tutorial JSON format
Test tutorials live in `test_data/`. See `README_TESTING.md` for the full schema including `uiAnimations` (move, click, drag, pause) and `fusionActions` (camera.orient, camera.fit, highlight.body, etc.). Coordinates in animations are percentages (0-100) relative to the animation area. Steps may include `requires` (context requirements), `expectedCommand` (for QC matching), and `captureViewport` (auto-screenshot on step load).

## Important Conventions

- **Python handlers must be retained** in the `_handlers` list to prevent garbage collection by Fusion's API.
- **Optional modules degrade gracefully** — core tutorial playback works even if context detection or completion detection fails to load.
- **Assets are base64 data URLs** — viewport screenshots and images are encoded at runtime, never served via HTTP.
- **Fusion destroys palettes on workspace switch** — the add-in recreates them as needed.
- **JS must wait for `window.adsk`** before calling bridge methods (`waitForBridge()` in main.js).
- Python: `snake_case` functions, `PascalCase` classes, `UPPER_SNAKE_CASE` constants.
- JavaScript: `camelCase` functions/variables, `PascalCase` classes.
- QC feedback uses symbols (checkmark, warning, stop) rather than colors for accessibility.
