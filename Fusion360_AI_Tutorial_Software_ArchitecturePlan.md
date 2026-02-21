# Software Architecture (SAD Section)

Fusion 360 AI Tutorial Plugin

------------------------------------------------------------------------

## 1. System Overview

The system consists of two operational planes:

### Local Plane (Fusion 360 Plugin)

Responsible for:

-   Loading tutorial manifests
-   Rendering guided tutorials
-   Playing UI animations
-   Detecting completion of modeling steps
-   Providing contextual guidance

This plane operates independently and does not require cloud
connectivity for tutorial playback.

### Cloud Plane (Optional)

Responsible for:

-   Generating tutorial manifests using AI
-   Processing screenshot uploads
-   Managing tutorial generation jobs
-   Storing manifests and CAD outputs

Cloud pipeline:

Plugin → Backend API → n8n → AI Model → Object Storage

------------------------------------------------------------------------

## 2. Plugin Runtime Architecture

The Fusion 360 plugin uses a hybrid architecture:

Python backend (Fusion Add‑In) HTML/JS frontend (Palette UI)

Communication occurs via Fusion 360's Palette bridge.

Bridge interface:

JS → Python: window.adsk.fusionSendData(JSON.stringify(message))

Python → JS: palette.sendInfoToHTML(JSON.stringify(message))

This architecture ensures low‑latency communication without external
servers.

------------------------------------------------------------------------

## 3. Tutorial Manifest Contract (Canonical Format)

The tutorial manifest is a JSON file that defines tutorial steps.

### Required fields

Root level:

-   tutorialId
-   title
-   description
-   steps\[\]

Step level:

-   stepId
-   stepNumber
-   title
-   instruction
-   detailedText (optional)
-   expandedContent.whyThisMatters (optional)
-   tips\[\]
-   qcChecks\[\]
-   uiAnimations\[\]
-   fusionActions\[\]

### Explicitly removed from schema

These keys MUST NOT exist:

-   metadata
-   warnings
-   parameters
-   expandedContent.parameters

Warnings and tips are merged into:

tips\[\]

Example:

tips: - 💡 Helpful guidance - ⚠️ Important caution

This simplifies rendering and avoids UI fragmentation.

------------------------------------------------------------------------

## 4. Plugin Component Architecture

### Core Python Modules

FusionTutorialOverlay.py Entry point. Creates palette, initializes
systems.

tutorial_manager.py Responsible for:

-   Loading manifests
-   Normalizing manifests
-   Managing step state
-   Advancing tutorial progression

Normalization rules:

-   Merge warnings → tips
-   Remove metadata
-   Remove parameters
-   Ensure tips exists
-   Ensure uiAnimations exists

completion_detector.py Responsible for:

-   Listening to Fusion events
-   Matching events to expectedCommand
-   Emitting completionEvent to UI

fusion_actions.py Responsible for:

-   Camera control
-   Selection highlighting
-   View manipulation

context_detector.py / context_poller.py Responsible for:

-   Monitoring workspace context
-   Warning user if wrong environment

------------------------------------------------------------------------

### Frontend (Palette)

main.js Initializes bridge and routes messages.

stepper.js Handles tutorial progression logic.

renderers/ Responsible for rendering:

-   Instruction text
-   Tips section
-   QC checklist
-   Animations

Removed UI elements:

-   Parameters card
-   Warnings card

Only Tips section remains.

------------------------------------------------------------------------

## 5. Completion Tracking Architecture

Each step contains qcChecks with expectedCommand.

Example:

expectedCommand: "Sweep"

Completion detector listens for:

-   command termination
-   feature creation
-   timeline changes

Matching logic uses:

Command match OR Feature evidence OR Geometry evidence

This allows flexible user workflows.

When match occurs:

Python → sends completionEvent → JS

JS → toggles checkbox

When all required checks complete:

Step automatically advances.

------------------------------------------------------------------------

## 6. UI Animation Architecture

Each step supports uiAnimations.

Animation types:

-   move
-   click
-   drag
-   pause
-   highlight
-   tooltip
-   focusCamera

Purpose:

-   Demonstrate correct workflow
-   Provide visual guidance
-   Reduce learning friction

Animations run independently from user interaction.

User actions always take priority.

------------------------------------------------------------------------

## 7. Cloud Architecture (Optional)

Plugin can generate tutorials using AI.

Flow:

1.  Plugin captures screenshots
2.  Upload to backend
3.  Backend creates job
4.  n8n orchestrates workflow
5.  AI generates tutorial manifest
6.  Storage saves manifest
7.  Plugin downloads manifest
8.  Plugin runs tutorial

Backend performs manifest validation before serving.

------------------------------------------------------------------------

## 8. Data Flow Summary

Tutorial Playback:

Manifest → TutorialManager → Renderer → Animation Player →
CompletionDetector → Progression

Tutorial Generation:

Plugin → Backend → n8n → AI → Storage → Plugin

------------------------------------------------------------------------

## 9. Security Architecture

Plugin does not directly access AI services.

All AI access occurs via backend.

Benefits:

-   API key protection
-   Access control
-   Rate limiting
-   Audit logging

------------------------------------------------------------------------

## 10. Scalability Architecture

Plugin:

-   Stateless tutorial execution
-   Lightweight runtime

Backend:

-   Supports concurrent tutorial generation jobs

n8n:

-   Provides queue‑based orchestration

Storage:

-   Supports unlimited tutorial storage

------------------------------------------------------------------------

## 11. Design Principles

This architecture prioritizes:

-   Reliability
-   Flexibility
-   Modularity
-   Low latency
-   Offline tutorial playback
-   Robust completion detection

------------------------------------------------------------------------

End of Software Architecture Section
