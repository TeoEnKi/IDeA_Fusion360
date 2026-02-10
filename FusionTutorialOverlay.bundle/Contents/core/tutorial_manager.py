"""
Tutorial Manager - Loads, validates, and manages tutorial state.
"""

import json
import os
from typing import Optional, Dict, List


class TutorialStep:
    """Represents a single tutorial step."""

    def __init__(self, data: dict):
        self.step_id = data.get("stepId", "")
        self.step_number = data.get("stepNumber", 0)
        self.title = data.get("title", "")
        self.instruction = data.get("instruction", "")
        self.detailed_text = data.get("detailedText", "")
        self.annotations = data.get("annotations", [])
        self.qc_checks = data.get("qcChecks", [])
        self.warnings = data.get("warnings", [])
        self.ui_animations = data.get("uiAnimations", [])
        self.fusion_actions = data.get("fusionActions", [])
        # Step preconditions - workspace/environment requirements
        self.requires = data.get("requires", {})
        # Visual step support - reference image and UI highlights
        self.visual_step = data.get("visualStep", {})
        # Expanded content for detailed information
        self.expanded_content = data.get("expandedContent", {})

    def to_dict(self) -> dict:
        """Convert step to dictionary for JSON serialization."""
        return {
            "stepId": self.step_id,
            "stepNumber": self.step_number,
            "title": self.title,
            "instruction": self.instruction,
            "detailedText": self.detailed_text,
            "annotations": self.annotations,
            "qcChecks": self.qc_checks,
            "warnings": self.warnings,
            "uiAnimations": self.ui_animations,
            "fusionActions": self.fusion_actions,
            "requires": self.requires,
            "visualStep": self.visual_step,
            "expandedContent": self.expanded_content
        }


class Tutorial:
    """Represents a complete tutorial with multiple steps."""

    def __init__(self, data: dict):
        self.tutorial_id = data.get("tutorialId", "")
        self.title = data.get("title", "")
        self.description = data.get("description", "")
        self.steps = [TutorialStep(s) for s in data.get("steps", [])]
        self.metadata = data.get("metadata", {})

    @classmethod
    def from_file(cls, file_path: str) -> 'Tutorial':
        """Load tutorial from a JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(data)

    def get_step(self, index: int) -> Optional[TutorialStep]:
        """Get a step by index."""
        if 0 <= index < len(self.steps):
            return self.steps[index]
        return None

    @property
    def total_steps(self) -> int:
        return len(self.steps)


class TutorialManager:
    """Manages tutorial loading and navigation."""

    def __init__(self):
        self.current_tutorial: Optional[Tutorial] = None
        self.current_step_index: int = 0

    def load_tutorial(self, data: dict) -> Optional[dict]:
        """Load tutorial from dictionary data."""
        self.current_tutorial = Tutorial(data)
        self.current_step_index = 0
        return self.get_current_step_payload()

    def load_from_file(self, file_path: str) -> Optional[dict]:
        """Load tutorial from JSON file."""
        if not os.path.exists(file_path):
            return None
        self.current_tutorial = Tutorial.from_file(file_path)
        self.current_step_index = 0
        return self.get_current_step_payload()

    def get_current_step_payload(self) -> Optional[dict]:
        """Get current step as a payload for the palette."""
        if not self.current_tutorial:
            return None

        step = self.current_tutorial.get_step(self.current_step_index)
        if not step:
            return None

        payload = step.to_dict()
        payload["currentIndex"] = self.current_step_index
        payload["totalSteps"] = self.current_tutorial.total_steps
        payload["tutorialTitle"] = self.current_tutorial.title
        return payload

    def next_step(self) -> Optional[dict]:
        """Navigate to next step."""
        if self.current_tutorial and self.current_step_index < self.current_tutorial.total_steps - 1:
            self.current_step_index += 1
        return self.get_current_step_payload()

    def prev_step(self) -> Optional[dict]:
        """Navigate to previous step."""
        if self.current_step_index > 0:
            self.current_step_index -= 1
        return self.get_current_step_payload()

    def go_to_step(self, index: int) -> Optional[dict]:
        """Navigate to a specific step."""
        if self.current_tutorial and 0 <= index < self.current_tutorial.total_steps:
            self.current_step_index = index
        return self.get_current_step_payload()

    def replay_step(self) -> Optional[dict]:
        """Get current step for replay."""
        return self.get_current_step_payload()


def validate_manifest(data: dict) -> List[str]:
    """Validate a tutorial manifest and return list of errors."""
    errors = []

    # Valid workspace and environment values for requires field
    VALID_WORKSPACES = ["Design", "Render", "Animation", "Simulation", "Manufacture", "Drawing", "Generative"]
    VALID_ENVIRONMENTS = ["Solid", "Surface", "Sheet Metal", "Plastic", "Mesh", "Sketch", "Form"]

    if not data.get("tutorialId"):
        errors.append("Missing tutorialId")
    if not data.get("title"):
        errors.append("Missing title")
    if not data.get("steps"):
        errors.append("Missing steps array")
    elif not isinstance(data["steps"], list):
        errors.append("Steps must be an array")
    else:
        for i, step in enumerate(data["steps"]):
            if not step.get("stepId"):
                errors.append(f"Step {i}: missing stepId")
            if not step.get("title"):
                errors.append(f"Step {i}: missing title")
            if not step.get("instruction"):
                errors.append(f"Step {i}: missing instruction")

            # Validate requires field if present
            requires = step.get("requires", {})
            if requires:
                if not isinstance(requires, dict):
                    errors.append(f"Step {i}: requires must be an object")
                else:
                    # Validate workspace if specified
                    if "workspace" in requires:
                        if requires["workspace"] not in VALID_WORKSPACES:
                            errors.append(f"Step {i}: invalid workspace '{requires['workspace']}' in requires")

                    # Validate environment if specified
                    if "environment" in requires:
                        if requires["environment"] not in VALID_ENVIRONMENTS:
                            errors.append(f"Step {i}: invalid environment '{requires['environment']}' in requires")

    return errors
