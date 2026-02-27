In the Fusion 360 API, the workspace and tab structure isn't exactly a "utility library" in the coding sense, but rather a collection of User Interface (UI) objects.
To answer your first question: Solid, Surface, Mesh, Sheet Metal, and Plastic are all Tabs within the Design Workspace. The "Utilities" section is also a Tab within that same workspace. Because they live in the same "parent" (the Design Workspace), you can toggle between them using the API by targeting their unique IDs.
The Logic for your Script
To "collapse" one and "open" another, you don't actually close a tab—you simply set the active tab to the one you want. Fusion will automatically visually focus on the new selection.
Here is a Python snippet to switch the focus from Utilities (or anywhere else) back to the Solid tab:
import adsk.core, adsk.fusion, traceback

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface
        
        # 1. Access the Design Workspace
        # The ID for the standard Design workspace is 'FusionSolidEnvironment'
        design_workspace = ui.workspaces.itemById('FusionSolidEnvironment')
        
        # 2. Access the Tabs within that workspace
        # 'SolidTab' is the ID for the Solid tab
        # 'MeshTab', 'SheetMetalTab', etc., are the others
        solid_tab = design_workspace.toolbarTabs.itemById('SolidTab')
        
        # 3. Activate the Solid Tab
        # This effectively "collapses" the view of any other active tab
        solid_tab.activate()
        
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

Key IDs for your Reference
If you want to swap between others, use these internal strings:
 * Solid Tab: SolidTab
 * Surface Tab: SurfaceTab
 * Mesh Tab: MeshTab
 * Sheet Metal Tab: SheetMetalTab
 * Plastic Tab: PlasticTab
 * Utilities Tab: UtilitiesTab
Why is it "Cold"?
In programming, "cold" usually refers to a state where a system isn't primed or running (like a "cold start"). If your script feels sluggish or "cold," it’s often because the API has to initialize the UI manager. By explicitly calling .activate(), you are forcing the UI to refresh its state.

If your custom plugin stays stuck on the Utilities tab and won't switch back to Solid, it's usually because of how Fusion 360 handles "UI focus" during the plugin's startup sequence.
Here are the three most likely reasons your code isn't triggering the tab change:
1. The "Active Workspace" Catch-22
Fusion 360 can only activate a tab if the Workspace containing that tab is currently active. If your plugin is loading while Fusion is still in the "starting up" phase or in a different environment (like Manufacture or Generative Design), the itemById('SolidTab') call will return a null object, or the .activate() command will be ignored.
The Fix: Always explicitly activate the Workspace before the Tab.
design_ws = ui.workspaces.itemById('FusionSolidEnvironment')
design_ws.activate() # Force the workspace first
solid_tab = design_ws.toolbarTabs.itemById('SolidTab')
solid_tab.activate()

2. Timing and Event Loops
If your code to switch tabs is inside the run() function or the stop() function of your plugin, it might be executing before the UI has fully rendered your custom panel. Fusion sometimes "resets" the view to the last active tab (Utilities) immediately after a plugin finishes its initial load.
The Fix: Try wrapping your activation code at the very end of your command's created event handler rather than the global run function.
3. Incorrect Tab IDs
Fusion updated its internal naming conventions recently. If you are using older documentation, the IDs might be slightly off. Ensure you are using the exact string literals.
| Target Tab | Internal ID |
|---|---|
| Solid | SolidTab |
| Utilities | UtilitiesTab |
| Design Workspace | FusionSolidEnvironment |
Implementation Check
Ensure your logic follows this flow to ensure the "Utilities" tab is bypassed:
def switchToSolid():
    app = adsk.core.Application.get()
    ui = app.userInterface