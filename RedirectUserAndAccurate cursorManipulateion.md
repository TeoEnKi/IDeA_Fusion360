If the user starts in **Surface** but the tutorial step needs **Solid**, the best approach is:

1. **Python (Fusion add-in) detects the current Fusion context** (workspace/tab/environment)  
2. **The palette asks permission** (“Do you want the AI to guide you?”)  
3. If user agrees, the palette shows a **redirect step** using a **preloaded Fusion UI image** and animates the cursor on that image to teach “where to click”  
4. **Python keeps checking Fusion state** until it confirms the user is now in **Solid**, then resumes the intended step

Below is the refined backend plan \+ user flow.

---

## **Backend plan (refined)**

### **A) What “backend” is in this architecture**

Your **backend** is split into two “brains”:

1. **Local backend \= Python add-in**  
* Source of truth for **where the user is in Fusion**  
* Controls step gating (“can we proceed?”)  
* Runs all model/viewport actions  
2. **Remote backend \= AI tutorial service**  
* Generates tutorial manifest (steps, required contexts, animations, fusionActions)

  ### **B) Add to the AI manifest: step preconditions**

Each step must specify what context it requires:

* `requires.workspace`: e.g., `Design`  
* `requires.environment`: e.g., `FusionSolidEnvironment` (or whatever ID you standardize on)  
* optional `requires.reason`: short string (“Extrude tool is in Solid”)

This is how the add-in knows *when* to redirect.

### **C) Add a “redirect template library” locally**

Don’t ask the AI to invent redirect UX every time. Keep it deterministic.

In the Python add-in, define a small mapping:

* If `current != required`:  
  * generate `RedirectStep(type="switchEnvironment", target="Solid")`

Redirect steps use:

* a **preloaded UI image** (e.g., `fusion_design_tabs.png`)  
* a known animation path (cursor sweep → hover on SOLID → click pulse)  
* symbols \+ text

  ### **D) Consent system state (stored locally)**

Maintain a user setting:

* `ai_guidance_mode`: `ON | OFF | ASK`

This controls whether you:

* auto-show the redirect guide  
* ask the user first  
* or only show a warning  
  ---

  ## **User flow (refined, with consent \+ redirect)**

  ### **Scenario: user is on Surface, step requires Solid**

  #### **Step 0 — User opens tutorial**

* Palette loads.  
* If first time: ask global permission:  
  * “Want guided help while you work?”  
  * **Yes / No**  
* Store preference locally.

  #### **Step 1 — User attempts Step N**

* User hits “Next”.  
* Palette sends `stepChanged(N)` to Python.

  #### **Step 2 — Python checks Fusion context (best way to “know where they are”)**

Python queries Fusion for:

* active **workspace** (e.g., Design vs Manufacture)  
* active **environment/tab** (e.g., Solid vs Surface)

Result examples:

* `current = Design + Surface`  
* `required = Design + Solid`

If match → send Step N to palette.

If mismatch → go to Step 3\.

#### **Step 3 — Notify and ask if AI should intervene**

Depending on `ai_guidance_mode`:

**Mode \= ON**

* proceed to redirect step immediately

**Mode \= ASK**

* palette shows:  
  * ⚠️ “You’re in Surface. This step needs Solid.”  
  * Buttons: **Show me where to go** / **Skip help**  
* If user chooses help → redirect step  
* If user skips → show warning only, don’t block (or block only if step truly impossible)

**Mode \= OFF**

* show warning only:  
  * ⚠️ “Switch to Solid tab to continue”  
  * Provide “Why” \+ short hint  
  * No cursor animation

  #### **Step 4 — Visual redirect step (preloaded image \+ accurate cursor)**

If user consented (ON or chose “Show me”):

Palette shows a redirect card:

* Title: “Switch to Solid tools”  
* ⛔ Current: Surface  
* ✅ Required: Solid  
* “Look at the top toolbar. Click **SOLID**.”

Under the text:

* **Static Fusion UI reference image** (bundled asset)  
* Cursor animation plays on this image:  
  * move cursor to tab row  
  * sweep left→right once (for zero-knowledge users)  
  * land on SOLID label  
  * click pulse (expand/contract)  
  * pause (“waiting…”)

This is accurate because it’s on a fixed reference image, not the real UI.

#### **Step 5 — Enforcement loop (Python keeps checking)**

While redirect step is shown:

* Python periodically re-checks Fusion context:  
  * “Are we in Solid yet?”

When it becomes true:

* Python sends `redirectComplete`  
* Palette updates to ✅ “Solid detected”  
* Auto-advance to Step N (the original intended step)  
  ---

