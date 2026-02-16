# Refined Software Architecture: Fusion 360 AI Tutorial Plugin

## 1. Architecture Overview

System consists of five main components:

1.  Fusion Plugin
2.  Backend API Gateway
3.  n8n Orchestration Layer
4.  AI Model Layer
5.  Object Storage

------------------------------------------------------------------------

## 2. Component Architecture

Fusion Plugin:

Responsibilities:

-   Capture screenshots
-   Upload screenshots
-   Request tutorial jobs
-   Poll job status
-   Download tutorial manifest
-   Play tutorial
-   Execute Fusion actions

Backend API Gateway:

Responsibilities:

-   Job management
-   Authentication
-   Security
-   Storage coordination

n8n Orchestration:

Responsibilities:

-   Run AI workflows
-   Queue jobs
-   Retry failed tasks

AI Model Layer:

Responsibilities:

-   Generate tutorial manifests
-   Generate CAD models

Object Storage:

Responsibilities:

-   Store screenshots
-   Store tutorial manifests
-   Store CAD models

------------------------------------------------------------------------

## 3. Data Flow

1.  Plugin captures screenshots
2.  Plugin uploads screenshots
3.  Plugin creates job
4.  Backend triggers n8n
5.  n8n runs AI models
6.  Outputs stored in storage
7.  Backend marks job complete
8.  Plugin downloads tutorial
9.  Plugin plays tutorial

------------------------------------------------------------------------

## 4. Plugin Internal Architecture

Modules:

cloud_client.py

Functions:

-   create_job()
-   upload_screenshot()
-   poll_job()
-   download_manifest()

tutorial_manager.py

completion_detector.py

fusion_actions.py

context_detector.py

------------------------------------------------------------------------

## 5. Deployment Architecture

Fusion Plugin → Backend → n8n → AI Models → Storage → Backend → Plugin

------------------------------------------------------------------------

## 6. Security Architecture

Plugin never communicates directly with AI models.

All communication passes through backend.

Backend protects API keys.

------------------------------------------------------------------------

## 7. Scalability

Backend and n8n support multiple concurrent tutorial generation jobs.

Plugin remains lightweight.
