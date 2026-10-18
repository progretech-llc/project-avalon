#!/usr/bin/env python3
"""Install on-demand native LampOS services for Avalon's digital body."""

import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
config = (
    Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "systemd/user"
)
config.mkdir(parents=True, exist_ok=True)
for executable in [
    ROOT / ".tools/lampos-os-server",
    ROOT / ".tools/avalon-harness-link",
    ROOT / ".lampos-venv/bin/python",
    Path("/usr/bin/avahi-publish-service"),
]:
    if not executable.exists():
        raise RuntimeError(
            f"Missing {executable}; follow docs/LAMPOS.md before installation"
        )
subprocess.run(
    ["/usr/bin/python3", str(ROOT / "scripts/prepare-lampos-host.py")], check=True
)
units = {
    "project-avalon-lampos.service": (
        "LampOS native skills and Harness",
        f"/usr/bin/python3 {ROOT}/scripts/run-lampos-host.py os",
        "",
    ),
    "project-avalon-body.service": (
        "Avalon native digital body media",
        f"/usr/bin/python3 {ROOT}/scripts/run-lampos-host.py hal",
        "After=project-avalon.service\n",
    ),
    "project-avalon-harness-link.service": (
        "Avalon encrypted Harness socket",
        str(ROOT / ".tools/avalon-harness-link"),
        "After=project-avalon-lampos.service\nRequires=project-avalon-lampos.service\n",
    ),
    "project-avalon-discovery.service": (
        "Avalon native Harness discovery",
        '/usr/bin/avahi-publish-service "Project Avalon" _autonomous._tcp 18894 device_type=avalon',
        "After=project-avalon-harness-link.service\nRequires=project-avalon-harness-link.service\n",
    ),
}
for name, (description, command, dependencies) in units.items():
    (config / name).write_text(f"""[Unit]
Description={description}
PartOf=project-avalon.service graphical-session.target
{dependencies}
[Service]
Type=simple
WorkingDirectory={ROOT}
ExecStart={command}
Restart=on-failure
RestartSec=3
KillMode=control-group
TimeoutStopSec=10
UMask=0077
NoNewPrivileges=yes
""")
drop = config / "project-avalon.service.d"
drop.mkdir(exist_ok=True)
(drop / "lampos.conf").write_text("[Unit]\nWants=" + " ".join(units) + "\n")
subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
print(
    "Installed native LampOS services; started only with Avalon, stopped with its session."
)
