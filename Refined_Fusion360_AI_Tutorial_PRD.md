# Refined PRD: Fusion 360 AI Tutorial Plugin (Cloud‑Generated Tutorial System)

## 1. Product Overview

The Fusion 360 AI Tutorial Plugin is an Autodesk Fusion 360 add‑in that
connects to a cloud‑based AI tutorial generation system. The plugin
captures user context (screenshots and workspace state), sends it to the
cloud, receives AI‑generated tutorials and optional CAD models, and
plays them interactively inside Fusion 360.

The system separates responsibilities into:

-   Cloud: Tutorial generation
-   Plugin: Tutorial playback and Fusion interaction

This ensures scalability, reliability, and maintainability.

------------------------------------------------------------------------

## 2. Problem Statement

Beginner CAD users face a large research tax --- time spent searching
tutorials instead of designing.

Help students with **zero or minimal CAD background** to complete a **functional, interactive CAD component** within a \~6-hour session by **reducing the “research tax”** (time lost searching for tools, tutorials, and fragmented explanations).

Goal: Allow beginners to build functional CAD models efficiently by
providing real‑time, AI‑generated tutorial guidance inside Fusion 360.

------------------------------------------------------------------------

## 3. Product Goals

Primary goals:

-   Reduce tutorial research time
-   Provide contextual, interactive tutorials
-   Enable users to complete CAD workflows faster
-   Integrate seamlessly into Fusion 360

Secondary goals:

-   Allow tutorial generation from screenshots and prompts
-   Support AI‑generated CAD models
-   Provide reusable tutorial manifests

------------------------------------------------------------------------

## 4. System Responsibilities

Cloud System:

-   Accept screenshots and prompts
-   Generate tutorial manifest
-   Generate optional CAD models
-   Store tutorial assets

Plugin:

-   Capture screenshots
-   Upload images
-   Request tutorial generation
-   Download tutorial manifest
-   Play tutorial interactively
-   Execute Fusion actions

------------------------------------------------------------------------

## 5. Product Features

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

------------------------------------------------------------------------

## 6. User Flow

Step 1: User opens plugin

Step 2: component stand captures screenshots

Step 3: User uploads screenshots to plugin

Step 4: User clicks Generate Tutorial

Step 5: Plugin requests tutorial generation

Step 6: Cloud generates tutorial

Step 7: Plugin downloads tutorial

Step 8: Plugin plays tutorial

------------------------------------------------------------------------

## 7. Tutorial Manifest Structure

Each tutorial contains:

-   tutorialId
-   title
-   steps

Each step contains:

-   title
-   instruction
-   detailedText
-   uiAnimations
-   fusionActions
-   completionTrigger
-   qcChecks
-   warnings

------------------------------------------------------------------------

## 8. Completion Trigger Schema

Defines how steps complete automatically.

Example:

{ "type": "featureCreated", "featureType": "ExtrudeFeature" }

------------------------------------------------------------------------

## 9. Functional Requirements

Plugin must:

-   Upload screenshots
-   Create tutorial jobs
-   Poll job status
-   Download tutorial manifest
-   Execute tutorial steps

Cloud must:

-   Accept uploads
-   Generate tutorial manifest
-   Store tutorial outputs

------------------------------------------------------------------------

## 10. Non‑Functional Requirements

Performance:

-   Tutorial generation: \<120 seconds
-   Tutorial playback startup: \<2 seconds

Reliability:

-   Retry failed jobs
-   Handle network errors

Security:

-   No API keys exposed in plugin
-   Secure upload and download

------------------------------------------------------------------------

## 11. Deployment

Plugin distributed via Autodesk App Store as .bundle package.

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