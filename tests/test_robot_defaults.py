import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from control import Catalog, Store
from runtime_config import configure
import test_media


class EngagedVoiceTest(unittest.TestCase):
    setUp = test_media.MediaTest.setUp
    tearDown = test_media.MediaTest.tearDown

    def test_followup_is_default_and_stays_opt_out_after_migration(self):
        from media import Media

        self.assertTrue(self.media.settings["followup_replies"])
        saved = {**self.media.settings, "followup_replies": False}
        self.control.store.set("devices", saved)
        with patch.object(Media, "_monitor"):
            restarted = Media(self.control)
        self.assertFalse(restarted.settings["followup_replies"])

    def test_same_owner_can_continue_after_speech_and_window_renews(self):
        observed = []
        worker = Mock()

        def events():
            yield json.dumps(
                {"text": "hey avalon hello", "addressed": True, "owner_match": True}
            ).encode()
            observed.append(self.media.followup == float("inf"))
            with patch("media.time.monotonic", return_value=100):
                self.media._pause_listener(False)
            observed.append(self.media.followup == 110)
            yield json.dumps(
                {"text": "and tomorrow?", "addressed": False, "owner_match": True}
            ).encode()
            observed.append(self.media.followup == float("inf"))

        worker.stdout = events()
        self.media.awake = self.media.listener_ready = True
        self.media.listener_paused = False
        self.media.listener = worker
        self.control.chat = Mock()
        with (
            patch("media.screen_locked", return_value=False),
            patch("media.terminate"),
            patch("media.time.monotonic", return_value=100),
        ):
            self.media._listen(worker)
        self.assertEqual(observed, [True, True, True])
        self.assertEqual(self.control.chat.call_count, 2)

    def test_sleep_blocks_late_spoken_result(self):
        import time

        self.media.speak = Mock()
        self.control.chat("hello", spoken=True)
        job = self.control.active
        self.media.stop()
        self.control.runtime.current.frames.put(
            {
                "type": "text",
                "request_id": job["id"],
                "run_id": job["id"],
                "part": {"text": "late reply"},
            }
        )
        self.control.runtime.current.frames.put(
            {"type": "session.idle", "request_id": job["id"], "run_id": job["id"]}
        )
        deadline = time.monotonic() + 2
        while self.control.active and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertIsNone(self.control.active)
        self.media.speak.assert_not_called()


class NativePlatformTest(unittest.TestCase):
    def test_installed_native_bridges_are_not_policy_blocked(self):
        with patch("control.shutil.which", return_value="/native/cli"):
            platforms = {p["id"]: p for p in Catalog().platforms()}
        self.assertTrue(platforms["codex"]["available"])
        self.assertTrue(platforms["claudecode"]["available"])

    def test_native_configuration_does_not_query_ollama_or_write_native_settings(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("runtime_config.shutil.which", return_value="/native/codex"),
            patch("runtime_config.urllib.request.urlopen") as ollama,
        ):
            cfg = configure(Path(directory), "native", platform="codex")
            ollama.assert_not_called()
            self.assertEqual(cfg["platform"], "codex")
            self.assertEqual(cfg["permission_mode"], "native")
            self.assertFalse((Path(directory) / "agent-home").exists())

    def test_platform_migration_keeps_existing_session(self):
        import sqlite3

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "old.sqlite"
            with sqlite3.connect(path) as db:
                db.execute(
                    "CREATE TABLE sessions(id TEXT PRIMARY KEY,title TEXT,model TEXT,workspace TEXT,mode TEXT,commands INTEGER,native TEXT,created REAL)"
                )
                db.execute(
                    "INSERT INTO sessions VALUES('old','Existing','local','/workspace','chat',0,NULL,1)"
                )
            db.close()
            store = Store(path)
            self.assertEqual(store.session("old")["platform"], "opencode")
            self.assertEqual(store.session("old")["title"], "Existing")
