"""Plugin tutorial loader service for fetching latest tutorial from webhook."""

import json
import socket
import urllib.error
import urllib.request


WEBHOOK_URL = "https://narwhjorl.app.n8n.cloud/webhook/get-latest-tutorial"


def fetch_latest_tutorial(timeout_seconds=15):
    """
    Fetch latest tutorial manifest from cloud webhook.

    Returns:
        {"ok": True, "data": <parsed_json>}
        or
        {"ok": False, "error": <message>}
    """
    request = urllib.request.Request(
        WEBHOOK_URL,
        method="GET",
        headers={"Accept": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status = getattr(response, "status", None) or response.getcode()
            if status < 200 or status >= 300:
                return {"ok": False, "error": f"Tutorial endpoint returned HTTP {status}"}

            raw = response.read()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("utf-8", errors="replace")

            try:
                payload = json.loads(text)
            except Exception:
                return {"ok": False, "error": "Invalid JSON response from tutorial endpoint"}

            return {"ok": True, "data": payload}

    except urllib.error.HTTPError as exc:
        return {"ok": False, "error": f"Tutorial endpoint returned HTTP {exc.code}"}
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, socket.timeout):
            return {"ok": False, "error": f"Request timed out after {int(timeout_seconds)}s"}
        return {"ok": False, "error": f"Network error while loading tutorial: {reason or 'unknown'}"}
    except socket.timeout:
        return {"ok": False, "error": f"Request timed out after {int(timeout_seconds)}s"}
    except Exception as exc:
        return {"ok": False, "error": f"Unexpected error while loading tutorial: {exc}"}
