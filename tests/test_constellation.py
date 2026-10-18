import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import constellation


class ConstellationSettingsTest(unittest.TestCase):
    def test_settings_are_separate_and_preserve_scene_and_standalone_config(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            standalone = folder / "factory-observatory/wallpaper.json"
            standalone.parent.mkdir()
            standalone.write_text('{"enabled":false,"foreground":true}')
            with patch.object(
                constellation, "CONFIG", folder / "project-avalon/constellation.json"
            ):
                saved = constellation.configure(
                    {
                        "foreground": False,
                        "solar_rotation": True,
                        "agent_mode": "satellite",
                    }
                )
                self.assertFalse(saved["foreground"])
                self.assertTrue(constellation.settings()["solar_rotation"])
                self.assertEqual(
                    json.loads(standalone.read_text()),
                    {"enabled": False, "foreground": True},
                )

    def test_invalid_or_standalone_power_fields_do_not_write(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(constellation, "CONFIG", Path(directory) / "settings.json"),
        ):
            for value in (
                {"enabled": True},
                {"glow": float("nan")},
                {"rotation_speed": 6},
                {"foreground": 1},
                {"agent_mode": "unknown"},
                {"black_hole_name": "x" * 33},
            ):
                with self.assertRaises(ValueError):
                    constellation.configure(value)
            self.assertFalse(constellation.CONFIG.exists())

    def test_unavailable_or_invalid_scene_is_explicitly_none(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(constellation, "SCENE", Path(directory) / "scene.json"),
        ):
            self.assertIsNone(constellation.scene())
            constellation.SCENE.write_text('{"schema":"wrong","nodes":[]}')
            self.assertIsNone(constellation.scene())
