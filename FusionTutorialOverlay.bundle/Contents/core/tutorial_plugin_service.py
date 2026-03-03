"""Plugin tutorial bootstrap service for n8n scan webhooks."""

import json
import socket
import urllib.error
import urllib.request


START_SCAN_URL = "https://narwhjorl.app.n8n.cloud/webhook/start-scan"
SCAN_STATUS_URL = "https://narwhjorl.app.n8n.cloud/webhook/scan-status"


def _decode_json_response(response_body: bytes, invalid_json_msg: str):
    """Decode bytes as UTF-8 JSON payload."""
    try:
        text = response_body.decode("utf-8")
    except UnicodeDecodeError:
        text = response_body.decode("utf-8", errors="replace")

    try:
        return {"ok": True, "data": json.loads(text)}
    except Exception:
        return {"ok": False, "error": invalid_json_msg}


def _http_json_request(request: urllib.request.Request, timeout_seconds: int, invalid_json_msg: str, error_prefix: str):
    """Send an HTTP request and return normalized JSON result."""
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status = getattr(response, "status", None) or response.getcode()
            if status < 200 or status >= 300:
                return {"ok": False, "error": f"{error_prefix} returned HTTP {status}"}

            raw = response.read()
            return _decode_json_response(raw, invalid_json_msg)

    except urllib.error.HTTPError as exc:
        return {"ok": False, "error": f"{error_prefix} returned HTTP {exc.code}"}
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, socket.timeout):
            return {"ok": False, "error": f"{error_prefix} timed out after {int(timeout_seconds)}s"}
        return {"ok": False, "error": f"Network error calling {error_prefix}: {reason or 'unknown'}"}
    except socket.timeout:
        return {"ok": False, "error": f"{error_prefix} timed out after {int(timeout_seconds)}s"}
    except Exception as exc:
        return {"ok": False, "error": f"Unexpected error calling {error_prefix}: {exc}"}


def start_scan(username: str, timeout_seconds=60):
    """Start n8n tutorial scan and return tutorial payload."""
    payload = json.dumps({"username": username}).encode("utf-8")
    request = urllib.request.Request(
        START_SCAN_URL,
        method="POST",
        data=payload,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json"
        },
    )
    return _http_json_request(
        request=request,
        timeout_seconds=timeout_seconds,
        invalid_json_msg="Invalid JSON response from start-scan endpoint",
        error_prefix="start-scan endpoint",
    )


def get_scan_status(timeout_seconds=10):
    """Fetch scan statusCode for debug/progress display."""
    request = urllib.request.Request(
        SCAN_STATUS_URL,
        method="GET",
        headers={"Accept": "application/json"},
    )
    result = _http_json_request(
        request=request,
        timeout_seconds=timeout_seconds,
        invalid_json_msg="Invalid JSON response from scan-status endpoint",
        error_prefix="scan-status endpoint",
    )
    if not result.get("ok"):
        return result

    data = result.get("data")
    if not isinstance(data, dict):
        return {"ok": False, "error": "scan-status response must be a JSON object"}

    status_code = data.get("statusCode")
    if not isinstance(status_code, int):
        return {"ok": False, "error": "scan-status response missing integer statusCode"}

    return {"ok": True, "statusCode": status_code}
