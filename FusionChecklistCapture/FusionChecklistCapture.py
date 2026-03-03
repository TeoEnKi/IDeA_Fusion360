import os
import json
from datetime import datetime, timezone

import adsk.core
from pathlib import Path


ADDIN_NAME = "Fusion Checklist Capture"
COMMAND_ID = "openChecklistCaptureCmd"
COMMAND_NAME = "Checklist Capture"
PALETTE_ID = "ChecklistCapturePalette"
PALETTE_NAME = "Checklist Capture"

IGNORE_COMMAND_PREFIXES = ("Select", "Pan", "Orbit", "Zoom")
IGNORE_COMMAND_CONTAINS = (
    "ChecklistCapture",
    "TutorialOverlay",
)
IGNORE_COMMAND_IDS = {
    COMMAND_ID,
    "showTutorialPanelCmd",
    "SelectCommand",
    "PanCommand",
    "OrbitCommand",
    "ZoomCommand",
    "CommitCommand",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "capture_output")
EXPORTS_DIR = os.path.join(BASE_DIR, "Exports")
DEBUG_LOG = os.path.join(BASE_DIR, "capture_debug.log")

_handlers = []
_app = None
_ui = None
_palette = None
_command_start_handler = None
_command_term_handler = None
_html_handler = None
_command_panel_ids = []



def _log(msg: str):
    try:
        print(f"[ChecklistCapture] {msg}")
    except Exception:
        pass
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass



def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")



def _session_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")



def _overlay_contents_dir() -> str:
    # .../API/AddIns/FusionChecklistCapture -> .../API/AddIns
    addins_root = os.path.dirname(BASE_DIR)
    return os.path.join(addins_root, "FusionTutorialOverlay.bundle", "Contents")



def _read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _should_ignore_runtime_command(command_id: str) -> bool:
    if not command_id:
        return True
    if command_id in IGNORE_COMMAND_IDS:
        return True
    if any(command_id.startswith(prefix) for prefix in IGNORE_COMMAND_PREFIXES):
        return True
    if any(token in command_id for token in IGNORE_COMMAND_CONTAINS):
        return True
    return False


def _write_json_atomic(path: str, payload):
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=True, indent=2)
    os.replace(tmp_path, path)



def _build_checklist_rows():
    overlay_contents = _overlay_contents_dir()
    sketch_path = os.path.join(overlay_contents, "assets", "UI Images", "Sketch", "Sketch_UIComponents.json")
    solid_path = os.path.join(overlay_contents, "assets", "UI Images", "Solid", "Solid_UIComponents.json")

    if not os.path.exists(sketch_path) or not os.path.exists(solid_path):
        raise FileNotFoundError(
            "Could not find FusionTutorialOverlay UI component JSON files. "
            f"Expected:\n{solid_path}\n{sketch_path}"
        )

    sketch = _read_json(sketch_path)
    solid = _read_json(solid_path)

    rows = []

    def add_from(config: dict, source_name: str, env: str):
        components = config.get("components", {})

        # Workspace and environment tabs are in scope (buttons + tabs).
        wd = components.get("workspaceDropdown")
        if wd:
            rows.append({
                "environment": env,
                "source_file": source_name,
                "component_path": "components.workspaceDropdown",
                "label": wd.get("label", ""),
                "current_commandId": wd.get("commandId", ""),
                "class": "tab_or_workspace",
            })
            for idx, opt in enumerate(wd.get("options", []), start=1):
                rows.append({
                    "environment": env,
                    "source_file": source_name,
                    "component_path": f"components.workspaceDropdown.options[{idx}]",
                    "label": opt.get("label", ""),
                    "current_commandId": opt.get("commandId", ""),
                    "class": "tab_or_workspace",
                })

        for tab_key, tab in (components.get("environmentTabs", {}) or {}).items():
            rows.append({
                "environment": env,
                "source_file": source_name,
                "component_path": f"components.environmentTabs.{tab_key}",
                "label": tab.get("label", ""),
                "current_commandId": tab.get("commandId", ""),
                "class": "tab_or_workspace",
            })

        for group_key, group in (components.get("toolbarGroups", {}) or {}).items():
            for idx, tool in enumerate(group.get("tools", []) or [], start=1):
                rows.append({
                    "environment": env,
                    "source_file": source_name,
                    "component_path": f"components.toolbarGroups.{group_key}.tools[{idx}]",
                    "label": tool.get("label", ""),
                    "current_commandId": tool.get("commandId", ""),
                    "class": "tool_button",
                })

        finish = components.get("finishSketch")
        if finish:
            rows.append({
                "environment": env,
                "source_file": source_name,
                "component_path": "components.finishSketch",
                "label": finish.get("label", ""),
                "current_commandId": finish.get("commandId", ""),
                "class": "tool_button",
            })

        for nav_key, nav in (components.get("navigationBar", {}) or {}).items():
            rows.append({
                "environment": env,
                "source_file": source_name,
                "component_path": f"components.navigationBar.{nav_key}",
                "label": nav.get("label", nav_key),
                "current_commandId": nav.get("commandId", ""),
                "class": "tool_button",
            })

    add_from(solid, "Solid_UIComponents.json", "solid")
    add_from(sketch, "Sketch_UIComponents.json", "sketch")

    for i, row in enumerate(rows, start=1):
        row["sequence"] = i
        row["observed_commandId"] = ""
        row["observed_terminated_commandId"] = ""
        row["status"] = "missing"
        row["eventCalled"] = ""
        row["captureSource"] = ""
        row["lastSavedAtUtc"] = ""
        row["excludedFromExport"] = False
        row["methodContext"] = ""
        row["evidence_line"] = ""
        row["notes"] = ""

    return rows


def _derive_ui_component_name(component_path: str, sequence: int) -> str:
    if not component_path:
        return f"component_{sequence}"

    if "[" in component_path and "]" in component_path:
        normalized = component_path.replace("components.", "")
        normalized = normalized.replace(".", "_")
        normalized = normalized.replace("[", "_")
        normalized = normalized.replace("]", "")
        return normalized

    segments = [s for s in component_path.split(".") if s]
    if not segments:
        return f"component_{sequence}"
    return segments[-1]


def _resolve_path_in_components(components_root: dict, component_path: str):
    if not isinstance(components_root, dict) or not component_path:
        return None

    path = component_path.strip()
    if path.startswith("components."):
        path = path[len("components."):]
    elif path == "components":
        return components_root

    node = components_root
    for segment in path.split("."):
        if not segment:
            return None

        if "[" in segment and segment.endswith("]"):
            name, index_str = segment.split("[", 1)
            index_str = index_str[:-1]
            if name:
                if not isinstance(node, dict) or name not in node:
                    return None
                node = node[name]
            if not isinstance(node, list):
                return None
            try:
                one_based_index = int(index_str)
            except ValueError:
                return None
            zero_based_index = one_based_index - 1
            if zero_based_index < 0 or zero_based_index >= len(node):
                return None
            node = node[zero_based_index]
            continue

        if not isinstance(node, dict) or segment not in node:
            return None
        node = node[segment]

    return node


def _resolve_component_metadata_from_path(component_path: str, solid_json: dict, sketch_json: dict) -> dict:
    for source in (solid_json, sketch_json):
        if not isinstance(source, dict):
            continue
        resolved = _resolve_path_in_components(source.get("components", {}), component_path)
        if isinstance(resolved, dict):
            return {
                "id": resolved.get("id", "") or "",
                "label": resolved.get("label", "") or "",
            }
    return {"id": "", "label": ""}


def _build_component_events_export(rows, exported_at_utc: str, session_id: str):
    overlay_contents = _overlay_contents_dir()
    source_solid_json_path = os.path.join(overlay_contents, "assets", "UI Images", "Solid", "Solid_UIComponents.json")
    source_sketch_json_path = os.path.join(overlay_contents, "assets", "UI Images", "Sketch", "Sketch_UIComponents.json")
    solid_json = _read_json(source_solid_json_path)
    sketch_json = _read_json(source_sketch_json_path)

    commands = {}
    for row in rows:
        command_id = row.get("current_commandId", "")
        # commands export should represent user-captured command IDs
        if row.get("excludedFromExport", False):
            continue
        if not command_id or not row.get("lastSavedAtUtc", ""):
            continue

        sequence = row.get("sequence", 0)
        component_path = row.get("component_path", "")
        meta = _resolve_component_metadata_from_path(component_path, solid_json, sketch_json)
        if not meta.get("id") and not meta.get("label"):
            _log(f"WARN unresolved component metadata for path={component_path} sequence={sequence}")

        base_key = _derive_ui_component_name(component_path, sequence)
        key = base_key
        if key in commands:
            key = f"{base_key}__{sequence}"

        # Component-keyed upsert: each prompted component has one dictionary.
        commands[key] = {
            "label": meta.get("label", ""),
            "commandDefinition": meta.get("id", ""),
            "commandId": command_id,
            "componentPath": component_path,
            "captureSource": row.get("captureSource", ""),
            "lastSavedAtUtc": row.get("lastSavedAtUtc", ""),
            "status": row.get("status", "missing"),
        }

    return {
        "sessionId": session_id,
        "exportedAtUtc": exported_at_utc,
        "sourceSolidJsonPath": source_solid_json_path,
        "sourceSketchJsonPath": source_sketch_json_path,
        "totalExportedComponents": len(commands),
        "commands": commands,
    }


class CaptureSession:
    def __init__(self):
        self.active = False
        self.armed = False
        self.session_id = ""
        self.rows = []
        self.index = 0
        self.raw_events = []
        self.raw_events_path = ""
        self.mapping_path = ""
        self.report_path = ""
        self.source_path = ""
        self.component_events_json_path = ""
        self.capture_state = "idle"
        self.pending_candidate = None
        self.last_observed_command = ""
        self.last_observed_event = ""
        self.last_observed_at = ""

    def start(self):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs(EXPORTS_DIR, exist_ok=True)
        self.session_id = _session_id()
        self.rows = _build_checklist_rows()
        self.index = 0
        self.active = True
        self.armed = False
        self.capture_state = "idle"
        self.pending_candidate = None
        self.last_observed_command = ""
        self.last_observed_event = ""
        self.last_observed_at = ""
        self.raw_events = []
        self.raw_events_path = os.path.join(OUTPUT_DIR, f"live_capture_events_{self.session_id}.jsonl")
        self.mapping_path = os.path.join(OUTPUT_DIR, f"ui_capture_mapping_{self.session_id}.csv")
        self.report_path = os.path.join(OUTPUT_DIR, f"ui_capture_report_{self.session_id}.md")
        self.source_path = os.path.join(OUTPUT_DIR, f"ui_capture_source_{self.session_id}.json")
        self.component_events_json_path = os.path.join(EXPORTS_DIR, f"ui_capture_component_events_{self.session_id}.json")
        self._persist_source()
        _log(f"Session started: {self.session_id} rows={len(self.rows)}")
        _log(f"Source JSON path: {self.source_path}")
        _log(f"Component events JSON path: {self.component_events_json_path}")

    def _persist_source(self):
        payload = {
            "sessionId": self.session_id,
            "updatedAtUtc": _utc_now(),
            "rows": self.rows,
        }
        _write_json_atomic(self.source_path, payload)

    def _ensure_active_row(self):
        if not self.active:
            raise RuntimeError("Start session first")
        if self.index < 0 or self.index >= len(self.rows):
            raise RuntimeError("Checklist complete")
        return self.rows[self.index]

    def _append_raw_event(self, event_type: str, command_id: str):
        ev = {
            "utcTimestamp": _utc_now(),
            "sessionId": self.session_id,
            "eventType": event_type,
            "commandId": command_id,
        }
        self.raw_events.append(ev)
        try:
            with open(self.raw_events_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(ev, ensure_ascii=True) + "\n")
        except Exception as e:
            _log(f"Failed writing raw event: {e}")

    def _update_last_observed(self, event_type: str, command_id: str):
        if not command_id:
            return
        self.last_observed_event = event_type
        self.last_observed_command = command_id
        self.last_observed_at = _utc_now()

    def arm_next(self):
        self._ensure_active_row()
        self.armed = True
        self.capture_state = "armed"
        self.pending_candidate = None

    def next_row(self):
        if not self.active:
            raise RuntimeError("Start session first")
        if self.index < len(self.rows):
            self.index += 1
        self.armed = False
        self.capture_state = "idle"
        self.pending_candidate = None

    def prev_row(self):
        if not self.active:
            raise RuntimeError("Start session first")
        if self.index > 0:
            self.index -= 1
        self.armed = False
        self.capture_state = "idle"
        self.pending_candidate = None

    def retry_capture(self):
        row = self._ensure_active_row()
        row["observed_commandId"] = ""
        row["observed_terminated_commandId"] = ""
        row["methodContext"] = ""
        row["evidence_line"] = ""
        row["notes"] = ""
        self.armed = True
        self.capture_state = "armed"
        self.pending_candidate = None

    def discard_capture(self):
        if not self.active:
            raise RuntimeError("Start session first")
        self.armed = False
        self.capture_state = "idle"
        self.pending_candidate = None

    def save_capture(self):
        row = self._ensure_active_row()
        if self.pending_candidate:
            method = self.pending_candidate.get("method", "")
            source = self.pending_candidate.get("source", "")
        else:
            if not self.last_observed_command:
                raise RuntimeError("No pending capture or observed command to save")
            method = self.last_observed_command
            source = self.last_observed_event or "observed"
        now = _utc_now()
        previous_command_id = row.get("current_commandId", "")

        row["eventCalled"] = method
        row["current_commandId"] = method
        row["captureSource"] = source
        row["lastSavedAtUtc"] = now
        row["excludedFromExport"] = False
        if self.pending_candidate:
            row["notes"] = "saved by user"
        else:
            row["notes"] = "saved from latest observed command (manual save fallback)"
        if source == "commandStarting":
            row["observed_commandId"] = method
        elif source == "commandTerminated":
            row["observed_terminated_commandId"] = method
        row["status"] = "match" if method == previous_command_id else "replace"
        row["methodContext"] = json.dumps(
            {"event": source, "handler": "PaletteHTMLEventHandler.saveCapture", "source": "live_capture"},
            ensure_ascii=True,
        )
        row["evidence_line"] = f"session={self.session_id};utc={now};event=saved;commandId={method};source={source}"

        self._persist_source()
        component_events_payload = _build_component_events_export(self.rows, _utc_now(), self.session_id)
        _write_json_atomic(self.component_events_json_path, component_events_payload)

        self.pending_candidate = None
        self.armed = False
        self.capture_state = "saved"

    def log_remove_component_intent(self):
        row = self._ensure_active_row()
        ts = _utc_now()
        existing = row.get("notes", "")
        marker = f"[{ts}] user_intent=remove_component"
        row["notes"] = f"{existing}; {marker}" if existing else marker
        # Remove current row from future command exports.
        row["excludedFromExport"] = True
        row["lastSavedAtUtc"] = ""
        row["eventCalled"] = ""
        row["captureSource"] = ""
        row["status"] = "missing"
        row["methodContext"] = ""
        row["evidence_line"] = ""
        self._append_raw_event("user_intent_remove_component", row.get("component_path", ""))
        self._persist_source()
        component_events_payload = _build_component_events_export(self.rows, _utc_now(), self.session_id)
        _write_json_atomic(self.component_events_json_path, component_events_payload)

    def capture_command_started(self, command_id: str):
        if not self.active:
            return

        if _should_ignore_runtime_command(command_id):
            return

        self._append_raw_event("command_started", command_id)
        self._update_last_observed("command_started", command_id)

        if not self.armed:
            return

        if self.pending_candidate is not None:
            return

        row = self._ensure_active_row()
        row["observed_commandId"] = command_id
        self.pending_candidate = {
            "method": command_id,
            "source": "commandStarting",
            "previousCommandId": row.get("current_commandId", ""),
            "previousEventCalled": row.get("eventCalled", ""),
            "capturedAtUtc": _utc_now(),
        }
        self.capture_state = "candidate_pending_confirmation"
        self.armed = False

    def capture_command_terminated(self, command_id: str):
        if not self.active:
            return

        if _should_ignore_runtime_command(command_id):
            return

        self._append_raw_event("command_terminated", command_id)
        self._update_last_observed("command_terminated", command_id)

        if not self.armed and self.pending_candidate is None:
            return

        if self.index < 0 or self.index >= len(self.rows):
            return

        row = self.rows[self.index]
        if not row.get("observed_terminated_commandId"):
            row["observed_terminated_commandId"] = command_id
        if self.armed and self.pending_candidate is None:
            self.pending_candidate = {
                "method": command_id,
                "source": "commandTerminated",
                "previousCommandId": row.get("current_commandId", ""),
                "previousEventCalled": row.get("eventCalled", ""),
                "capturedAtUtc": _utc_now(),
            }
            self.capture_state = "candidate_pending_confirmation"
            self.armed = False

    def export(self):
        if not self.active:
            raise RuntimeError("Start session first")

        import csv

        os.makedirs(EXPORTS_DIR, exist_ok=True)
        fields = [
            "sequence",
            "component_path",
            "label",
            "current_commandId",
            "eventCalled",
            "captureSource",
            "lastSavedAtUtc",
            "observed_commandId",
            "observed_terminated_commandId",
            "status",
            "methodContext",
            "evidence_line",
            "notes",
        ]
        with open(self.mapping_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for row in self.rows:
                writer.writerow({k: row.get(k, "") for k in fields})

        exported_at_utc = _utc_now()
        component_events_payload = _build_component_events_export(self.rows, exported_at_utc, self.session_id)
        _write_json_atomic(self.component_events_json_path, component_events_payload)

        counts = {"match": 0, "replace": 0, "missing": 0}
        for row in self.rows:
            st = row.get("status", "missing")
            if st not in counts:
                counts["missing"] += 1
            else:
                counts[st] += 1

        with open(self.report_path, "w", encoding="utf-8") as f:
            f.write("# UI Capture Audit Report\n\n")
            f.write(f"- Session ID: `{self.session_id}`\n")
            f.write(f"- Checklist entries: `{len(self.rows)}`\n")
            f.write(f"- Status counts: `match={counts['match']}`, `replace={counts['replace']}`, `missing={counts['missing']}`\n")
            saved_count = len([r for r in self.rows if r.get("lastSavedAtUtc")])
            f.write(f"- Saved command IDs: `{saved_count}`\n")
            f.write(f"- Source JSON: `{self.source_path}`\n")
            f.write(f"- Component Events JSON: `{self.component_events_json_path}`\n")
            f.write(f"- Exported components: `{component_events_payload['totalExportedComponents']}`\n")
            f.write(f"- Mapping CSV: `{self.mapping_path}`\n")
            f.write(f"- Raw events: `{self.raw_events_path}`\n\n")

            f.write("## High-confidence replacements\n\n")
            replacements = [r for r in self.rows if r.get("status") == "replace"]
            if not replacements:
                f.write("- None\n")
            else:
                for row in replacements:
                    f.write(
                        f"- `{row['component_path']}` ({row['label']}): "
                        f"`{row['current_commandId']}` -> `{row['observed_commandId']}`\n"
                    )

            f.write("\n## Missing captures\n\n")
            missing = [r for r in self.rows if r.get("status") == "missing"]
            if not missing:
                f.write("- None\n")
            else:
                for row in missing:
                    note = row.get("notes", "No captured command_started event.")
                    f.write(f"- `{row['component_path']}` ({row['label']}): {note}\n")

            f.write("\n## Saved command IDs\n\n")
            saved_rows = [r for r in self.rows if r.get("lastSavedAtUtc")]
            if not saved_rows:
                f.write("- None\n")
            else:
                for row in saved_rows:
                    f.write(
                        f"- `{row['component_path']}` ({row['label']}): "
                        f"`commandId={row['current_commandId']}` "
                        f"`captureSource={row.get('captureSource', '')}` "
                        f"`lastSavedAtUtc={row.get('lastSavedAtUtc', '')}`\n"
                    )

        _log(f"Exported mapping: {self.mapping_path}")
        _log(f"Exported report: {self.report_path}")
        _log(f"Exported component events JSON: {self.component_events_json_path}")

    def state_payload(self):
        total = len(self.rows)
        current = self.rows[self.index] if self.active and self.index < total else None
        return {
            "action": "state",
            "sessionActive": self.active,
            "sessionId": self.session_id,
            "armed": self.armed,
            "captureState": self.capture_state,
            "index": self.index,
            "total": total,
            "completed": len([r for r in self.rows if r.get("lastSavedAtUtc")]),
            "current": current,
            "pendingCandidate": self.pending_candidate,
            "lastObservedCommand": self.last_observed_command,
            "lastObservedEvent": self.last_observed_event,
            "lastObservedAtUtc": self.last_observed_at,
            "mappingPath": self.mapping_path,
            "reportPath": self.report_path,
            "sourcePath": self.source_path,
            "componentEventsJsonPath": self.component_events_json_path,
            "outputDir": OUTPUT_DIR,
            "exportsDir": EXPORTS_DIR,
        }


SESSION = CaptureSession()


class CommandStartingHandler(adsk.core.ApplicationCommandEventHandler):
    def notify(self, args: adsk.core.ApplicationCommandEventArgs):
        try:
            cmd = ""
            if hasattr(args, "commandDefinitionId"):
                cmd = args.commandDefinitionId or ""
            if not cmd and hasattr(args, "commandId"):
                cmd = args.commandId or ""
            if cmd:
                SESSION.capture_command_started(cmd)
                _send_state()
        except Exception as e:
            _log(f"Error in commandStarting handler: {e}")


class CommandTerminatedHandler(adsk.core.ApplicationCommandEventHandler):
    def notify(self, args: adsk.core.ApplicationCommandEventArgs):
        try:
            cmd = args.commandId if hasattr(args, "commandId") else ""
            if cmd:
                SESSION.capture_command_terminated(cmd)
                _send_state()
        except Exception as e:
            _log(f"Error in commandTerminated handler: {e}")


class PaletteHTMLEventHandler(adsk.core.HTMLEventHandler):
    def notify(self, args: adsk.core.HTMLEventArgs):
        try:
            data = {}
            if args.data:
                data = json.loads(args.data)
            action = data.get("action", "")
            if not action:
                return
            _log(f"HTML action received: {action}")

            if action == "ready":
                _send_state("Bridge ready")
                return

            if action == "startSession":
                SESSION.start()
                _send_state("Session started")
                return

            if action == "armNext":
                SESSION.arm_next()
                _send_state("Armed for next command click")
                return

            if action == "saveCapture":
                SESSION.save_capture()
                _send_state("Capture saved to commandId")
                return

            if action == "logRemoveComponent":
                SESSION.log_remove_component_intent()
                _send_state("Logged user intent: remove component")
                return

            if action == "discardCapture":
                SESSION.discard_capture()
                _send_state("Capture discarded")
                return

            if action == "retryCapture":
                SESSION.retry_capture()
                _send_state("Retry armed for current target")
                return

            if action == "nextRow":
                SESSION.next_row()
                _send_state("Moved to next target")
                return

            if action == "prevRow":
                SESSION.prev_row()
                _send_state("Moved to previous target")
                return

            if action == "skipCurrent":
                SESSION.next_row()
                _send_state("Row skipped")
                return

            if action == "back":
                SESSION.prev_row()
                _send_state("Moved back one row")
                return

            if action == "export":
                SESSION.export()
                _send_state("Export complete")
                return

            _send_state(f"Unknown action: {action}")
        except Exception as e:
            _log(f"HTML action error: {e}")
            _send_state(f"Action error: {e}")


class CommandExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args: adsk.core.CommandEventArgs):
        _open_palette()


class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args: adsk.core.CommandCreatedEventArgs):
        try:
            on_execute = CommandExecuteHandler()
            args.command.execute.add(on_execute)
            _handlers.append(on_execute)
        except Exception as e:
            _log(f"CommandCreated handler error: {e}")



def _send_state(message: str = ""):
    global _palette
    if not _palette:
        return
    payload = SESSION.state_payload()
    if message:
        payload["message"] = message
    try:
        _palette.sendInfoToHTML("response", json.dumps(payload))
        if message:
            _log(f"State sent to HTML: {message}")
        else:
            _log("State sent to HTML")
    except Exception as e:
        _log(f"Failed sending state to HTML: {e}")


def _ensure_command_controls(cmd_def: adsk.core.CommandDefinition):
    """Add command button to multiple known panels for workspace compatibility."""
    global _command_panel_ids
    _command_panel_ids = []

    panel_ids = [
        "ToolsUtilitiesPanel",
        "SolidScriptsAddinsPanel",
        "ToolsScriptsAddinsPanel",
    ]

    for panel_id in panel_ids:
        try:
            panel = _ui.allToolbarPanels.itemById(panel_id)
            if not panel:
                continue
            control = panel.controls.itemById(COMMAND_ID)
            if control:
                control.deleteMe()
            panel.controls.addCommand(cmd_def)
            _command_panel_ids.append(panel_id)
        except Exception as e:
            _log(f"Panel add failed for {panel_id}: {e}")

    if _command_panel_ids:
        _log(f"Command placed in panels: {', '.join(_command_panel_ids)}")
    else:
        _log("No known toolbar panel found for command placement.")


def _open_palette():
    global _palette, _html_handler
    try:
        if not _palette:
            html_file = Path(BASE_DIR, "palette", "checklist_palette.html").resolve()
            html_path = str(html_file).replace("\\", "/")
            html_uri = html_file.as_uri()
            _log(f"Opening palette HTML file: {html_path}")
            _log(f"Opening palette HTML URI: {html_uri}")
            _palette = _ui.palettes.add(
                PALETTE_ID,
                PALETTE_NAME,
                html_uri,
                False,
                True,
                True,
                420,
                540,
                True,
            )
            _html_handler = PaletteHTMLEventHandler()
            _palette.incomingFromHTML.add(_html_handler)
            _handlers.append(_html_handler)
        _palette.isVisible = True
        _send_state()
    except Exception as e:
        _log(f"Palette open error: {e}")



def run(context):
    global _app, _ui, _command_start_handler, _command_term_handler

    _app = adsk.core.Application.get()
    _ui = _app.userInterface if _app else None
    if not _ui:
        return

    try:
        with open(DEBUG_LOG, "w", encoding="utf-8") as f:
            f.write("=== Checklist Capture Add-in Started ===\n")
        _log(f"Runtime script path: {os.path.abspath(__file__).replace('\\', '/')}")

        cmd_def = _ui.commandDefinitions.itemById(COMMAND_ID)
        if cmd_def:
            cmd_def.deleteMe()

        cmd_def = _ui.commandDefinitions.addButtonDefinition(
            COMMAND_ID,
            COMMAND_NAME,
            "Open guided click checklist capture tool",
            "",
        )

        on_created = CommandCreatedHandler()
        cmd_def.commandCreated.add(on_created)
        _handlers.append(on_created)

        _ensure_command_controls(cmd_def)

        _command_start_handler = CommandStartingHandler()
        _ui.commandStarting.add(_command_start_handler)
        _handlers.append(_command_start_handler)

        _command_term_handler = CommandTerminatedHandler()
        _ui.commandTerminated.add(_command_term_handler)
        _handlers.append(_command_term_handler)

        _open_palette()

        _log("Checklist Capture add-in started")
    except Exception as e:
        _log(f"run() error: {e}")



def stop(context):
    global _palette, _command_start_handler, _command_term_handler, _html_handler, _command_panel_ids

    try:
        if _ui:
            try:
                if _command_start_handler:
                    _ui.commandStarting.remove(_command_start_handler)
            except Exception:
                pass
            try:
                if _command_term_handler:
                    _ui.commandTerminated.remove(_command_term_handler)
            except Exception:
                pass

            for panel_id in _command_panel_ids:
                try:
                    panel = _ui.allToolbarPanels.itemById(panel_id)
                    if panel:
                        control = panel.controls.itemById(COMMAND_ID)
                        if control:
                            control.deleteMe()
                except Exception:
                    pass

            cmd_def = _ui.commandDefinitions.itemById(COMMAND_ID)
            if cmd_def:
                cmd_def.deleteMe()

            if _palette:
                try:
                    if _html_handler:
                        _palette.incomingFromHTML.remove(_html_handler)
                except Exception:
                    pass
                _palette.deleteMe()
                _palette = None

        _command_start_handler = None
        _command_term_handler = None
        _html_handler = None
        _command_panel_ids = []
        _handlers.clear()
        _log("Checklist Capture add-in stopped")
    except Exception as e:
        _log(f"stop() error: {e}")
