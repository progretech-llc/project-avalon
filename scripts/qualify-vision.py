#!/usr/bin/env python3
"""Real single-model image round-trip with an authored fixture, never camera capture."""

import base64
import json
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from control import Controller, Runtime

assert subprocess.check_output(
    [
        "gdbus",
        "call",
        "--session",
        "--dest",
        "org.gnome.ScreenSaver",
        "--object-path",
        "/org/gnome/ScreenSaver",
        "--method",
        "org.gnome.ScreenSaver.GetActive",
    ],
    text=True,
).strip() in ("(true,)", "(false,)")
# Stop the production owner before the isolated qualification uses its single
# gateway unit. Production settings/history are untouched and restored by resume.
subprocess.run(["systemctl", "--user", "stop", "project-avalon.service"], check=True)
state = ROOT / ".runtime/vision-qualification"
state.mkdir(exist_ok=True)
link = state / "agent"
if not link.exists():
    link.symlink_to(ROOT / ".runtime/agent", target_is_directory=True)
control = None
try:
    control = Controller(state, runtime=Runtime(ROOT / ".runtime/agent"))
    control.select({"model": "qwen3.5:4b", "title": "Authored image qualification"})
    neutral = {
        "gaze": [0, 0],
        "level": 0,
        "recording": False,
        "speaking": False,
        "transcribing": False,
    }
    control.media = SimpleNamespace(
        state=neutral,
        stop=lambda: None,
        stop_audio=lambda: None,
        snapshot=lambda: None,
        vision_attachment=lambda: [
            {
                "type": "image",
                "url": "data:image/png;base64,"
                + base64.b64encode(
                    (ROOT / "static/avatars/mascot.png").read_bytes()
                ).decode(),
            }
        ],
    )
    control.chat(
        "Describe the main subject and its colors in this supplied image in one sentence. Do not use tools.",
        vision=True,
    )
    deadline = time.monotonic() + 300
    while control.active and time.monotonic() < deadline:
        time.sleep(0.2)
    result = control.snapshot()
    reply = result["messages"][-1]
    assert reply["status"] == "complete", result["status"]
    assert any(
        word in reply["text"].lower() for word in ("robot", "teal", "green", "mascot")
    ), reply["text"]
    evidence = {
        "method": "Actual Controller → pinned LampOS gateway → OpenCode → selected Ollama vision model, using original avatar PNG as an explicitly authored fixture. No camera frame or secondary VLM. Production runtime stopped before qualification and restarted afterwards.",
        "model": result["session"]["model"],
        "reply": reply["text"],
        "status": reply["status"],
    }
    (ROOT / "docs/evidence/phase-4/vision.json").write_text(
        json.dumps(evidence, indent=2) + "\n"
    )
    print(json.dumps(evidence, indent=2), flush=True)
finally:
    if control:
        control.close()
    subprocess.run(
        ["systemctl", "--user", "start", "project-avalon.service"], check=True
    )
