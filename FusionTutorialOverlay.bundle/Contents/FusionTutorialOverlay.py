"""
FusionTutorialOverlay - AI-driven tutorial overlay for Fusion 360
Main add-in entry point
"""

# Minimal imports first - these should never fail
import os
import sys
import traceback
import base64
import time

# Get the directory for logging BEFORE any other imports
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_LOG_PATH = os.path.join(_THIS_DIR, "debug.log")

# Debug helper - writes to file since Text Commands may not show
def debug_log(message: str):
    """Write debug message to both print and a log file."""
    try:
        print(f"[TutorialOverlay] {message}")
    except:
        pass
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")
    except:
        pass

# Clear log and start fresh
try:
    with open(_LOG_PATH, "w", encoding="utf-8") as f:
        f.write("=== Module Loading ===\n")
except:
    pass

debug_log("Step 1: Basic imports done")

# Now try Fusion imports
try:
    import adsk.core
    debug_log("Step 2: adsk.core imported")
except Exception as e:
    debug_log(f"FAILED to import adsk.core: {e}")
    raise

try:
    import adsk.fusion
    debug_log("Step 3: adsk.fusion imported")
except Exception as e:
    debug_log(f"FAILED to import adsk.fusion: {e}")
    raise

try:
    import json
    debug_log("Step 4: json imported")
except Exception as e:
    debug_log(f"FAILED to import json: {e}")
    raise

debug_log("Step 5: All basic imports complete")

# Add the Contents directory to path for imports
ADDIN_DIR = os.path.dirname(os.path.abspath(__file__))
if ADDIN_DIR not in sys.path:
    sys.path.insert(0, ADDIN_DIR)

# Import core modules with error handling
CORE_MODULES_LOADED = False
CORE_IMPORT_ERROR = ""
try:
    from core.context_detector import FusionContextDetector
    from core.consent_manager import ConsentManager, AIGuidanceMode
    from core.redirect_templates import RedirectTemplateLibrary
    from core.context_poller import ContextPollingManager
    from core.completion_detector import CompletionDetector, CompletionEvent, CompletionEventType
    CORE_MODULES_LOADED = True
    debug_log("Core modules loaded successfully")
except Exception as e:
    CORE_IMPORT_ERROR = str(e)
    debug_log(f"Core module import failed: {e}")

# Global handlers to prevent garbage collection
_handlers = []
_app = None
_ui = None
_palette = None
_tutorial_manager = None

# New global state for redirect system
_context_detector = None
_consent_manager = None
_context_poller = None
_is_redirecting = False
_pending_step_index = None

# Completion detection system
_completion_detector = None
_screenshot_dir = None

# Add-in metadata
ADDIN_NAME = "AI Tutorial Overlay"
PALETTE_ID = "TutorialOverlayPalette"
PALETTE_NAME = "Tutorial Guide"
COMMAND_ID = "showTutorialPanelCmd"

def get_resource_path(relative_path: str) -> str:
    """Get absolute path to a resource file."""
    this_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(this_dir, relative_path)
    # Normalize path separators for cross-platform compatibility
    return full_path.replace("\\", "/")


class TutorialManager:
    """Manages tutorial state and step navigation."""

    def __init__(self):
        self.current_tutorial = None
        self.current_step_index = 0
        self.total_steps = 0

    def load_tutorial(self, tutorial_data: dict):
        """Load a tutorial from JSON data."""
        self.current_tutorial = tutorial_data
        self.current_step_index = 0
        self.total_steps = len(tutorial_data.get("steps", []))
        return self.get_current_step()

    def load_from_file(self, file_path: str):
        """Load tutorial from a JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return self.load_tutorial(data)

    def get_current_step(self) -> dict:
        """Get the current step data."""
        if not self.current_tutorial:
            return None
        steps = self.current_tutorial.get("steps", [])
        if 0 <= self.current_step_index < len(steps):
            step = steps[self.current_step_index].copy()
            step["currentIndex"] = self.current_step_index
            step["totalSteps"] = self.total_steps
            step["tutorialTitle"] = self.current_tutorial.get("title", "Tutorial")
            return step
        return None

    def next_step(self) -> dict:
        """Move to the next step."""
        if self.current_step_index < self.total_steps - 1:
            self.current_step_index += 1
        return self.get_current_step()

    def prev_step(self) -> dict:
        """Move to the previous step."""
        if self.current_step_index > 0:
            self.current_step_index -= 1
        return self.get_current_step()

    def go_to_step(self, index: int) -> dict:
        """Go to a specific step by index."""
        if 0 <= index < self.total_steps:
            self.current_step_index = index
        return self.get_current_step()


class FusionActionsRunner:
    """Executes Fusion 360 viewport actions (camera, selection, etc.)."""

    def __init__(self):
        self.app = adsk.core.Application.get()

    def execute_actions(self, actions: list):
        """Execute a list of Fusion actions."""
        results = []
        for action in actions:
            action_type = action.get("type", "")
            result = {"action": action_type, "success": False}

            try:
                if action_type == "camera.fit":
                    result["success"] = self._camera_fit()
                elif action_type == "camera.orient":
                    result["success"] = self._camera_orient(action.get("orientation", "front"))
                elif action_type == "camera.focus":
                    result["success"] = self._camera_focus(action.get("target"))
                elif action_type == "prompt.selectEntity":
                    result["success"] = self._prompt_select(action.get("entityType", "face"))
                elif action_type == "highlight.body":
                    result["success"] = self._highlight_body(action.get("bodyName"))
                else:
                    result["message"] = f"Unknown action type: {action_type}"
            except Exception as e:
                result["message"] = str(e)

            results.append(result)
        return results

    def _camera_fit(self) -> bool:
        """Fit the camera to show all geometry."""
        try:
            viewport = self.app.activeViewport
            if viewport:
                viewport.fit()
                return True
        except:
            pass
        return False

    def _camera_orient(self, orientation: str) -> bool:
        """Orient camera to a standard view."""
        try:
            viewport = self.app.activeViewport
            if not viewport:
                return False

            camera = viewport.camera
            orientations = {
                "front": adsk.core.ViewOrientations.FrontViewOrientation,
                "back": adsk.core.ViewOrientations.BackViewOrientation,
                "top": adsk.core.ViewOrientations.TopViewOrientation,
                "bottom": adsk.core.ViewOrientations.BottomViewOrientation,
                "left": adsk.core.ViewOrientations.LeftViewOrientation,
                "right": adsk.core.ViewOrientations.RightViewOrientation,
                "iso": adsk.core.ViewOrientations.IsoTopRightViewOrientation
            }

            view_orient = orientations.get(orientation.lower())
            if view_orient:
                camera.viewOrientation = view_orient
                viewport.camera = camera
                viewport.fit()
                return True
        except:
            pass
        return False

    def _camera_focus(self, target: dict) -> bool:
        """Focus camera on a specific point or entity."""
        try:
            viewport = self.app.activeViewport
            if viewport:
                viewport.fit()
                return True
        except:
            pass
        return False

    def _prompt_select(self, entity_type: str) -> bool:
        """Show a selection prompt for a specific entity type."""
        global _ui
        try:
            if _ui:
                entity_names = {
                    "face": "face",
                    "edge": "edge",
                    "body": "body",
                    "sketch": "sketch",
                    "plane": "plane"
                }
                name = entity_names.get(entity_type, "entity")
                # Note: actual selection would use SelectionCommandInput in a proper command
                return True
        except:
            pass
        return False

    def _highlight_body(self, body_name: str) -> bool:
        """Highlight a specific body by name."""
        try:
            design = adsk.fusion.Design.cast(self.app.activeProduct)
            if design:
                root = design.rootComponent
                for body in root.bRepBodies:
                    if body.name == body_name:
                        # Fusion doesn't have direct highlight API, but we can select
                        return True
        except:
            pass
        return False


class PaletteHTMLEventHandler(adsk.core.HTMLEventHandler):
    """Handles events from the HTML palette JavaScript."""

    def __init__(self):
        super().__init__()
        self._setup_completion_callback()

    def _setup_completion_callback(self):
        """Setup completion detector callback to notify palette of events."""
        global _completion_detector, _palette

        if CORE_MODULES_LOADED and _completion_detector:
            _completion_detector.add_callback(self._on_completion_event)

    def _on_completion_event(self, event):
        """Called when a completion event is detected."""
        global _palette, _tutorial_manager

        # Log what the user actually did vs what the current step expects
        current_step = _tutorial_manager.get_current_step() if _tutorial_manager else None
        step_title = current_step.get('title', '?') if current_step else '(no step loaded)'
        step_index = current_step.get('currentIndex', '?') if current_step else '?'

        debug_log(f"")
        debug_log(f" === COMPLETION EVENT (Step {step_index}: {step_title}) ===")
        debug_log(f" USER'S CURRENT ACTIVITY: eventType='{event.event_type.value}', entityName='{event.entity_name}', info={event.additional_info}")

        if current_step:
            qc_checks = current_step.get('qcChecks', [])
            if qc_checks:
                expected_commands = []
                for qc in qc_checks:
                    cmd = qc.get('expectedCommand', '(none)')
                    text = qc.get('text', qc.get('message', ''))
                    expected_commands.append(f"'{cmd}' ({text})")
                debug_log(f" EXPECTED ACTIVITY: {', '.join(expected_commands)}")

                # Check if any expected command matches the user's actual activity
                user_command_id = (event.additional_info or {}).get('commandId', '')
                matched = False
                for qc in qc_checks:
                    exp_cmd = qc.get('expectedCommand', '')
                    if exp_cmd and exp_cmd == user_command_id:
                        matched = True
                        debug_log(f" MATCH FOUND: expectedCommand='{exp_cmd}' matches user commandId='{user_command_id}'")
                        break

                if not matched and user_command_id:
                    debug_log(f" NO MATCH: user commandId='{user_command_id}' does not match any expectedCommand")
                elif not user_command_id:
                    debug_log(f" NO COMMAND ID in event — text-based fallback matching will be attempted in JS")
            else:
                debug_log(f" EXPECTED ACTIVITY: (no qcChecks defined for this step)")
        debug_log(f" ==========================================")

        if _palette:
            try:
                event_data = {
                    "action": "completionEvent",
                    "event": event.to_dict()
                }
                _palette.sendInfoToHTML("response", json.dumps(event_data))
                debug_log(f" Completion event sent to palette: {event.event_type.value}")
            except Exception as e:
                debug_log(f" Error sending completion event to palette: {e}")
        else:
            debug_log(f" WARNING: _palette is None, cannot send completion event to JS")

    def notify(self, args: adsk.core.HTMLEventArgs):
        global _tutorial_manager, _palette, _consent_manager, _context_detector
        global _context_poller, _is_redirecting, _pending_step_index

        # Debug: log both action and data from HTMLEventArgs
        debug_log(f" HTMLEventHandler - action: '{args.action}', data: '{args.data[:100] if args.data else 'empty'}'")

        # Try to get the actual message - could be in args.data or args.action
        raw_message = args.data if args.data else args.action

        # Guard against empty or missing data
        if not raw_message or raw_message.strip() == '':
            debug_log(" Ignoring empty message")
            return

        try:
            data = json.loads(raw_message)
            action = data.get("action", "")

            # Ignore acknowledgment responses from JavaScript (no action to process)
            # This includes {"data":""}, {"status":"ok"}, or any message without "action"
            if not action or action == "":
                debug_log(f" Ignoring non-action message: {args.data[:50]}")
                return

            debug_log(f" Processing action: {action}")

            response = {"action": action, "success": False}

            if action == "ready":
                # Palette is ready, send initial tutorial data
                response = self._handle_ready()

            elif action == "loadTutorial":
                # Load a specific tutorial
                tutorial_id = data.get("tutorialId", "test")
                response = self._handle_load_tutorial(tutorial_id)

            elif action == "next":
                response = self._handle_navigation("next")

            elif action == "prev":
                response = self._handle_navigation("prev")

            elif action == "goToStep":
                index = data.get("index", 0)
                response = self._handle_navigation("goToStep", index)

            # Consent system actions
            elif action == "getConsent":
                response = self._handle_get_consent()

            elif action == "setConsent":
                mode = data.get("mode", "ASK")
                response = self._handle_set_consent(mode)

            # Redirect actions
            elif action == "showRedirectHelp":
                response = self._handle_show_redirect_help()

            elif action == "skipRedirectHelp":
                target_index = data.get("targetIndex")
                response = self._handle_skip_redirect_help(target_index)

            elif action == "skipRedirect":
                response = self._handle_skip_redirect()

            # Completion detection and screenshot actions
            elif action == "captureViewport":
                response = self._handle_capture_viewport(data.get("filename", "viewport.png"))

            elif action == "checkQCConditions":
                conditions = data.get("conditions", [])
                response = self._handle_check_qc(conditions)

            elif action == "getDesignState":
                response = self._handle_get_design_state()

            elif action == "resetTracking":
                response = self._handle_reset_tracking()

            # Send response back to palette
            if _palette:
                debug_log(f" Sending response to palette: {response.get('action', 'unknown')}")
                _palette.sendInfoToHTML("response", json.dumps(response))

        except Exception as e:
            debug_log(f" Exception in notify: {e}")
            if _palette:
                error_response = {"action": "error", "message": str(e)}
                _palette.sendInfoToHTML("response", json.dumps(error_response))

    def _handle_ready(self) -> dict:
        """Handle palette ready event - load tutorial immediately."""
        global _consent_manager, _palette

        debug_log(" _handle_ready called")

        # Load tutorial first for fast startup (change "mug" to "test" for box tutorial)
        response = self._handle_load_tutorial("mug")
        debug_log(f" Tutorial load response: {response.get('action', 'unknown')}")

        # Check if first run consent is needed (non-blocking, optional feature)
        try:
            if _consent_manager and _consent_manager.is_first_run():
                # Send consent required as a separate message after tutorial loads
                if _palette:
                    _palette.sendInfoToHTML("response", json.dumps({
                        "action": "consentRequired",
                        "firstRun": True
                    }))
        except Exception:
            pass  # Consent is optional, don't block tutorial

        return response

    def _handle_load_tutorial(self, tutorial_id: str) -> dict:
        """Load a tutorial by ID."""
        global _tutorial_manager

        try:
            # For testing, load from test_data folder
            test_file = get_resource_path(f"test_data/{tutorial_id}_tutorial.json")
            debug_log(f" Looking for tutorial at: {test_file}")

            if os.path.exists(test_file):
                debug_log(" Tutorial file found, loading...")
                step = _tutorial_manager.load_from_file(test_file)
                if step:
                    debug_log(" Tutorial loaded, executing fusion actions...")
                    self._execute_fusion_actions(step)
                    self._auto_capture_viewport(step)
                    debug_log(" Returning tutorialLoaded response")
                    return {
                        "action": "tutorialLoaded",
                        "step": step,
                        "success": True
                    }

            # If no file found, return error
            debug_log(f" Tutorial file not found at {test_file}")
            return {
                "action": "error",
                "message": f"Tutorial '{tutorial_id}' not found",
                "success": False
            }

        except Exception as e:
            debug_log(f" Error loading tutorial: {e}")
            return {
                "action": "error",
                "message": str(e),
                "success": False
            }

    def _execute_fusion_actions(self, step: dict):
        """Execute Fusion actions for a step."""
        actions = step.get("fusionActions", [])
        if actions:
            runner = FusionActionsRunner()
            runner.execute_actions(actions)

    def _auto_capture_viewport(self, step: dict):
        """Auto-capture viewport screenshot if the step requests it."""
        global _completion_detector, _screenshot_dir, _palette

        if not step.get("captureViewport"):
            return

        if not CORE_MODULES_LOADED or not _completion_detector or not _palette:
            return

        try:
            # Brief delay so Fusion renders camera changes first
            time.sleep(0.3)

            if not _screenshot_dir:
                _screenshot_dir = get_resource_path("screenshots")
                os.makedirs(_screenshot_dir, exist_ok=True)

            filename = f"viewport_auto_{int(time.time() * 1000)}.png"
            output_path = os.path.join(_screenshot_dir, filename)

            success = _completion_detector.capture_viewport_screenshot(output_path)
            if success:
                with open(output_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')

                capture_response = {
                    "action": "viewportCaptured",
                    "success": True,
                    "imageData": f"data:image/png;base64,{image_data}",
                    "path": f"screenshots/{filename}"
                }
                _palette.sendInfoToHTML("response", json.dumps(capture_response))
                debug_log(f" Auto-captured viewport for step: {step.get('stepId', 'unknown')}")
        except Exception as e:
            debug_log(f" Auto-capture viewport failed: {e}")

    def _handle_navigation(self, direction: str, index: int = None) -> dict:
        """Handle navigation with optional context checking."""
        global _tutorial_manager, _context_detector, _consent_manager
        global _is_redirecting, _pending_step_index, _context_poller, _palette

        debug_log(f" _handle_navigation called: direction={direction}, index={index}")
        debug_log(f" Current step index: {_tutorial_manager.current_step_index}")

        # Determine target step
        if direction == "next":
            target_index = _tutorial_manager.current_step_index + 1
        elif direction == "prev":
            target_index = _tutorial_manager.current_step_index - 1
        else:  # goToStep
            target_index = index

        debug_log(f" Target step index: {target_index}")

        # Get target step data
        steps = _tutorial_manager.current_tutorial.get("steps", [])
        if target_index < 0 or target_index >= len(steps):
            return {"action": "error", "message": "Invalid step index", "success": False}

        target_step = steps[target_index]
        requires = target_step.get("requires", {})

        # Stop any context polling left over from a previous mismatch warning
        if _context_poller and _context_poller.is_polling:
            _context_poller.stop_polling()

        # Check context requirements and warn if mismatched (non-blocking)
        try:
            if requires and _context_detector and CORE_MODULES_LOADED:
                debug_log(f" Step requires: {requires}")
                # Fresh API call to Fusion 360 for current context
                current_context = _context_detector.get_current_context()
                debug_log(f" Current context: workspace={current_context.workspace.value}, environment={current_context.environment.value}")

                matches = _context_detector.matches_requirements(requires)
                debug_log(f" Context matches requirements: {matches}")

                if not matches:
                    # Context doesn't match - send warning but don't block navigation
                    debug_log(" Context mismatch detected, sending non-blocking warning...")
                    mismatch_details = _context_detector.get_mismatch_details(requires)
                    if _palette:
                        warning_msg = {
                            "action": "contextWarning",
                            "mismatch": mismatch_details,
                            "targetIndex": target_index,
                            "success": True
                        }
                        _palette.sendInfoToHTML("response", json.dumps(warning_msg))

                    # Poll for context resolution so the warning auto-hides
                    # when the user switches to the correct environment
                    if _context_poller:
                        _context_poller.start_polling(
                            required=requires,
                            on_matched=self._on_warning_context_resolved,
                            interval_ms=1000
                        )
                else:
                    debug_log(" Context matches, proceeding with navigation")
        except Exception as e:
            debug_log(f" Context check error (proceeding anyway): {e}")

        # Always proceed with navigation regardless of context match
        if direction == "next":
            step = _tutorial_manager.next_step()
        elif direction == "prev":
            step = _tutorial_manager.prev_step()
        else:
            step = _tutorial_manager.go_to_step(target_index)

        if step:
            self._execute_fusion_actions(step)
            self._auto_capture_viewport(step)
            return {"action": "updateStep", "step": step, "success": True}

        return {"action": "error", "message": "Navigation failed", "success": False}

    def _handle_context_mismatch(self, requires: dict, target_index: int) -> dict:
        """Handle context mismatch based on consent mode."""
        global _context_detector, _consent_manager, _is_redirecting, _pending_step_index
        global _context_poller, _palette

        if not CORE_MODULES_LOADED or not _context_detector:
            # Fallback - just proceed with navigation
            return None

        mismatch_details = _context_detector.get_mismatch_details(requires)
        guidance_mode = _consent_manager.get_guidance_mode() if _consent_manager else AIGuidanceMode.ASK

        if guidance_mode == AIGuidanceMode.OFF:
            # Just show a warning but allow navigation
            return {
                "action": "contextWarning",
                "mismatch": mismatch_details,
                "success": True
            }

        elif guidance_mode == AIGuidanceMode.ASK:
            # Ask user if they want redirect help
            return {
                "action": "askRedirect",
                "mismatch": mismatch_details,
                "targetIndex": target_index,
                "success": True
            }

        else:  # AIGuidanceMode.ON
            # Automatically show redirect guidance
            return self._start_redirect(mismatch_details, target_index)

    def _start_redirect(self, mismatch_details: dict, target_index: int) -> dict:
        """Start redirect guidance and polling."""
        global _is_redirecting, _pending_step_index, _context_poller, _palette, _context_detector

        if not CORE_MODULES_LOADED:
            return None

        _is_redirecting = True
        _pending_step_index = target_index

        # Generate redirect step
        redirect_step = RedirectTemplateLibrary.generate_redirect_step(
            mismatch_details,
            target_index
        )

        if not redirect_step:
            return {"action": "error", "message": "Could not generate redirect step", "success": False}

        # Start context polling
        required = mismatch_details.get("required", {})
        if _context_poller:
            _context_poller.start_polling(
                required=required,
                on_matched=self._on_context_resolved,
                interval_ms=500
            )

        return {
            "action": "redirectStep",
            "step": redirect_step.to_dict(),
            "success": True
        }

    def _on_context_resolved(self, resolved_context: dict):
        """Callback when context polling detects a match."""
        global _is_redirecting, _pending_step_index, _palette, _tutorial_manager

        _is_redirecting = False

        # Send context resolved message to palette
        if _palette:
            _palette.sendInfoToHTML("response", json.dumps({
                "action": "redirectComplete",
                "resolvedContext": resolved_context,
                "pendingStepIndex": _pending_step_index
            }))

        # Auto-advance to pending step after a brief delay
        # (The palette will handle this based on the message)

    def _on_warning_context_resolved(self, resolved_context: dict):
        """Callback when context matches after a mismatch warning — dismiss the warning in JS."""
        global _palette

        debug_log(f" Context resolved — dismissing warning in palette")
        if _palette:
            try:
                _palette.sendInfoToHTML("response", json.dumps({
                    "action": "contextResolved"
                }))
            except Exception as e:
                debug_log(f" Error sending contextResolved: {e}")

    def _handle_get_consent(self) -> dict:
        """Get current consent/guidance mode."""
        global _consent_manager

        if not CORE_MODULES_LOADED or not _consent_manager:
            return {"action": "consent", "mode": "ASK", "firstRun": False, "success": True}

        return {
            "action": "consent",
            "mode": _consent_manager.get_guidance_mode().value,
            "firstRun": _consent_manager.is_first_run(),
            "success": True
        }

    def _handle_set_consent(self, mode: str) -> dict:
        """Set consent/guidance mode."""
        global _consent_manager

        if not CORE_MODULES_LOADED or not _consent_manager:
            # Consent system not available, just acknowledge and continue
            return {"action": "consentSet", "mode": mode, "success": True}

        try:
            guidance_mode = AIGuidanceMode(mode)
            _consent_manager.set_guidance_mode(guidance_mode)
            _consent_manager.mark_first_run_complete()
            return {"action": "consentSet", "mode": mode, "success": True}

        except ValueError:
            return {"action": "error", "message": f"Invalid mode: {mode}", "success": False}

    def _handle_show_redirect_help(self) -> dict:
        """User chose to see redirect help from ASK dialog."""
        global _is_redirecting, _pending_step_index, _context_detector

        # This is called when user clicks "Show me how" in ASK mode
        # We should already have mismatch details from the askRedirect response
        # For now, return success - the actual redirect is handled by askRedirect response
        return {"action": "showingRedirectHelp", "success": True}

    def _handle_skip_redirect_help(self, target_index: int = None) -> dict:
        """User chose to skip redirect help - recheck context and navigate if it matches."""
        global _is_redirecting, _pending_step_index, _tutorial_manager, _context_detector

        debug_log(f" _handle_skip_redirect_help called with target_index={target_index}")

        _is_redirecting = False
        _pending_step_index = None

        # If we have a target index, recheck context and navigate if it now matches
        if target_index is not None and _tutorial_manager:
            steps = _tutorial_manager.current_tutorial.get("steps", [])
            if 0 <= target_index < len(steps):
                target_step = steps[target_index]
                requires = target_step.get("requires", {})

                # Recheck context
                if requires and _context_detector and CORE_MODULES_LOADED:
                    debug_log(f" Rechecking context for step {target_index}")
                    current_context = _context_detector.get_current_context()
                    debug_log(f" Current context: workspace={current_context.workspace.value}, environment={current_context.environment.value}")

                    if _context_detector.matches_requirements(requires):
                        # Context now matches! Navigate to the step
                        debug_log(" Context now matches! Navigating to step.")
                        step = _tutorial_manager.go_to_step(target_index)
                        if step:
                            self._execute_fusion_actions(step)
                            return {
                                "action": "updateStep",
                                "step": step,
                                "success": True
                            }
                    else:
                        # Context still doesn't match - show warning
                        debug_log(" Context still doesn't match - user needs to switch manually")
                        mismatch = _context_detector.get_mismatch_details(requires)
                        return {
                            "action": "contextWarning",
                            "mismatch": mismatch,
                            "message": "Please switch to the correct environment and click Next again.",
                            "success": True
                        }
                else:
                    # No context requirements - just navigate
                    step = _tutorial_manager.go_to_step(target_index)
                    if step:
                        self._execute_fusion_actions(step)
                        return {
                            "action": "updateStep",
                            "step": step,
                            "success": True
                        }

        return {"action": "redirectSkipped", "success": True}

    def _handle_skip_redirect(self) -> dict:
        """Handle skip button during active redirect."""
        global _is_redirecting, _pending_step_index, _context_poller, _tutorial_manager

        # Stop polling
        if CORE_MODULES_LOADED and _context_poller:
            _context_poller.stop_polling()

        _is_redirecting = False

        # Still navigate to the pending step despite context mismatch
        if _pending_step_index is not None:
            step = _tutorial_manager.go_to_step(_pending_step_index)
            _pending_step_index = None

            if step:
                self._execute_fusion_actions(step)
                return {
                    "action": "updateStep",
                    "step": step,
                    "skippedRedirect": True,
                    "success": True
                }

        return {"action": "redirectSkipped", "success": True}

    def _handle_capture_viewport(self, filename: str) -> dict:
        """Capture the current viewport as an image and return as base64 data URL."""
        global _completion_detector, _screenshot_dir

        if not CORE_MODULES_LOADED or not _completion_detector:
            return {"action": "viewportCaptured", "success": False, "message": "Completion detector not available"}

        try:
            # Ensure screenshot directory exists
            if not _screenshot_dir:
                _screenshot_dir = get_resource_path("screenshots")
                os.makedirs(_screenshot_dir, exist_ok=True)

            # Generate full path
            output_path = os.path.join(_screenshot_dir, filename)

            # Capture the viewport
            success = _completion_detector.capture_viewport_screenshot(output_path)

            if success:
                # Read and encode as base64 for reliable display in Qt WebEngine
                with open(output_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')

                return {
                    "action": "viewportCaptured",
                    "success": True,
                    "imageData": f"data:image/png;base64,{image_data}",
                    "path": f"screenshots/{filename}",
                    "fullPath": output_path
                }
            else:
                return {"action": "viewportCaptured", "success": False, "message": "Failed to capture viewport"}

        except Exception as e:
            return {"action": "viewportCaptured", "success": False, "message": str(e)}

    def _handle_check_qc(self, conditions: list) -> dict:
        """Check QC conditions against current design state."""
        global _completion_detector

        if not CORE_MODULES_LOADED or not _completion_detector:
            return {"action": "qcResults", "success": False, "results": []}

        try:
            results = _completion_detector.check_qc_conditions(conditions)
            return {
                "action": "qcResults",
                "success": True,
                "results": results
            }
        except Exception as e:
            return {"action": "qcResults", "success": False, "message": str(e), "results": []}

    def _handle_get_design_state(self) -> dict:
        """Get the current state of the design."""
        global _completion_detector

        if not CORE_MODULES_LOADED or not _completion_detector:
            return {"action": "designState", "success": False, "state": {}}

        try:
            state = _completion_detector.get_current_state()
            return {
                "action": "designState",
                "success": True,
                "state": state
            }
        except Exception as e:
            return {"action": "designState", "success": False, "message": str(e), "state": {}}

    def _handle_reset_tracking(self) -> dict:
        """Reset the completion tracking (for new step)."""
        global _completion_detector

        if CORE_MODULES_LOADED and _completion_detector:
            _completion_detector.reset_tracking()

        return {"action": "trackingReset", "success": True}


class PaletteCloseEventHandler(adsk.core.UserInterfaceGeneralEventHandler):
    """Handles palette close event."""

    def __init__(self):
        super().__init__()

    def notify(self, args):
        global _palette
        _palette = None


class CommandExecutedHandler(adsk.core.CommandEventHandler):
    """Handles command execution to show the palette."""

    def __init__(self):
        super().__init__()

    def notify(self, args: adsk.core.CommandEventArgs):
        global _palette, _ui, _handlers

        debug_log("CommandExecutedHandler.notify() called")

        try:
            # Check if palette already exists
            _palette = _ui.palettes.itemById(PALETTE_ID)
            debug_log(f"Existing palette: {_palette is not None}")

            if not _palette:
                # Create new palette - IMPORTANT: Create with isVisible=False to avoid
                # race condition where JavaScript sends "ready" before handler is attached
                palette_html = get_resource_path("palette/tutorial_palette.html")
                debug_log(f"Palette HTML path: {palette_html}")
                debug_log(f"HTML file exists: {os.path.exists(palette_html)}")

                _palette = _ui.palettes.add(
                    PALETTE_ID,
                    PALETTE_NAME,
                    palette_html,
                    False,  # isVisible - start hidden to avoid race condition
                    True,   # showCloseButton
                    True,   # isResizable
                    400,    # width
                    600,    # height
                    True    # useNewWebBrowser (Qt WebEngine)
                )
                debug_log("Palette created")

                # Add HTML event handler BEFORE making palette visible
                html_handler = PaletteHTMLEventHandler()
                _palette.incomingFromHTML.add(html_handler)
                _handlers.append(html_handler)
                debug_log("HTML event handler attached")

                # Add close handler
                close_handler = PaletteCloseEventHandler()
                _palette.closed.add(close_handler)
                _handlers.append(close_handler)

                # Set docking
                _palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight

                # NOW make the palette visible - handler is ready to receive messages
                _palette.isVisible = True
                debug_log("Palette made visible")

            else:
                _palette.isVisible = True
                debug_log("Existing palette made visible")

        except Exception as e:
            debug_log(f"ERROR in CommandExecutedHandler: {traceback.format_exc()}")
            if _ui:
                _ui.messageBox(f"Failed to show palette: {str(e)}")


class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    """Handles command creation."""

    def __init__(self):
        super().__init__()

    def notify(self, args: adsk.core.CommandCreatedEventArgs):
        global _handlers

        debug_log("CommandCreatedHandler.notify() called")

        try:
            cmd = args.command

            # Add execute handler
            exec_handler = CommandExecutedHandler()
            cmd.execute.add(exec_handler)
            _handlers.append(exec_handler)
            debug_log("Execute handler added to command")

        except Exception as e:
            debug_log(f"ERROR in CommandCreatedHandler: {str(e)}")
            if _ui:
                _ui.messageBox(f"Command creation failed: {str(e)}")


def run(context):
    """Add-in entry point - called when add-in is started."""
    global _app, _ui, _tutorial_manager, _handlers
    global _context_detector, _consent_manager, _context_poller
    global _completion_detector, _screenshot_dir

    debug_log("=== run() called - add-in starting ===")

    try:
        _app = adsk.core.Application.get()
        _ui = _app.userInterface
        _tutorial_manager = TutorialManager()
        debug_log(" Basic initialization complete")

        # Initialize new modules (optional - basic tutorial works without them)
        if CORE_MODULES_LOADED:
            try:
                _context_detector = FusionContextDetector()

                # User data directory for preferences
                user_data_dir = get_resource_path("user_data")
                _consent_manager = ConsentManager(user_data_dir)

                # Context poller for redirect enforcement
                _context_poller = ContextPollingManager(_context_detector)

                # Completion detector for checklist toggling
                _completion_detector = CompletionDetector()
                _completion_detector.start()
                debug_log(" Completion detector initialized and started")

                # Screenshot directory
                _screenshot_dir = get_resource_path("screenshots")
                os.makedirs(_screenshot_dir, exist_ok=True)
            except Exception as e:
                # Log but continue - basic tutorial functionality will still work
                debug_log(f"Warning: Could not initialize redirect modules: {e}")

        # Create command definition
        cmd_defs = _ui.commandDefinitions
        cmd_def = cmd_defs.itemById(COMMAND_ID)

        if not cmd_def:
            cmd_def = cmd_defs.addButtonDefinition(
                COMMAND_ID,
                ADDIN_NAME,
                "Open AI Tutorial Overlay",
                ""  # No resource folder for icon
            )

        # Add command created handler
        created_handler = CommandCreatedHandler()
        cmd_def.commandCreated.add(created_handler)
        _handlers.append(created_handler)

        # Add to toolbar
        toolbar_panel = _ui.allToolbarPanels.itemById("SolidScriptsAddinsPanel")
        if toolbar_panel:
            existing_control = toolbar_panel.controls.itemById(COMMAND_ID)
            if not existing_control:
                toolbar_panel.controls.addCommand(cmd_def)

        # Also add to TOOLS tab for easier access
        tools_panel = _ui.allToolbarPanels.itemById("ToolsUtilitiesPanel")
        if tools_panel:
            existing_control = tools_panel.controls.itemById(COMMAND_ID)
            if not existing_control:
                tools_panel.controls.addCommand(cmd_def)

        debug_log("Add-in started successfully! Command should be in toolbar.")

    except Exception as e:
        debug_log(f"ERROR in run(): {traceback.format_exc()}")
        if _ui:
            _ui.messageBox(f"Add-in startup failed:\n{traceback.format_exc()}")


def stop(context):
    """Add-in cleanup - called when add-in is stopped."""
    global _app, _ui, _palette, _handlers
    global _context_detector, _consent_manager, _context_poller, _is_redirecting
    global _completion_detector, _screenshot_dir

    try:
        # Stop completion detector if active
        if CORE_MODULES_LOADED and _completion_detector:
            try:
                _completion_detector.stop()
            except Exception:
                pass
            _completion_detector = None

        # Stop context polling if active
        if CORE_MODULES_LOADED and _context_poller:
            try:
                _context_poller.stop_polling()
            except Exception:
                pass
            _context_poller = None

        _context_detector = None
        _consent_manager = None
        _is_redirecting = False
        _screenshot_dir = None

        # Remove palette
        if _palette:
            _palette.deleteMe()
            _palette = None

        # Remove command from panels
        toolbar_panel = _ui.allToolbarPanels.itemById("SolidScriptsAddinsPanel")
        if toolbar_panel:
            cmd_control = toolbar_panel.controls.itemById(COMMAND_ID)
            if cmd_control:
                cmd_control.deleteMe()

        tools_panel = _ui.allToolbarPanels.itemById("ToolsUtilitiesPanel")
        if tools_panel:
            cmd_control = tools_panel.controls.itemById(COMMAND_ID)
            if cmd_control:
                cmd_control.deleteMe()

        # Remove command definition
        cmd_def = _ui.commandDefinitions.itemById(COMMAND_ID)
        if cmd_def:
            cmd_def.deleteMe()

        # Clear handlers
        _handlers.clear()

    except Exception as e:
        if _ui:
            _ui.messageBox(f"Add-in stop failed:\n{str(e)}")
