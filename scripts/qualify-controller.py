#!/usr/bin/env python3
"""Explicit live qualification; uses synthetic data in the installed local service."""

import urllib.request, json, http.cookiejar, time, subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
base = "http://127.0.0.1:8766"
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
)
csrf = ""


def api(path, data=None):
    r = opener.open(
        urllib.request.Request(
            base + path,
            data=None if data is None else json.dumps(data).encode(),
            headers={
                "Origin": base,
                "Content-Type": "application/json",
                "X-CSRF-Token": csrf,
            },
        ),
        timeout=60,
    )
    return json.load(r)


for i in range(30):
    try:
        csrf = api(
            "/api/auth",
            {
                "token": json.loads((root / ".runtime/control-auth.json").read_text())[
                    "entry"
                ]
            },
        )["csrf"]
        break
    except Exception:
        time.sleep(0.5)
for i in range(30):
    s = api("/api/state")
    if s["status"] == "idle":
        break
    time.sleep(0.5)
workspace = root / ".runtime/qualification-workspace"
workspace.mkdir(exist_ok=True)
for name in ("proof.txt", "denied.txt"):
    (workspace / name).unlink(missing_ok=True)
results = {}


def turn(text, key):
    api("/api/chat", {"text": text})
    for i in range(305):
        time.sleep(1)
        s = api("/api/state")
        if not s["active_turn"]:
            print(key, s["status"], s["messages"][-1]["text"][:400], flush=True)
            assert s["messages"][-1]["status"] == "complete", s["status"]
            results[key] = {
                "status": s["messages"][-1]["status"],
                "reply": s["messages"][-1]["text"],
            }
            return s
    raise RuntimeError("Turn timed out")


s = api(
    "/api/select",
    {
        "model": "qwen3-coder:30b",
        "title": "Phase 2 qualification",
        "workspace": str(workspace),
        "mode": "edit",
        "cancel_current": True,
    },
)
sid = s["session"]["id"]
turn(
    "Use your write or apply_patch tool to create proof.txt in the current workspace with exactly AVALON_EDIT_OK. Do not run shell commands. Then report completion.",
    "allowed_edit",
)
results["allowed_file"] = (
    (workspace / "proof.txt").read_text()
    if (workspace / "proof.txt").exists()
    else None
)
assert results["allowed_file"] and "AVALON_EDIT_OK" in results["allowed_file"]
api(
    "/api/select",
    {"session_id": sid, "mode": "read", "commands": False, "cancel_current": True},
)
turn(
    "Permissions have now changed. Attempt to create denied.txt with the write or apply_patch tool, with text SHOULD_NOT_EXIST. Do not use shell commands or alternatives. If access is denied, say DENIED.",
    "revoked_edit",
)
assert not (workspace / "denied.txt").exists()
results["revoked_file_absent"] = True
api(
    "/api/chat",
    {
        "text": "Write a very long detailed explanation of sorting algorithms, covering each algorithm step by step."
    },
)
time.sleep(2)
api("/api/stop", {})
before = api("/api/state")
time.sleep(3)
after = api("/api/state")
assert before["active_turn"] is None and after["active_turn"] is None
assert before["messages"][-1]["status"] == "cancelled"
assert before["messages"] == after["messages"]
result = subprocess.run(
    ["systemctl", "--user", "is-active", "project-avalon-runtime.service"],
    capture_output=True,
    text=True,
)
assert result.stdout.strip() == "inactive"
results["cancellation"] = {
    "runtime": result.stdout.strip(),
    "stale_events": False,
    "partial_status": before["messages"][-1]["status"],
}
api("/api/select", {"session_id": sid, "mode": "chat", "commands": False})
results["reconnected"] = True
(root / "docs/evidence/phase-2").mkdir(parents=True, exist_ok=True)
(root / "docs/evidence/phase-2/runtime.json").write_text(
    json.dumps(results, indent=2) + "\n"
)
print(
    "QUALIFIED",
    json.dumps(
        {k: v for k, v in results.items() if k not in ("allowed_edit", "revoked_edit")}
    ),
    flush=True,
)
