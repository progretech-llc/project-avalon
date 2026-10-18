#!/usr/bin/env python3
"""Explicit local-model qualification: real work continues across all avatar changes."""

import urllib.request, json, http.cookiejar, time, subprocess, importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
    {"token": json.loads((ROOT / ".runtime/control-auth.json").read_text())["entry"]},
)["csrf"]
spec = importlib.util.spec_from_file_location("shell", ROOT / "tests/qualify-shell.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sh = m.Shell((ROOT / ".runtime/test-bus").read_text())
assert sh.evaluate("GLib.getenv('AVALON_TEST_SHELL')") == "1"
sh.evaluate(
    "Main.extensionManager.lookup('avalon@progretech.com').stateObj._statePath="
    + json.dumps(str(ROOT / ".runtime/desktop/visual-state.json"))
)
api("/api/select", {"model": "qwen3-coder:30b", "title": "Avalon", "mode": "chat"})
turn = api(
    "/api/chat",
    {
        "text": "Introduce yourself as Avalon, a local AI presence, in one friendly sentence. Do not use any tools."
    },
)["turn"]
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
observed = []
for avatar in ["ethereal", "sentinel", "mascot", "abstract"]:
    state = api(
        "/api/appearance",
        {"avatar": avatar, "motion": "system", "quality": "balanced", "fps": 30},
    )
    assert state["active_turn"] == turn, (
        "The real turn ended before all avatar changes were verified"
    )
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
    time.sleep(0.28)
    value = sh.evaluate(
        "(() => {const e=Main.extensionManager.lookup('avalon@progretech.com').stateObj;return {state:e._areas[0]._effect._values.state,avatar:e._appearance.avatar,model:e._model};})()"
    )
    assert value["state"] == 2 and value["avatar"] == avatar, value
    observed.append(value)
api("/api/appearance", {"avatar": "ethereal"})
completed = False
for i in range(305):
    time.sleep(0.3)
    state = api("/api/state")
    native = sh.evaluate(
        "Main.extensionManager.lookup('avalon@progretech.com').stateObj._areas[0]._effect._values.state"
    )
    if native == 5:
        completed = True
    if not state["active_turn"]:
        assert state["messages"][-1]["status"] == "complete", state["status"]
        if completed:
            break
        time.sleep(0.3)
else:
    raise AssertionError("Real turn did not complete")
result = {
    "platform": "opencode",
    "model": state["session"]["model"],
    "real_working_state_observations": observed,
    "active_turn_preserved_across_avatar_changes": True,
    "runtime_pid_unchanged": True,
    "native_completion_observed": completed,
    "reply": state["messages"][-1]["text"],
}
(ROOT / "docs/evidence/phase-3/live-events.json").write_text(
    json.dumps(result, indent=2) + "\n"
)
print(json.dumps(result, indent=2))
assert completed
