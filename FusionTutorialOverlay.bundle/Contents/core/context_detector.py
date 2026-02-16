"""
Context Detector - Detects the current Fusion 360 workspace and environment context.
Used to verify step preconditions and trigger redirect guidance.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

try:
    import adsk.core
    import adsk.fusion
    FUSION_AVAILABLE = True
except ImportError:
    FUSION_AVAILABLE = False


class Workspace(Enum):
    """Fusion 360 workspaces."""
    DESIGN = "Design"
    RENDER = "Render"
    ANIMATION = "Animation"
    SIMULATION = "Simulation"
    MANUFACTURE = "Manufacture"
    DRAWING = "Drawing"
    GENERATIVE = "Generative"
    UNKNOWN = "Unknown"


class Environment(Enum):
    """Fusion 360 design environments (tabs within Design workspace)."""
    SOLID = "Solid"
    SURFACE = "Surface"
    SHEET_METAL = "Sheet Metal"
    PLASTIC = "Plastic"
    MESH = "Mesh"
    SKETCH = "Sketch"  # When actively editing a sketch
    FORM = "Form"  # T-Spline environment
    UNKNOWN = "Unknown"


@dataclass
class FusionContext:
    """Represents the current Fusion 360 UI context."""
    workspace: Workspace
    environment: Environment
    has_active_document: bool
    has_active_sketch: bool
    document_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for JSON serialization."""
        return {
            "workspace": self.workspace.value,
            "environment": self.environment.value,
            "hasActiveDocument": self.has_active_document,
            "hasActiveSketch": self.has_active_sketch,
            "documentName": self.document_name
        }


def _debug_log(message: str):
    """Debug logging for context detector."""
    try:
        print(f"[ContextDetector] {message}")
    except:
        pass


class FusionContextDetector:
    """Detects the current Fusion 360 context."""

    def __init__(self):
        self._app = None
        if FUSION_AVAILABLE:
            try:
                self._app = adsk.core.Application.get()
            except:
                pass

    def get_current_context(self) -> FusionContext:
        """Get the current Fusion 360 context."""
        if not FUSION_AVAILABLE or not self._app:
            return FusionContext(
                workspace=Workspace.UNKNOWN,
                environment=Environment.UNKNOWN,
                has_active_document=False,
                has_active_sketch=False
            )

        try:
            workspace = self._detect_workspace()
            environment = self._detect_environment()
            has_document = self._has_active_document()
            has_sketch = self._has_active_sketch()
            doc_name = self._get_document_name()

            return FusionContext(
                workspace=workspace,
                environment=environment,
                has_active_document=has_document,
                has_active_sketch=has_sketch,
                document_name=doc_name
            )
        except Exception:
            return FusionContext(
                workspace=Workspace.UNKNOWN,
                environment=Environment.UNKNOWN,
                has_active_document=False,
                has_active_sketch=False
            )

    def _detect_workspace(self) -> Workspace:
        """Detect the current workspace."""
        try:
            ui = self._app.userInterface
            active_workspace = ui.activeWorkspace

            if not active_workspace:
                return Workspace.UNKNOWN

            workspace_id = active_workspace.id.lower()

            workspace_map = {
                "fusionsolidmodeling": Workspace.DESIGN,
                "fusiontooldesignenv": Workspace.DESIGN,
                "fusioncamenv": Workspace.MANUFACTURE,
                "fusonrenderenvironment": Workspace.RENDER,
                "fusiondrawingenvironment": Workspace.DRAWING,
                "fusionsimulationenvironment": Workspace.SIMULATION,
                "fusionanimationenvironment": Workspace.ANIMATION,
                "fusiongendesignenvironment": Workspace.GENERATIVE,
            }

            for key, value in workspace_map.items():
                if key in workspace_id:
                    return value

            # Default to Design if in solid modeling context
            if "solid" in workspace_id or "design" in workspace_id:
                return Workspace.DESIGN

            return Workspace.UNKNOWN

        except Exception:
            return Workspace.UNKNOWN

    def _detect_environment(self) -> Environment:
        """Detect the current environment within the Design workspace.

        Priority order:
        1. Active toolbar tab (most reliable — updates immediately on tab click)
        2. Active sketch check (secondary — activeEditObject can lag behind UI)
        3. Workspace ID fallback
        4. Default to SOLID if in Design workspace
        """
        try:
            ui = self._app.userInterface
            active_workspace = ui.activeWorkspace

            if not active_workspace:
                return Environment.UNKNOWN

            # Primary: check active toolbar tab (most reliable indicator)
            try:
                toolbar_tabs = active_workspace.toolbarTabs
                if toolbar_tabs:
                    _debug_log(f"Found {toolbar_tabs.count} toolbar tabs")
                    for i in range(toolbar_tabs.count):
                        tab = toolbar_tabs.item(i)
                        tab_id = tab.id if tab.id else "unknown"
                        tab_name = tab.name if tab.name else "unknown"
                        is_active = tab.isActive

                        if is_active:
                            _debug_log(f"Active tab: id='{tab_id}', name='{tab_name}'")
                            tab_id_lower = tab_id.lower()
                            tab_name_lower = tab_name.lower()

                            # Check tab ID or name for environment
                            if "solid" in tab_id_lower or "solid" in tab_name_lower:
                                _debug_log("Detected: SOLID environment")
                                return Environment.SOLID
                            if "surface" in tab_id_lower or "surface" in tab_name_lower:
                                _debug_log("Detected: SURFACE environment")
                                return Environment.SURFACE
                            if "sheetmetal" in tab_id_lower or "sheet metal" in tab_name_lower:
                                _debug_log("Detected: SHEET_METAL environment")
                                return Environment.SHEET_METAL
                            if "mesh" in tab_id_lower or "mesh" in tab_name_lower:
                                _debug_log("Detected: MESH environment")
                                return Environment.MESH
                            if "plastic" in tab_id_lower or "plastic" in tab_name_lower:
                                _debug_log("Detected: PLASTIC environment")
                                return Environment.PLASTIC
                            if "form" in tab_id_lower or "form" in tab_name_lower or "sculpt" in tab_name_lower:
                                _debug_log("Detected: FORM environment")
                                return Environment.FORM

                            _debug_log(f"Tab '{tab_name}' did not match any known environment")
            except Exception as e:
                _debug_log(f"Error checking toolbar tabs: {e}")

            # Secondary: if actively editing a sketch, report SKETCH
            if self._has_active_sketch():
                _debug_log("Detected: SKETCH environment (active sketch, no toolbar tab match)")
                return Environment.SKETCH

            # Fallback: check workspace ID for non-Design environments
            try:
                workspace_id = active_workspace.id.lower()

                if "sheetmetal" in workspace_id:
                    return Environment.SHEET_METAL
                if "surface" in workspace_id:
                    return Environment.SURFACE
                if "mesh" in workspace_id:
                    return Environment.MESH
                if "form" in workspace_id or "tspline" in workspace_id:
                    return Environment.FORM
            except:
                pass

            # Default to Solid if in Design workspace (most common case)
            workspace = self._detect_workspace()
            if workspace == Workspace.DESIGN:
                return Environment.SOLID

            return Environment.UNKNOWN

        except Exception:
            return Environment.UNKNOWN

    def _has_active_document(self) -> bool:
        """Check if there's an active document."""
        try:
            return self._app.activeDocument is not None
        except:
            return False

    def _has_active_sketch(self) -> bool:
        """Check if there's an active sketch being edited."""
        try:
            product = self._app.activeProduct
            if product and product.productType == 'DesignProductType':
                design = adsk.fusion.Design.cast(product)
                if design:
                    return design.activeEditObject is not None and \
                           design.activeEditObject.objectType == adsk.fusion.Sketch.classType()
        except:
            pass
        return False

    def _get_document_name(self) -> Optional[str]:
        """Get the name of the active document."""
        try:
            doc = self._app.activeDocument
            if doc:
                return doc.name
        except:
            pass
        return None

    def matches_requirements(self, requirements: Dict[str, Any]) -> bool:
        """
        Check if the current context matches the given requirements.

        Args:
            requirements: Dict with optional keys:
                - workspace: Required workspace name (e.g., "Design")
                - environment: Required environment name (e.g., "Solid")
                - hasActiveDocument: Whether a document must be open
                - hasActiveSketch: Whether a sketch must be active

        Returns:
            True if all requirements are met, False otherwise.
        """
        if not requirements:
            return True

        context = self.get_current_context()

        # Check workspace
        required_workspace = requirements.get("workspace")
        if required_workspace:
            if context.workspace.value.lower() != required_workspace.lower():
                return False

        # Check environment
        required_environment = requirements.get("environment")
        if required_environment:
            if context.environment.value.lower() != required_environment.lower():
                return False

        # Check active document
        if requirements.get("hasActiveDocument", False):
            if not context.has_active_document:
                return False

        # Check active sketch
        if requirements.get("hasActiveSketch", False):
            if not context.has_active_sketch:
                return False

        return True

    def get_mismatch_details(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get details about what requirements are not met.

        Args:
            requirements: The requirements to check against.

        Returns:
            Dict with:
                - matched: Boolean indicating if all requirements are met
                - current: The current context values
                - required: The required context values
                - mismatches: List of specific mismatch descriptions
        """
        context = self.get_current_context()
        mismatches = []

        required_workspace = requirements.get("workspace")
        required_environment = requirements.get("environment")

        if required_workspace:
            if context.workspace.value.lower() != required_workspace.lower():
                mismatches.append({
                    "type": "workspace",
                    "current": context.workspace.value,
                    "required": required_workspace,
                    "message": f"Switch from {context.workspace.value} to {required_workspace} workspace"
                })

        if required_environment:
            if context.environment.value.lower() != required_environment.lower():
                mismatches.append({
                    "type": "environment",
                    "current": context.environment.value,
                    "required": required_environment,
                    "message": f"Switch from {context.environment.value} to {required_environment} environment"
                })

        if requirements.get("hasActiveDocument", False) and not context.has_active_document:
            mismatches.append({
                "type": "document",
                "current": False,
                "required": True,
                "message": "Open a document to continue"
            })

        if requirements.get("hasActiveSketch", False) and not context.has_active_sketch:
            mismatches.append({
                "type": "sketch",
                "current": False,
                "required": True,
                "message": "Enter sketch edit mode to continue"
            })

        return {
            "matched": len(mismatches) == 0,
            "current": context.to_dict(),
            "required": requirements,
            "mismatches": mismatches,
            "reason": requirements.get("reason", "This step requires a specific context")
        }
