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
        os.execv(
            "/usr/bin/google-chrome",
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
