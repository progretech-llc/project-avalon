"""Avalon's PipeWire output adapter for LampOS's native music player."""

import json
from pathlib import Path
from hal.drivers.voice.music_service import MusicService


class AvalonMusicService(MusicService):
    def _output_pipeline(self):
        path = Path(__file__).resolve().parent / ".runtime/lampos/selected-audio.json"
        settings = json.loads(path.read_text()) if path.exists() else {}
        target = settings.get("output", "default")
        args = [
            "pw-play",
            "--raw",
            "--rate",
            "44100",
            "--channels",
            "2",
            "--format",
            "s16",
            "--latency",
            "150ms",
        ]
        if target != "default":
            args += ["--target", target]
        return ["-f", "s16le"], [*args, "-"], {}
