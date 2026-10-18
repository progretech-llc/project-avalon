#!/usr/bin/env python3
"""Local synthesized speech → ASR → actual selected agent → PCM; no physical capture."""

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs/evidence/phase-4"
OUT.mkdir(parents=True, exist_ok=True)


def speech(text):
    proc = subprocess.Popen(
        [str(ROOT / ".media-venv/bin/python"), str(ROOT / "media_worker.py"), "speak"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        pcm, errors = proc.communicate(text.encode(), timeout=40)
        assert proc.returncode == 0 and len(pcm) > 16000, errors.decode()[-500:]
        return pcm
    finally:
        from media import terminate

        terminate(proc)


command = "Say hello in one sentence."
source = speech(command)
raw = subprocess.run(
    [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "s16le",
        "-ar",
        "22050",
        "-ac",
        "1",
        "-i",
        "pipe:0",
        "-f",
        "s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        "pipe:1",
    ],
    input=source,
    stdout=subprocess.PIPE,
    check=True,
).stdout
transcription = subprocess.run(
    [str(ROOT / ".media-venv/bin/python"), str(ROOT / "media_worker.py"), "transcribe"],
    input=raw,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    timeout=60,
    check=True,
)
text = json.loads(transcription.stdout)["text"]
assert "hello" in text.lower() and "sentence" in text.lower(), text
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True)
    page = b.new_page(viewport={"width": 1440, "height": 1000})
    page.goto(
        "http://127.0.0.1:8766/#entry="
        + json.loads((ROOT / ".runtime/control-auth.json").read_text())["entry"]
    )
    page.locator("#access-note").wait_for(state="hidden")
    before = page.request.get("http://127.0.0.1:8766/api/state").json()
    assert not before["active_turn"]
    headers = {"Origin": "http://127.0.0.1:8766", "X-CSRF-Token": before["csrf"]}
    pid = subprocess.check_output(
        [
            "systemctl",
            "--user",
            "show",
            "project-avalon-runtime.service",
            "-p",
            "MainPID",
            "--value",
        ],
        text=True,
    ).strip()
    request = page.request.post(
        "http://127.0.0.1:8766/api/chat", data={"text": text}, headers=headers
    )
    assert request.status == 202, request.text()
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        after = page.request.get("http://127.0.0.1:8766/api/state").json()
        if not after["active_turn"]:
            break
        time.sleep(0.25)
    assert after["messages"][-1]["status"] == "complete", after["status"]
    assert before["session"]["id"] == after["session"]["id"]
    assert (
        subprocess.check_output(
            [
                "systemctl",
                "--user",
                "show",
                "project-avalon-runtime.service",
                "-p",
                "MainPID",
                "--value",
            ],
            text=True,
        ).strip()
        == pid
    )
    response = after["messages"][-1]["text"]
    generated = speech(response)
    locked_operations = []
    if after["devices"]["locked"]:
        for action in ("record", "camera_on", "read_reply"):
            r = page.request.post(
                "http://127.0.0.1:8766/api/media",
                data={"action": action},
                headers=headers,
            )
            assert r.status == 400 and "locked" in r.json()["error"].lower()
            locked_operations.append(action)
    for width, height, name in [(1440, 1000, "desktop"), (390, 844, "mobile")]:
        page.set_viewport_size({"width": width, "height": height})
        page.locator('[data-page="devices"]').click()
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / f"devices-{name}.png"), full_page=True)
        assert not page.evaluate("document.documentElement.scrollWidth>innerWidth")
    inventory = page.request.get("http://127.0.0.1:8766/api/devices").json()
    evidence = {
        "method": "Synthesized English fixture, actual CPU recognition, real selected LampOS/OpenCode/Ollama turn, generated response PCM. Physical microphone/speaker/camera not exercised while Ubuntu is locked.",
        "command": command,
        "transcript": text,
        "reply": response,
        "model": after["session"]["model"],
        "same_session_and_runtime": True,
        "source_pcm_bytes": len(source),
        "response_pcm_bytes": len(generated),
        "response_sha256": hashlib.sha256(generated).hexdigest(),
        "locked_operations_denied": locked_operations,
        "device_counts": {k: len(v) for k, v in inventory.items()},
        "capture_left_off": not any(
            after["devices"][k] for k in ("recording", "camera", "speaking")
        ),
    }
    (OUT / "media.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))
    b.close()
