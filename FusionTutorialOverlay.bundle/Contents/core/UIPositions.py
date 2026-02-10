"""
fusion360_ui_map.py

Normalized UI hit-map for Autodesk Fusion 360 (Design workspace)
Coordinate system:
- (0.0, 0.0) = top-left of window
- (1.0, 1.0) = bottom-right of window
"""

from dataclasses import dataclass
from typing import Tuple, Dict


@dataclass
class Bounds:
    top_left: Tuple[float, float]
    bottom_right: Tuple[float, float]

    @property
    def center(self) -> Tuple[float, float]:
        return (
            (self.top_left[0] + self.bottom_right[0]) / 2,
            (self.top_left[1] + self.bottom_right[1]) / 2,
        )


@dataclass
class UIComponent:
    name: str
    bounds: Bounds
    clickable: bool = True


UI_MAP: Dict[str, UIComponent] = {

    # =========================
    # Top Application Bar
    # =========================

    "app_menu": UIComponent(
        name="App Menu / File",
        bounds=Bounds((0.015, 0.015), (0.060, 0.060)),
    ),

    "save": UIComponent(
        name="Save",
        bounds=Bounds((0.065, 0.015), (0.095, 0.060)),
    ),

    "undo": UIComponent(
        name="Undo",
        bounds=Bounds((0.100, 0.015), (0.130, 0.060)),
    ),

    "redo": UIComponent(
        name="Redo",
        bounds=Bounds((0.135, 0.015), (0.165, 0.060)),
    ),

    # =========================
    # Workspace Tabs
    # =========================

    "workspace_solid": UIComponent(
        name="Workspace – SOLID",
        bounds=Bounds((0.020, 0.080), (0.070, 0.130)),
    ),

    "workspace_surface": UIComponent(
        name="Workspace – SURFACE",
        bounds=Bounds((0.075, 0.080), (0.135, 0.130)),
    ),

    "workspace_mesh": UIComponent(
        name="Workspace – MESH",
        bounds=Bounds((0.140, 0.080), (0.185, 0.130)),
    ),

    "workspace_sheet_metal": UIComponent(
        name="Workspace – SHEET METAL",
        bounds=Bounds((0.190, 0.080), (0.265, 0.130)),
    ),

    "workspace_plastic": UIComponent(
        name="Workspace – PLASTIC",
        bounds=Bounds((0.270, 0.080), (0.330, 0.130)),
    ),

    "workspace_utilities": UIComponent(
        name="Workspace – UTILITIES",
        bounds=Bounds((0.335, 0.080), (0.400, 0.130)),
    ),

    # =========================
    # Main Toolbar Sections
    # =========================

    "toolbar_create": UIComponent(
        name="Create Toolbar",
        bounds=Bounds((0.020, 0.140), (0.140, 0.215)),
    ),

    "toolbar_modify": UIComponent(
        name="Modify Toolbar",
        bounds=Bounds((0.145, 0.140), (0.255, 0.215)),
    ),

    "toolbar_configure": UIComponent(
        name="Configure Toolbar",
        bounds=Bounds((0.260, 0.140), (0.335, 0.215)),
    ),

    "toolbar_construct": UIComponent(
        name="Construct Toolbar",
        bounds=Bounds((0.340, 0.140), (0.420, 0.215)),
    ),

    "toolbar_inspect": UIComponent(
        name="Inspect Toolbar",
        bounds=Bounds((0.425, 0.140), (0.495, 0.215)),
    ),

    "toolbar_insert": UIComponent(
        name="Insert Toolbar",
        bounds=Bounds((0.500, 0.140), (0.565, 0.215)),
    ),

    "toolbar_assemble": UIComponent(
        name="Assemble Toolbar",
        bounds=Bounds((0.570, 0.140), (0.650, 0.215)),
    ),

    "tool_select": UIComponent(
        name="Select Tool",
        bounds=Bounds((0.655, 0.140), (0.715, 0.215)),
    ),

    # =========================
    # Browser Panel (Left)
    # =========================

    "browser_panel": UIComponent(
        name="Browser Panel",
        bounds=Bounds((0.000, 0.215), (0.190, 0.700)),
        clickable=False,
    ),

    "document_settings": UIComponent(
        name="Document Settings",
        bounds=Bounds((0.015, 0.255), (0.175, 0.295)),
    ),

    "units": UIComponent(
        name="Units (mm, g)",
        bounds=Bounds((0.030, 0.295), (0.175, 0.330)),
    ),

    "origin": UIComponent(
        name="Origin",
        bounds=Bounds((0.015, 0.355), (0.175, 0.390)),
    ),

    # =========================
    # Canvas & View Controls
    # =========================

    "modeling_canvas": UIComponent(
        name="Modeling Canvas",
        bounds=Bounds((0.190, 0.215), (0.980, 0.930)),
        clickable=False,
    ),

    "origin_marker": UIComponent(
        name="Origin Marker",
        bounds=Bounds((0.575, 0.545), (0.595, 0.565)),
    ),

    "viewcube": UIComponent(
        name="ViewCube",
        bounds=Bounds((0.905, 0.170), (0.975, 0.255)),
    ),

    "view_controls": UIComponent(
        name="View Navigation Controls",
        bounds=Bounds((0.400, 0.930), (0.650, 0.985)),
    ),
}


# =========================
# Helper Functions
# =========================

def get_component_center(component_id: str) -> Tuple[float, float]:
    """Return the normalized center of a UI component."""
    return UI_MAP[component_id].bounds.center


def list_clickable_components():
    """Return all clickable UI components."""
    return {
        k: v for k, v in UI_MAP.items()
        if v.clickable
    }


if __name__ == "__main__":
    # Example debug output
    for cid, comp in UI_MAP.items():
        print(f"{cid:25s} center = {comp.bounds.center}")
