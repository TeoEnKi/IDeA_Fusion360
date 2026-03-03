#!/usr/bin/env python3
"""Build PLAN.md outputs (CSV + Markdown) from live capture events and checklist."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


METHOD_CONTEXT = '{"event":"commandStarting","handler":"CommandStartingHandler.notify","source":"live_capture"}'


def _read_checklist(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _read_events(path: Path) -> List[Dict]:
    if not path.exists():
        return []

    out = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            rec["_lineNo"] = line_no
            out.append(rec)
    return out


def _installed_events_path() -> Path:
    appdata = Path.home() / "AppData" / "Roaming"
    return (
        appdata
        / "Autodesk"
        / "Autodesk Fusion 360"
        / "API"
        / "AddIns"
        / "FusionTutorialOverlay.bundle"
        / "Contents"
        / "live_capture_events.jsonl"
    )


def _pick_latest_session(events: List[Dict]) -> str:
    by_session = defaultdict(list)
    for ev in events:
        by_session[ev.get("sessionId", "")].append(ev)

    # choose the session with the highest first line no (latest append run)
    latest_session = ""
    latest_line = -1
    for session, recs in by_session.items():
        first_line = min(r.get("_lineNo", 0) for r in recs)
        if first_line > latest_line:
            latest_line = first_line
            latest_session = session
    return latest_session


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate live-capture mapping CSV + Markdown report.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument(
        "--checklist",
        default="implementationplans/live_capture/ui_click_checklist.csv",
        help="Checklist CSV path.",
    )
    parser.add_argument(
        "--events",
        default="FusionTutorialOverlay.bundle/Contents/live_capture_events.jsonl",
        help="Live capture events JSONL path.",
    )
    parser.add_argument(
        "--out-dir",
        default="implementationplans/live_capture",
        help="Output directory.",
    )
    parser.add_argument(
        "--session-id",
        default="",
        help="Optional explicit sessionId. Defaults to latest session found.",
    )
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    checklist_path = (root / args.checklist).resolve()
    events_path = (root / args.events).resolve()
    out_dir = (root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    checklist = _read_checklist(checklist_path)
    if not events_path.exists():
        fallback = _installed_events_path()
        if fallback.exists():
            events_path = fallback

    all_events = _read_events(events_path)
    session_id = args.session_id or _pick_latest_session(all_events)

    started = [
        e for e in all_events
        if e.get("sessionId", "") == session_id and e.get("eventType") == "command_started"
    ]
    terminated = [
        e for e in all_events
        if e.get("sessionId", "") == session_id and e.get("eventType") == "command_terminated"
    ]

    mapping_rows: List[Dict[str, str]] = []
    replace_count = 0
    match_count = 0
    missing_count = 0

    for idx, item in enumerate(checklist):
        observed = started[idx] if idx < len(started) else None
        current = item.get("current_commandId", "")

        if observed is None:
            status = "missing"
            observed_id = ""
            evidence = ""
            notes = "No captured command_started event at this sequence index."
            missing_count += 1
        else:
            observed_id = observed.get("commandId", "")
            if observed_id == current:
                status = "match"
                notes = ""
                match_count += 1
            else:
                status = "replace"
                notes = "Observed command differs from current mapping."
                replace_count += 1
            evidence = f"session={session_id};line={observed.get('_lineNo','')};utc={observed.get('utcTimestamp','')}"

        mapping_rows.append({
            "component_path": item.get("component_path", ""),
            "label": item.get("label", ""),
            "current_commandId": current,
            "observed_commandId": observed_id,
            "status": status,
            "methodContext": METHOD_CONTEXT if observed_id else "",
            "evidence_line": evidence,
            "notes": notes,
        })

    extra_started = max(0, len(started) - len(checklist))
    extra_terminated = len(terminated)

    csv_path = out_dir / "ui_capture_mapping.csv"
    fields = [
        "component_path",
        "label",
        "current_commandId",
        "observed_commandId",
        "status",
        "methodContext",
        "evidence_line",
        "notes",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(mapping_rows)

    md_path = out_dir / "ui_capture_report.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write("# UI Capture Audit Report\n\n")
        f.write(f"- Events source: `{events_path}`\n")
        f.write(f"- Session ID: `{session_id or '(none found)'}`\n")
        f.write(f"- Checklist entries: `{len(checklist)}`\n")
        f.write(f"- Captured command_started events: `{len(started)}`\n")
        f.write(f"- Captured command_terminated events: `{extra_terminated}`\n")
        f.write(f"- Status counts: `match={match_count}`, `replace={replace_count}`, `missing={missing_count}`\n")
        f.write(f"- Extra command_started beyond checklist: `{extra_started}`\n\n")

        f.write("## High-confidence replacements\n\n")
        replacement_rows = [r for r in mapping_rows if r["status"] == "replace"]
        if not replacement_rows:
            f.write("- None\n")
        else:
            for row in replacement_rows:
                f.write(
                    f"- `{row['component_path']}` ({row['label']}): "
                    f"`{row['current_commandId']}` -> `{row['observed_commandId']}` "
                    f"({row['evidence_line']})\n"
                )

        f.write("\n## Missing captures\n\n")
        missing_rows = [r for r in mapping_rows if r["status"] == "missing"]
        if not missing_rows:
            f.write("- None\n")
        else:
            for row in missing_rows:
                f.write(f"- `{row['component_path']}` ({row['label']}): {row['notes']}\n")

    print(f"Wrote mapping CSV: {csv_path}")
    print(f"Wrote report MD: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
