"""
Completion Detector - Detects Fusion 360 API events for checklist toggling
Uses Fusion 360's event system to track when actions are completed.
"""

import adsk.core
import adsk.fusion
import os
from typing import Callable, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

# Import debug_log from parent module, with fallback
def _debug_log(message: str):
    """Write debug message to both print and log file."""
    try:
        print(f"[CompletionDetector] {message}")
    except:
        pass
    try:
        log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "debug.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[CompletionDetector] {message}\n")
    except:
        pass


class CompletionEventType(Enum):
    """Types of completion events we can detect."""
    SKETCH_CREATED = "sketch_created"
    SKETCH_FINISHED = "sketch_finished"
    FEATURE_CREATED = "feature_created"
    EXTRUDE_CREATED = "extrude_created"
    FILLET_CREATED = "fillet_created"
    CHAMFER_CREATED = "chamfer_created"
    REVOLVE_CREATED = "revolve_created"
    SWEEP_CREATED = "sweep_created"
    SHELL_CREATED = "shell_created"
    BODY_CREATED = "body_created"
    COMPONENT_CREATED = "component_created"
    SELECTION_CHANGED = "selection_changed"
    ACTIVE_DOCUMENT_CHANGED = "active_document_changed"
    COMMAND_STARTED = "command_started"
    COMMAND_TERMINATED = "command_terminated"


@dataclass
class CompletionEvent:
    """Represents a completion event."""
    event_type: CompletionEventType
    entity_name: str = ""
    entity_id: str = ""
    additional_info: Dict = None

    def to_dict(self) -> Dict:
        return {
            "eventType": self.event_type.value,
            "entityName": self.entity_name,
            "entityId": self.entity_id,
            "additionalInfo": self.additional_info or {}
        }


# Map Fusion command IDs to event types for command_started detection
COMMAND_MAP = {
    'SketchCreate': 'sketch',
    'SketchActivate': 'sketch',
    'SketchCenterRectangle': 'sketch_rectangle',
    'SketchRectangle': 'sketch_rectangle',
    'SketchLine': 'sketch_line',
    'SketchCircle': 'sketch_circle',
    'SketchArc': 'sketch_arc',
    'Sketch3PointArc': 'sketch_arc',
    'SketchFittedSpline': 'sketch_spline',
    'SketchSpline': 'sketch_spline',
    'SketchDimension': 'sketch_dimension',
    'SketchConstraint': 'sketch_constraint',
    'FinishSketch': 'finish_sketch',
    'Extrude': 'extrude',
    'FilletEdge': 'fillet',
    'ChamferEdge': 'chamfer',
    'Revolve': 'revolve',
    'Sweep': 'sweep',
    'Shell': 'shell',
    'Loft': 'loft',
    'Hole': 'hole',
}


class CommandStartingHandler(adsk.core.ApplicationCommandEventHandler):
    """Handles commandStarting events to detect when the user clicks a tool."""

    def __init__(self, on_completion: Callable[[CompletionEvent], None]):
        super().__init__()
        self.on_completion = on_completion

    def notify(self, args: adsk.core.ApplicationCommandEventArgs):
        try:
            command_id = args.commandId
            mapped_type = COMMAND_MAP.get(command_id, '')
            _debug_log(f"USER ACTION: command_started -> commandId='{command_id}', mappedType='{mapped_type}'")
            event = CompletionEvent(
                event_type=CompletionEventType.COMMAND_STARTED,
                entity_name=COMMAND_MAP.get(command_id, command_id),
                additional_info={
                    'commandId': command_id,
                    'mappedType': mapped_type
                }
            )
            self.on_completion(event)
        except Exception as e:
            _debug_log(f"ERROR in CommandStartingHandler.notify: {e}")


class TimelineEventHandler(adsk.core.ApplicationCommandEventHandler):
    """Handles command termination events to detect feature creation."""

    def __init__(self, on_completion: Callable[[CompletionEvent], None]):
        super().__init__()
        self.on_completion = on_completion
        self._last_timeline_count = 0

    def notify(self, args: adsk.core.ApplicationCommandEventArgs):
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)

            if not design:
                _debug_log("USER ACTION: command_terminated but no active design")
                return

            # Pass the command ID through in additional_info
            command_id = args.commandId if hasattr(args, 'commandId') else ''
            _debug_log(f"USER ACTION: command_terminated -> commandId='{command_id}'")

            # Check timeline for new features
            timeline = design.timeline
            current_count = timeline.count if timeline else 0

            _debug_log(f"  Timeline count: previous={self._last_timeline_count}, current={current_count}")

            if current_count > self._last_timeline_count:
                # New feature was added
                for i in range(self._last_timeline_count, current_count):
                    try:
                        item = timeline.item(i)
                        entity = item.entity
                        event_type = self._get_event_type(entity)
                        entity_type_name = type(entity).__name__
                        entity_name = getattr(entity, 'name', entity_type_name)

                        _debug_log(f"  New timeline item [{i}]: entityType='{entity_type_name}', name='{entity_name}', eventType='{event_type.value if event_type else 'None'}'")

                        if event_type:
                            info = self._get_entity_info(entity)
                            info['commandId'] = command_id
                            event = CompletionEvent(
                                event_type=event_type,
                                entity_name=entity_name,
                                entity_id=str(i),
                                additional_info=info
                            )
                            self.on_completion(event)
                    except Exception as e:
                        _debug_log(f"  ERROR processing timeline item [{i}]: {e}")

                self._last_timeline_count = current_count
            else:
                # No new timeline items — but if this was a recognized command
                # (e.g. SketchLine, Sketch3PointArc), fire a command_terminated
                # event so JS can still complete checklist items for sketch tools
                # that don't create their own timeline entries.
                if command_id in COMMAND_MAP:
                    _debug_log(f"  No new timeline items, but '{command_id}' is a known command — firing command_terminated event")
                    event = CompletionEvent(
                        event_type=CompletionEventType.COMMAND_TERMINATED,
                        entity_name=COMMAND_MAP.get(command_id, command_id),
                        additional_info={
                            'commandId': command_id,
                            'mappedType': COMMAND_MAP.get(command_id, '')
                        }
                    )
                    self.on_completion(event)
                else:
                    _debug_log(f"  No new timeline items (command '{command_id}' is not a tracked command)")

        except Exception as e:
            _debug_log(f"ERROR in TimelineEventHandler.notify: {e}")

    def _get_event_type(self, entity) -> Optional[CompletionEventType]:
        """Map entity type to completion event type."""
        type_name = type(entity).__name__

        mapping = {
            'Sketch': CompletionEventType.SKETCH_CREATED,
            'ExtrudeFeature': CompletionEventType.EXTRUDE_CREATED,
            'FilletFeature': CompletionEventType.FILLET_CREATED,
            'ChamferFeature': CompletionEventType.CHAMFER_CREATED,
            'RevolveFeature': CompletionEventType.REVOLVE_CREATED,
            'SweepFeature': CompletionEventType.SWEEP_CREATED,
            'ShellFeature': CompletionEventType.SHELL_CREATED,
        }

        return mapping.get(type_name, CompletionEventType.FEATURE_CREATED)

    def _get_entity_info(self, entity) -> Dict:
        """Extract additional info from entity."""
        info = {}

        try:
            if hasattr(entity, 'name'):
                info['name'] = entity.name
            if hasattr(entity, 'healthState'):
                info['healthy'] = entity.healthState == adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState
        except:
            pass

        return info

    def reset_count(self):
        """Reset the timeline count tracking."""
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            if design and design.timeline:
                self._last_timeline_count = design.timeline.count
        except:
            self._last_timeline_count = 0


class SketchEventHandler(adsk.core.ActiveSelectionEventHandler):
    """Handles sketch-related events."""

    def __init__(self, on_completion: Callable[[CompletionEvent], None]):
        super().__init__()
        self.on_completion = on_completion
        self._was_in_sketch = False

    def notify(self, args: adsk.core.ActiveSelectionEventArgs):
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)

            if not design:
                return

            # Check if we just exited sketch mode
            is_in_sketch = design.activeEditObject and \
                          type(design.activeEditObject).__name__ == 'Sketch'

            if self._was_in_sketch and not is_in_sketch:
                # Sketch was finished
                _debug_log("USER ACTION: sketch_finished (exited sketch mode)")
                event = CompletionEvent(
                    event_type=CompletionEventType.SKETCH_FINISHED,
                    entity_name="Sketch",
                    additional_info={"action": "finished"}
                )
                self.on_completion(event)
            elif not self._was_in_sketch and is_in_sketch:
                sketch_name = getattr(design.activeEditObject, 'name', 'unknown')
                _debug_log(f"USER ACTION: entered sketch mode -> sketch='{sketch_name}'")

            self._was_in_sketch = is_in_sketch

        except Exception as e:
            _debug_log(f"ERROR in SketchEventHandler.notify: {e}")


class CompletionDetector:
    """
    Main completion detector that manages event subscriptions
    and notifies the palette when actions are completed.
    """

    def __init__(self):
        self._handlers: List = []
        self._callbacks: List[Callable[[CompletionEvent], None]] = []
        self._is_active = False
        self._timeline_handler: Optional[TimelineEventHandler] = None
        self._command_starting_handler: Optional[CommandStartingHandler] = None
        self._app = adsk.core.Application.get()

    def start(self):
        """Start listening for completion events."""
        if self._is_active:
            _debug_log("start() called but already active")
            return

        try:
            ui = self._app.userInterface

            # Subscribe to command terminated event (fires after any command completes)
            self._timeline_handler = TimelineEventHandler(self._on_event)
            ui.commandTerminated.add(self._timeline_handler)
            self._handlers.append(self._timeline_handler)
            _debug_log("Subscribed to commandTerminated event")

            # Subscribe to command starting event (fires when user clicks a tool)
            self._command_starting_handler = CommandStartingHandler(self._on_event)
            ui.commandStarting.add(self._command_starting_handler)
            self._handlers.append(self._command_starting_handler)
            _debug_log("Subscribed to commandStarting event")

            self._is_active = True
            _debug_log("CompletionDetector is now active and listening for events")

        except Exception as e:
            _debug_log(f"ERROR in CompletionDetector.start: {e}")

    def stop(self):
        """Stop listening for completion events."""
        self._is_active = False

        # Clean up handlers
        try:
            ui = self._app.userInterface
            if self._timeline_handler:
                ui.commandTerminated.remove(self._timeline_handler)
            if self._command_starting_handler:
                ui.commandStarting.remove(self._command_starting_handler)
        except:
            pass

        self._handlers.clear()
        self._timeline_handler = None
        self._command_starting_handler = None

    def add_callback(self, callback: Callable[[CompletionEvent], None]):
        """Add a callback to be notified of completion events."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[CompletionEvent], None]):
        """Remove a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def reset_tracking(self):
        """Reset timeline tracking (call when loading a new step)."""
        if self._timeline_handler:
            self._timeline_handler.reset_count()

    def _on_event(self, event: CompletionEvent):
        """Internal handler that dispatches to all callbacks."""
        _debug_log(f"Dispatching event '{event.event_type.value}' to {len(self._callbacks)} callback(s)")
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                _debug_log(f"ERROR in completion callback: {e}")

    def capture_viewport_screenshot(self, output_path: str) -> bool:
        """
        Capture the current viewport as an image.

        Args:
            output_path: Full path where the image should be saved (e.g., "C:/temp/screenshot.png")

        Returns:
            True if successful, False otherwise
        """
        try:
            viewport = self._app.activeViewport
            if not viewport:
                return False

            # Save the viewport as an image
            success = viewport.saveAsImageFile(output_path, 0, 0)
            return success

        except Exception as e:
            return False

    def get_current_state(self) -> Dict:
        """Get the current state of the design for QC checks."""
        state = {
            "hasDesign": False,
            "sketchCount": 0,
            "bodyCount": 0,
            "featureCount": 0,
            "activeSketch": None,
            "selectedEntities": []
        }

        try:
            design = adsk.fusion.Design.cast(self._app.activeProduct)
            if not design:
                return state

            state["hasDesign"] = True

            # Count sketches
            root = design.rootComponent
            state["sketchCount"] = root.sketches.count

            # Count bodies
            state["bodyCount"] = root.bRepBodies.count

            # Count features
            if design.timeline:
                state["featureCount"] = design.timeline.count

            # Check for active sketch
            active_edit = design.activeEditObject
            if active_edit and type(active_edit).__name__ == 'Sketch':
                state["activeSketch"] = active_edit.name

            # Get selected entities
            selection = self._app.userInterface.activeSelections
            if selection:
                for i in range(selection.count):
                    try:
                        entity = selection.item(i).entity
                        state["selectedEntities"].append({
                            "type": type(entity).__name__,
                            "name": getattr(entity, 'name', 'unknown')
                        })
                    except:
                        pass

        except Exception as e:
            pass

        return state

    def check_qc_conditions(self, conditions: List[Dict]) -> List[Dict]:
        """
        Check a list of QC conditions against the current state.

        Args:
            conditions: List of condition dicts with 'type', 'expected', etc.

        Returns:
            List of results with 'passed' boolean for each condition
        """
        results = []
        state = self.get_current_state()

        for condition in conditions:
            result = {"condition": condition, "passed": False}

            try:
                cond_type = condition.get("type", "")

                if cond_type == "sketch_exists":
                    result["passed"] = state["sketchCount"] > 0

                elif cond_type == "body_exists":
                    result["passed"] = state["bodyCount"] > 0

                elif cond_type == "feature_count_gte":
                    expected = condition.get("expected", 0)
                    result["passed"] = state["featureCount"] >= expected

                elif cond_type == "not_in_sketch":
                    result["passed"] = state["activeSketch"] is None

                elif cond_type == "in_sketch":
                    result["passed"] = state["activeSketch"] is not None

                elif cond_type == "body_count_gte":
                    expected = condition.get("expected", 0)
                    result["passed"] = state["bodyCount"] >= expected

            except Exception as e:
                pass

            results.append(result)

        return results
