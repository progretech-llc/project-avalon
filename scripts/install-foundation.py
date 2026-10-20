#!/usr/bin/env python3
"""Install the qualified user-level extension and on-demand diagnostic launcher."""
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def run(*args):subprocess.run(args,check=True)

def main():
    if 'GNOME Shell 50.' not in subprocess.check_output(['gnome-shell','--version'],text=True):
        raise RuntimeError('Foundation installer requires qualified GNOME Shell 50')
    for path in [ROOT/'.tools/avalon-runtime',ROOT/'.tools/avalon-probe',ROOT/'.runtime/agent/gateway.json']:
        if not path.exists():raise RuntimeError('Build and configure the isolated runtime before installation')
    package=ROOT/'.runtime/packages';package.mkdir(parents=True,exist_ok=True)
    run('gnome-extensions','pack','--force','--out-dir',str(package),'--extra-source=ownership.js','--extra-source=ownership-core.js','--extra-source=chat-overlay.js','--extra-source=chat-client.py','--extra-source=presence.glsl','--extra-source=galaxy.js','--extra-source=constellation-wallpaper.js','--extra-source=constellation-presence.js','--extra-source=memory_viewer.py','--extra-source=progre.png',str(ROOT/'gnome-extension'))
    run('gnome-extensions','install','--force',str(package/'avalon@progretech.com.shell-extension.zip'))
    constellation=ROOT.parent/'constellation'
    if constellation.exists():
        # Only update its extension. Preserve its source, settings, agents and timer.
        run('gnome-extensions','pack','--force','--out-dir',str(package),'--extra-source=galaxy.js','--extra-source=memory_viewer.py','--extra-source=ownership.js','--extra-source=ownership-core.js',str(constellation/'gnome-extension'))
        run('gnome-extensions','install','--force',str(package/'factory-observatory@progretech.com.shell-extension.zip'))
    data=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))
    config=Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))
    app=data/'applications/project-avalon.desktop';app.parent.mkdir(parents=True,exist_ok=True)
    app.write_text(f'''[Desktop Entry]
Type=Application
Name=Project Avalon
Comment=Open the Avalon Presence Control Center
Exec=/usr/bin/python3 "{ROOT}/avalon.py"
Icon=preferences-desktop-wallpaper
Terminal=false
Categories=Utility;Settings;
StartupNotify=true
''')
    desktop=Path(subprocess.check_output(['xdg-user-dir','DESKTOP'],text=True).strip())
    if desktop.is_dir():
        shortcut=desktop/app.name;shutil.copy2(app,shortcut);shortcut.chmod(0o755)
        subprocess.run(['gio','set',str(shortcut),'metadata::trusted','true'],capture_output=True)
    unit=config/'systemd/user/project-avalon-runtime.service';unit.parent.mkdir(parents=True,exist_ok=True)
    unit.write_text(f'''[Unit]
Description=Project Avalon isolated LampOS gateway
After=network.target

[Service]
Type=simple
ExecStart="{ROOT}/.tools/avalon-runtime" --state "{ROOT}/.runtime/agent"
Restart=on-failure
RestartSec=3
UMask=0077
NoNewPrivileges=yes
''')
    run('systemctl','--user','daemon-reload')
    print('Installed on-demand runtime, application launcher, Desktop shortcut and both wallpaper guards. No autostart enabled. Log out/in to load new extension code in the login session.')

if __name__=='__main__':main()
