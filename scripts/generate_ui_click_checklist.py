#!/usr/bin/env python3
"""Generate deterministic click checklist rows from Sketch/Solid UI component JSONs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List


def _read_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _iter_rows(config: Dict, source_name: str, env: str) -> Iterable[Dict[str, str]]:
    components = config.get("components", {})

    # Workspace dropdown and options
    wd = components.get("workspaceDropdown")
    if wd:
        yield {
            "environment": env,
            "source_file": source_name,
            "component_path": "components.workspaceDropdown",
            "label": wd.get("label", ""),
            "current_commandId": wd.get("commandId", ""),
            "class": "tab_or_workspace",
        }
        for idx, opt in enumerate(wd.get("options", []), start=1):
            yield {
                "environment": env,
                "source_file": source_name,
                "component_path": f"components.workspaceDropdown.options[{idx}]",
                "label": opt.get("label", ""),
                "current_commandId": opt.get("commandId", ""),
                "class": "tab_or_workspace",
            }

    # Environment tabs
    for tab_key, tab in (components.get("environmentTabs", {}) or {}).items():
        yield {
            "environment": env,
            "source_file": source_name,
            "component_path": f"components.environmentTabs.{tab_key}",
            "label": tab.get("label", ""),
            "current_commandId": tab.get("commandId", ""),
            "class": "tab_or_workspace",
        }

    # Toolbar tools (primary button clicks)
    for group_key, group in (components.get("toolbarGroups", {}) or {}).items():
        tools = group.get("tools", []) or []
        for idx, tool in enumerate(tools, start=1):
            yield {
                "environment": env,
                "source_file": source_name,
                "component_path": f"components.toolbarGroups.{group_key}.tools[{idx}]",
                "label": tool.get("label", ""),
                "current_commandId": tool.get("commandId", ""),
                "class": "tool_button",
            }

    # Sketch-only finish sketch button
    fs = components.get("finishSketch")
    if fs:
        yield {
            "environment": env,
            "source_file": source_name,
            "component_path": "components.finishSketch",
            "label": fs.get("label", ""),
            "current_commandId": fs.get("commandId", ""),
            "class": "tool_button",
        }

    # Navigation controls (if present)
    for nav_key, nav in (components.get("navigationBar", {}) or {}).items():
        yield {
            "environment": env,
            "source_file": source_name,
            "component_path": f"components.navigationBar.{nav_key}",
            "label": nav.get("label", nav_key),
            "current_commandId": nav.get("commandId", ""),
            "class": "tool_button",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate UI click checklist for live capture.")
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root path (default: current directory).",
    )
    parser.add_argument(
        "--out-dir",
        default="implementationplans/live_capture",
        help="Output directory for checklist files.",
    )
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    out_dir = (root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    sketch_path = root / "FusionTutorialOverlay.bundle/Contents/assets/UI Images/Sketch/Sketch_UIComponents.json"
    solid_path = root / "FusionTutorialOverlay.bundle/Contents/assets/UI Images/Solid/Solid_UIComponents.json"

    sketch = _read_json(sketch_path)
    solid = _read_json(solid_path)

    rows: List[Dict[str, str]] = []
    rows.extend(_iter_rows(solid, "Solid_UIComponents.json", "solid"))
    rows.extend(_iter_rows(sketch, "Sketch_UIComponents.json", "sketch"))

    for i, row in enumerate(rows, start=1):
        row["sequence"] = str(i)

    csv_path = out_dir / "ui_click_checklist.csv"
    fields = ["sequence", "environment", "source_file", "component_path", "label", "current_commandId", "class"]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    md_path = out_dir / "ui_click_checklist.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write("# UI Click Checklist (Live Capture)\n\n")
        f.write("Click each item in this exact order once.\n\n")
        for row in rows:
            f.write(
                f"{row['sequence']}. [{row['environment']}] {row['label']} "
                f"(`{row['component_path']}`) expected current: `{row['current_commandId']}`\n"
            )

    print(f"Wrote checklist CSV: {csv_path}")
    print(f"Wrote checklist MD: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

