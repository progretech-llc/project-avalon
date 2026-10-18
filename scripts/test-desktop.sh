#!/usr/bin/env bash
# Disposable real GNOME Shell. Does not restart or modify the login session.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir"
mkdir -p .runtime/shell-data/gnome-shell/extensions .runtime/shell-config .runtime/shell-state .runtime/shell-desktop .cache/shell
mkdir -p .runtime/shell-data/gnome-shell/extensions/{avalon@progretech.com,factory-observatory@progretech.com,avalon-test@progretech.com}
cp -r gnome-extension/. .runtime/shell-data/gnome-shell/extensions/avalon@progretech.com/
cp -r ../constellation/gnome-extension/. .runtime/shell-data/gnome-shell/extensions/factory-observatory@progretech.com/
cp -r tests/fixtures/shell-driver/. .runtime/shell-data/gnome-shell/extensions/avalon-test@progretech.com/
printf 'XDG_DESKTOP_DIR="%s/.runtime/shell-desktop"\n' "$repo_dir" > .runtime/shell-config/user-dirs.dirs
printf 'Avalon desktop icon layering proof.\n' > .runtime/shell-desktop/Avalon-proof.txt
export XDG_DATA_HOME="$repo_dir/.runtime/shell-data"
export XDG_CONFIG_HOME="$repo_dir/.runtime/shell-config"
export XDG_STATE_HOME="$repo_dir/.runtime/shell-state"
export XDG_CACHE_HOME="$repo_dir/.cache/shell"
export XDG_RUNTIME_DIR="/run/user/$(id -u)/avalon-test"
export GSETTINGS_BACKEND=keyfile
export AVALON_TEST_SHELL=1
export AVALON_TEST_MONITOR="${AVALON_TEST_MONITOR:-1600x900}"
[[ "$AVALON_TEST_MONITOR" =~ ^[0-9]{3,4}x[0-9]{3,4}$ ]] || exit 2
mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"
# Remove only peer wallpaper autostarts in this isolated keyfile backend, so
# cold memory accounting starts before an avatar pipeline has been allocated.
python3 -c 'from gi.repository import Gio; s=Gio.Settings.new("org.gnome.shell"); s.set_strv("enabled-extensions",[x for x in s.get_strv("enabled-extensions") if x not in ("avalon@progretech.com","factory-observatory@progretech.com")]); Gio.Settings.sync()'
exec dbus-run-session -- bash -c '
  printf "%s" "$DBUS_SESSION_BUS_ADDRESS" > .runtime/test-bus
  exec gnome-shell --headless --virtual-monitor="$AVALON_TEST_MONITOR" --wayland --no-x11 --wayland-display avalon-proof --debug-control
'
