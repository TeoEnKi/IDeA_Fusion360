"""
Redirect Templates - Pre-defined redirect step templates for common navigation scenarios.
Generates redirect steps when users need to switch workspaces or environments.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class RedirectStep:
    """Represents a redirect guidance step."""
    step_type: str = "redirect"
    title: str = ""
    instruction: str = ""
    reference_image: str = ""
    current_context: Dict[str, str] = None
    required_context: Dict[str, str] = None
    ui_animations: List[Dict] = None
    original_step_index: int = 0
    reason: str = ""

    def __post_init__(self):
        if self.current_context is None:
            self.current_context = {}
        if self.required_context is None:
            self.required_context = {}
        if self.ui_animations is None:
            self.ui_animations = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "stepType": self.step_type,
            "title": self.title,
            "instruction": self.instruction,
            "referenceImage": self.reference_image,
            "currentContext": self.current_context,
            "requiredContext": self.required_context,
            "uiAnimations": self.ui_animations,
            "originalStepIndex": self.original_step_index,
            "reason": self.reason,
            "isRedirect": True
        }


class RedirectTemplateLibrary:
    """Library of redirect templates for common navigation scenarios."""

    # Templates organized by redirect type, then by target
    TEMPLATES = {
        "switchEnvironment": {
            "Solid": {
                "title": "Switch to Solid Environment",
                "instruction": "Click the SOLID tab in the Design toolbar to access solid modeling tools.",
                "reference_image": "fusion_design_tabs.png",
                "ui_animations": [
                    {"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 20, "y": 10}, "duration": 500},
                    {"type": "click", "at": {"x": 20, "y": 10}},
                    {"type": "pause", "duration": 300}
                ]
            },
            "Surface": {
                "title": "Switch to Surface Environment",
                "instruction": "Click the SURFACE tab in the Design toolbar to access surface modeling tools.",
                "reference_image": "fusion_design_tabs.png",
                "ui_animations": [
                    {"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 35, "y": 10}, "duration": 500},
                    {"type": "click", "at": {"x": 35, "y": 10}},
                    {"type": "pause", "duration": 300}
                ]
            },
            "Sheet Metal": {
                "title": "Switch to Sheet Metal Environment",
                "instruction": "Click the SHEET METAL tab in the Design toolbar to access sheet metal tools.",
                "reference_image": "fusion_design_tabs.png",
                "ui_animations": [
                    {"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 50, "y": 10}, "duration": 500},
                    {"type": "click", "at": {"x": 50, "y": 10}},
                    {"type": "pause", "duration": 300}
                ]
            },
            "Mesh": {
                "title": "Switch to Mesh Environment",
                "instruction": "Click the MESH tab in the Design toolbar to access mesh editing tools.",
                "reference_image": "fusion_design_tabs.png",
                "ui_animations": [
                    {"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 65, "y": 10}, "duration": 500},
                    {"type": "click", "at": {"x": 65, "y": 10}},
                    {"type": "pause", "duration": 300}
                ]
            },
            "Sketch": {
                "title": "Enter Sketch Mode",
                "instruction": "Double-click on a sketch in the timeline or browser, or click Create Sketch to start a new sketch.",
                "reference_image": "fusion_sketch_mode.png",
                "ui_animations": [
                    {"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 30, "y": 80}, "duration": 500},
                    {"type": "click", "at": {"x": 30, "y": 80}},
                    {"type": "click", "at": {"x": 30, "y": 80}},
                    {"type": "pause", "duration": 300}
                ]
            },
            "Form": {
                "title": "Switch to Form (T-Spline) Environment",
                "instruction": "Click Create Form in the toolbar, or double-click an existing Form feature.",
                "reference_image": "fusion_form_mode.png",
                "ui_animations": [
                    {"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 80, "y": 10}, "duration": 500},
                    {"type": "click", "at": {"x": 80, "y": 10}},
                    {"type": "pause", "duration": 300}
                ]
            }
        },
        "switchWorkspace": {
            "Design": {
                "title": "Switch to Design Workspace",
                "instruction": "Click the workspace dropdown at the top-left and select 'Design'.",
                "reference_image": "fusion_workspace_selector.png",
                "ui_animations": [
                    {"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 10, "y": 5}, "duration": 500},
                    {"type": "click", "at": {"x": 10, "y": 5}},
                    {"type": "pause", "duration": 400},
                    {"type": "move", "from": {"x": 10, "y": 5}, "to": {"x": 10, "y": 20}, "duration": 300},
                    {"type": "click", "at": {"x": 10, "y": 20}}
                ]
            },
            "Render": {
                "title": "Switch to Render Workspace",
                "instruction": "Click the workspace dropdown at the top-left and select 'Render'.",
                "reference_image": "fusion_workspace_selector.png",
                "ui_animations": [
                    {"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 10, "y": 5}, "duration": 500},
                    {"type": "click", "at": {"x": 10, "y": 5}},
                    {"type": "pause", "duration": 400},
                    {"type": "move", "from": {"x": 10, "y": 5}, "to": {"x": 10, "y": 30}, "duration": 300},
                    {"type": "click", "at": {"x": 10, "y": 30}}
                ]
            },
            "Manufacture": {
                "title": "Switch to Manufacture Workspace",
                "instruction": "Click the workspace dropdown at the top-left and select 'Manufacture'.",
                "reference_image": "fusion_workspace_selector.png",
                "ui_animations": [
                    {"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 10, "y": 5}, "duration": 500},
                    {"type": "click", "at": {"x": 10, "y": 5}},
                    {"type": "pause", "duration": 400},
                    {"type": "move", "from": {"x": 10, "y": 5}, "to": {"x": 10, "y": 40}, "duration": 300},
                    {"type": "click", "at": {"x": 10, "y": 40}}
                ]
            },
            "Simulation": {
                "title": "Switch to Simulation Workspace",
                "instruction": "Click the workspace dropdown at the top-left and select 'Simulation'.",
                "reference_image": "fusion_workspace_selector.png",
                "ui_animations": [
                    {"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 10, "y": 5}, "duration": 500},
                    {"type": "click", "at": {"x": 10, "y": 5}},
                    {"type": "pause", "duration": 400},
                    {"type": "move", "from": {"x": 10, "y": 5}, "to": {"x": 10, "y": 50}, "duration": 300},
                    {"type": "click", "at": {"x": 10, "y": 50}}
                ]
            },
            "Drawing": {
                "title": "Switch to Drawing Workspace",
                "instruction": "Click the workspace dropdown at the top-left and select 'Drawing'.",
                "reference_image": "fusion_workspace_selector.png",
                "ui_animations": [
                    {"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 10, "y": 5}, "duration": 500},
                    {"type": "click", "at": {"x": 10, "y": 5}},
                    {"type": "pause", "duration": 400},
                    {"type": "move", "from": {"x": 10, "y": 5}, "to": {"x": 10, "y": 60}, "duration": 300},
                    {"type": "click", "at": {"x": 10, "y": 60}}
                ]
            }
        },
        "openDocument": {
            "default": {
                "title": "Open a Document",
                "instruction": "Open an existing design or create a new one from File > New Design.",
                "reference_image": "fusion_new_design.png",
                "ui_animations": [
                    {"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 5, "y": 5}, "duration": 500},
                    {"type": "click", "at": {"x": 5, "y": 5}},
                    {"type": "pause", "duration": 300}
                ]
            }
        },
        "exitSketch": {
            "default": {
                "title": "Exit Sketch Mode",
                "instruction": "Click 'Finish Sketch' in the toolbar or press Escape to exit sketch editing.",
                "reference_image": "fusion_finish_sketch.png",
                "ui_animations": [
                    {"type": "move", "from": {"x": 50, "y": 50}, "to": {"x": 90, "y": 10}, "duration": 500},
                    {"type": "click", "at": {"x": 90, "y": 10}},
                    {"type": "pause", "duration": 300}
                ]
            }
        }
    }

    @classmethod
    def generate_redirect_step(
        cls,
        mismatch_details: Dict[str, Any],
        original_step_index: int
    ) -> Optional[RedirectStep]:
        """
        Generate a redirect step based on mismatch details.

        Args:
            mismatch_details: The mismatch details from FusionContextDetector.get_mismatch_details()
            original_step_index: The index of the step that requires the redirect

        Returns:
            A RedirectStep instance, or None if no template matches.
        """
        if mismatch_details.get("matched", True):
            return None

        mismatches = mismatch_details.get("mismatches", [])
        if not mismatches:
            return None

        # Handle the first mismatch (could chain multiple redirects if needed)
        mismatch = mismatches[0]
        mismatch_type = mismatch.get("type", "")
        required = mismatch.get("required", "")
        current = mismatch.get("current", "")

        template = None
        redirect_type = ""

        if mismatch_type == "workspace":
            redirect_type = "switchWorkspace"
            template = cls.TEMPLATES.get("switchWorkspace", {}).get(required)
        elif mismatch_type == "environment":
            redirect_type = "switchEnvironment"
            template = cls.TEMPLATES.get("switchEnvironment", {}).get(required)
        elif mismatch_type == "document":
            redirect_type = "openDocument"
            template = cls.TEMPLATES.get("openDocument", {}).get("default")
        elif mismatch_type == "sketch":
            # Need to enter sketch mode
            redirect_type = "switchEnvironment"
            template = cls.TEMPLATES.get("switchEnvironment", {}).get("Sketch")

        if not template:
            # Generate a generic redirect step
            return RedirectStep(
                title=f"Navigate to {required}",
                instruction=mismatch.get("message", f"Please switch to {required}"),
                current_context={"type": mismatch_type, "value": str(current)},
                required_context={"type": mismatch_type, "value": str(required)},
                original_step_index=original_step_index,
                reason=mismatch_details.get("reason", "")
            )

        return RedirectStep(
            title=template.get("title", ""),
            instruction=template.get("instruction", ""),
            reference_image=template.get("reference_image", ""),
            current_context={"type": mismatch_type, "value": str(current)},
            required_context={"type": mismatch_type, "value": str(required)},
            ui_animations=template.get("ui_animations", []),
            original_step_index=original_step_index,
            reason=mismatch_details.get("reason", "")
        )

    @classmethod
    def get_template(cls, redirect_type: str, target: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific template.

        Args:
            redirect_type: The type of redirect (e.g., "switchEnvironment")
            target: The target value (e.g., "Solid")

        Returns:
            The template dictionary, or None if not found.
        """
        return cls.TEMPLATES.get(redirect_type, {}).get(target)

    @classmethod
    def get_available_templates(cls) -> Dict[str, List[str]]:
        """Get a summary of available templates."""
        summary = {}
        for redirect_type, targets in cls.TEMPLATES.items():
            summary[redirect_type] = list(targets.keys())
        return summary
