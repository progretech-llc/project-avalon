#!/usr/bin/env python3
"""Run the pinned native OS/HAL inside Avalon's private state."""

import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".runtime/lampos"
SOURCE = ROOT / ".runtime/lampos-source"
p = argparse.ArgumentParser()
p.add_argument("service", choices=["os", "hal"])
p.add_argument("--media", choices=["virtual", "host"], default="virtual")
args = p.parse_args()
env = os.environ.copy()
env.update(
    DEVICE_TYPE="avalon",
    DEVICES_DIR=str(SOURCE / "robots"),
    OS_BACKEND_UPLINK="off",
    OS_AGENT_HOME=str(STATE / "agent-home"),
    OS_AGENT_STATE_PATH=str(STATE / "config/agent_state.json"),
    OS_LOG_FILE=str(STATE / "logs/os-server.log"),
    OS_GELF_SPOOL_DIR=str(STATE / "logs/spool"),
    OS_HAL_LOG_FILE=str(STATE / "logs/hal.log"),
    OS_BOOTSTRAP_CONFIG=str(STATE / "config/bootstrap.json"),
    OS_CONFIG_PATH=str(STATE / "config/config.json"),
    PYTHONPATH=os.pathsep.join([str(ROOT), str(SOURCE)]),
)
if args.service == "os":
    os.chdir(STATE)
    os.execve(
        str(ROOT / ".tools/lampos-os-server"),
        [str(ROOT / ".tools/lampos-os-server")],
        env,
    )
else:
    env.update(
        HAL_MODE="production",
        HAL_HTTP_PORT="5001",
        HAL_SIMULATE="1",
        HAL_SIM_MEDIA=args.media,
        HAL_BOARD="sim",
        HAL_LOG_DIR=str(STATE / "logs"),
        HAL_USERS_DIR=str(STATE / "users"),
        HAL_STRANGERS_DIR=str(STATE / "strangers"),
        HAL_BT_STATE_DIR=str(STATE),
        HAL_VOLUME_STATE_PATH=str(STATE / "volume"),
        HAL_TTS_CACHE_DIR=str(STATE / "tts_cache"),
        HAL_SNAPSHOT_DIR=str(STATE / "snapshots"),
        HAL_SNAPSHOT_PERSIST_DIR=str(STATE / "snapshots/persist"),
        HAL_CALIBRATION_DIR=str(STATE / "calibration"),
        HAL_USER_BEARING_PATH=str(STATE / "user_bearing.json"),
        HAL_FACE_HEIGHT_PATH=str(STATE / "face_height.json"),
        HAL_VOICE_STRANGERS_DIR=str(STATE / "voice_strangers"),
        HAL_DL_STALL_LOG=str(STATE / "logs/stall.log"),
    )
    python = str(ROOT / ".lampos-venv/bin/python")
    os.chdir(SOURCE)
    os.execve(
        python,
        [
            python,
            "-m",
            "uvicorn",
            "robot_body:app",
            "--host",
            "127.0.0.1",
            "--port",
            "5001",
        ],
        env,
    )
