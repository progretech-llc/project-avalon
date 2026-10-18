import unittest
from speech import DEFAULTS, validate, clean_text
from tracking import focus_position


class PresenceTest(unittest.TestCase):
    def test_voice_controls_reject_invalid_or_nonfinite_values(self):
        validate(DEFAULTS)
        for item in (
            {"voice_pitch": float("nan")},
            {"voice_pitch": 13},
            {"voice_pitch": True},
            {"voice_speed": 0},
            {"voice_speed": float("inf")},
            {"voice_engine": "remote"},
            {"voice_style": "../arbitrary"},
        ):
            with self.assertRaises(ValueError):
                validate({**DEFAULTS, **item})

    def test_camera_attention_matches_image_side_and_stays_bounded(self):
        self.assertEqual(focus_position((0, 0, 100, 100), 200, 200), [-0.5, 0.5])
        self.assertEqual(focus_position((100, 100, 100, 100), 200, 200), [0.5, -0.5])
        self.assertEqual(focus_position((1000, -1000, 100, 100), 200, 200), [1.0, 1.0])

    def test_speech_skips_code_and_keeps_readable_link_text(self):
        self.assertEqual(
            clean_text("**Hello** [world](https://example.com)."), "Hello world."
        )
        self.assertNotIn("rm -rf", clean_text("```sh\nrm -rf example\n```"))


class PublicationTest(unittest.TestCase):
    def test_visual_heartbeat_is_atomic_without_forcing_disk_sync(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from runtime_config import atomic_json

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            with patch("runtime_config.os.fsync") as sync:
                atomic_json(path, {"status": "speaking"}, durable=False)
                sync.assert_not_called()
                self.assertEqual(json.loads(path.read_text()), {"status": "speaking"})
                atomic_json(path, {"saved": True})
                sync.assert_called_once()
            self.assertEqual(list(Path(directory).iterdir()), [path])
