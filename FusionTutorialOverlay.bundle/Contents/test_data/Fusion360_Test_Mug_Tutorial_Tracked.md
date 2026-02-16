# Fusion 360 Test Tutorial — Create a Coffee Mug

Learn to model a complete coffee mug with handle using revolve, shell, and sweep operations.

## Tutorial Metadata
- tutorialId: `mug`
- version: `1.1`
- difficulty: `intermediate`
- estimatedTime: `25 minutes`
- tags: `revolve, shell, sweep, handle, mug`
- schemaVersion: `2.0`

## Tracking Defaults (how the plugin should evaluate progress)
- enableStepTracking: `True`
- enableCheckTracking: `True`
- autoAdvance: `True`
- completeStepWhen: `allRequiredChecksPassed`
- manualOverrideAllowed: `True`
- eventLog.emitCheckUpdates: `True`
- eventLog.emitStepCompleted: `True`

## Steps

## Step 1: Start a New Sketch
**stepToBeCompleted:** `Start a New Sketch`

**Instruction:** Click on the XZ plane (Front plane) in the Origin folder to create a new sketch for the mug profile.

**Why:** Revolve is ideal for creating symmetrical objects like mugs, vases, and bowls.

**Tips:**
- The XZ plane is vertical - perfect for drawing the mug's side profile
- You can also right-click on the plane and select 'Create Sketch'
- The origin will be at the center bottom of your mug

**VisualStep:**
- image: `test_data/fusion_ui.png`
- caption: Expand Origin in the Browser and click on the XZ plane
- highlights (labels only):
  - Origin folder (rect)

**UI Focus (UI-map keys):**
- `components.browser.items.origin` — origin

**Auto-complete logic:**
- Trigger: `{"type": "sketchCreated", "plane": "XZ", "workspace": "Design"}`
- Timeout: `180s`
- Listen for events: `sketchCreated, commandStarted, commandExecuted`
- Step completes when required checks pass: `sketch_on_xz, in_sketch_mode`

**QC Checks (per-check detectors):**
- [ ] `sketch_on_xz` (required) ✅ Sketch created on XZ (Front) plane
  - Detector: `sketch.createdOnPlane (plane=XZ)`
- [ ] `in_sketch_mode` (required) ✅ You are in sketch editing mode
  - Detector: `ui.inSketchMode`

**Warnings:**
- ⚠️ Make sure to select XZ plane, not XY plane

**Fusion Actions (camera / assist):**
- `{"type": "camera.orient", "orientation": "front"}`
- `{"type": "camera.fit"}`

**UI Animations (cursor demo):**
- `{"type": "move", "from": {"x": 20, "y": 30}, "to": {"x": 8, "y": 36}, "duration": 600}`
- `{"type": "click", "at": {"x": 8, "y": 36}}`

## Step 2: Draw the Mug Profile
**stepToBeCompleted:** `Draw the Mug Profile`

**Instruction:** Use the Line tool (L) to draw the mug's cross-section. Start at the origin, go up 90mm, right 35mm, down 85mm, then right 5mm and down 5mm to create the base.

**Why:** Drawing only half the profile is efficient because Revolve will mirror it automatically.

**Tips:**
- Press L to quickly activate the Line tool
- Type dimensions directly while drawing for precision
- Keep lines connected - gaps will cause revolve to fail

**Reference data (from expandedContent):**
- dimensions: `{"height": "90mm (outer wall)", "radius": "35mm (gives 70mm diameter)", "wallThickness": "5mm", "baseThickness": "5mm"}`

**VisualStep:**
- image: `test_data/fusion_ui.png`
- caption: Select the Line tool from CREATE menu or press L
- highlights (labels only):
  - CREATE (rect)

**UI Focus (UI-map keys):**
- `components.browser.items.origin` — origin
- `components.toolbarGroups.create` — CREATE (Create tools dropdown (New Component, Sketch, Extrude, etc.))

**Auto-complete logic:**
- Trigger: `{"type": "sketchUpdated"}`
- Timeout: `420s`
- Listen for events: `sketchGeometryChanged, dimensionCreated, dimensionEdited, commandStarted`
- Step completes when required checks pass: `profile_origin, profile_height_90, profile_width_35`

**QC Checks (per-check detectors):**
- [ ] `profile_origin` (required) ✅ Profile starts at origin (0,0)
  - Detector: `sketch.endpointAtPoint (point={"xMm":0,"yMm":0}, toleranceMm=0.25)`
- [ ] `profile_height_90` (required) ✅ Height is 90mm
  - Detector: `sketch.dimensionExists (orientation=vertical, toleranceMm=0.5, valueMm=90)`
- [ ] `profile_width_35` (required) ✅ Width is 35mm
  - Detector: `sketch.dimensionExists (orientation=horizontal, toleranceMm=0.5, valueMm=35)`

**Warnings:**
- ⚠️ Draw on the RIGHT side of the Y-axis only

**Fusion Actions (camera / assist):**
- `{"type": "camera.orient", "orientation": "front"}`

**UI Animations (cursor demo):**
- `{"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 19, "y": 13}, "duration": 400}`
- `{"type": "click", "at": {"x": 19, "y": 13}}`

## Step 3: Close the Profile
**stepToBeCompleted:** `Close the Profile`

**Instruction:** Complete the profile by drawing a line from the bottom right corner back to the origin along the center axis.

**Why:** Fusion 360 requires closed profiles for most 3D operations.

**Tips:**
- Click exactly on the origin point to close the profile
- A closed profile will show as a shaded region

**UI Focus (UI-map keys):**
- `components.browser.items.origin` — origin

**Auto-complete logic:**
- Trigger: `{"type": "sketchProfileClosed"}`
- Timeout: `240s`
- Listen for events: `sketchGeometryChanged, sketchProfileCreated`
- Step completes when required checks pass: `profile_closed, profile_shaded_region`

**QC Checks (per-check detectors):**
- [ ] `profile_closed` (required) ✅ Profile is fully closed
  - Detector: `sketch.profileClosed (minProfiles=1)`
- [ ] `profile_shaded_region` (required) ✅ Profile shows as shaded region
  - Detector: `sketch.profileShaded (expected=True)`

**UI Animations (cursor demo):**
- `{"type": "move", "from": {"x": 75, "y": 80}, "to": {"x": 50, "y": 80}, "duration": 500}`
- `{"type": "click", "at": {"x": 50, "y": 80}}`

## Step 4: Finish the Sketch
**stepToBeCompleted:** `Finish the Sketch`

**Instruction:** Click 'Finish Sketch' in the toolbar or press Escape to exit sketch mode.

**Why:** Always finish your sketch before applying 3D operations. This locks the geometry and makes it available for the Revolve command.

**Tips:**
- Green checkmark in toolbar = Finish Sketch
- Press Escape as a shortcut

**UI Focus (UI-map keys):**
- `commonActions.finishSketch` — Finish Sketch (Only visible when in sketch mode)

**Auto-complete logic:**
- Trigger: `{"type": "sketchFinished"}`
- Timeout: `180s`
- Listen for events: `commandExecuted, sketchFinished, timelineChanged`
- Step completes when required checks pass: `sketch_finished, sketch_in_timeline`

**QC Checks (per-check detectors):**
- [ ] `sketch_finished` (required) ✅ Sketch is finished
  - Detector: `sketch.isEditing (expected=False)`
- [ ] `sketch_in_timeline` (required) ✅ Sketch appears in browser/timeline
  - Detector: `timeline.containsFeature (featureType=Sketch)`

**UI Animations (cursor demo):**
- `{"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 90, "y": 8}, "duration": 500}`
- `{"type": "click", "at": {"x": 90, "y": 8}}`

## Step 5: Revolve the Profile
**stepToBeCompleted:** `Revolve the Profile`

**Instruction:** Go to Create > Revolve (or press R), select your profile, and choose the Y-axis as the revolution axis. Set angle to 360 degrees.

**Requires:**
- workspace: `Design`
- environment: `Solid`
- reason: `The Revolve tool is in the Solid modeling environment`

**Why:** Revolve is perfect for any object with circular symmetry.

**Tips:**
- The axis must be on the edge of or outside your profile
- You can revolve less than 360 degrees for partial shapes

**Reference data (from expandedContent):**
- parameters: `{"profile": "Your closed sketch profile", "axis": "Y-axis (vertical center line)", "angle": "360 degrees", "operation": "New Body"}`

**VisualStep:**
- image: `test_data/fusion_ui.png`
- caption: Click CREATE dropdown, then select Revolve
- highlights (labels only):
  - CREATE > Revolve (rect)
  - SOLID tab (rect)

**UI Focus (UI-map keys):**
- `components.toolbarGroups.create` — CREATE (Create tools dropdown (New Component, Sketch, Extrude, etc.))
- `commonActions.switchToSolid` — Switch to Solid
- `components.toolbarGroups.create.tools[id=revolve]` — revolve (Tool in CREATE)

**Auto-complete logic:**
- Trigger: `{"type": "featureCreated", "featureType": "RevolveFeature"}`
- Timeout: `300s`
- Listen for events: `featureCreated, timelineChanged, commandExecuted`
- Step completes when required checks pass: `revolve_profile_selected, revolve_axis_y, revolve_angle_360`

**QC Checks (per-check detectors):**
- [ ] `revolve_profile_selected` (required) ✅ Profile is selected (highlighted)
  - Detector: `command.inputSelected (command=Revolve, input=profile, minCount=1)`
- [ ] `revolve_axis_y` (required) ✅ Y-axis selected as revolution axis
  - Detector: `command.inputEquals (command=Revolve, input=axis, value=Y)`
- [ ] `revolve_angle_360` (required) ✅ Angle is set to 360 degrees
  - Detector: `command.inputEquals (command=Revolve, input=angleDeg, tolerance=0.1, value=360)`

**Warnings:**
- ⚠️ If revolve fails, check that profile doesn't cross the axis

**Fusion Actions (camera / assist):**
- `{"type": "camera.orient", "orientation": "iso"}`
- `{"type": "camera.fit"}`

**UI Animations (cursor demo):**
- `{"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 19, "y": 13}, "duration": 500}`
- `{"type": "click", "at": {"x": 19, "y": 13}}`

## Step 6: Create Handle Sketch
**stepToBeCompleted:** `Create Handle Sketch`

**Instruction:** Create a new sketch on the XZ plane. We'll draw the handle's path on the side of the mug.

**Why:** Sweep is ideal for creating handles, pipes, and any shape that follows a curved path.

**Tips:**
- The XZ plane passes through the center of the mug
- Position the handle path to connect with the mug's outer surface

**VisualStep:**
- image: `test_data/fusion_ui.png`
- caption: Click on XZ plane in Origin folder to start a new sketch
- highlights (labels only):
  - Origin > XZ Plane (rect)

**UI Focus (UI-map keys):**
- `components.browser.items.origin` — origin

**Auto-complete logic:**
- Trigger: `{"type": "sketchCreated", "plane": "XZ"}`
- Timeout: `240s`
- Listen for events: `sketchCreated, commandExecuted`
- Step completes when required checks pass: `handle_sketch_on_xz`

**QC Checks (per-check detectors):**
- [ ] `handle_sketch_on_xz` (required) ✅ New sketch started on XZ plane
  - Detector: `sketch.createdOnPlane (plane=XZ)`

**Fusion Actions (camera / assist):**
- `{"type": "camera.orient", "orientation": "right"}`
- `{"type": "camera.fit"}`

**UI Animations (cursor demo):**
- `{"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 8, "y": 36}, "duration": 500}`
- `{"type": "click", "at": {"x": 8, "y": 36}}`

## Step 7: Draw Handle Path
**stepToBeCompleted:** `Draw Handle Path`

**Instruction:** Use the 3-Point Arc tool to draw a C-shaped handle path. Start 15mm from the top, arc outward 25mm, and end 20mm from the bottom.

**Why:** Handle ergonomics matter! The arc should provide enough space for fingers.

**Tips:**
- Use 3-Point Arc for smooth curves
- First click: top attachment point
- Second click: bottom attachment point
- Third click: controls the arc's bulge

**Reference data (from expandedContent):**
- dimensions: `{"topAttachment": "15mm from rim", "bottomAttachment": "20mm from base", "arcDepth": "25mm outward from mug surface"}`

**VisualStep:**
- image: `test_data/fusion_ui.png`
- caption: Find 3-Point Arc in CREATE > Arc dropdown
- highlights (labels only):
  - CREATE > Arc (rect)

**UI Focus (UI-map keys):**
- `components.toolbarGroups.create` — CREATE (Create tools dropdown (New Component, Sketch, Extrude, etc.))
- `toolId:3-point-arc (not in UI map)`

**Auto-complete logic:**
- Trigger: `{"type": "sketchUpdated"}`
- Timeout: `420s`
- Listen for events: `sketchGeometryChanged, commandStarted, dimensionCreated, dimensionEdited`
- Step completes when required checks pass: `handle_path_arc_exists, handle_clearance_ok`

**QC Checks (per-check detectors):**
- [ ] `handle_path_arc_exists` (required) ✅ Arc starts at mug surface level
  - Detector: `sketch.arcExists (minCount=1)`
- [ ] `arc_ends_at_mug_surface_level` (required) ✅ Arc ends at mug surface level
  - Detector: `manualCheck`
- [ ] `handle_clearance_ok` (required) ✅ Enough finger clearance (~25mm)
  - Detector: `sketch.dimensionExists (note=Finger clearance, toleranceMm=5, valueMm=25)`

**Warnings:**
- ⚠️ Path should not intersect the mug body

**UI Animations (cursor demo):**
- `{"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 60, "y": 25}, "duration": 400}`
- `{"type": "click", "at": {"x": 60, "y": 25}}`
- `{"type": "move", "from": {"x": 60, "y": 25}, "to": {"x": 60, "y": 70}, "duration": 400}`
- `{"type": "click", "at": {"x": 60, "y": 70}}`
- `{"type": "move", "from": {"x": 60, "y": 70}, "to": {"x": 80, "y": 47}, "duration": 400}`
- `{"type": "click", "at": {"x": 80, "y": 47}}`

## Step 8: Create Handle Profile Sketch
**stepToBeCompleted:** `Create Handle Profile Sketch`

**Instruction:** Finish the path sketch, then create a new sketch perpendicular to the path at its starting point. Draw a 10mm x 8mm rounded rectangle for the handle cross-section.

**Why:** The profile shape affects both comfort and strength.

**Tips:**
- Create sketch on a plane perpendicular to the path start
- Center the profile on the path endpoint

**Reference data (from expandedContent):**
- dimensions: `{"width": "10mm", "height": "8mm", "cornerRadius": "2mm"}`

**Auto-complete logic:**
- Trigger: `{"type": "sketchCreated"}`
- Timeout: `420s`
- Listen for events: `sketchGeometryChanged, sketchCreated, dimensionCreated`
- Step completes when required checks pass: `handle_profile_perpendicular, handle_profile_closed`

**QC Checks (per-check detectors):**
- [ ] `handle_profile_perpendicular` (required) ✅ Profile is perpendicular to path
  - Detector: `sketch.planePerpendicularToPath (pathRef=handle_path)`
- [ ] `handle_profile_closed` (required) ✅ Rounded rectangle is closed
  - Detector: `sketch.profileClosed (minProfiles=1)`

**Warnings:**
- ⚠️ Profile must be on a plane perpendicular to the path

**Fusion Actions (camera / assist):**
- `{"type": "camera.orient", "orientation": "iso"}`

**UI Animations (cursor demo):**
- `{"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 60, "y": 25}, "duration": 400}`
- `{"type": "click", "at": {"x": 60, "y": 25}}`

## Step 9: Sweep the Handle
**stepToBeCompleted:** `Sweep the Handle`

**Instruction:** Go to Create > Sweep. Select the rounded rectangle as the Profile and the arc as the Path. Set Operation to 'Join' to merge with the mug body.

**Requires:**
- workspace: `Design`
- environment: `Solid`
- reason: `The Sweep tool is in the Solid modeling environment`

**Why:** The Join operation makes the handle and mug body one continuous solid.

**Tips:**
- Select Profile first, then Path
- If it doesn't join, check that surfaces are touching

**Reference data (from expandedContent):**
- parameters: `{"profile": "Rounded rectangle sketch", "path": "Arc path sketch", "operation": "Join"}`

**VisualStep:**
- image: `test_data/fusion_ui.png`
- caption: Click CREATE dropdown, then select Sweep
- highlights (labels only):
  - CREATE > Sweep (rect)
  - SOLID tab (rect)

**UI Focus (UI-map keys):**
- `components.toolbarGroups.create` — CREATE (Create tools dropdown (New Component, Sketch, Extrude, etc.))
- `commonActions.switchToSolid` — Switch to Solid
- `toolId:sweep (not in UI map)`
- `toolId:3-point-arc (not in UI map)`

**Auto-complete logic:**
- Trigger: `{"type": "featureCreated", "featureType": "SweepFeature"}`
- Timeout: `300s`
- Listen for events: `featureCreated, timelineChanged, commandExecuted`
- Step completes when required checks pass: `sweep_profile_selected, sweep_path_selected, sweep_operation_join`

**QC Checks (per-check detectors):**
- [ ] `sweep_profile_selected` (required) ✅ Profile selected (rounded rectangle)
  - Detector: `command.inputSelected (command=Sweep, input=profile, minCount=1)`
- [ ] `sweep_path_selected` (required) ✅ Path selected (arc)
  - Detector: `command.inputSelected (command=Sweep, input=path, minCount=1)`
- [ ] `sweep_operation_join` (required) ✅ Operation set to Join
  - Detector: `command.inputEquals (command=Sweep, input=operation, value=Join)`

**Warnings:**
- ⚠️ If sweep fails, ensure profile is perpendicular to path

**Fusion Actions (camera / assist):**
- `{"type": "camera.orient", "orientation": "iso"}`
- `{"type": "camera.fit"}`

**UI Animations (cursor demo):**
- `{"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 19, "y": 13}, "duration": 400}`
- `{"type": "click", "at": {"x": 19, "y": 13}}`

## Step 10: Add Fillet to Rim
**stepToBeCompleted:** `Add Fillet to Rim`

**Instruction:** Select the Fillet tool (F), click on the top inner and outer edges of the mug rim, and set radius to 2mm.

**Requires:**
- workspace: `Design`
- environment: `Solid`
- reason: `The Fillet tool is in the Solid modeling environment`

**Why:** Filleting the rim makes it comfortable to drink from and removes sharp edges that could chip.

**Tips:**
- Select both inner and outer rim edges
- Hold Ctrl to select multiple edges
- 2mm is comfortable for drinking

**VisualStep:**
- image: `test_data/fusion_ui.png`
- caption: Find Fillet in MODIFY dropdown or press F
- highlights (labels only):
  - MODIFY > Fillet (rect)

**UI Focus (UI-map keys):**
- `components.toolbarGroups.modify` — MODIFY (Modify tools dropdown (Fillet, Chamfer, Shell, etc.))
- `components.toolbarGroups.modify.tools[id=fillet]` — fillet (Tool in MODIFY)
- `commonActions.fillet` — Fillet

**Auto-complete logic:**
- Trigger: `{"type": "featureCreated", "featureType": "FilletFeature"}`
- Timeout: `240s`
- Listen for events: `featureCreated, timelineChanged, commandExecuted`
- Step completes when required checks pass: `rim_edges_selected_inner, rim_edges_selected_outer, fillet_radius_2`

**QC Checks (per-check detectors):**
- [ ] `rim_edges_selected_inner` (required) ✅ Inner rim edge selected
  - Detector: `command.inputSelected (command=Fillet, edgeGroup=innerRim, input=edges, minCount=1)`
- [ ] `rim_edges_selected_outer` (required) ✅ Outer rim edge selected
  - Detector: `command.inputSelected (command=Fillet, edgeGroup=outerRim, input=edges, minCount=1)`
- [ ] `fillet_radius_2` (required) ✅ Fillet radius is 2mm
  - Detector: `command.inputEquals (command=Fillet, input=radiusMm, tolerance=0.25, value=2)`

**Fusion Actions (camera / assist):**
- `{"type": "camera.orient", "orientation": "front"}`
- `{"type": "camera.fit"}`

**UI Animations (cursor demo):**
- `{"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 41, "y": 13}, "duration": 400}`
- `{"type": "click", "at": {"x": 41, "y": 13}}`

## Step 11: Fillet Handle Joints
**stepToBeCompleted:** `Fillet Handle Joints`

**Instruction:** Add 5mm fillets where the handle meets the mug body to create smooth transitions.

**Why:** The handle attachment points experience the most stress. Fillets reduce stress concentration.

**Tips:**
- Select the edges where handle meets mug body
- Larger radius = stronger joint

**UI Focus (UI-map keys):**
- `components.toolbarGroups.modify.tools[id=fillet]` — fillet (Tool in MODIFY)
- `commonActions.fillet` — Fillet

**Auto-complete logic:**
- Trigger: `{"type": "featureCreated", "featureType": "FilletFeature"}`
- Timeout: `240s`
- Listen for events: `featureCreated, timelineChanged, commandExecuted`
- Step completes when required checks pass: `handle_joint_top_fillet, handle_joint_bottom_fillet, fillet_radius_5`

**QC Checks (per-check detectors):**
- [ ] `handle_joint_top_fillet` (required) ✅ Top handle joint filleted
  - Detector: `command.inputSelected (command=Fillet, edgeGroup=handleTop, input=edges, minCount=1)`
- [ ] `handle_joint_bottom_fillet` (required) ✅ Bottom handle joint filleted
  - Detector: `command.inputSelected (command=Fillet, edgeGroup=handleBottom, input=edges, minCount=1)`
- [ ] `fillet_radius_5` (required) ✅ Fillet radius is 5mm
  - Detector: `command.inputEquals (command=Fillet, input=radiusMm, tolerance=0.5, value=5)`

**Warnings:**
- ⚠️ If fillet fails, try a smaller radius

**Fusion Actions (camera / assist):**
- `{"type": "camera.orient", "orientation": "iso"}`
- `{"type": "camera.fit"}`

**UI Animations (cursor demo):**
- `{"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 65, "y": 30}, "duration": 400}`
- `{"type": "click", "at": {"x": 65, "y": 30}}`

## Step 12: Add Base Fillet
**stepToBeCompleted:** `Add Base Fillet`

**Instruction:** Add a 3mm fillet to the bottom outer edge of the mug for a finished look.

**Why:** A small fillet on the base edge prevents chipping and gives the mug a refined appearance.

**Tips:**
- 3mm is enough to protect without changing the look dramatically

**UI Focus (UI-map keys):**
- `components.toolbarGroups.modify.tools[id=fillet]` — fillet (Tool in MODIFY)
- `commonActions.fillet` — Fillet

**Auto-complete logic:**
- Trigger: `{"type": "featureCreated", "featureType": "FilletFeature"}`
- Timeout: `180s`
- Listen for events: `featureCreated, timelineChanged, commandExecuted`
- Step completes when required checks pass: `base_edge_selected, fillet_radius_3`

**QC Checks (per-check detectors):**
- [ ] `base_edge_selected` (required) ✅ Bottom outer edge selected
  - Detector: `command.inputSelected (command=Fillet, edgeGroup=baseOuter, input=edges, minCount=1)`
- [ ] `fillet_radius_3` (required) ✅ Fillet radius is 3mm
  - Detector: `command.inputEquals (command=Fillet, input=radiusMm, tolerance=0.5, value=3)`

**Fusion Actions (camera / assist):**
- `{"type": "camera.orient", "orientation": "iso"}`

**UI Animations (cursor demo):**
- `{"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 50, "y": 75}, "duration": 400}`
- `{"type": "click", "at": {"x": 50, "y": 75}}`

## Step 13: Review Your Mug
**stepToBeCompleted:** `Review Your Mug`

**Instruction:** Rotate the view to inspect your completed mug from all angles. Check handle attachment, wall thickness, and overall proportions.

**Why:** Quality checking catches issues before they become expensive mistakes.

**Tips:**
- Use Section Analysis to check wall thickness
- Orbit around to see all sides

**Reference data (from expandedContent):**
- finalChecklist: `["Mug body is hollow (not solid)", "Handle is attached at both ends", "All fillets applied successfully"]`

**Auto-complete logic:**
- Trigger: `{"type": "manual"}`
- Timeout: `0s`

**QC Checks (per-check detectors):**
- [ ] `mug_dimensions_70mm_diameter_x_90mm_tall` (required) ✅ Mug dimensions: ~70mm diameter x 90mm tall
  - Detector: `manualCheck`
- [ ] `wall_thickness_5mm` (required) ✅ Wall thickness: 5mm
  - Detector: `manualCheck`
- [ ] `handle_securely_attached` (required) ✅ Handle securely attached
  - Detector: `manualCheck`
- [ ] `all_edges_smoothly_filleted` (required) ✅ All edges smoothly filleted
  - Detector: `manualCheck`

**Fusion Actions (camera / assist):**
- `{"type": "camera.fit"}`

**UI Animations (cursor demo):**
- `{"type": "drag", "from": {"x": 30, "y": 50}, "to": {"x": 70, "y": 50}, "duration": 1200}`

## Step 14: Congratulations!
**stepToBeCompleted:** `Congratulations!`

**Instruction:** You've successfully modeled a coffee mug! Your mug is ready for rendering, 3D printing, or further customization.

**Why:** The techniques you've learned are fundamental to product design.

**Reference data (from expandedContent):**
- nextSteps: `["Try adding a logo or text to the mug surface", "Experiment with different handle shapes", "Add an appearance/material in the Render workspace", "Export as STL for 3D printing"]`
- skillsLearned: `["Creating profiles for Revolve operations", "Using Revolve for cylindrical shapes", "Drawing paths for Sweep operations", "Using Sweep with Join operation", "Strategic fillet placement"]`

**Auto-complete logic:**
- Trigger: `{"type": "manual"}`
- Timeout: `0s`

**QC Checks (per-check detectors):**
- [ ] `tutorial_completed_successfully` (required) ✅ Tutorial completed successfully!
  - Detector: `manualCheck`

**Fusion Actions (camera / assist):**
- `{"type": "camera.orient", "orientation": "iso"}`
- `{"type": "camera.fit"}`

**UI Animations (cursor demo):**
- `{"type": "click", "at": {"x": 50, "y": 50}}`


## UI Map Reference (source keys)
This tutorial refers to UI targets by key (instead of bounding boxes). Keys come from the UI map JSON.

- `components.*` keys describe navbar/browser regions and major tool groups.
- `commonActions.*` keys are common high-frequency actions (e.g., `createSketch`, `finishSketch`).