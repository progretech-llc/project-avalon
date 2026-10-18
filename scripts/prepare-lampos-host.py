#!/usr/bin/env python3
"""Prepare pinned LampOS in private state with scoped Ubuntu port relocation."""

import io
import json
import os
import secrets
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".runtime/lampos"
SOURCE = ROOT / ".runtime/lampos-source"


def main():
    pin = json.loads((ROOT / "dependencies.json").read_text())["lampos"]["revision"]
    current = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT / ".deps/lampos", text=True
    ).strip()
    if current != pin:
        raise RuntimeError("Native LampOS source must match dependencies.json")
    if not SOURCE.exists():
        data = subprocess.check_output(
            ["git", "archive", "HEAD"], cwd=ROOT / ".deps/lampos"
        )
        SOURCE.mkdir(mode=0o700)
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            archive.extractall(SOURCE, filter="data")
    previous = STATE / "source.json"
    manifest = json.loads(previous.read_text()) if previous.exists() else {}
    if manifest.get("upstream", pin) != pin:
        raise RuntimeError(
            "Private LampOS source is from another pin; migrate it before preparing"
        )
    changed = set(manifest.get("port_relocated_python_files", []))
    # Another company app owns :5000. Relocate only native localhost OS URLs;
    # device APIs, provider traffic, model and delegation behavior stay upstream.
    for directory in ["hal", "skills"]:
        for path in (SOURCE / directory).rglob("*.py"):
            before = path.read_text()
            after = before.replace("http://127.0.0.1:5000/", "http://127.0.0.1:18895/")
            if after != before:
                path.write_text(after)
                changed.add(str(path.relative_to(SOURCE)))
    runtime = SOURCE / "hal/runtime.py"
    runtime.write_text(
        runtime.read_text().replace(
            "from hal.drivers.voice.music_service import MusicService",
            "from avalon_music import AvalonMusicService as MusicService",
        )
    )
    for name in [
        "config",
        "logs",
        "media",
        "users",
        "strangers",
        "tts_cache",
        "snapshots",
    ]:
        (STATE / name).mkdir(parents=True, exist_ok=True, mode=0o700)
    shutil.copytree(
        ROOT / "robots/avalon", SOURCE / "robots/avalon", dirs_exist_ok=True
    )
    config = STATE / "config/config.json"
    if not config.exists():
        value = {
            "httpPort": 18895,
            "device_type": "avalon",
            "agent_runtime": "hermes",
            "llm_config_mode": "runtime",
            "llm_model": "native",
            "set_up_completed": False,
            "llm_api_key": secrets.token_urlsafe(48),
            "tts_provider": "piper",
            "tts_voice": "en_US-ljspeech-medium",
            "wakeword": True,
            "wake_phrases": ["hey avalon"],
            "wake_followup_s": 10,
            "realtime": {"enabled": False},
        }
        config.write_text(json.dumps(value, indent=2) + "\n")
        config.chmod(0o600)
    (STATE / "source.json").write_text(
        json.dumps(
            {
                "upstream": pin,
                "os_port": 18895,
                "port_relocated_python_files": sorted(changed),
            },
            indent=2,
        )
        + "\n"
    )
    print("Prepared private pinned LampOS host source, digital body and configuration.")


if __name__ == "__main__":
    main()
