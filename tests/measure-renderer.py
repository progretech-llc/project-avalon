#!/usr/bin/env python3
"""CPU/RSS/frame accounting in a guarded disposable compositor, never login Shell."""

import importlib.util, json, os, time, subprocess
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "qualification", Path(__file__).with_name("qualify-shell.py")
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sh = m.Shell(Path(".runtime/test-bus").read_text())
assert sh.evaluate("GLib.getenv('AVALON_TEST_SHELL')") == "1"
pid = sh.evaluate("new imports.gi.Gio.Credentials().get_unix_pid()")
sh.evaluate(
    "(() => {if(globalThis.paintSignal)global.stage.disconnect(globalThis.paintSignal);globalThis.paintCount=0;globalThis.paintSignal=global.stage.connect('after-paint',()=>{globalThis.paintCount++;});return true})()"
)


def proc():
    fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    rss = next(
        int(line.split()[1]) * 1024
        for line in Path(f"/proc/{pid}/status").read_text().splitlines()
        if line.startswith("VmRSS:")
    )
    proportional = next(
        int(line.split()[1]) * 1024
        for line in Path(f"/proc/{pid}/smaps_rollup").read_text().splitlines()
        if line.startswith("Pss:")
    )
    return {
        "pss_bytes": proportional,
        "cpu_seconds": (int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK"),
        "rss_bytes": rss,
        "paint": sh.evaluate("globalThis.paintCount"),
    }


def sample(seconds):
    a = proc()
    start = time.monotonic()
    time.sleep(seconds)
    elapsed = time.monotonic() - start
    b = proc()
    return {
        "seconds": elapsed,
        "cpu_percent_one_core": 100 * (b["cpu_seconds"] - a["cpu_seconds"]) / elapsed,
        "stage_paints_per_second": (b["paint"] - a["paint"]) / elapsed,
        "rss_bytes": b["rss_bytes"],
        "pss_bytes": b["pss_bytes"],
    }


sh.call("DisableExtension", m.GLib.Variant("(s)", (m.AVALON,)))
time.sleep(3)
assert sh.snapshot()["avalon"]["count"] == 0
baseline = sample(30)
print("baseline", json.dumps(baseline), flush=True)
path = Path(".runtime/shell-state/project-avalon/visual-state.json")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(
    json.dumps(
        {
            "schema": 1,
            "heartbeat": time.time() + 5,
            "status": "idle",
            "appearance": {
                "avatar": "ethereal",
                "quality": "balanced",
                "fps": 30,
                "motion": "full",
            },
        }
    )
)
sh.enable(m.AVALON)
sh.wait_owner(m.AVALON)
time.sleep(3)
# Refresh only the heartbeat; no fabricated busy activity is used in this idle test.
sh.evaluate(
    "Main.extensionManager.lookup('avalon@progretech.com').stateObj._statePath="
    + json.dumps(str(Path(".runtime/desktop/visual-state.json").resolve()))
)
# Shader/driver startup is excluded from the steady idle sample, retained in
# the separate first-cold sample evidence. Keep all consecutive intervals.
time.sleep(10)
trials = []
for index in range(3):
    trials.append(sample(30))
    print("active interval", index + 1, json.dumps(trials[-1]), flush=True)
active = dict(trials[-1])
active["seconds"] = sum(t["seconds"] for t in trials)
for field in ("cpu_percent_one_core", "stage_paints_per_second"):
    active[field] = sum(t[field] * t["seconds"] for t in trials) / active["seconds"]
print("active", json.dumps(active), flush=True)
results = {
    "compositor_pid": pid,
    "resolution": sh.evaluate("Main.layoutManager.monitors.map(m=>[m.width,m.height])"),
    "monitor_count": 1,
    "quality": "balanced",
    "avatar": "ethereal",
    "frame_limit": 30,
    "compositor": "GNOME Shell 50.1, isolated native headless GPU compositor",
    "frame_metric": "Clutter Stage after-paint; not physical scanout",
    "cpu_metric": "process user+system ticks; 100% is one CPU core; active minus disabled baseline",
    "baseline": baseline,
    "active": active,
    "active_intervals": trials,
    "incremental_cpu_percent_one_core": active["cpu_percent_one_core"]
    - baseline["cpu_percent_one_core"],
    "logical_cpus": os.cpu_count(),
}
Path("docs/evidence/phase-3").mkdir(parents=True, exist_ok=True)
Path("docs/evidence/phase-3/performance.json").write_text(
    json.dumps(results, indent=2) + "\n"
)
print(json.dumps(results, indent=2), flush=True)
