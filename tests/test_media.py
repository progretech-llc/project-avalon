import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from test_control import FakeCatalog, FakeRuntime

from control import Conflict, Controller
from media import Media, rms

INVENTORY = {
    "inputs": [{"id": "mic:stable", "name": "MS-S1 microphone"}],
    "outputs": [{"id": "speaker:stable", "name": "Speaker"}],
    "cameras": [{"id": "/dev/v4l/by-id/fixture-video-index0", "name": "Camera"}],
}


class MediaTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.config = patch("control.configure", return_value={})
        self.config.start()
        self.control = Controller(
            Path(self.directory.name), FakeCatalog(), FakeRuntime()
        )
        with patch.object(Media, "_monitor"):
            self.media = self.control.media = Media(self.control)
        self.control.resume()

    def tearDown(self):
        self.control.close()
        self.config.stop()
        self.directory.cleanup()

    def test_locked_device_operations_never_start_a_process(self):
        with (
            patch("media.screen_locked", return_value=True),
            patch.object(self.media, "_spawn") as spawn,
        ):
            for action in (
                self.media.record,
                self.media.finish,
                self.media.enable_camera,
                lambda: self.media.speak("hello"),
                self.media.vision_attachment,
                self.media.wake,
            ):
                with self.assertRaisesRegex(ValueError, "locked"):
                    action()
            spawn.assert_not_called()

    def test_device_validation_and_missing_saved_device_never_fall_back(self):
        with patch("media.devices", return_value=INVENTORY):
            for data in (
                {"input": "missing"},
                {"output": ["bad"]},
                {"spoken_replies": "yes"},
                {"camera": "/etc/passwd"},
                {"shell": "pwd"},
            ):
                with self.assertRaises(ValueError):
                    self.media.configure(data)
            self.media.configure(
                {
                    "input": "mic:stable",
                    "output": "speaker:stable",
                    "camera": INVENTORY["cameras"][0]["id"],
                }
            )
            self.assertEqual(
                self.media._target("input")[:2], ["--target", "mic:stable"]
            )
            self.assertIn("node.dont-reconnect=true", self.media._target("input")[-1])
        with patch(
            "media.devices", return_value={"inputs": [], "outputs": [], "cameras": []}
        ):
            with self.assertRaisesRegex(ValueError, "disconnected"):
                self.media._target("input")
        self.assertEqual(self.media.settings["input"], "mic:stable")

    def test_switch_and_stop_discard_audio_camera_and_stale_transcript(self):
        self.media.pcm.extend(b"private captured audio")
        self.media.state.update(recording=True, camera=True, speaking=True)
        self.media.frame.write_bytes(b"private frame")
        fence = (self.control.selected, self.control.generation, self.media.epoch)
        self.control.select({"model": "large:local", "cancel_current": True})
        worker = Mock(returncode=0)
        worker.communicate.return_value = (
            json.dumps({"text": "old command"}).encode(),
            None,
        )
        with patch("media.terminate"):
            self.media._transcribe(worker, b"audio", fence)
        self.assertEqual(self.control.snapshot()["messages"], [])
        self.assertFalse(self.media.pcm)
        self.assertFalse(self.media.state["recording"])
        self.assertFalse(self.media.state["camera"])
        self.assertFalse(self.media.frame.exists())
        self.control.cancel()
        self.assertFalse(self.media.state["speaking"])

    def test_transcript_dispatch_is_exactly_once_on_current_fence(self):
        self.media.state["transcribing"] = True
        fence = (self.control.selected, self.control.generation, self.media.epoch)
        worker = Mock(returncode=0)
        worker.communicate.return_value = (
            json.dumps({"text": "real transcript"}).encode(),
            None,
        )
        with patch("media.screen_locked", return_value=False), patch("media.terminate"):
            self.media._transcribe(worker, b"audio", fence)
            self.media._transcribe(worker, b"audio", fence)
        self.assertEqual(len(self.control.runtime.current.sent), 1)
        self.assertEqual(
            self.control.runtime.current.sent[0]["payload"]["content"],
            "real transcript",
        )
        self.assertTrue(self.control.active["spoken"])

    def test_nonvision_model_cannot_receive_camera_image(self):
        self.media.state["camera"] = True
        self.media.frame.write_bytes(b"jpeg")
        with patch("media.screen_locked", return_value=False):
            with self.assertRaisesRegex(ValueError, "no vision"):
                self.control.chat("describe", vision=True)
        self.assertEqual(self.control.runtime.current.sent, [])
        self.assertEqual(self.control.snapshot()["messages"], [])

    def test_spoken_command_uses_one_current_camera_frame(self):
        self.media.state["camera"] = True
        image = [{"type": "image", "url": "data:image/jpeg;base64,ZnJhbWU="}]
        with patch.object(self.media, "vision_attachment", return_value=image) as frame:
            self.control.chat("Can you tell me what this is?", spoken=True)
        frame.assert_called_once_with()
        payload = self.control.runtime.current.sent[-1]["payload"]
        self.assertEqual(payload["attachments"], image)

    def test_spoken_camera_failure_does_not_send_a_text_only_guess(self):
        self.media.state["camera"] = True
        with patch.object(
            self.media, "vision_attachment", side_effect=ValueError("stale camera")
        ):
            with self.assertRaisesRegex(ValueError, "stale camera"):
                self.control.chat("What is this?", spoken=True)
        self.assertEqual(self.control.runtime.current.sent, [])
        self.assertEqual(self.control.snapshot()["messages"], [])

    def test_wake_requires_vision_without_starting_devices(self):
        with (
            patch("media.screen_locked", return_value=False),
            patch.object(self.media, "_spawn") as spawn,
        ):
            with self.assertRaisesRegex(ValueError, "vision model"):
                self.media.wake()
            spawn.assert_not_called()

    def test_wake_and_sleep_own_listener_and_camera(self):
        self.media.settings["input"] = "default"
        worker = Mock()
        worker.poll.return_value = None

        def camera():
            self.media.camera = worker
            self.media.state["camera"] = True

        with (
            patch("media.screen_locked", return_value=False),
            patch("media.devices", return_value=INVENTORY),
            patch.object(
                self.control.catalog, "validate", return_value={"vision": True}
            ),
            patch.object(self.media, "snapshot", return_value={"speech_ready": True}),
            patch.object(self.media, "enable_camera", side_effect=camera),
            patch.object(self.media, "_spawn", return_value=worker),
            patch("threading.Thread.start"),
            patch("media.terminate"),
        ):
            self.media.wake()
            self.assertTrue(self.media.awake)
            self.assertIs(self.media.listener, worker)
            self.assertEqual(
                self.media.settings["camera"], INVENTORY["cameras"][0]["id"]
            )
            self.media.stop()
        self.assertFalse(self.media.awake)
        self.assertIsNone(self.media.listener)
        self.assertIsNone(self.media.camera)

    def test_ambient_transcript_never_dispatches(self):
        worker = Mock()
        worker.stdout = [
            json.dumps({"text": "open everything", "addressed": False}).encode()
        ]
        self.media.awake = self.media.listener_ready = True
        self.media.listener_paused = False
        self.media.listener = worker
        with patch("media.screen_locked", return_value=False), patch("media.terminate"):
            self.media._listen(worker)
        self.assertEqual(self.control.runtime.current.sent, [])
        self.assertFalse(self.media.awake)

    def test_listener_phrase_is_validated_before_devices_stop(self):
        with (
            patch("media.devices", return_value=INVENTORY),
            patch.object(self.media, "stop") as stop,
        ):
            for phrase in ("", "   ", "!", "x" * 81, None):
                with self.assertRaises(ValueError):
                    self.media.configure({"listener_phrase": phrase})
            stop.assert_not_called()

    def test_pipewire_sample_limit_keeps_complete_recording_with_exit_one(self):
        worker = Mock()
        worker.stdout = io.BytesIO(b"\x01\x00" * 240000)
        worker.wait.return_value = 1
        self.media.capture = worker
        self.media.state["recording"] = True
        self.media._read_audio(worker, self.media.epoch)
        self.assertEqual(len(self.media.pcm), 480000)
        self.assertFalse(self.media.state["recording"])
        self.assertIn("fifteen seconds", self.media.state["notice"])
        self.media.capture = None

    def test_rms_and_public_visual_contract_exclude_raw_media(self):
        self.assertEqual(rms(b"\0" * 320), 0)
        self.assertGreater(rms(b"\xff\x3f" * 160), 0)
        self.media.state.update(recording=True, level=0.5, gaze=[0.2, -0.3])
        self.media.pcm.extend(b"private audio")
        self.control.publish()
        data = json.loads(self.control.visual.read_text())
        self.assertEqual(data["status"], "listening")
        self.assertEqual(data["sensors"], {"gaze": [0.2, -0.3], "level": 0.5})
        self.assertNotIn("private", json.dumps(data))
        self.assertNotIn("settings", data)

    def test_lock_stops_media_clears_approval_and_unlock_does_not_resume(self):
        self.media.locked = False
        self.media.state.update(recording=True, camera=True, speaking=True)
        self.media.pcm.extend(b"private")
        self.control.pending_action = {"id": "pending", "expires": 9999999999}
        with (
            patch.object(self.control.closing, "wait", side_effect=[False, True]),
            patch("media.screen_locked", return_value=True),
        ):
            self.media._monitor()
        self.assertIsNone(self.control.pending_action)
        self.assertFalse(self.media.pcm)
        for key in ("recording", "camera", "speaking"):
            self.assertFalse(self.media.state[key])
        with (
            patch.object(self.control.closing, "wait", side_effect=[False, True]),
            patch("media.screen_locked", return_value=False),
        ):
            self.media._monitor()
        self.assertFalse(self.media.locked)
        self.assertFalse(self.media.state["recording"])
        self.assertFalse(self.media.state["camera"])

    def test_late_audio_after_mute_never_starts_playback(self):
        worker = Mock()
        worker.stdout = io.BytesIO(b"\xff\x3f" * 1000)
        epoch = self.media.epoch
        self.media.stop_audio()
        with patch.object(self.media, "_spawn") as spawn, patch("media.terminate"):
            self.media._play(worker, [], epoch)
            spawn.assert_not_called()
        self.assertFalse(self.media.state["speaking"])

    def test_configure_stops_capture_and_persists_identity_not_enabled_state(self):
        self.media.state.update(recording=True, camera=True, speaking=True)
        with patch("media.devices", return_value=INVENTORY):
            self.media.configure({"input": "mic:stable"})
        self.assertFalse(
            any(self.media.state[k] for k in ("recording", "camera", "speaking"))
        )
        self.assertNotIn("recording", self.control.store.get("devices"))
        self.assertEqual(self.control.store.get("devices")["input"], "mic:stable")


class ApprovalTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.config = patch("control.configure", return_value={})
        self.config.start()
        self.control = Controller(
            Path(self.directory.name), FakeCatalog(), FakeRuntime()
        )
        self.control.resume()
        Path(self.control.snapshot()["session"]["workspace"]).mkdir(parents=True)

    def tearDown(self):
        self.control.close()
        self.config.stop()
        self.directory.cleanup()

    def proposal(self):
        self.control.set_desktop_actions(True)
        self.control.chat("Open the workspace")
        self.control.runtime.current.emit("text", {"text": "[[avalon:open_workspace]]"})
        self.control.runtime.current.emit("session.idle")
        for _ in range(200):
            if self.control.pending_action:
                return self.control.pending_action.copy()
            threading.Event().wait(0.005)
        self.fail("No proposal received")

    def test_proposal_requires_approval_and_is_consumed_once(self):
        with (
            patch("control.subprocess.Popen") as launch,
            patch("media.screen_locked", return_value=False),
        ):
            action = self.proposal()
            launch.assert_not_called()
            self.control.decide_action({"id": action["id"], "approve": True})
            launch.assert_called_once()
            self.assertEqual(launch.call_args.args[0], ["xdg-open", action["path"]])
            with self.assertRaises(Conflict):
                self.control.decide_action({"id": action["id"], "approve": True})

    def test_denial_revocation_lock_expiry_and_switch_never_execute(self):
        for condition in ("deny", "revoke", "lock", "expire", "switch"):
            with (
                patch("control.subprocess.Popen") as launch,
                patch("media.screen_locked", return_value=condition == "lock"),
            ):
                action = self.proposal()
                if condition == "revoke":
                    self.control.set_desktop_actions(False)
                elif condition == "expire":
                    self.control.pending_action["expires"] = 0
                elif condition == "switch":
                    self.control.select({"model": "large:local"})
                try:
                    self.control.decide_action(
                        {"id": action["id"], "approve": condition != "deny"}
                    )
                except Conflict:
                    pass
                launch.assert_not_called()

    def test_disabled_desktop_actions_do_not_accept_model_marker(self):
        self.control.chat("open")
        self.control.runtime.current.emit("text", {"text": "[[avalon:open_workspace]]"})
        self.control.runtime.current.emit("session.idle")
        threading.Event().wait(0.05)
        self.assertIsNone(self.control.pending_action)
