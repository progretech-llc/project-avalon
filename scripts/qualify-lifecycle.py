#!/usr/bin/env python3
"""Explicit live model-switch/restart check using a synthetic interrupted turn."""

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


csrf = api(
    "/api/auth",
    {"token": json.loads((root / ".runtime/control-auth.json").read_text())["entry"]},
)["csrf"]
s = api("/api/state")
assert s["active_turn"] is None
sid = s["session"]["id"]
original = s["session"]["model"]
models = api("/api/models")["models"]
alternative = min(
    [m for m in models if m["tools"] and m["name"] != original], key=lambda m: m["size"]
)["name"]
oldpid = int(
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
    )
)
api("/api/chat", {"text": "Explain binary search in detail for a student."})
time.sleep(2)
group = subprocess.check_output(
    [
        "systemctl",
        "--user",
        "show",
        "project-avalon-runtime.service",
        "-p",
        "ControlGroup",
        "--value",
    ],
    text=True,
).strip()
children = [
    pid
    for pid in Path("/sys/fs/cgroup" + group + "/cgroup.procs").read_text().split()
    if int(pid) != oldpid
]
assert children, "No live CLI child found for cancellation qualification"

s = api(
    "/api/select",
    {
        "model": alternative,
        "cancel_current": True,
        "title": "Model switching qualification",
    },
)
assert s["session"]["model"] == alternative and s["active_turn"] is None
assert not Path(f"/proc/{oldpid}").exists()
assert all(not Path("/proc/" + pid).exists() for pid in children)
api("/api/select", {"session_id": sid, "mode": "chat", "commands": False})
before = api("/api/state")
assert before["messages"][-1]["status"] == "cancelled"
subprocess.run(["systemctl", "--user", "restart", "project-avalon.service"], check=True)
for i in range(40):
    try:
        after = api("/api/state")
        if after["status"] == "idle":
            break
    except Exception:
        pass
    time.sleep(0.5)
assert after["active_turn"] is None and after["session"]["id"] == sid
assert after["messages"] == before["messages"]
results = {
    "model_switch": {
        "from": original,
        "to": alternative,
        "returned_to": after["session"]["model"],
        "old_gateway_reaped": True,
        "old_children_reaped": len(children),
        "cancelled": True,
    },
    "service_restart": {
        "selected_session_retained": True,
        "messages_retained": True,
        "no_replayed_turn": True,
    },
}
(root / "docs/evidence/phase-2/lifecycle.json").write_text(
    json.dumps(results, indent=2) + "\n"
)
print(json.dumps(results, indent=2))
