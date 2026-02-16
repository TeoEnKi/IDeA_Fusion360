Below is a **clean, corrected, and fully updated PRD in Markdown**, rewritten to reflect **everything we refined** in this conversation.

I have:

* **Removed** obsolete assumptions (hardware buttons, LEDs, scan rig, static-only constraint)  
* **Corrected** the solution to match the **Fusion 360 App Store add-in \+ palette overlay**  
* **Aligned** milestones, architecture, and user flow with **AI-generated animated guidance \+ 3D viewport interaction**  
* **Preserved the original pedagogical intent** (reduce research tax, surface hidden knowledge, 6-hour lesson constraint)

This is a **true PRD**, not just architecture notes.

---

# **PRD: AI-Driven Tutorial Overlay for Fusion 360**

## **1\. Problem Statement**

### **Goal (6-hour lesson constraint)**

Design a system that enables students with **zero or minimal CAD background** to complete a **functional, interactive CAD component** within a \~6-hour session by **reducing the “research tax”** (time lost searching for tools, tutorials, and fragmented explanations).

### **Core problem**

Past student prototypes and instructor examples contain valuable **“hidden knowledge”**:

* why a fillet exists  
* why a clearance is required  
* why a joint is dimensioned a certain way

However, this knowledge:

* is locked inside finished models or verbal explanations  
* is difficult for beginners to extract into a **repeatable design process**  
* cannot be easily followed in real time inside Fusion 360

Students spend cognitive effort **finding what to do**, instead of **learning why they are doing it**.

---

## **2\. Product Vision**

### **What this product is**

A **Fusion 360 add-in** that displays an **AI-generated, step-by-step tutorial overlay** inside Fusion, guiding students through a CAD workflow using:

* **Clear step cards** (short text \+ rationale)  
* **Animated cursor demonstrations** (move / click / drag)  
* **Real 3D model interaction** (camera focus, selection prompts, highlights)  
* **Symbol-based feedback** (✅ ⚠️ ⛔) instead of colors or hardware devices

The tutorial is generated dynamically by an AI model and played through a **side-panel (palette)** while the student works in the **real Fusion viewport**.

---

## **3\. Explicit Design Decisions (Corrections to Old PRD)**

### **Removed / deprecated**

* ❌ Physical scan rigs and camera arrays  
* ❌ ESP hardware buttons (Next / Prev / Ask / Toggle)  
* ❌ Status LEDs  
* ❌ Static-only tutorial constraint  
* ❌ Local Flask server as a runtime dependency

These were useful early exploration ideas but add friction, cost, and deployment complexity.

### **Adopted instead**

* ✅ Fusion 360 **Add-in \+ HTML Palette**  
* ✅ Autodesk App Store distribution  
* ✅ AI-generated **animated guidance**  
* ✅ **No physical hardware required**  
* ✅ All interaction via Fusion UI \+ palette  
* ✅ Python↔JS bridge for all model interaction

---

## **4\. Target Users**

### **Primary**

* First-time CAD learners  
* Secondary school / early university students  
* Workshop participants (short, intensive sessions)

### **Secondary**

* Instructors preparing guided exercises  
* Teaching assistants reviewing common mistakes  
* Curriculum designers building reusable learning assets

---

## **5\. Product Features**

### **A) Step-Based Tutorial Overlay**

Each tutorial consists of **ordered steps**, shown one at a time:

* What to do (short instruction)
* Why it matters (design intent)
* QC reminders (fit, clearance, manufacturability)
* Common mistakes to avoid

### **B) Automatic Step Progression (Action Detection)**

The tutorial **automatically advances** when the user completes the required action:

* **No manual "Next" button required** — reduces cognitive overhead
* Add-in monitors Fusion 360 events (timeline changes, sketch completion, feature creation)
* Each step defines **completion criteria** that trigger auto-advancement
* Visual + audio feedback confirms step completion before moving forward

**Supported completion triggers:**

* `sketchCreated` — user started a new sketch
* `sketchFinished` — user exited sketch mode
* `extrudeCreated` — extrusion feature added to timeline
* `filletCreated` — fillet feature added
* `selectionMade` — user selected required entity type
* `dimensionSet` — dimension constraint applied
* `featureCreated` — any feature added (generic)

**Fallback:** Manual "Skip" button available if detection fails or user wants to proceed without completing.

### **C) Animated Cursor Guidance (UI-side)**

Each step may include **cursor animation primitives**:

* Move cursor from A → B
* Click (expand/contract pulse)
* Drag (click \+ move \+ release)
* Pause / wait for user

These animations **demonstrate intent**, not automate Fusion.

### **D) Real 3D Model Interaction (Fusion-side)**

For each step, the add-in may:

* Move the camera to a clear viewpoint
* Zoom or isolate relevant geometry
* Prompt the user to select a face/edge/body
* Validate the selection
* Capture a viewport snapshot for reference

### **E) Symbol-Based Feedback (Accessibility-friendly)**

Status is shown using symbols, not colors:

* ✅ Correct / safe
* ⚠️ Caution / check this
* ⛔ Stop / incorrect

Symbols appear in the palette UI alongside each step.

---

## **6\. User Flow (6-Hour Lesson Optimized)**

### **0:00–0:30 — Context & Goal**

Instructor introduces:

* the target component  
* key functional constraints  
* what students will build by the end

### **0:30–1:00 — Tutorial Generation**

* Student opens the add-in from Fusion toolbar  
* Enters prompt or selects task  
* AI generates tutorial manifest

### **1:00–3:00 — Guided Build Loop**

For each step:

1. Step card appears in palette
2. Animated cursor demonstrates action
3. Fusion viewport highlights / zooms
4. **Student performs action in Fusion**
5. **Add-in detects completion automatically**
6. Symbol feedback confirms correctness
7. **Tutorial auto-advances to next step**

No manual button clicks required — the flow is seamless and action-driven.

### **3:00–4:45 — Independent Variation**

* Students adapt the design  
* Tutorial remains available as reference  
* QC symbols help self-check

### **4:45–6:00 — Review & Reflection**

* Instructor reviews outcomes  
* Students articulate “why” behind features  
* Tutorial may be saved or reused

---

## **7\. System Architecture (High-Level)**

### **Runtime Components**

#### **1\) Fusion Add-in (Python)**

* Creates toolbar command  
* Opens HTML palette  
* Fetches AI tutorial manifest  
* Executes Fusion API actions (camera, selection, highlight)  
* Sends step data \+ assets to palette

#### **2\) HTML Palette (JS/CSS)**

* Renders step cards
* Displays symbols (✅ ⚠️ ⛔)
* Plays cursor animations
* **Receives auto-progression signals from Python**
* Provides "Skip" button as fallback (not primary navigation)
* Shows completion feedback animation between steps
* Communicates with Python via Fusion bridge

#### **3\) AI Tutorial Service**

* Generates structured tutorial manifest  
* Outputs:  
  * steps  
  * cursor animation instructions  
  * Fusion action intents  
  * QC \+ rationale

---

## **8\. Data Contract (Tutorial Manifest)**

Each tutorial is a single JSON object containing:

### **Per-Step Data**

* `title`
* `instruction`
* `why`
* `qcChecks[]` (with symbols)
* `warnings[]`
* `uiAnimations[]` (move / click / drag / pause)
* `fusionActions[]` (camera, select, validate)
* `completionTrigger` — **NEW: defines what action completes this step**

### **Completion Trigger Schema**

```json
{
  "completionTrigger": {
    "type": "featureCreated",      // Event type to listen for
    "featureType": "ExtrudeFeature", // Optional: specific feature type
    "timeout": 300,                 // Optional: seconds before showing skip hint
    "validation": {                 // Optional: validate the result
      "minValue": 10,
      "maxValue": 100,
      "entityType": "face"
    }
  }
}
```

**Trigger Types:**
* `sketchCreated` — new sketch started
* `sketchFinished` — sketch mode exited
* `featureCreated` — timeline feature added (with optional `featureType`)
* `selectionMade` — entity selected (with optional `entityType`)
* `commandExecuted` — specific command run (with `commandId`)
* `manual` — requires explicit user action (Skip button)

This manifest is the **stable contract** between AI and player.

---

## **9\. Deployment & Distribution**

### **Primary Channel**

* **Autodesk App Store**

### **Packaging**

* `.bundle` format with `PackageContents.xml`  
* No external installers required  
* Per-user installation

### **Runtime Guarantees**

* No local servers  
* No open ports  
* No filesystem access from JS  
* All assets passed via Python↔JS bridge

---

## **10\. Non-Goals (Explicitly Out of Scope)**

* Fully automated CAD actions  
* Replacing instructor judgment  
* Advanced parametric reasoning AI  
* Real-time collaboration  
* External hardware dependencies

---

## **11\. Success Metrics**

### **Learning Effectiveness**

* Students complete a functional part within 6 hours  
* Students can explain **why** features exist

### **Usability**

* Add-in opens in \<2 seconds  
* Steps are understandable without external tutorials

### **Adoption**

* Instructors can reuse tutorials across cohorts  
* Students voluntarily replay steps

---

## **12\. Product Milestones (Updated)**

### **Milestone 1 — Tutorial Player MVP**

* Fusion add-in + palette
* Static step cards
* Symbol feedback
* Manual test tutorial

### **Milestone 2 — Animated Guidance**

* Cursor move / click / drag animations
* Replay per step

### **Milestone 3 — 3D Model Interaction + Auto-Progression**

* Camera control
* Selection prompts
* Validation feedback
* **Fusion event monitoring (timeline, sketches, features)**
* **Automatic step advancement on action completion**
* Skip button fallback

### **Milestone 4 — AI Integration**

* Replace test data with AI-generated manifests
* AI-generated completion triggers per step

