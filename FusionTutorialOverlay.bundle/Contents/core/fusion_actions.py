"""
Fusion Actions Runner - Executes viewport actions in Fusion 360.
Handles selection prompts and entity highlighting.
"""

import adsk.core
import adsk.fusion
from typing import List, Dict, Optional


class FusionActionsRunner:
    """Executes Fusion 360 viewport and model actions."""

    def __init__(self):
        self.app = adsk.core.Application.get()

    def execute_actions(self, actions: List[dict]) -> List[dict]:
        """Execute a list of Fusion actions and return results."""
        results = []
        for action in actions:
            result = self._execute_single_action(action)
            results.append(result)
        return results

    def _execute_single_action(self, action: dict) -> dict:
        """Execute a single action and return result."""
        action_type = action.get("type", "")
        result = {"action": action_type, "success": False}

        try:
            if action_type.startswith("prompt."):
                result = self._handle_prompt_action(action)
            elif action_type.startswith("highlight."):
                result = self._handle_highlight_action(action)
            elif action_type.startswith("viewport."):
                result = self._handle_viewport_action(action)
            else:
                result["message"] = f"Unknown action type: {action_type}"

        except Exception as e:
            result["message"] = str(e)
            result["success"] = False

        return result

    def _handle_prompt_action(self, action: dict) -> dict:
        """Handle selection prompt actions."""
        action_type = action.get("type", "")
        result = {"action": action_type, "success": False}

        if action_type == "prompt.selectEntity":
            entity_type = action.get("entityType", "face")
            message = action.get("message", f"Please select a {entity_type}")

            # Store the expected selection for validation
            result["entityType"] = entity_type
            result["message"] = message
            result["success"] = True

        elif action_type == "prompt.message":
            message = action.get("message", "")
            ui = self.app.userInterface
            if ui:
                ui.messageBox(message)
            result["success"] = True

        return result

    def _handle_highlight_action(self, action: dict) -> dict:
        """Handle entity highlighting actions."""
        action_type = action.get("type", "")
        result = {"action": action_type, "success": False}

        design = adsk.fusion.Design.cast(self.app.activeProduct)
        if not design:
            result["message"] = "No active design"
            return result

        root = design.rootComponent

        if action_type == "highlight.body":
            body_name = action.get("bodyName", "")
            for body in root.bRepBodies:
                if body.name == body_name:
                    # Select the body to highlight it
                    ui = self.app.userInterface
                    if ui:
                        selection = ui.activeSelections
                        selection.clear()
                        selection.add(body)
                    result["success"] = True
                    break

        elif action_type == "highlight.component":
            comp_name = action.get("componentName", "")
            for occ in root.occurrences:
                if occ.name == comp_name:
                    ui = self.app.userInterface
                    if ui:
                        selection = ui.activeSelections
                        selection.clear()
                        selection.add(occ)
                    result["success"] = True
                    break

        elif action_type == "highlight.clear":
            ui = self.app.userInterface
            if ui:
                ui.activeSelections.clear()
            result["success"] = True

        return result

    def _handle_viewport_action(self, action: dict) -> dict:
        """Handle viewport-related actions."""
        action_type = action.get("type", "")
        result = {"action": action_type, "success": False}

        if action_type == "viewport.captureImage":
            # Capture viewport screenshot
            # Note: This would save to a file, then convert to data URL
            viewport = self.app.activeViewport
            if viewport:
                result["success"] = True
                result["message"] = "Viewport capture not implemented for local test"

        elif action_type == "viewport.refresh":
            viewport = self.app.activeViewport
            if viewport:
                viewport.refresh()
                result["success"] = True

        return result

    def get_model_info(self) -> Optional[dict]:
        """Get information about the current model."""
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        if not design:
            return None

        root = design.rootComponent

        info = {
            "name": root.name,
            "bodies": [b.name for b in root.bRepBodies],
            "sketches": [s.name for s in root.sketches],
            "occurrences": [o.name for o in root.occurrences],
            "features": [f.name for f in root.features if f.name],
        }

        return info
