#!/usr/bin/env python3
"""Open the local control center without a password prompt or terminal."""

import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent


def main():
    subprocess.run(
        ["systemctl", "--user", "start", "project-avalon.service"], check=True
    )
    auth = ROOT / ".runtime/control-auth.json"
    deadline = time.monotonic() + 12
    while not auth.exists():
        if time.monotonic() > deadline:
            raise RuntimeError("Avalon did not become ready. Check its user service.")
        time.sleep(0.1)
    token = json.loads(auth.read_text())["entry"]
    subprocess.Popen(
        ["xdg-open", "http://127.0.0.1:8766/#entry=" + token],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


if __name__ == "__main__":
    main()
