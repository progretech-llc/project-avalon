#!/usr/bin/env python3
"""Check shared status text in a disposable GNOME Shell using synthetic state."""

import argparse
import importlib.util
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "shell_check", ROOT / "tests/qualify-shell.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
parser = argparse.ArgumentParser()
parser.add_argument("--bus-file", type=Path, required=True)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
sh = module.Shell(args.bus_file.read_text())
assert sh.evaluate("GLib.getenv('AVALON_TEST_SHELL')") == "1", (
    "Refusing the login Shell"
)
args.out.mkdir(parents=True, exist_ok=True)
fixture = (args.out / "visual-state.json").resolve()
sh.enable(module.AVALON)
sh.wait_owner(module.AVALON)
sh.evaluate(
    "Main.overview.hide(); Main.extensionManager.lookup('avalon@progretech.com').stateObj._statePath="
    + json.dumps(str(fixture))
)


def check(status, awake, label, avatar="constellation"):
    fixture.write_text(
        json.dumps(
            dict(
                schema=1,
                heartbeat=time.time(),
                status=status,
                awake=awake,
                model="fixture",
                appearance=dict(avatar=avatar, motion="full", fps=30),
                sensors=dict(gaze=[0, 0], level=0),
            )
        )
    )
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        value = sh.evaluate("""(() => {
            const e=Main.extensionManager.lookup('avalon@progretech.com').stateObj;
            return {label:e._areas[0]._status.text, galaxy:!!e._galaxy,
                overlayVisible:e._areas[0].visible,
                canvasVisible:e._areas[0]._canvas.visible,
                aboveGalaxy:!e._galaxy || e._areas.every(a=>a.get_parent().get_children().indexOf(a) >
                    a.get_parent().get_children().indexOf(e._galaxy._areas.at(-1)))};
        })()""")
        if value["label"] == label and value["galaxy"] == (avatar == "constellation"):
            assert value["overlayVisible"] and value["aboveGalaxy"], value
            assert value["canvasVisible"] == (avatar != "constellation"), value
            return value
        time.sleep(0.1)
    raise AssertionError(value)


results = {}
for status, awake, label in [
    ("idle", False, "Sleeping"),
    ("idle", True, "Ready"),
    ("listening", True, "Listening"),
    ("working", True, "Working"),
    ("speaking", True, "Speaking"),
]:
    results[label] = check(status, awake, label)
    if label in ("Sleeping", "Ready"):
        sh.capture(args.out / (label.lower() + ".png"))
sh.evaluate("""(() => {const e=Main.extensionManager.lookup('avalon@progretech.com').stateObj;
    e._build();e._galaxy._buildAreas();return true;})()""")
results["monitor_rebuild"] = check("idle", True, "Ready")
results["avatar_switch"] = check("idle", False, "Sleeping", "ethereal")
results["return_to_galaxy"] = check("idle", False, "Sleeping")
sh.enable(module.CONSTELLATION)
sh.wait_owner(module.CONSTELLATION)
assert (
    sh.evaluate(
        "Main.extensionManager.lookup('avalon@progretech.com').stateObj?._galaxy??null"
    )
    is None
)
results["exclusive_cleanup"] = True
(args.out / "results.json").write_text(json.dumps(results, indent=2) + "\n")
print(
    "Galaxy HUD: sleep/wake, live states, layer order, monitor rebuild, avatar switch and cleanup passed"
)
