#!/usr/bin/env python3
"""Open the local control center without a password prompt or terminal."""

import json
from pathlib import Path
import subprocess
import time
import sys
import os
import urllib.request
import http.cookiejar

ROOT = Path(__file__).resolve().parent


def stop_when_off():
    """Release the native backend when its last owned panel exits while Off."""
    checked = False
    for uuid in ('avalon@progretech.com', 'factory-observatory@progretech.com'):
        result = subprocess.run(['gnome-extensions', 'info', uuid], capture_output=True,
                                text=True, timeout=5, env={**os.environ, 'LC_ALL': 'C'})
        if result.returncode == 0:
            checked = True
            if 'Enabled: Yes' in result.stdout:
                return False
    if not checked:
        return False
    subprocess.run(['systemctl', '--user', 'stop', '--no-block', 'project-avalon.service'], check=True)
    return True


def panel(argv):
    try:
        return subprocess.call(argv)
    finally:
        stop_when_off()


def main():
    subprocess.run(
        ["systemctl", "--user", "start", "project-avalon.service"], check=True
    )
    auth = ROOT / ".runtime/control-auth.json"
    deadline = time.monotonic() + 12
    while True:
        try:
            if auth.exists():
                with urllib.request.urlopen("http://127.0.0.1:8766/", timeout=0.5):
                    break
        except OSError:
            pass
        if time.monotonic() > deadline:
            raise RuntimeError("Avalon did not become ready. Check its user service.")
        time.sleep(0.1)
    token = json.loads(auth.read_text())["entry"]
    if "--toggle-presence" in sys.argv:
        client = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )
        origin = "http://127.0.0.1:8766"

        def request(path, data=None, csrf=""):
            req = urllib.request.Request(
                origin + path,
                data=json.dumps(data).encode() if data is not None else None,
                headers={
                    "Content-Type": "application/json",
                    "Origin": origin,
                    "X-CSRF-Token": csrf,
                },
            )
            with client.open(req, timeout=15) as reply:
                return json.load(reply)

        csrf = request("/api/auth", {"token": token})["csrf"]
        state = request("/api/state")
        if not state.get("session") or state.get("runtime_status") == "disconnected":
            request("/api/connect", {}, csrf)
        request(
            "/api/media",
            {"action": "sleep" if state.get("devices", {}).get("awake") else "wake"},
            csrf,
        )
    elif "--panel" in sys.argv:
        profile = ROOT / ".runtime/panel-browser"
        profile.mkdir(mode=0o700, exist_ok=True)
        panel(
            [
                "google-chrome",
                "--user-data-dir=" + str(profile),
                "--no-first-run",
                "--disable-background-mode",
                "--app=http://127.0.0.1:8766/#entry=" + token,
            ],
        )
    else:
        subprocess.run(
            ["systemctl", "--user", "start", "project-avalon-panel.service"], check=True
        )


if __name__ == "__main__":
    main()
