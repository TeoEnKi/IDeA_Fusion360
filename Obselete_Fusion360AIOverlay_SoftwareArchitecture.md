# **Fusion 360 AI Tutorial Overlay — Software Architecture**

## **0) What changed vs the original PRD**

* **Distribution:** target **Autodesk App Store** packaging (`.bundle` + `PackageContents.xml`) instead of "copy ZIP into AddIns."
* **Issue 2 fix:** **remove Flask from production** (no `localhost:5000`, no local HTTP server). The original PRD used Flask to serve JSON/images over HTTP, but we now use **Python -> JS bridge** to deliver tutorial + assets.
* **User interaction UX:** **no ESP / physical buttons**, no color LEDs. Status is shown as **symbols** in the palette UI: checkmark (good) / warning (caution) / stop (fix).
* **3D model interaction:** done **in Fusion's real viewport** via Python (camera, highlight, selection prompts), because JS **cannot access the Fusion API directly**.

---

## **1) Product goal**

An AI-driven tutorial "overlay" that:

* Shows **step-by-step instructions** (text + callouts + QC + warnings)
* Plays **cursor animations** beside the step (move/click/drag)
* Guides the user in the **real Fusion viewport** (camera focus, selection prompts, highlight)
* Is **easy to install and launch** via Autodesk App Store distribution

---

## **2) High-level architecture (runtime)**

          +------------------------------+
           |        AI Tutorial API        |
           |  POST /tutorials/generate     |
           +---------------+--------------+
                           | HTTPS (JSON)
                           v
+----------------------------------------------------------+
|               Fusion 360 Add-in (Python)                 |
|  - Creates toolbar command + opens palette               |
|  - Fetches AI manifest + validates schema                |
|  - Runs Fusion Actions (camera/highlight/selection)      |
|  - Detects context (workspace/environment/sketch)        |
|  - Monitors completion events (timeline/command)         |
|  - Packages assets into data URLs                        |
|  - Sends step payloads to JS via sendInfoToHTML          |
|  - Receives step events from JS via fusionSendData       |
+----------------------------+-----------------------------+
                             |  Fusion messaging bridge (JSON)
                             |  JS->Python: adsk.fusionSendData()
                             |  Python->JS: palette.sendInfoToHTML()
                             v
         +-----------------------------------+
         |     HTML Palette (JS/CSS UI)      |
         | - Step cards + symbols            |
         | - Cursor animation player         |
         | - Annotations overlay (% coords)  |
         | - Next/Prev buttons               |
         | - Non-blocking context warnings   |
         | - QC checklist with live toggling  |
         +-----------------------------------+

(Fusion viewport is the real 3D scene; Python controls it via Fusion API.)

**Why this split is necessary**

* The palette **can't call Fusion API** and **can't access filesystem** like a normal app.
* So: **JS renders** + **Python drives Fusion**.

---

## **3) Deployment architecture (Autodesk App Store-ready)**

### **3.1 Packaging target**

Ship as an App Store-compatible **`.bundle`** package (Autodesk uses `.bundle` + `PackageContents.xml`).

### **3.2 Add-in requirements**

* Must be an **add-in**, not a script, because you need persistent UI + palette + handlers.
* Use **Qt WebEngine / "new browser"** (set `useNewWebBrowser=True`) when creating palette.
* Store handler references globally to avoid garbage collection (common Fusion add-in pitfall).

---

## **4) Core components (detailed)**

### **A) Fusion Add-in (Python) — "Orchestrator + Fusion Actions"**

**Responsibilities**

1. **UI setup**
   * Create toolbar command -> open palette
2. **Bridge handler**
   * Receive `next`, `prev`, `goToStep` from JS via `adsk.fusionSendData()`
   * Send `updateStep`, `assets`, `completionEvent`, `contextWarning` back to JS via `palette.sendInfoToHTML()`
3. **AI manifest retrieval**
   * Call AI service (HTTPS) to get tutorial manifest (JSON)
   * Validate and normalize manifest before sending to UI
4. **Fusion Actions Runner (3D model interaction)**
   * Camera: fit, zoom, orient, focus region
   * Selection prompts: "pick a face/edge/body"
   * Optional: isolate/show/hide bodies for clarity
   * Optional: capture viewport images (for "what it should look like" snapshots)
5. **Asset Manager**
   * Read cursor sprite and any images
   * Convert to **data URLs** (e.g., `data:image/png;base64,...`)
   * Push to palette in a single "assets payload" (no Flask)
6. **Context Detection + Polling**
   * `context_detector.py` — Detects current workspace and environment. Toolbar tab state is the primary signal (most reliable, updates immediately on click); active sketch (`design.activeEditObject`) is a secondary signal that can lag behind the UI.
   * `context_poller.py` — Periodically re-checks context during redirect steps and after non-blocking context warnings. Fires a callback when the user switches to the correct environment, allowing the warning to auto-dismiss.
7. **Consent Manager**
   * `consent_manager.py` — Manages the user's preference for AI-guided redirect help (ON / ASK / OFF modes). Persists to a JSON file in `user_data/`. Shows a first-run consent dialog.
8. **Redirect Templates**
   * `redirect_templates.py` — Generates animated redirect step data showing users how to switch workspaces/environments when context doesn't match step requirements.
9. **Completion Detection**
   * `completion_detector.py` — Monitors Fusion API events (timeline item creation, command start/terminate) to detect when the user performs actions matching tutorial QC checks. Sends `completionEvent` messages to the palette for live QC checklist toggling.

**Important runtime edge-case**

* Fusion deletes palettes when switching workspaces; add-in must detect and recreate.

---

### **B) HTML Palette (JS/CSS) — "Step UI + Cursor Animation"**

**Responsibilities**

1. **Step Card UI**
   * Title, short instruction, detailed instruction
   * Annotations overlay (percent-based coords)
   * QC + warnings displayed with symbols (instead of LEDs/colors)
   * QC checks toggle automatically via `completionEvent` from Python — items transition through pending -> checking -> completed states
2. **Navigation UI**
   * Buttons: Next / Previous
   * Optional keyboard support when palette has focus (viewport steals focus often)
   * Context warnings are non-blocking — navigation always proceeds; a dismissible footer warning auto-dismisses on timer or when context resolves
3. **Animation Player**
   * Plays per-step cursor directives: `move`, `click`, `drag`, `pause`
4. **Bridge client**
   * Wait for `window.adsk` injection before calling `fusionSendData` (timing issue)
5. **Renderer strategy pattern**
   * Keep Static and Animated rendering decoupled; add `AnimatedRenderer` without refactor
   * `RedirectRenderer` handles redirect step display when context guidance is active
6. **Consent Dialog**
   * `consentDialog.js` — First-run dialog asking user about AI guidance preference

---

### **C) AI Tutorial API (external)**

**Responsibilities**

* Generate tutorial manifest with:
  * steps, text, QC, warnings
  * cursor animation directives (move/click/drag)
  * fusion actions (camera/selection guidance)

---

## **5) Data contracts**

### **5.1 Tutorial manifest (conceptual)**

A single JSON object: `tutorialId`, `title`, `steps[]`.

Each step contains *two tracks*:

* **UI track** (what JS shows/animates)
* **Fusion track** (what Python does in the viewport)

### **5.2 Step structure (recommended fields)**

* `stepId`, `stepNumber`, `title`
* `instruction` (short), `detailedText` (long)
* `annotations[]` (percent coordinates)
* `qcChecks[]` (each item has `symbol` and `text`; optionally `expectedCommand` for auto-completion matching)
* `warnings[]` (each item has `symbol` and text)
* `uiAnimations[]` (cursor directives)
* `fusionActions[]` (3D viewport actions executed by Python)
* `requires` (context requirements: `workspace`, `environment`, `hasActiveDocument`, `hasActiveSketch`)
* `expectedCommand` (Fusion command ID for completion detection, e.g. `"SketchLine"`, `"Extrude"`)
* `captureViewport` (boolean — auto-capture a viewport screenshot when this step loads)

### **5.3 Cursor animation directives (UI track)**

Minimum directive types:

* `move`: from(x,y) -> to(x,y), duration, easing
* `click`: at(x,y), pulse parameters (expand/contract), optional ripple
* `drag`: from(x,y) -> to(x,y), duration, pressed=true during motion
* `pause`: duration OR "wait for user Next"

These animations are "teaching visuals" in the palette, not actual clicking inside Fusion.

### **5.4 Fusion actions (3D model interaction track)**

Minimum action types (MVP):

* `camera.fit` / `camera.orient` / `camera.focus`
* `prompt.selectEntity` (face/edge/body)
* `validate.selection` (type/constraints)
* `viewport.captureImage` (optional screenshot for step card)

---

## **6) Runtime workflow (end-to-end)**

### **6.1 Startup**

1. User installs from App Store -> add-in appears in Fusion.
2. User clicks toolbar button -> palette opens. (Palette created with Qt browser)
3. First-run consent dialog asks about AI guidance preference.

### **6.2 Generate tutorial**

1. Palette shows "Generate tutorial" UI.
2. JS requests generation via `adsk.fusionSendData('generateTutorial', {...})`.
3. Python calls AI API, validates manifest.

### **6.3 Step display + 3D interaction (per step)**

1. JS triggers `next` or `prev` on button click.
2. Python checks context requirements for target step:
   * If mismatched: sends non-blocking `contextWarning` to JS (warning footer auto-dismisses after 5s or when context resolves)
   * Navigation **always proceeds** regardless of context match
3. Python runs `fusionActions[]` (camera, selection prompt, etc.).
4. Python sends step payload back via `sendInfoToHTML('response', payload)`
5. JS:
   * updates text + annotations
   * displays QC symbols (pending state)
   * plays `uiAnimations[]` cursor demo
6. User performs the real action in Fusion viewport.
7. Completion detector fires `completionEvent` -> JS toggles matching QC checks to completed.

---

## **7) Solving "Issue 2" (no Flask) — Option A**

Original PRD uses Flask to serve JSON + images and avoid `file://` palette problems.
Refined approach:

* **Python reads assets** (cursor sprite, optional screenshots)
* Converts them to **data URLs**
* Sends them to JS through the bridge (`sendInfoToHTML('assets', ...)`)
* JS uses them directly in `<img src="data:...">`

Result: no ports, no firewall prompts, no localhost dependency.

---

## **8) Project structure**

```
FusionTutorialOverlay.bundle/
+-- PackageContents.xml
+-- Contents/
    +-- FusionTutorialOverlay.py          # Entry point, palette creation, bridge handler
    +-- FusionTutorialOverlay.manifest
    +-- core/
    |   +-- __init__.py
    |   +-- tutorial_manager.py           # Load/validate manifest + state
    |   +-- completion_detector.py        # Timeline/command event monitoring, QC detection
    |   +-- context_detector.py           # Workspace/environment detection (toolbar tabs)
    |   +-- context_poller.py             # Periodic context re-checking
    |   +-- consent_manager.py            # AI guidance consent (ON/ASK/OFF)
    |   +-- redirect_templates.py         # Generate redirect step data
    |   +-- fusion_actions.py             # Camera/select/validate/capture
    |   +-- assets.py                     # Cursor sprite -> data URL
    |   +-- Fusion360_SolidNavbar.json    # UI navbar mapping data
    +-- palette/
    |   +-- tutorial_palette.html
    |   +-- static/
    |       +-- css/
    |       |   +-- main.css
    |       +-- js/
    |           +-- main.js               # Bridge init, waits for window.adsk
    |           +-- stepper.js            # Step navigation (Next/Previous)
    |           +-- consentDialog.js       # First-run consent dialog
    |           +-- renderers/
    |               +-- BaseRenderer.js
    |               +-- StaticRenderer.js
    |               +-- AnimatedRenderer.js   # Cursor move/click/drag
    |               +-- RedirectRenderer.js   # Context redirect guidance
    +-- test_data/
    |   +-- mug_tutorial.json             # Test tutorial for standalone mode
    |   +-- existing_model_tutorial.json
    |   +-- fusion_ui.png
    |   +-- mug_reference.png
    +-- screenshots/                      # Auto-captured viewport images
    +-- assets/
        +-- UI Images/
            +-- Fusion360SolidNavbar.png
```

---

## **9) UX spec: symbols (not colors, not hardware)**

In the palette:

* Checkmark — **Good / correct**
* Warning — **Caution / check this**
* Stop — **Stop / fix before continuing**

Use symbols consistently for:

* QC checks
* Warnings
* Selection validation feedback from Python

---

## **10) Non-negotiable technical constraints**

* JS cannot access Fusion API; must go through Python.
* `window.adsk` is injected after load; you must wait/poll before calling bridge.
* Palette can be invalidated on workspace switches; recreate when needed.
