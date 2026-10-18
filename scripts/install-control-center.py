#!/usr/bin/env python3
"""Install the on-demand control center and shared desktop-state location."""

import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    subprocess.run(
        ["/usr/bin/python3", str(ROOT / "scripts/install-foundation.py")], check=True
    )
    state = ROOT / ".runtime"
    (state / "desktop").mkdir(parents=True, exist_ok=True, mode=0o700)
    state_home = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    state_home.mkdir(parents=True, exist_ok=True)
    link = state_home / "project-avalon"
    if link.is_symlink():
        if link.resolve() != (state / "desktop").resolve():
            raise RuntimeError(
                "A different Avalon desktop state directory already exists; preserving it"
            )
    elif link.exists():
        raise RuntimeError(
            "An existing Avalon state directory needs explicit migration; preserving it"
        )
    else:
        link.symlink_to(state / "desktop", target_is_directory=True)
    config = (
        Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        / "systemd/user"
    )
    (config / "project-avalon.service").write_text(f"""[Unit]
Description=Project Avalon Presence Control Center
After=network.target

[Service]
Type=simple
WorkingDirectory={ROOT}
ExecStart={ROOT}/.venv/bin/python {ROOT}/app.py
Environment=AVALON_STATE_DIR={state}
Restart=on-failure
RestartSec=3
TimeoutStopSec=15
KillMode=control-group
UMask=0077
NoNewPrivileges=yes
""")
    (config / "project-avalon-runtime.service").write_text(f"""[Unit]
Description=Project Avalon isolated LampOS gateway
PartOf=project-avalon.service

[Service]
Type=simple
ExecStart={ROOT}/.tools/avalon-runtime --state {state}/agent
Restart=on-failure
RestartSec=3
TimeoutStopSec=5
KillMode=control-group
UMask=0077
NoNewPrivileges=yes
""")
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    print(
        "Installed on-demand Presence Control Center. Open Project Avalon from the app menu or Desktop."
    )


if __name__ == "__main__":
    main()
