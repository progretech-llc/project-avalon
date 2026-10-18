#!/usr/bin/env python3
"""Real-shell state and background checks, isolated compositor only."""

import importlib.util, json, time
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "shell", Path(__file__).with_name("qualify-shell.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
shell = module.Shell(Path(".runtime/test-bus").read_text())
assert shell.evaluate("GLib.getenv('AVALON_TEST_SHELL')") == "1"
root = Path(".runtime/shell-state/project-avalon")
root.mkdir(parents=True, exist_ok=True)
path = root / "visual-state.json"
values = {}
for status, expected in [
    ("disconnected", 0),
    ("idle", 1),
    ("working", 2),
    ("writing", 3),
    ("executing", 4),
    ("completed", 5),
    ("failed", 6),
    ("cancelled", 7),
    ("switching", 8),
]:
    path.write_text(
        json.dumps({"schema": 1, "status": status, "heartbeat": time.time()})
    )
    time.sleep(0.35)
    value = shell.evaluate(
        "Main.extensionManager.lookup('avalon@progretech.com').stateObj._activity"
    )
    assert value == expected, (status, value)
    values[status] = value
path.write_text(
    json.dumps({"schema": 1, "status": "working", "heartbeat": time.time() - 20})
)
time.sleep(0.35)
assert (
    shell.evaluate(
        "Main.extensionManager.lookup('avalon@progretech.com').stateObj._activity"
    )
    == 0
)
shell.evaluate(
    """(() => {const s=new imports.gi.Gio.Settings({schema_id:'org.gnome.desktop.background'});s.set_string('picture-uri','file:///mnt/PT-Storage/Tools%20%26%20Assets/Constellation/data/progretech-constellation.png');s.set_string('picture-uri-dark','file:///home/test/custom.png');return true;})()"""
)
shell.call("DisableExtension", module.GLib.Variant("(s)", (module.AVALON,)))
result = shell.evaluate(
    """(() => {const s=new imports.gi.Gio.Settings({schema_id:'org.gnome.desktop.background'});return {light:s.get_string('picture-uri'),default:s.get_default_value('picture-uri').deep_unpack(),dark:s.get_string('picture-uri-dark')};})()"""
)
assert (
    result["light"] == result["default"]
    and result["dark"] == "file:///home/test/custom.png"
), result
shell.enable(module.AVALON)
shell.wait_owner(module.AVALON)
report = {
    "states": values,
    "stale_disconnected": True,
    "legacy_background_restore": result,
    "custom_preserved": True,
}
Path("docs/evidence/phase-2/shell/states.json").write_text(
    json.dumps(report, indent=2) + "\n"
)
print(json.dumps(report, indent=2))
