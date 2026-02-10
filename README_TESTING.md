# AI Tutorial Overlay for Fusion 360 - Testing Guide

## Project Structure

```
FusionTutorialOverlay.bundle/
├── PackageContents.xml          # App Store package manifest
└── Contents/
    ├── FusionTutorialOverlay.py # Main add-in entry point
    ├── help.html                # Help documentation
    ├── core/                    # Python modules
    │   ├── __init__.py
    │   ├── tutorial_manager.py  # Tutorial state management
    │   ├── fusion_actions.py    # Fusion 360 API actions
    │   └── assets.py            # Asset to data URL conversion
    ├── palette/                 # HTML palette UI
    │   ├── tutorial_palette.html
    │   └── static/
    │       ├── css/main.css
    │       └── js/
    │           ├── main.js      # Entry point + bridge
    │           ├── stepper.js   # Step navigation
    │           └── renderers/   # UI renderers
    ├── test_data/               # Test tutorials
    │   ├── test_tutorial.json
    │   └── existing_model_tutorial.json
    └── assets/                  # Images (cursor, icons)
```

## Testing Methods

### Method 1: Standalone HTML Testing (No Fusion 360 Required)

This is the quickest way to test the UI and animations without Fusion 360.

1. Open the palette HTML directly in a browser:
   ```
   FusionTutorialOverlay.bundle/Contents/palette/tutorial_palette.html
   ```

2. The palette will detect that Fusion is not available and automatically run in "standalone test mode"

3. You'll see a test tutorial with 3 steps demonstrating:
   - Basic step display
   - Cursor animations (move, click, drag)
   - QC checks and warnings
   - Navigation controls

### Method 2: Install in Fusion 360

1. **Locate the Fusion 360 Add-ins folder:**
   - Windows: `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns`
   - macOS: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns`

2. **Copy the bundle:**
   Copy the entire `FusionTutorialOverlay.bundle` folder to the AddIns directory.

3. **Restart Fusion 360** (or use Scripts and Add-Ins dialog to reload)

4. **Enable the add-in:**
   - Go to `Tools > Add-Ins` (or press `Shift+S`)
   - Find "FusionTutorialOverlay" in the list
   - Check "Run" to start it
   - Optionally check "Run on Startup"

5. **Launch the tutorial:**
   - Look for "AI Tutorial Overlay" button in:
     - Tools > Utilities panel
     - Scripts and Add-Ins panel
   - Click to open the tutorial palette

### Method 3: Debug Mode in Fusion 360

For development and debugging:

1. Open Fusion 360
2. Go to `Tools > Add-Ins`
3. Click "Scripts and Add-Ins"
4. Navigate to the bundle's Contents folder
5. Select `FusionTutorialOverlay.py`
6. Click "Debug" to run with Python debugger attached

## Test Tutorials Included

### 1. `test_tutorial.json` - Create a Simple Box with Fillet
A 7-step beginner tutorial that teaches:
- Creating a sketch on the XY plane
- Drawing a rectangle with dimensions
- Finishing a sketch
- Extruding to create a 3D body
- Adding fillets to edges
- Model review

This tutorial demonstrates the fundamental Sketch → Extrude → Modify workflow.

### 2. `existing_model_tutorial.json` - Exploring an Existing Model
A 7-step tutorial for understanding any existing 3D model:
- Viewing from different angles
- Using the timeline
- Inspecting features
- Using the browser panel
- Measuring geometry
- Section analysis

This tutorial works with ANY model you have open in Fusion 360.

## Creating Custom Test Tutorials

Create a new JSON file in `test_data/` following this structure:

```json
{
  "tutorialId": "my_custom_tutorial",
  "title": "My Custom Tutorial",
  "description": "Description here",
  "steps": [
    {
      "stepId": "step-1",
      "stepNumber": 1,
      "title": "Step Title",
      "instruction": "What to do",
      "detailedText": "Why this matters",
      "qcChecks": [
        { "symbol": "✅", "text": "Check item" }
      ],
      "warnings": [
        { "symbol": "⚠️", "text": "Warning message" }
      ],
      "uiAnimations": [
        { "type": "move", "from": {"x": 20, "y": 20}, "to": {"x": 80, "y": 80}, "duration": 500 },
        { "type": "click", "at": {"x": 80, "y": 80} }
      ],
      "fusionActions": [
        { "type": "camera.orient", "orientation": "iso" },
        { "type": "camera.fit" }
      ]
    }
  ]
}
```

To load your custom tutorial:
1. Name it `{tutorialId}_tutorial.json` (e.g., `my_custom_tutorial.json`)
2. Place it in the `test_data/` folder
3. Modify `main.js` to load your tutorial ID, or update the Python code

## Animation Types

### UI Animations (cursor movements in palette)

| Type | Parameters | Description |
|------|------------|-------------|
| `move` | `from: {x, y}`, `to: {x, y}`, `duration` | Move cursor from point A to B |
| `click` | `at: {x, y}` | Show click ripple effect |
| `drag` | `from: {x, y}`, `to: {x, y}`, `duration` | Click, drag, release |
| `pause` | `duration` | Wait before next animation |

Coordinates are percentages (0-100) relative to the animation area.

### Fusion Actions (executed in Fusion 360)

| Type | Parameters | Description |
|------|------------|-------------|
| `camera.fit` | - | Fit view to model |
| `camera.orient` | `orientation` | Set view (front, top, iso, etc.) |
| `camera.focus` | `target` | Focus on point or entity |
| `prompt.selectEntity` | `entityType`, `message` | Request user selection |
| `highlight.body` | `bodyName` | Highlight a body |
| `highlight.clear` | - | Clear highlights |

## Troubleshooting

### Palette doesn't open
- Check Fusion 360's Python console for errors
- Ensure the add-in is enabled in Tools > Add-Ins
- Try restarting Fusion 360

### Animations don't play
- Check browser console (F12) for JavaScript errors
- Verify the tutorial JSON is valid
- Ensure `uiAnimations` array is present in step data

### Camera actions don't work
- These only work inside Fusion 360, not in standalone mode
- Check that a design is open (not a drawing or animation)

### Palette shows blank/error
- The HTML palette requires Qt WebEngine (Fusion 360's new browser)
- Check the file path in the Python code matches actual location

## Development Notes

- **Handler retention:** Python handlers are stored in `_handlers` list to prevent garbage collection
- **Bridge timing:** JavaScript must wait for `window.adsk` injection before calling `fusionSendData`
- **Workspace switches:** Fusion deletes palettes on workspace switch; add-in recreates as needed
- **No Flask:** Assets are sent as data URLs through the bridge, no HTTP server needed
