"""Plugin tutorial loader service (temporary local-only mode)."""

import json
import os

_DEFAULT_CONFIG = {
    "localPath": "test_data/mug_tutorial.json"
}


def _get_data_source_config(contents_dir):
    """Load local tutorial config and return merged defaults."""
    config = dict(_DEFAULT_CONFIG)
    config_path = os.path.join(contents_dir, "config", "tutorial_source.json")

    if not os.path.exists(config_path):
        return config

    with open(config_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    if isinstance(loaded, dict):
        config.update(loaded)
    return config


def _load_local_tutorial(contents_dir, local_path):
    """Load tutorial data from a local JSON path under Contents."""
    safe_relative = str(local_path or _DEFAULT_CONFIG["localPath"]).replace("\\", "/").lstrip("/").strip()
    local_file_path = os.path.normpath(os.path.join(contents_dir, safe_relative))
    contents_root = os.path.normpath(contents_dir)

    if os.path.commonpath([contents_root, local_file_path]) != contents_root:
        return {"ok": False, "error": f"Local tutorial path is outside Contents: {safe_relative}"}

    try:
        with open(local_file_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return {"ok": True, "data": payload}
    except FileNotFoundError:
        return {"ok": False, "error": f"Local tutorial file not found: {safe_relative}"}
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"Invalid JSON in local tutorial file {safe_relative}: {exc}"}
    except Exception as exc:
        return {"ok": False, "error": f"Unexpected error while loading local tutorial {safe_relative}: {exc}"}


def fetch_latest_tutorial(timeout_seconds=15):
    """
    Load tutorial manifest from local test data (temporary mode).

    Returns:
        {"ok": True, "data": <parsed_json>}
        or
        {"ok": False, "error": <message>}
    """
    _ = timeout_seconds  # Kept for call-site compatibility.
    contents_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        config = _get_data_source_config(contents_dir)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"Invalid JSON in config/tutorial_source.json: {exc}"}
    except Exception as exc:
        return {"ok": False, "error": f"Failed to read config/tutorial_source.json: {exc}"}

    return _load_local_tutorial(contents_dir, config.get("localPath", _DEFAULT_CONFIG["localPath"]))
