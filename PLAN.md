## Live Fusion Command Capture Plan for Sketch/Solid UI Component IDs

### Summary
Run a controlled live-capture test in Fusion 360 to collect real command IDs for every button/tab referenced in:
- [Sketch_UIComponents.json](C:/Users/teoen/GitHub/IDeA_Fusion360/FusionTutorialOverlay.bundle/Contents/assets/UI%20Images/Sketch/Sketch_UIComponents.json)
- [Solid_UIComponents.json](C:/Users/teoen/GitHub/IDeA_Fusion360/FusionTutorialOverlay.bundle/Contents/assets/UI%20Images/Solid/Solid_UIComponents.json)

Then generate:
1. A CSV mapping (`component_path,current_commandId,observed_commandId,status,notes`)
2. A Markdown audit report with evidence and exact JSON patch targets

Defaults chosen from your preferences:
- Scope: `buttons + tabs`
- Source of truth: `live capture + docs`
- Output: `CSV + report`
- Keep both semantics: Fusion command ID + method context

### Source Baseline (Authoritative)
- `commandId` should come from Fusion command events (`ApplicationCommandEventArgs.commandId`):  
  https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ApplicationCommandEventArgs_commandId.htm
- Click-start event to capture:  
  https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/UserInterface_commandStarting.htm
- Command definitions object model (for lookup/validation):  
  https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/UserInterface_commandDefinitions.htm
- Your referenced page currently returns Autodesk error page (checked March 2, 2026):  
  https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-7B5A90C8-E94C-48DA-B16B-430729B734DC

### Important Interface/Schema Changes
1. `commandId` in UI component JSONs will be normalized to observed Fusion `args.commandId` values for clickable tools and tabs.
2. Add `methodContext` (new field) on each corrected component:
- `event`: `commandStarting`
- `handler`: `CommandStartingHandler.notify`
- `source`: `live_capture`
3. Structural/non-click container nodes (panel containers, browser folders unless directly clickable command targets) keep metadata IDs and are marked `status: structural` in the report, not forced into fake command IDs.

### Implementation Plan
1. **Pre-flight verification**
- Confirm event hooks already active in [completion_detector.py](C:/Users/teoen/GitHub/IDeA_Fusion360/FusionTutorialOverlay.bundle/Contents/core/completion_detector.py) for `ui.commandStarting` and `ui.commandTerminated`.
- Confirm deployment/runbook in [CLAUDE.md](C:/Users/teoen/GitHub/IDeA_Fusion360/CLAUDE.md) and installed-bundle path consistency.

2. **Live capture protocol (guided manual clicks)**
- Start add-in in Fusion.
- Clear prior log.
- Execute a fixed click script covering all buttons/tabs from both JSON files, one-by-one in deterministic order.
- For each click, capture:
  - UTC timestamp
  - UI component path (e.g., `toolbarGroups.create.tools[line]`)
  - observed `commandStarting.commandId`
  - optional `commandTerminated.commandId` (for confirmation)

3. **Evidence extraction and normalization**
- Parse log lines into structured rows.
- Deduplicate by component path.
- Resolve collisions:
  - if multiple IDs observed for same component, mark `ambiguous` and require second pass.
  - if no event emitted, mark `non-command-ui` or `capture-missed`.

4. **Mapping generation**
- Produce CSV with columns:
  - `component_path`
  - `label`
  - `current_commandId`
  - `observed_commandId`
  - `status` (`match|replace|ambiguous|structural|missing`)
  - `methodContext`
  - `evidence_line`
  - `notes`
- Produce Markdown report:
  - High-confidence replacements
  - Ambiguous items needing retest
  - Structural nodes intentionally not converted

5. **Patch specification (decision-complete)**
- Apply `replace` rows to both JSON files.
- Add `methodContext` only where `status` is `match` or `replace`.
- Do not alter coordinates, labels, image indices, or grouping keys.
- Do not force IDs for `status: structural`.

6. **Post-change validation**
- JSON parse validation for both files.
- Regression check that renderer target resolution still works (no key/id breakage for highlight paths).
- Smoke check that QC matching semantics align with command IDs expected in tutorial checks.

### Test Cases and Scenarios
1. **Happy path**
- Click a known tool (e.g., Sketch Line) and verify one `commandStarting` ID is captured and mapped.
2. **Known mismatch**
- Item currently using fake/object name (e.g., `SketchStop`) is replaced by observed runtime ID (`FinishSketch`) when confirmed.
3. **Container behavior**
- Click panel/tab/container that is not a command; verify it is classified `structural` or mapped only if it emits real command ID.
4. **Ambiguous command**
- Same visual button yields multiple command IDs across contexts; ensure report marks `ambiguous`, no auto-replace.
5. **No-event case**
- Click emits no capture event; classify as `missing` with retry note.

### Assumptions and Defaults
- Fusion runtime events are authoritative over static label names.
- `commandStarting` is canonical for “button clicked” intent.
- `commandTerminated` is secondary corroboration only.
- Existing tutorial QC uses command IDs, so normalized `commandId` must match runtime event values.
- If a UI element is not an executable command, it is not forced to a synthetic command ID.
