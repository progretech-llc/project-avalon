"""Fixed local calls into the pinned LampOS services; no provider secrets in UI."""

import json
from functools import lru_cache
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / ".runtime/lampos"
UNITS = [
    "project-avalon-lampos.service",
    "project-avalon-body.service",
    "project-avalon-harness-link.service",
    "project-avalon-discovery.service",
]


def request(path, data=None, *, hal=False, method=None):
    config = json.loads((STATE / "config/config.json").read_text())
    base = "http://127.0.0.1:" + ("5001" if hal else "18895")
    req = urllib.request.Request(
        base + path,
        data=json.dumps(data).encode() if data is not None else None,
        method=method,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + config["llm_api_key"],
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            raw = response.read(4 * 1024 * 1024 + 1)
    except urllib.error.URLError as exc:
        raise ValueError(
            "LampOS service could not complete this request. Check its status and retry."
        ) from exc
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError("LampOS response exceeded the supported size")
    result = json.loads(raw)
    if not hal:
        if result.get("status") != 1:
            raise ValueError("LampOS rejected this request")
        return result.get("data")
    return result


def status():
    try:
        harness = request("/api/harness/status")
        music = request("/audio/status", hal=True)
        return {
            "running": True,
            "harness": harness,
            "music": music,
            "speech": "Local Whisper / Kokoro",
            "body": "Digital avatar; native music and Harness services; no physical motors or LEDs",
        }
    except (OSError, ValueError):
        return {
            "running": False,
            "harness": {"state": "stopped", "paired": False, "connected": False},
            "music": {},
            "speech": "Local Whisper / Kokoro",
        }


def start():
    subprocess.run(
        ["systemctl", "--user", "start", *UNITS],
        check=True,
        timeout=20,
        capture_output=True,
    )
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        value = status()
        if value["running"]:
            return value
        time.sleep(0.15)
    raise ValueError("LampOS is still starting. Check status in a moment.")


def output_volume(settings, value=None):
    target = settings.get("output", "default")
    node = "@DEFAULT_AUDIO_SINK@"
    if target != "default":
        raw = subprocess.check_output(["pw-dump"], timeout=5)
        nodes = json.loads(raw)
        match = next(
            (
                item
                for item in nodes
                if (item.get("info", {}).get("props", {}).get("node.name") == target)
            ),
            None,
        )
        if not match:
            raise ValueError("The selected speaker is unavailable")
        node = str(match["id"])
    if value is not None:
        if type(value) is not int or not 0 <= value <= 100:
            raise ValueError("Volume must be 0–100 percent")
        subprocess.run(
            ["wpctl", "set-volume", node, str(value / 100)],
            check=True,
            timeout=5,
            capture_output=True,
        )
    raw = subprocess.check_output(["wpctl", "get-volume", node], timeout=5, text=True)
    percent = round(float(raw.split()[1]) * 100)
    return {"volume": percent, "control": "PipeWire selected output", "status": "ok"}


@lru_cache(maxsize=2)
def _journal_version(path, mtime_ns, size):
    return json.loads(Path(path).read_text())


def _journal():
    path = STATE / "config/harness/results.json"
    try:
        info = path.stat()
    except FileNotFoundError:
        return {}
    if info.st_size > 64 * 1024 * 1024:
        raise ValueError("LampOS result journal exceeds its native limit")
    return _journal_version(str(path), info.st_mtime_ns, info.st_size)


def harness_result(run_id):
    for record in _journal().get("results", {}).values():
        if any(item.get("runId") == run_id for item in record.get("inputs", [])):
            return record["payload"]["fullText"]
    return None


def process_response(text, run_id):
    """Let the native OS parse and dispatch hardware markers, then hide them in UI."""
    if "[HW:" not in text:
        return text
    import re

    config = json.loads((STATE / "config/config.json").read_text())
    body = {
        "event": "agent:end",
        "context": {"platform": "avalon", "session_id": run_id, "response": text},
    }
    req = urllib.request.Request(
        "http://127.0.0.1:18895/api/agent/channel-turn",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + config["llm_api_key"],
        },
    )
    with urllib.request.urlopen(req, timeout=12) as response:
        if response.status != 200:
            raise ValueError("LampOS did not accept the action")
    return re.sub(r"\[HW:\s*[\w/-]+(?::\s*\{[^{}]*\})?\]", "", text).strip()


def stop_music():
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:5001/audio/stop",
            data=b"{}",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=2):
            pass
    except (OSError, ValueError):
        pass


def harness_pending(run_id):
    return any(
        item.get("runId") == run_id for item in _journal().get("inputs", {}).values()
    )


def harness_delivery(run_id):
    inputs = _journal().get("inputs", {})
    entry = next(
        (item for item in inputs.values() if item.get("runId") == run_id), None
    )
    if entry is None:
        return None
    reply = request(
        "/api/harness/request",
        {"type": "receipt.get", "idempotencyKey": entry["idempotencyKey"]},
    )
    return reply.get("receipt")
