"""Avalon-owned galaxy settings; standalone Constellation is read-only."""

import json
import math
import os
from pathlib import Path
from runtime_config import atomic_json

CONFIG = (
    Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    / "project-avalon/constellation.json"
)
SOURCE_SCENE = (
    Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    / "factory-observatory/scene.json"
)
SCENE = (
    Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    / "project-avalon/constellation-scene.json"
)
DATA = (
    Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    / "constellation"
)
DEFAULTS = dict(
    paused=False,
    foreground=True,
    rotation_speed=0.85,
    glow=0.82,
    rays=0.72,
    density=0.72,
    links=True,
    labels=True,
    agent_mode="orbiting",
    solar_rotation=False,
    solar_rotation_speed=1.0,
    solar_clockwise=False,
    write_lights=False,
    black_hole_name="Shared worker",
)


def settings():
    try:
        saved = json.loads(CONFIG.read_text())
        return {key: saved.get(key, value) for key, value in DEFAULTS.items()}
    except (OSError, ValueError):
        return dict(DEFAULTS)


def configure(data):
    if not isinstance(data, dict) or set(data) - DEFAULTS.keys():
        raise ValueError("Unknown galaxy setting")
    value = {**settings(), **data}
    for key, default in DEFAULTS.items():
        item = value[key]
        if type(default) is bool:
            if type(item) is not bool:
                raise ValueError("Choose a valid " + key)
        elif type(default) is float:
            maximum = (
                5
                if key == "rotation_speed"
                else 10
                if key == "solar_rotation_speed"
                else 1
            )
            if (
                type(item) not in (int, float)
                or not math.isfinite(item)
                or not 0 <= item <= maximum
            ):
                raise ValueError("Invalid " + key)
        elif key == "agent_mode":
            if item not in ("orbiting", "asteroid", "satellite"):
                raise ValueError("Choose a valid agent motion")
        elif (
            not isinstance(item, str)
            or not item.strip()
            or len(item) > 32
            or any(ord(c) < 32 for c in item)
        ):
            raise ValueError("Use a name of 1–32 characters")
    atomic_json(CONFIG, value)
    return value


def scene():
    try:
        if SCENE.stat().st_size > 8 * 1024 * 1024:
            raise ValueError("Scene too large")
        data = json.loads(SCENE.read_text())
        if (
            data.get("schema") != "factory-observatory-wallpaper/v1"
            or not isinstance(data.get("nodes"), list)
            or not isinstance(data.get("links"), list)
        ):
            return None
        return data
    except (OSError, ValueError):
        return None


def foreground():
    for name in ("foreground.png", "progre-foreground.png"):
        if (DATA / name).is_file():
            return DATA / name
    return None
