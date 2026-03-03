#!/usr/bin/env python3
"""Validate tutorial highlight component keys against Sketch/Solid UI component maps."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


def _read_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _build_allowed_keys(config: Dict) -> Set[str]:
    keys: Set[str] = set()
    components = config.get("components", {}) or {}

    toolbar_groups = components.get("toolbarGroups", {}) or {}
    for group_id, group in toolbar_groups.items():
        keys.add(f"toolbar.{group_id}")
        for tool in (group.get("tools", []) or []):
            tool_id = tool.get("id")
            if tool_id:
                keys.add(f"toolbar.{group_id}.{tool_id}")

    for tab_id in (components.get("environmentTabs", {}) or {}).keys():
        keys.add(f"environmentTabs.{tab_id}")

    if components.get("workspaceDropdown"):
        keys.add("workspaceDropdown")

    browser_items = ((components.get("browser", {}) or {}).get("items", {}) or {})
    for item_id in browser_items.keys():
        keys.add(f"browser.{item_id}")

    for nav_id in (components.get("navigationBar", {}) or {}).keys():
        keys.add(f"nav.{nav_id}")

    if components.get("finishSketch"):
        keys.add("finishSketch")
        keys.add("toolbar.finishSketch")

    return keys


def _build_component_label_lookup(config: Dict) -> Dict[str, str]:
    labels: Dict[str, str] = {}
    components = config.get("components", {}) or {}

    toolbar_groups = components.get("toolbarGroups", {}) or {}
    for group_id, group in toolbar_groups.items():
        group_label = group.get("label")
        if group_label:
            labels[f"toolbar.{group_id}"] = str(group_label)
        for tool in (group.get("tools", []) or []):
            tool_id = tool.get("id")
            tool_label = tool.get("label")
            if tool_id and tool_label:
                labels[f"toolbar.{group_id}.{tool_id}"] = str(tool_label)

    for tab_id, tab in (components.get("environmentTabs", {}) or {}).items():
        tab_label = tab.get("label")
        if tab_label:
            labels[f"environmentTabs.{tab_id}"] = str(tab_label)

    wd = components.get("workspaceDropdown")
    if wd and wd.get("label"):
        labels["workspaceDropdown"] = str(wd.get("label"))

    browser_items = ((components.get("browser", {}) or {}).get("items", {}) or {})
    for item_id, item in browser_items.items():
        item_label = item.get("label")
        if item_label:
            labels[f"browser.{item_id}"] = str(item_label)

    nav_items = components.get("navigationBar", {}) or {}
    for nav_id, nav in nav_items.items():
        nav_label = nav.get("label")
        if nav_label:
            labels[f"nav.{nav_id}"] = str(nav_label)

    finish = components.get("finishSketch")
    if finish and finish.get("label"):
        labels["finishSketch"] = str(finish.get("label"))
        labels["toolbar.finishSketch"] = str(finish.get("label"))

    return labels


def _iter_highlights(tutorial: Dict) -> Iterable[Tuple[str, str, Optional[str]]]:
    for step in tutorial.get("steps", []) or []:
        step_id = step.get("stepId", "<missing-stepId>")
        visual_step = step.get("visualStep", {}) or {}
        for image in visual_step.get("images", []) or []:
            for highlight in image.get("highlights", []) or []:
                component = highlight.get("component")
                if component:
                    yield step_id, str(component), highlight.get("label")


def _estimate_step_exit_context(step: Dict, current_workspace: str, current_environment: str) -> Tuple[str, str]:
    """Estimate workspace/environment after fusionActions for one step."""
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


def _validate_step_entry_contexts(tutorial: Dict) -> List[Tuple[str, str, str, str, str]]:
    """
    Return mismatches where requires.* does not match inferred step-entry context.

    Tuple format:
      (step_id, declared_workspace, declared_environment, inferred_workspace, inferred_environment)
    """
    steps = tutorial.get("steps", []) or []
    if not steps:
        return []

    first_requires = steps[0].get("requires", {}) or {}
    expected_workspace = str(first_requires.get("workspace", "")).strip() or "Design"
    expected_environment = str(first_requires.get("environment", "")).strip() or "Solid"

    mismatches: List[Tuple[str, str, str, str, str]] = []
    for idx, step in enumerate(steps, start=1):
        step_id = str(step.get("stepId", f"step-{idx}"))
        requires = step.get("requires", {}) or {}
        declared_workspace = str(requires.get("workspace", "")).strip()
        declared_environment = str(requires.get("environment", "")).strip()

        workspace_mismatch = (
            bool(declared_workspace) and declared_workspace.lower() != expected_workspace.lower()
        )
        environment_mismatch = (
            bool(declared_environment) and declared_environment.lower() != expected_environment.lower()
        )
        if workspace_mismatch or environment_mismatch:
            mismatches.append(
                (step_id, declared_workspace, declared_environment, expected_workspace, expected_environment)
            )

        expected_workspace, expected_environment = _estimate_step_exit_context(
            step,
            expected_workspace,
            expected_environment
        )

    return mismatches


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate tutorial highlight components against Sketch/Solid UI component JSONs."
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root (default: current directory).",
    )
    parser.add_argument(
        "--tutorial",
        default="FusionTutorialOverlay.bundle/Contents/test_data/cube_hole_tutorial.json",
        help="Tutorial JSON path relative to repo root.",
    )
    parser.add_argument(
        "--strict-labels",
        action="store_true",
        help="Fail if highlight label does not match the UI component label.",
    )
    parser.add_argument(
        "--strict-step-context",
        action="store_true",
        help="Fail if step requires.* does not match inferred step-entry context.",
    )
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    tutorial_path = (root / args.tutorial).resolve()
    sketch_path = (root / "FusionTutorialOverlay.bundle/Contents/assets/UI Images/Sketch/Sketch_UIComponents.json").resolve()
    solid_path = (root / "FusionTutorialOverlay.bundle/Contents/assets/UI Images/Solid/Solid_UIComponents.json").resolve()

    tutorial = _read_json(tutorial_path)
    sketch = _read_json(sketch_path)
    solid = _read_json(solid_path)

    allowed_keys = _build_allowed_keys(sketch) | _build_allowed_keys(solid)
    label_lookup = _build_component_label_lookup(sketch)
    label_lookup.update(_build_component_label_lookup(solid))

    invalid_components: List[Tuple[str, str]] = []
    invalid_labels: List[Tuple[str, str, str, str]] = []

    for step_id, component, label in _iter_highlights(tutorial):
        if component not in allowed_keys:
            invalid_components.append((step_id, component))
            continue

        if args.strict_labels and label is not None:
            expected_label = label_lookup.get(component)
            if expected_label and str(label) != expected_label:
                invalid_labels.append((step_id, component, str(label), expected_label))
    step_context_mismatches = _validate_step_entry_contexts(tutorial)

    if invalid_components:
        print("Invalid highlight component references found:")
        for step_id, component in invalid_components:
            print(f"  - {step_id}: {component}")

    if invalid_labels:
        print("Highlight label mismatches found:")
        for step_id, component, actual, expected in invalid_labels:
            print(f"  - {step_id}: {component} label='{actual}' expected='{expected}'")
    if step_context_mismatches:
        print("Step-entry context mismatches found:")
        for step_id, declared_ws, declared_env, inferred_ws, inferred_env in step_context_mismatches:
            print(
                f"  - {step_id}: "
                f"requires workspace='{declared_ws or '<unset>'}', environment='{declared_env or '<unset>'}' "
                f"but inferred step-entry is workspace='{inferred_ws}', environment='{inferred_env}'"
            )

    total = sum(1 for _ in _iter_highlights(tutorial))
    print(f"Checked {total} highlight component reference(s) in {tutorial_path.name}.")

    if invalid_components or invalid_labels:
        return 1

    if step_context_mismatches and args.strict_step_context:
        return 1

    print("Validation passed: all highlight component references are UI-JSON valid.")
    if step_context_mismatches and not args.strict_step_context:
        print("Step-entry context mismatches were reported as warnings (non-fatal).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
