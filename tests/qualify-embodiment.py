#!/usr/bin/env python3
"""All avatar/state/quality combinations and safety branches in isolated Shell."""

import importlib.util, json, time, statistics
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "shell", Path(__file__).with_name("qualify-shell.py")
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sh = m.Shell(Path(".runtime/test-bus").read_text())
assert sh.evaluate("GLib.getenv('AVALON_TEST_SHELL')") == "1"
sh.enable(m.AVALON)
sh.wait_owner(m.AVALON)
path = Path(".runtime/shell-state/project-avalon/visual-state.json").resolve()
path.parent.mkdir(parents=True, exist_ok=True)
sh.evaluate(
    "Main.extensionManager.lookup('avalon@progretech.com').stateObj._statePath="
    + json.dumps(str(path))
)
states = {
    "disconnected": 0,
    "idle": 1,
    "working": 2,
    "writing": 3,
    "executing": 4,
    "completed": 5,
    "failed": 6,
    "cancelled": 7,
    "switching": 8,
}
out = Path("docs/evidence/phase-3")
out.mkdir(parents=True, exist_ok=True)
settings = {"avatar": "ethereal", "quality": "balanced", "fps": 30, "motion": "full"}


def write(status="idle", **appearance):
    settings.update(appearance)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            {
                "schema": 1,
                "status": status,
                "heartbeat": time.time(),
                "appearance": settings,
                "model": "qualification:local",
            }
        )
    )
    temporary.replace(path)


def value(code):
    return sh.evaluate(
        "(() => {const e=Main.extensionManager.lookup('avalon@progretech.com').stateObj;return "
        + code
        + ";})()"
    )


def wait(predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.005)
    raise AssertionError("Renderer did not apply fixture")


latencies = []
matrix = []
for index, avatar in enumerate(("ethereal", "sentinel", "mascot", "abstract")):
    for status, expected in states.items():
        start = time.monotonic()
        write(status, avatar=avatar)
        wait(
            lambda: (
                value("e._areas[0]._effect._values.state") == expected
                and value("e._areas[0]._effect._values.avatar") == index
            )
        )
        latencies.append((time.monotonic() - start) * 1000)
        matrix.append([avatar, status])
    write("idle", avatar=avatar)
    time.sleep(0.3)
    sh.evaluate("Main.messageTray._banner?.close(); true")
    sh.capture(out / f"wallpaper-{avatar}.png")
for quality, index in [("economy", 0), ("balanced", 1), ("high", 2)]:
    write("idle", quality=quality)
    wait(lambda: value("e._areas[0]._effect._values.quality") == index)
frame_rates = {}
for fps in (15, 30, 60):
    write("working", avatar="ethereal", quality="balanced", fps=fps, motion="full")
    wait(lambda: value("e._timerFps") == fps)
    start = time.monotonic()
    frames = value("e._frames")
    time.sleep(1.1)
    frame_rates[str(fps)] = (value("e._frames") - frames) / (time.monotonic() - start)
    assert frame_rates[str(fps)] <= fps * 1.12
    if fps <= 30:
        assert frame_rates[str(fps)] >= fps * 0.85
write("idle", fps=30)
write("idle", quality="balanced", motion="reduced")
wait(lambda: value("e._appearance.motion") == "reduced")
time.sleep(0.3)
frames = value("e._frames")
time.sleep(1)
assert value("e._frames") == frames, "Reduced motion kept drawing"
write("completed")
wait(lambda: value("e._areas[0]._effect._values.state") == 5)
# Shield renderer branch is simulated only in this disposable test Shell.
sh.evaluate(
    "Object.defineProperty(Main.screenShield,'locked',{get:()=>true,configurable:true});true"
)
write("working", motion="full")
time.sleep(0.3)
frames = value("e._frames")
time.sleep(0.3)
assert value("e._frames") == frames
assert value("e._areas.every(a=>!a.visible)")
sh.evaluate("delete Main.screenShield.locked;true")
wait(lambda: value("e._areas.every(a=>a.visible)"))
sh.evaluate("Main.overview.show();true")
time.sleep(0.7)
frames = value("e._frames")
time.sleep(0.3)
assert value("e._frames") == frames
sh.evaluate("Main.overview.hide();true")
time.sleep(0.8)
write("working")
time.sleep(0.3)
path.write_text("{malformed")
wait(lambda: value("e._activity") == 0)
write("working")
time.sleep(0.3)
d = json.loads(path.read_text())
d["heartbeat"] = time.time() - 20
path.write_text(json.dumps(d))
wait(lambda: value("e._activity") == 0)
for malformed in (
    "null",
    "[]",
    json.dumps(
        {
            "schema": 1,
            "heartbeat": time.time(),
            "status": "toString",
            "appearance": {"avatar": "__proto__"},
        }
    ),
    "x" * 5000,
):
    path.write_text(malformed)
    wait(lambda: value("e._activity") == 0)
    assert value("e._appearance.avatar") == "ethereal"
    time.sleep(0.22)
write("idle", avatar="ethereal")
time.sleep(0.3)
report = {
    "matrix": matrix,
    "quality_modes": 3,
    "frame_rates": frame_rates,
    "reduced_motion_stops_frames": True,
    "reduced_motion_keeps_state_updates": True,
    "simulated_lock_hides_and_pauses": True,
    "overview_pauses": True,
    "malformed_and_stale_disconnect": True,
    "event_to_uniform_ms": latencies,
    "p95_ms": sorted(latencies)[int(len(latencies) * 0.95)],
    "measurement": "atomic sanitized fixture write to applied native shader state; 5ms polling; actual physical scanout not claimed",
}
(out / "renderer.json").write_text(json.dumps(report, indent=2) + "\n")
print(
    json.dumps(
        {k: v for k, v in report.items() if k not in ("matrix", "event_to_uniform_ms")},
        indent=2,
    )
)
assert report["p95_ms"] < 500
