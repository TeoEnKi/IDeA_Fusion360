"""
FusionTutorialOverlay - AI-driven tutorial overlay for Fusion 360
Main add-in entry point
"""

# Minimal imports first - these should never fail
import os
import sys
import traceback
import time
import hashlib
import importlib

BUILD_STAMP = "2026-03-01-cloud-latest-loader-v1"
EXPECTED_INSTALL_FRAGMENT = "AppData/Roaming/Autodesk/Autodesk Fusion 360/API/AddIns/FusionTutorialOverlay.bundle/Contents/FusionTutorialOverlay.py"

# Debug logging disabled for production plugin behavior.
def debug_log(message: str):
    """No-op: debug logging is intentionally disabled."""
    return

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
debug_log(f"Build: {BUILD_STAMP}")

# Add the Contents directory to path for imports
ADDIN_DIR = os.path.dirname(os.path.abspath(__file__))
if ADDIN_DIR not in sys.path:
    sys.path.insert(0, ADDIN_DIR)

# Import core modules with error handling
CORE_MODULES_LOADED = False
CORE_IMPORT_ERROR = ""
WEBHOOK_MODULE_LOADED = False
WEBHOOK_IMPORT_ERROR = ""
WEBHOOK_MODULE_FILE = ""
WEBHOOK_SYMBOLS = {
    "start_scan": False,
    "get_scan_status": False
}
start_scan = None
get_scan_status = None
try:
    from core.context_detector import FusionContextDetector
    from core.consent_manager import ConsentManager, AIGuidanceMode
    from core.redirect_templates import RedirectTemplateLibrary
    from core.context_poller import ContextPollingManager
    from core.completion_detector import CompletionDetector, CompletionEvent, CompletionEventType
    CORE_MODULES_LOADED = True
    debug_log("Core modules loaded successfully (non-webhook)")
except Exception as e:
    CORE_IMPORT_ERROR = traceback.format_exc()
    debug_log(f"Core module import failed: {e}")

try:
    import core.tutorial_plugin_service as tutorial_plugin_service
    module_id_before = id(tutorial_plugin_service)
    start_before = callable(getattr(tutorial_plugin_service, "start_scan", None))
    status_before = callable(getattr(tutorial_plugin_service, "get_scan_status", None))
    debug_log(
        "Webhook import pre-reload: "
        f"module_id={module_id_before}, "
        f"start_scan={start_before}, get_scan_status={status_before}"
    )

    tutorial_plugin_service = importlib.reload(tutorial_plugin_service)
    module_id_after = id(tutorial_plugin_service)
    debug_log(
        "Webhook import post-reload: "
        f"module_id={module_id_after}, reload_executed=True"
    )

    WEBHOOK_MODULE_LOADED = True
    WEBHOOK_MODULE_FILE = str(getattr(tutorial_plugin_service, "__file__", "") or "")
    start_scan = getattr(tutorial_plugin_service, "start_scan", None)
    get_scan_status = getattr(tutorial_plugin_service, "get_scan_status", None)
    WEBHOOK_SYMBOLS["start_scan"] = callable(start_scan)
    WEBHOOK_SYMBOLS["get_scan_status"] = callable(get_scan_status)

    # Fallback: bust importer cache and force a fresh import when symbols are still missing.
    if not WEBHOOK_SYMBOLS["start_scan"] or not WEBHOOK_SYMBOLS["get_scan_status"]:
        debug_log("Webhook symbols missing after reload; running cache-busting re-import fallback")
        sys.modules.pop("core.tutorial_plugin_service", None)
        importlib.invalidate_caches()
        tutorial_plugin_service = importlib.import_module("core.tutorial_plugin_service")
        WEBHOOK_MODULE_FILE = str(getattr(tutorial_plugin_service, "__file__", "") or WEBHOOK_MODULE_FILE)
        start_scan = getattr(tutorial_plugin_service, "start_scan", None)
        get_scan_status = getattr(tutorial_plugin_service, "get_scan_status", None)
        WEBHOOK_SYMBOLS["start_scan"] = callable(start_scan)
        WEBHOOK_SYMBOLS["get_scan_status"] = callable(get_scan_status)
        debug_log(
            "Webhook import fallback result: "
            f"module_id={id(tutorial_plugin_service)}, "
            f"start_scan={WEBHOOK_SYMBOLS['start_scan']}, "
            f"get_scan_status={WEBHOOK_SYMBOLS['get_scan_status']}"
        )

    debug_log(f"Webhook module loaded: {WEBHOOK_MODULE_FILE or '<unknown-file>'}")
    debug_log(
        "Webhook symbols: "
        f"start_scan={WEBHOOK_SYMBOLS['start_scan']}, "
        f"get_scan_status={WEBHOOK_SYMBOLS['get_scan_status']}"
    )
    if not WEBHOOK_SYMBOLS["start_scan"] or not WEBHOOK_SYMBOLS["get_scan_status"]:
        sample_keys = sorted(list(getattr(tutorial_plugin_service, "__dict__", {}).keys()))[:30]
        debug_log(f"Webhook module dict sample keys: {sample_keys}")
except Exception as e:
    WEBHOOK_IMPORT_ERROR = traceback.format_exc()
    debug_log(f"Webhook module import failed: {e}")

if not CORE_MODULES_LOADED and WEBHOOK_MODULE_LOADED:
    debug_log("Degraded mode: webhook bootstrap enabled; redirect/completion modules unavailable.")

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
_workspace_feedback_template = None
_environment_feedback_templates = {}
_runtime_identity_ok = True

# Add-in metadata
ADDIN_NAME = "AI Tutorial Overlay"
PALETTE_ID = "TutorialOverlayPalette"
PALETTE_NAME = "Tutorial Guide"
COMMAND_ID = "showTutorialPanelCmd"
STRICT_QC_COMMAND_VALIDATION = False
_allowed_qc_command_ids_cache = None
TEST_TUTORIAL_RELATIVE_PATH = "test_data/cube_hole_tutorial.json"

def get_resource_path(relative_path: str) -> str:
    """Get absolute path to a resource file."""
    this_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(this_dir, relative_path)
    # Normalize path separators for cross-platform compatibility
    return full_path.replace("\\", "/")


def _collect_command_ids_from_json(node, output_set: set):
    """Recursively collect commandId values from a nested JSON object."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "commandId" and isinstance(value, str) and value.strip():
                output_set.add(value.strip())
            else:
                _collect_command_ids_from_json(value, output_set)
    elif isinstance(node, list):
        for item in node:
            _collect_command_ids_from_json(item, output_set)


def get_allowed_qc_command_ids() -> set:
    """Return allowed command IDs from Sketch/Solid UI components metadata."""
    global _allowed_qc_command_ids_cache

    if _allowed_qc_command_ids_cache is not None:
        return _allowed_qc_command_ids_cache

    allowed = set()
    metadata_paths = [
        get_resource_path("assets/UI Images/Sketch/Sketch_UIComponents.json"),
        get_resource_path("assets/UI Images/Solid/Solid_UIComponents.json"),
    ]

    for path in metadata_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            _collect_command_ids_from_json(payload, allowed)
        except Exception as e:
            debug_log(f" Failed to load commandId metadata from {path}: {e}")

    _allowed_qc_command_ids_cache = allowed
    return allowed


def validate_tutorial_qc_checks(tutorial_data: dict, strict_command_id_check: bool = False) -> list:
    """Validate qcChecks.expectedCommand fields. Returns a list of error strings."""
    errors = []
    steps = tutorial_data.get("steps", [])
    allowed_ids = get_allowed_qc_command_ids() if strict_command_id_check else set()

    for step_idx, step in enumerate(steps, start=1):
        qc_checks = step.get("qcChecks", [])
        if not isinstance(qc_checks, list):
            errors.append(f"Step {step_idx}: qcChecks must be an array")
            continue

        for qc_idx, qc in enumerate(qc_checks, start=1):
            if not isinstance(qc, dict):
                errors.append(f"Step {step_idx} QC {qc_idx}: check must be an object")
                continue

            expected_command = str(qc.get("expectedCommand", "")).strip()
            if not expected_command:
                errors.append(f"Step {step_idx} QC {qc_idx}: missing expectedCommand")
                continue

            if strict_command_id_check and expected_command not in allowed_ids:
                errors.append(
                    f"Step {step_idx} QC {qc_idx}: expectedCommand '{expected_command}' is not in Sketch/Solid UIComponents commandId set"
                )

    return errors


def _estimate_step_exit_context(step: dict, current_workspace: str, current_environment: str) -> tuple:
    """Estimate workspace/environment after this step's fusionActions run."""
    workspace = str(current_workspace or "").strip() or "Design"
    environment = str(current_environment or "").strip() or "Solid"

    actions = step.get("fusionActions", []) or []
    for action in actions:
        if not isinstance(action, dict):
            continue

        action_type = str(action.get("type", "")).strip()
        if action_type == "ui.openWorkspace":
            next_workspace = str(action.get("workspace", "")).strip()
            next_environment = str(action.get("environment", "")).strip()
            if next_workspace:
                workspace = next_workspace
            if next_environment:
                environment = next_environment
            continue

        if action_type == "ui.enterMode":
            mode = str(action.get("mode", "")).strip().lower()
            if mode == "sketch":
                environment = "Sketch"
            continue

        if action_type == "ui.exitMode":
            mode = str(action.get("mode", "")).strip().lower()
            if mode == "sketch":
                environment = "Solid"

    return workspace, environment


def validate_tutorial_step_entry_contexts(tutorial_data: dict) -> list:
    """Validate that requires.* represents context at the beginning of each step."""
    warnings = []
    steps = tutorial_data.get("steps", []) or []
    if not steps:
        return warnings

    first_requires = steps[0].get("requires", {}) or {}
    expected_workspace = str(first_requires.get("workspace", "")).strip() or "Design"
    expected_environment = str(first_requires.get("environment", "")).strip() or "Solid"

    for step_idx, step in enumerate(steps, start=1):
        step_id = step.get("stepId", f"step-{step_idx}")
        requires = step.get("requires", {}) or {}
        declared_workspace = str(requires.get("workspace", "")).strip()
        declared_environment = str(requires.get("environment", "")).strip()

        if declared_workspace and declared_workspace.lower() != expected_workspace.lower():
            warnings.append(
                f"Step {step_idx} ({step_id}): requires.workspace='{declared_workspace}' "
                f"but inferred step-entry workspace is '{expected_workspace}'"
            )

        if declared_environment and declared_environment.lower() != expected_environment.lower():
            warnings.append(
                f"Step {step_idx} ({step_id}): requires.environment='{declared_environment}' "
                f"but inferred step-entry environment is '{expected_environment}'"
            )

        expected_workspace, expected_environment = _estimate_step_exit_context(
            step,
            expected_workspace,
            expected_environment
        )

    return warnings


def get_runtime_signature() -> dict:
    """Return runtime identity details for deployment verification."""
    script_path = os.path.abspath(__file__).replace("\\", "/")
    header_hash = "unknown"
    try:
        with open(__file__, "rb") as f:
            header = f.read(1024)
        header_hash = hashlib.sha1(header).hexdigest()[:12]
    except Exception:
        pass

    path_matches_expected = EXPECTED_INSTALL_FRAGMENT.replace("\\", "/") in script_path
    return {
        "buildStamp": BUILD_STAMP,
        "scriptPath": script_path,
        "headerHash": header_hash,
        "pathMatchesExpected": path_matches_expected,
        "coreModulesLoaded": CORE_MODULES_LOADED,
        "webhookModuleLoaded": WEBHOOK_MODULE_LOADED,
        "webhookImportError": (WEBHOOK_IMPORT_ERROR or "").strip(),
        "webhookModuleFile": WEBHOOK_MODULE_FILE,
        "webhookSymbols": WEBHOOK_SYMBOLS.copy()
    }


def _build_webhook_unavailable_message() -> str:
    """Build explicit diagnostics when webhook bootstrap capability is unavailable."""
    missing = []
    if not WEBHOOK_SYMBOLS.get("start_scan", False):
        missing.append("start_scan")
    if not WEBHOOK_SYMBOLS.get("get_scan_status", False):
        missing.append("get_scan_status")

    parts = ["Webhook bootstrap unavailable."]
    if WEBHOOK_MODULE_FILE:
        parts.append(f"module={WEBHOOK_MODULE_FILE}")
    if missing:
        parts.append(f"missing_symbols={','.join(missing)}")
    if WEBHOOK_IMPORT_ERROR:
        parts.append(f"import_error={WEBHOOK_IMPORT_ERROR.strip()}")
    elif CORE_IMPORT_ERROR and not CORE_MODULES_LOADED:
        parts.append(f"non_webhook_core_error={CORE_IMPORT_ERROR.strip()}")

    parts.append("Fix: redeploy add-in and restart Fusion.")
    return " ".join(parts)


def validate_runtime_identity() -> tuple:
    """Check whether the running script path looks like the installed AddIns bundle path."""
    sig = get_runtime_signature()
    if sig["pathMatchesExpected"]:
        return True, sig
    msg = (
        "Runtime deployment mismatch detected.\n\n"
        f"Running from:\n{sig['scriptPath']}\n\n"
        f"Expected path fragment:\n{EXPECTED_INSTALL_FRAGMENT}\n\n"
        "Fix:\n"
        "1) Stop the add-in in Fusion\n"
        "2) Copy this repo bundle to %APPDATA%/Autodesk/Autodesk Fusion 360/API/AddIns/FusionTutorialOverlay.bundle\n"
        "3) Delete __pycache__ in installed bundle\n"
        "4) Restart add-in / Fusion"
    )
    return False, {"message": msg, **sig}


def get_workspace_feedback_template() -> dict:
    """Load and cache modal reference image + workspace selector annotation."""
    global _workspace_feedback_template

    if _workspace_feedback_template is not None:
        return _workspace_feedback_template

    fallback = {
        "referenceImageSrc": "../assets/UI Images/Solid/Solid_0.png",
        "annotation": {
            "label": "Workspace selector",
            "shape": "circle",
            "position": {"x": 4.2, "y": 12.0, "width": 6.8, "height": 8.5}
        }
    }

    try:
        metadata_path = get_resource_path("assets/UI Images/Solid/Solid_UIComponents.json")
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        workspace_dropdown = metadata.get("components", {}).get("workspaceDropdown", {})
        position = workspace_dropdown.get("position", {})

        _workspace_feedback_template = {
            "referenceImageSrc": "../assets/UI Images/Solid/Solid_0.png",
            "annotation": {
                "label": workspace_dropdown.get("label", "Workspace selector"),
                "shape": "circle",
                "position": {
                    "x": position.get("x", 4.2),
                    "y": position.get("y", 12.0),
                    "width": position.get("width", 6.8),
                    "height": position.get("height", 8.5)
                }
            }
        }
    except Exception as e:
        debug_log(f" Failed to load workspace feedback template, using fallback: {e}")
        _workspace_feedback_template = fallback

    return _workspace_feedback_template


def get_environment_feedback_template(required_environment: str) -> dict:
    """Load/cached modal reference image + annotation for a Design environment tab."""
    global _environment_feedback_templates

    env_name = str(required_environment or "").strip()
    env_key = env_name.lower()
    if env_key in _environment_feedback_templates:
        return _environment_feedback_templates[env_key]

    # Prefer matching screenshot/metadata when available; otherwise fall back to Solid navbar image.
    source_configs = [
        (
            get_resource_path("assets/UI Images/Sketch/Sketch_UIComponents.json"),
            "../assets/UI Images/Sketch/Sketch_0.png",
            {
                "solid": "solid",
                "surface": "surface",
                "mesh": "mesh",
                "sketch": "sketch"
            }
        ),
        (
            get_resource_path("assets/UI Images/Solid/Solid_UIComponents.json"),
            "../assets/UI Images/Solid/Solid_0.png",
            {
                "solid": "solid",
                "surface": "surface",
                "mesh": "mesh",
                "sheet metal": "sheetMetal",
                "sheet_metal": "sheetMetal",
                "sheetmetal": "sheetMetal"
            }
        )
    ]

    for metadata_path, image_src, tab_key_map in source_configs:
        try:
            tab_key = tab_key_map.get(env_key)
            if not tab_key:
                continue

            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            env_tab = (
                metadata.get("components", {})
                .get("environmentTabs", {})
                .get(tab_key, {})
            )
            position = env_tab.get("position")
            if not isinstance(position, dict):
                continue

            template = {
                "referenceImageSrc": image_src,
                "annotation": {
                    "label": env_tab.get("label", env_name),
                    "shape": "circle",
                    "position": {
                        "x": position.get("x", 0),
                        "y": position.get("y", 0),
                        "width": position.get("width", 5.0),
                        "height": position.get("height", 5.0)
                    }
                }
            }
            _environment_feedback_templates[env_key] = template
            return template
        except Exception as e:
            debug_log(f" Failed to load environment feedback template ({env_name}) from {metadata_path}: {e}")

    # Fallback: reuse workspace selector image/annotation if no environment tab metadata exists.
    fallback = get_workspace_feedback_template()
    _environment_feedback_templates[env_key] = fallback
    return fallback


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
    """Executes Fusion 360 viewport actions (selection, highlighting, etc.)."""

    def __init__(self):
        self.app = adsk.core.Application.get()

    def execute_actions(self, actions: list):
        """Execute a list of Fusion actions."""
        results = []
        for action in actions:
            action_type = action.get("type", "")
            result = {"action": action_type, "success": False}

            try:
                if action_type == "prompt.selectEntity":
                    result["success"] = self._prompt_select(action.get("entityType", "face"))
                elif action_type == "highlight.body":
                    result["success"] = self._highlight_body(action.get("bodyName"))
                else:
                    result["message"] = f"Unknown action type: {action_type}"
            except Exception as e:
                result["message"] = str(e)

            results.append(result)
        return results

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

        current_step = _tutorial_manager.get_current_step() if _tutorial_manager else None
        qc_checks = current_step.get('qcChecks', []) if current_step else []
        user_command_id = str((event.additional_info or {}).get('commandId', '')).strip()
        is_command_event = event.event_type.value in ('command_started', 'command_terminated')

        # Keep command boundary events flowing to JS so it can infer completion
        # from command transitions, even when no direct expectedCommand match exists.
        if is_command_event:
            if user_command_id == 'SelectCommand':
                return
            if not user_command_id:
                return
            debug_log(
                f" Boundary detection support: forwarding {event.event_type.value} "
                f"for commandId='{user_command_id}'"
            )

        # Log what the user actually did vs what the current step expects
        step_title = current_step.get('title', '?') if current_step else '(no step loaded)'
        step_index = current_step.get('currentIndex', '?') if current_step else '?'

        debug_log(f"")
        debug_log(f" === COMPLETION EVENT (Step {step_index}: {step_title}) ===")
        debug_log(f" USER'S CURRENT ACTIVITY: eventType='{event.event_type.value}', entityName='{event.entity_name}', info={event.additional_info}")

        if current_step:
            if qc_checks:
                expected_commands = []
                for qc in qc_checks:
                    cmd = qc.get('expectedCommand', '(none)')
                    text = qc.get('text', qc.get('message', ''))
                    expected_commands.append(f"'{cmd}' ({text})")
                debug_log(f" EXPECTED ACTIVITY: {', '.join(expected_commands)}")

                # Check if any expected command matches the user's actual activity
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
                # Palette is ready, return bootstrap entry state
                response = self._handle_ready()

            elif action == "loadTutorial":
                response = self._handle_load_tutorial(data.get("tutorialId", ""))

            elif action == "startTutorialFetch":
                response = self._handle_start_tutorial_fetch()

            elif action == "checkScanStatus":
                response = self._handle_check_scan_status()

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

            # Completion detection actions
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
        """Handle palette ready event by returning bootstrap entry state."""
        global _palette

        debug_log(" _handle_ready called")

        # Send runtime identity so stale bundle issues are obvious in JS logs.
        try:
            if _palette:
                _palette.sendInfoToHTML("response", json.dumps({
                    "action": "runtimeInfo",
                    **get_runtime_signature()
                }))
        except Exception as e:
            debug_log(f" Failed to send runtimeInfo: {e}")

        return {
            "action": "bootstrapReady",
            "success": True
        }

    def _handle_load_tutorial(self, tutorial_id: str) -> dict:
        """Legacy loadTutorial route is disabled in cloud-only mode."""
        return {
            "action": "error",
            "message": "Loading local tutorials by ID is disabled in cloud-only mode.",
            "success": False
        }

    def _handle_start_tutorial_fetch(self) -> dict:
        """Load tutorial payload from local test data."""
        global _tutorial_manager, _runtime_identity_ok, _consent_manager, _palette

        if not _runtime_identity_ok:
            return {
                "action": "error",
                "phase": "load-test-data",
                "message": "Runtime deployment mismatch detected. Re-deploy the add-in bundle and restart.",
                "success": False
            }

        try:
            test_tutorial_file = get_resource_path(TEST_TUTORIAL_RELATIVE_PATH)
            if not os.path.exists(test_tutorial_file):
                return {
                    "action": "error",
                    "phase": "load-test-data",
                    "message": f"Test tutorial file not found: {test_tutorial_file}",
                    "success": False
                }

            with open(test_tutorial_file, "r", encoding="utf-8") as f:
                tutorial_data = json.load(f)

            if not isinstance(tutorial_data, dict):
                return {
                    "action": "error",
                    "phase": "load-test-data",
                    "message": "Tutorial payload is invalid.",
                    "success": False
                }
            if not isinstance(tutorial_data.get("steps"), list) or len(tutorial_data.get("steps", [])) == 0:
                return {
                    "action": "error",
                    "phase": "load-test-data",
                    "message": "Tutorial payload is missing a valid steps array.",
                    "success": False
                }

            qc_validation_errors = validate_tutorial_qc_checks(
                tutorial_data,
                strict_command_id_check=STRICT_QC_COMMAND_VALIDATION
            )
            if qc_validation_errors:
                message = f"Tutorial QC validation failed: {qc_validation_errors[0]}"
                debug_log(f" {message}")
                return {
                    "action": "error",
                    "phase": "load-test-data",
                    "message": message,
                    "success": False
                }

            step_context_warnings = validate_tutorial_step_entry_contexts(tutorial_data)
            if step_context_warnings:
                debug_log(" Tutorial step-entry context warnings (non-blocking):")
                for warning in step_context_warnings:
                    debug_log(f"  - {warning}")

            step = _tutorial_manager.load_tutorial(tutorial_data)
            if not step:
                return {
                    "action": "error",
                    "phase": "load-test-data",
                    "message": "Unable to initialize tutorial from test data payload.",
                    "success": False
                }

            self._ensure_initial_step_context(step)
            debug_log(" Tutorial loaded from local test data payload, executing fusion actions...")
            self._execute_fusion_actions(step)
            mismatch_feedback = self._build_workspace_mismatch_feedback(step)

            # Keep existing consent prompt behavior, now after successful load.
            try:
                if _consent_manager and _consent_manager.is_first_run():
                    if _palette:
                        _palette.sendInfoToHTML("response", json.dumps({
                            "action": "consentRequired",
                            "firstRun": True
                        }))
            except Exception:
                pass

            response = {
                "action": "tutorialLoaded",
                "step": step,
                "success": True
            }
            if mismatch_feedback:
                response["workspaceMismatchFeedback"] = mismatch_feedback
            return response
        except Exception as e:
            debug_log(f" Error loading tutorial from local test data: {e}")
            return {
                "action": "error",
                "phase": "load-test-data",
                "message": str(e),
                "success": False
            }

    def _handle_check_scan_status(self) -> dict:
        """Return scan status for debug/progress display."""
        if not WEBHOOK_MODULE_LOADED or not callable(get_scan_status):
            diag = _build_webhook_unavailable_message()
            debug_log(diag)
            return {
                "action": "error",
                "phase": "scan-status",
                "message": diag,
                "success": False
            }

        try:
            result = get_scan_status(timeout_seconds=10)
            if not result.get("ok"):
                return {
                    "action": "error",
                    "phase": "scan-status",
                    "message": result.get("error", "Failed to fetch scan status."),
                    "success": False
                }

            return {
                "action": "scanStatus",
                "statusCode": result.get("statusCode", -1),
                "success": True
            }
        except Exception as e:
            debug_log(f" Error checking scan status: {e}")
            return {
                "action": "error",
                "phase": "scan-status",
                "message": str(e),
                "success": False
            }

    def _execute_fusion_actions(self, step: dict):
        """Execute Fusion actions for a step."""
        actions = step.get("fusionActions", [])
        if actions:
            runner = FusionActionsRunner()
            runner.execute_actions(actions)

    def _ensure_initial_step_context(self, step: dict):
        """Best-effort auto-switch to the first step's required context."""
        global _context_detector

        if not step or not CORE_MODULES_LOADED or not _context_detector:
            return

        requires = step.get("requires", {}) or {}
        required_workspace = requires.get("workspace")
        required_environment = requires.get("environment")
        if not required_workspace and not required_environment:
            return

        try:
            tools_tab_active = self._is_tools_tab_active()
            current = _context_detector.get_current_context()
            workspace_mismatch = (
                bool(required_workspace) and
                str(current.workspace.value).lower() != str(required_workspace).lower()
            )
            environment_mismatch = (
                bool(required_environment) and
                str(current.environment.value).lower() != str(required_environment).lower()
            )

            # Startup timing edge case: detector can transiently report Solid while
            # UI focus is still on ToolsTab/Utilities. Force switch attempt anyway.
            force_switch_from_tools = tools_tab_active and str(required_environment).lower() == "solid"

            if not workspace_mismatch and not environment_mismatch and not force_switch_from_tools:
                return

            debug_log(
                f" Initial tutorial open auto-switch attempt: "
                f"current={current.workspace.value}/{current.environment.value}, "
                f"required={required_workspace}/{required_environment}"
            )

            # Retry a few times because launching from Add-Ins/Utilities can leave
            # Fusion in a transient UI state on initial palette open.
            for _ in range(4):
                if str(required_environment).lower() == "solid":
                    self._collapse_tools_tab_to_solid()
                    self._pump_ui_events(0.1)

                if workspace_mismatch and required_workspace:
                    self._activate_workspace_by_name(required_workspace)
                    self._pump_ui_events(0.15)

                if required_environment:
                    self._activate_environment_tab(required_environment)
                    self._pump_ui_events(0.2)

                # Re-check after each attempt and exit early if matched.
                current = _context_detector.get_current_context()
                workspace_mismatch = (
                    bool(required_workspace) and
                    str(current.workspace.value).lower() != str(required_workspace).lower()
                )
                environment_mismatch = (
                    bool(required_environment) and
                    str(current.environment.value).lower() != str(required_environment).lower()
                )
                if not workspace_mismatch and not environment_mismatch:
                    break

        except Exception as e:
            debug_log(f" Initial tutorial context auto-switch failed (continuing): {e}")

    def _is_tools_tab_active(self) -> bool:
        """Detect whether ToolsTab currently has focus."""
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface if app else None
            if not ui:
                return False

            global_tabs = getattr(ui, "toolbarTabs", None)
            if global_tabs:
                tools_tab = global_tabs.itemById("ToolsTab")
                if tools_tab and getattr(tools_tab, "isActive", False):
                    return True

            active_workspace = ui.activeWorkspace
            ws_tabs = active_workspace.toolbarTabs if active_workspace else None
            if ws_tabs:
                tools_tab = ws_tabs.itemById("ToolsTab")
                if tools_tab and getattr(tools_tab, "isActive", False):
                    return True
        except Exception:
            pass

        return False

    def _collapse_tools_tab_to_solid(self) -> bool:
        """If ToolsTab is active, switch to SolidTab before rendering tutorial step."""
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface if app else None
            if not ui:
                return False

            # Try global toolbar tabs first (matches user-observed API path)
            global_tabs = getattr(ui, "toolbarTabs", None)
            if global_tabs:
                tools_tab = global_tabs.itemById("ToolsTab")
                solid_tab = global_tabs.itemById("SolidTab")
                if tools_tab and getattr(tools_tab, "isActive", False) and solid_tab:
                    solid_tab.activate()
                    debug_log(" Collapsed ToolsTab by activating SolidTab (ui.toolbarTabs)")
                    return True

            # Fallback: active workspace toolbar tabs
            active_workspace = ui.activeWorkspace
            ws_tabs = active_workspace.toolbarTabs if active_workspace else None
            if ws_tabs:
                tools_tab = ws_tabs.itemById("ToolsTab")
                solid_tab = ws_tabs.itemById("SolidTab")
                if tools_tab and getattr(tools_tab, "isActive", False) and solid_tab:
                    solid_tab.activate()
                    debug_log(" Collapsed ToolsTab by activating SolidTab (activeWorkspace.toolbarTabs)")
                    return True
        except Exception as e:
            debug_log(f" Failed collapsing ToolsTab to SolidTab: {e}")

        return False

    def _pump_ui_events(self, delay_seconds: float = 0.1):
        """Let Fusion process UI changes between activation attempts."""
        try:
            adsk.doEvents()
        except Exception:
            pass
        time.sleep(delay_seconds)
        try:
            adsk.doEvents()
        except Exception:
            pass

    def _activate_workspace_by_name(self, workspace_name: str) -> bool:
        """Attempt to activate a top-level Fusion workspace by name."""
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface if app else None
            if not ui:
                return False

            # Preferred: iterate workspaces collection and activate matching display name.
            try:
                workspaces = ui.workspaces
                if workspaces:
                    for i in range(workspaces.count):
                        ws = workspaces.item(i)
                        ws_name = (getattr(ws, "name", "") or "").strip()
                        if ws_name.lower() == str(workspace_name).lower():
                            ws.activate()
                            return True
            except Exception:
                pass

            # Fallback: execute workspace command definition.
            cmd_map = {
                "design": "DesignWorkspace",
                "render": "RenderWorkspace",
                "manufacture": "ManufactureWorkspace",
                "simulation": "SimulationWorkspace",
                "drawing": "DrawingWorkspace",
                "animation": "AnimationWorkspace",
                "generative": "GenerativeDesignWorkspace",
            }
            cmd_id = cmd_map.get(str(workspace_name).lower())
            if cmd_id:
                cmd_def = ui.commandDefinitions.itemById(cmd_id)
                if cmd_def:
                    cmd_def.execute()
                    return True
        except Exception as e:
            debug_log(f" Failed to activate workspace '{workspace_name}': {e}")

        return False

    def _activate_environment_tab(self, environment_name: str) -> bool:
        """Attempt to activate a Design environment tab by name."""
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface if app else None
            active_workspace = ui.activeWorkspace if ui else None
            if not active_workspace:
                return False

            target = str(environment_name).strip().lower()

            # First try Design workspace + explicit tab activation. This is the most
            # reliable path when launched from Add-Ins (ToolsTab/Utilities focus).
            try:
                design_tab_map = {
                    "solid": "SolidTab",
                    "surface": "SurfaceTab",
                    "mesh": "MeshTab",
                    "sheet metal": "SheetMetalTab",
                    "sketch": "SketchTab",
                    "plastic": "PlasticTab",
                }
                tab_id = design_tab_map.get(target)
                if tab_id and ui.workspaces:
                    design_ws = ui.workspaces.itemById("FusionSolidEnvironment")
                    if design_ws:
                        design_ws.activate()
                        self._pump_ui_events(0.1)
                        solid_tab = design_ws.toolbarTabs.itemById(tab_id)
                        if solid_tab:
                            solid_tab.activate()
                            debug_log(f" Activated Design workspace + tab: FusionSolidEnvironment/{tab_id}")
                            return True

                # Form is typically a separate environment/workspace in some builds.
                if target == "form" and ui.workspaces:
                    sculpt_ws = ui.workspaces.itemById("FusionSculptEnvironment")
                    if sculpt_ws:
                        sculpt_ws.activate()
                        debug_log(" Activated environment workspace: FusionSculptEnvironment")
                        return True
            except Exception:
                pass

            toolbar_tabs = active_workspace.toolbarTabs
            if toolbar_tabs:
                alias_map = {
                    "sheet metal": ["sheetmetal", "sheet metal"],
                    "utilities": ["utilities", "utility"],
                    "form": ["form", "sculpt", "tspline"],
                }
                terms = set([target])
                for alias in alias_map.get(target, []):
                    terms.add(alias)

                for i in range(toolbar_tabs.count):
                    tab = toolbar_tabs.item(i)
                    tab_id = (getattr(tab, "id", "") or "").lower()
                    tab_name = (getattr(tab, "name", "") or "").lower()
                    if any(term in tab_id or term in tab_name for term in terms):
                        try:
                            tab.activate()
                            debug_log(f" Activated environment toolbar tab: {tab.id or tab.name}")
                            return True
                        except Exception:
                            # Fall through to command-based activation using the tab id.
                            if tab_id and ui:
                                cmd_def = ui.commandDefinitions.itemById(tab.id)
                                if cmd_def:
                                    cmd_def.execute()
                                    debug_log(f" Activated environment via tab command id: {tab.id}")
                                    return True

            # Fallback: execute tab command definition if exposed.
            cmd_map = {
                "solid": "SolidTab",
                "surface": "SurfaceTab",
                "mesh": "MeshTab",
                "sheet metal": "SheetMetalTab",
                "sketch": "SketchTab",
                "form": "FormTab",
                "utilities": "UtilitiesTab",
            }
            cmd_id = cmd_map.get(target)
            if cmd_id and ui:
                cmd_def = ui.commandDefinitions.itemById(cmd_id)
                if cmd_def:
                    cmd_def.execute()
                    debug_log(f" Activated environment via known command: {cmd_id}")
                    return True

            # Last resort: fuzzy search command definitions for a tab command that
            # contains the target term (helps across Fusion builds with different IDs).
            if ui:
                try:
                    defs = ui.commandDefinitions
                    for i in range(defs.count):
                        cmd = defs.item(i)
                        cid = (getattr(cmd, "id", "") or "").lower()
                        cname = (getattr(cmd, "name", "") or "").lower()
                        if any(term in cid or term in cname for term in terms):
                            if "tab" in cid or "tab" in cname:
                                cmd.execute()
                                debug_log(f" Activated environment via fuzzy command: {cmd.id}")
                                return True
                except Exception:
                    pass
        except Exception as e:
            debug_log(f" Failed to activate environment '{environment_name}': {e}")

        return False

    def _build_workspace_mismatch_feedback(self, step: dict) -> dict:
        """Create payload for a non-blocking workspace/environment mismatch modal."""
        global _context_detector

        if not step or not CORE_MODULES_LOADED or not _context_detector:
            return None

        requires = (step.get("requires") or {})
        required_workspace = requires.get("workspace")
        required_environment = requires.get("environment")
        if not required_workspace and not required_environment:
            return None

        try:
            current_context = _context_detector.get_current_context()
            current_workspace = current_context.workspace.value
            current_environment = current_context.environment.value

            workspace_mismatch = (
                bool(required_workspace) and
                str(current_workspace).lower() != str(required_workspace).lower()
            )
            environment_mismatch = (
                bool(required_environment) and
                str(current_environment).lower() != str(required_environment).lower()
            )

            if not workspace_mismatch and not environment_mismatch:
                return None

            mismatch_type = "workspace" if workspace_mismatch else "environment"
            if mismatch_type == "workspace":
                template = get_workspace_feedback_template()
                title = "Wrong Workspace for This Step"
                message = (
                    f"This step expects the {required_workspace} workspace. "
                    "You can close this and continue, but the UI may not match until you switch."
                )
                required_value = required_workspace
                current_value = current_workspace
                annotation_label = "Open the workspace selector here"
            else:
                template = get_environment_feedback_template(required_environment)
                title = "Wrong Environment for This Step"
                message = (
                    f"This step expects the {required_environment} environment (tab) in Fusion. "
                    "You can close this and continue, but the toolbar and commands may not match until you switch."
                )
                required_value = required_environment
                current_value = current_environment
                annotation_label = f"Switch to {required_environment} here"

            annotation = template.get("annotation", {})
            position = annotation.get("position", {})

            return {
                "title": title,
                "message": message,
                "mismatchType": mismatch_type,
                "currentWorkspace": current_value,
                "requiredWorkspace": required_value,
                "referenceImageSrc": template.get("referenceImageSrc", "../assets/UI Images/Solid/Solid_0.png"),
                "annotation": {
                    "label": annotation_label,
                    "shape": annotation.get("shape", "circle"),
                    "position": {
                        "x": position.get("x", 4.2),
                        "y": position.get("y", 12.0),
                        "width": position.get("width", 6.8),
                        "height": position.get("height", 8.5)
                    }
                }
            }
        except Exception as e:
            debug_log(f" Workspace mismatch feedback check failed: {e}")
            return None

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
            response = {"action": "updateStep", "step": step, "success": True}
            mismatch_feedback = self._build_workspace_mismatch_feedback(step)
            if mismatch_feedback:
                response["workspaceMismatchFeedback"] = mismatch_feedback
            return response

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
                            response = {
                                "action": "updateStep",
                                "step": step,
                                "success": True
                            }
                            mismatch_feedback = self._build_workspace_mismatch_feedback(step)
                            if mismatch_feedback:
                                response["workspaceMismatchFeedback"] = mismatch_feedback
                            return response
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
                        response = {
                            "action": "updateStep",
                            "step": step,
                            "success": True
                        }
                        mismatch_feedback = self._build_workspace_mismatch_feedback(step)
                        if mismatch_feedback:
                            response["workspaceMismatchFeedback"] = mismatch_feedback
                        return response

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
                response = {
                    "action": "updateStep",
                    "step": step,
                    "skippedRedirect": True,
                    "success": True
                }
                mismatch_feedback = self._build_workspace_mismatch_feedback(step)
                if mismatch_feedback:
                    response["workspaceMismatchFeedback"] = mismatch_feedback
                return response

        return {"action": "redirectSkipped", "success": True}

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
    global _completion_detector
    global _runtime_identity_ok

    debug_log("=== run() called - add-in starting ===")
    debug_log(f"Runtime build stamp: {BUILD_STAMP}")

    try:
        _app = adsk.core.Application.get()
        _ui = _app.userInterface
        _tutorial_manager = TutorialManager()
        debug_log(" Basic initialization complete")

        # Mandatory runtime identity check to catch stale installed bundle.
        _runtime_identity_ok, identity = validate_runtime_identity()
        debug_log(f" Runtime script path: {identity.get('scriptPath')}")
        debug_log(f" Runtime header hash: {identity.get('headerHash')}")
        if not _runtime_identity_ok and _ui:
            try:
                _ui.messageBox(identity.get("message", "Runtime identity validation failed."))
            except Exception:
                pass

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
    global _completion_detector

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
