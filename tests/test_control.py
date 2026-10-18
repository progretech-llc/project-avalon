import json
import queue
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from control import Catalog, Conflict, Controller, Unavailable


class FakeCatalog:
    def models(self, refresh=False):
        return [
            {
                "name": "small:local",
                "tools": True,
                "size": 100,
                "vision": False,
                "capabilities": ["completion", "tools"],
            },
            {
                "name": "large:local",
                "tools": True,
                "size": 200,
                "vision": False,
                "capabilities": ["completion", "tools"],
            },
        ]

    def choose(self):
        return "small:local"

    def validate(self, name, mode):
        if name not in ("small:local", "large:local"):
            raise ValueError("Model missing")
        return next(m for m in self.models() if m["name"] == name)

    def platforms(self):
        return [
            {"id": "opencode", "available": True, "name": "OpenCode"},
            {"id": "codex", "available": False, "reason": "Restricted bridge required"},
        ]


class FakeSocket:
    def __init__(self):
        self.frames = queue.Queue()
        self.sent = []
        self.closed = False

    def send(self, value):
        self.sent.append(json.loads(value))

    def recv(self, timeout=None):
        item = self.frames.get(timeout=2)
        if isinstance(item, Exception):
            raise item
        return json.dumps(item)

    def close(self):
        self.closed = True

    def emit(self, kind, part=None, request=None):
        identifier = request or self.sent[-1]["id"]
        self.frames.put(
            {
                "type": kind,
                "part": part or {},
                "request_id": identifier,
                "run_id": identifier,
            }
        )


class FakeRuntime:
    def __init__(self):
        self.starts = 0
        self.stops = 0
        self.current = None
        self.live = 0
        self.maximum = 0
        self.saved = None

    def start(self):
        assert self.live == 0, "Started before previous runtime stopped"
        self.starts += 1
        self.live = 1
        self.maximum = max(self.maximum, self.live)
        self.current = FakeSocket()
        return self.current

    def stop(self):
        self.stops += 1
        self.live = 0
        if self.current:
            self.current.close()

    def native(self):
        return self.saved

    def restore(self, raw):
        self.saved = raw


class ControlTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.runtime = FakeRuntime()
        self.configure = patch("control.configure", return_value={})
        self.configure.start()
        self.control = Controller(
            Path(self.directory.name), FakeCatalog(), self.runtime
        )

    def tearDown(self):
        self.control.close()
        self.configure.stop()
        self.directory.cleanup()

    def connect(self, **data):
        return self.control.select({"model": "small:local", **data})

    def wait(self, predicate):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.01)
        self.fail("State transition did not finish")

    def test_one_turn_and_one_runtime_owner(self):
        self.assertEqual(self.control.state.stat().st_mode & 0o777, 0o700)
        self.connect()
        self.control.chat("first")
        with self.assertRaises(Conflict):
            self.control.chat("second")
        with self.assertRaises(Conflict):
            self.control.select({"model": "large:local"})
        self.assertEqual(self.runtime.maximum, 1)
        self.assertEqual(
            len(
                [m for m in self.control.snapshot()["messages"] if m["role"] == "user"]
            ),
            1,
        )

    def test_switch_fences_late_events_from_cancelled_turn(self):
        self.connect()
        self.control.chat("old")
        old = self.runtime.current
        request = old.sent[-1]["id"]
        self.control.select({"model": "large:local", "cancel_current": True})
        self.control.chat("new")
        new = self.runtime.current
        old.emit("text", {"text": "stale secret"}, request)
        old.emit("session.idle", request=request)
        new.emit("text", {"text": "fresh answer"})
        new.emit("session.idle")
        self.wait(lambda: self.control.active is None)
        self.assertEqual(
            self.control.snapshot()["messages"][-1]["text"], "fresh answer"
        )
        self.assertEqual(self.control.snapshot()["session"]["model"], "large:local")
        self.assertEqual(self.runtime.maximum, 1)

    def test_invalid_or_blocked_target_keeps_current_runtime(self):
        self.connect()
        starts = self.runtime.starts
        stops = self.runtime.stops
        with self.assertRaises(ValueError):
            self.control.select({"model": "missing"})
        with self.assertRaises(Unavailable):
            self.control.select({"platform": "codex"})
        self.assertEqual((self.runtime.starts, self.runtime.stops), (starts, stops))
        self.assertEqual(self.control.status, "idle")

    def test_tool_state_is_based_on_explicit_event(self):
        self.connect()
        self.control.chat("edit")
        self.runtime.current.emit(
            "tool_use", {"tool": "edit", "state": {"status": "running"}}
        )
        self.wait(lambda: self.control.status == "writing")
        self.assertEqual(
            json.loads(self.control.visual.read_text())["status"], "writing"
        )
        self.runtime.current.emit("text", {"text": "done"})
        self.runtime.current.emit("session.idle")
        self.wait(lambda: self.control.active is None)
        self.assertEqual(self.control.snapshot()["messages"][-1]["status"], "complete")

    def test_cancel_marks_partial_response_and_requires_reconnect(self):
        self.connect()
        self.control.chat("long")
        self.runtime.current.emit("text", {"text": "partial"})
        self.wait(lambda: self.control.snapshot()["messages"][-1]["text"] == "partial")
        self.control.cancel()
        self.assertEqual(self.control.snapshot()["messages"][-1]["status"], "cancelled")
        with self.assertRaises(Conflict):
            self.control.chat("do not replay")

    def test_failed_connection_is_never_success(self):
        self.connect()
        self.control.chat("fail")
        self.runtime.current.frames.put(ConnectionError())
        self.wait(lambda: self.control.status == "failed")
        self.assertEqual(self.control.snapshot()["messages"][-1]["status"], "failed")

    def test_session_history_and_native_id_survive_controller_restart(self):
        self.connect()
        identifier = self.control.selected
        self.control.chat("remember")
        self.runtime.saved = '{"session_id":"native-123"}'
        self.runtime.current.emit("text", {"text": "saved answer"})
        self.runtime.current.emit("session.idle")
        self.wait(lambda: self.control.active is None)
        self.control.close()
        other = Controller(Path(self.directory.name), FakeCatalog(), FakeRuntime())
        try:
            self.assertEqual(other.selected, identifier)
            self.assertIsNone(other.active)
            self.assertEqual(other.snapshot()["messages"][-1]["text"], "saved answer")
            other.resume()
            self.assertEqual(other.runtime.saved, '{"session_id":"native-123"}')
        finally:
            other.close()

    def test_appearance_changes_do_not_restart_or_cancel_a_turn(self):
        self.connect()
        self.control.chat("continue")
        identifier = self.control.active["id"]
        starts, stops = self.runtime.starts, self.runtime.stops
        self.assertTrue(self.control.appearance["idle_saver"])
        self.control.set_appearance({"idle_saver": False})
        self.assertFalse(self.control.store.get("appearance")["idle_saver"])
        for avatar in ("ethereal", "sentinel", "mascot", "abstract"):
            state = self.control.set_appearance({"avatar": avatar, "motion": "reduced"})
            self.assertEqual(state["active_turn"], identifier)
            self.assertEqual((self.runtime.starts, self.runtime.stops), (starts, stops))
            self.assertEqual(
                json.loads(self.control.visual.read_text())["appearance"]["avatar"],
                avatar,
            )
        self.assertEqual(self.control.store.get("appearance")["avatar"], "abstract")

    def test_desktop_and_preview_use_identical_shader_source(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(
            (root / "static/presence.glsl").read_bytes(),
            (root / "gnome-extension/presence.glsl").read_bytes(),
        )

    def test_invalid_appearance_does_not_change_saved_settings(self):
        original = self.control.appearance.copy()
        for data in (
            {"avatar": "../bad"},
            {"fps": True},
            {"fps": 120},
            {"quality": "unbounded"},
            {"motion": "rapid"},
            {"executable": "run"},
            {"idle_saver": "yes"},
            [],
        ):
            with self.assertRaises(ValueError):
                self.control.set_appearance(data)
        self.assertEqual(self.control.appearance, original)

    def test_capability_discovery_excludes_embedding_models(self):
        def local(path, body=None):
            if path == "tags":
                return {"models": [{"name": "embed"}, {"name": "chat"}]}
            return {
                "capabilities": ["embedding"]
                if body["model"] == "embed"
                else ["completion"]
            }

        with patch("control.local_json", side_effect=local):
            result = Catalog().models()
            self.assertEqual([m["name"] for m in result], ["chat"])

    def test_commands_require_workspace_access(self):
        with self.assertRaises(ValueError):
            self.connect(mode="chat", commands=True)


if __name__ == "__main__":
    unittest.main()
