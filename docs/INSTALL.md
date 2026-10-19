# Install Avalon from source

Avalon is a developer preview for **Ubuntu, GNOME Shell 50, Wayland and Linux x86_64**. Other GNOME versions and desktop environments are not qualified. Review the commands before running them; setup installs user services and a desktop extension. It does not replace your agent CLIs or install a reasoning model.

## Before you start

Install and configure these independently using their official documentation:

- [Ollama](https://ollama.com/) with at least one local model already installed and its local API available on `127.0.0.1:11434`.
- [OpenCode](https://opencode.ai/) available as `opencode` on your PATH. The recorded qualification uses OpenCode 1.19.3; see [dependencies.json](../dependencies.json).
- [uv](https://docs.astral.sh/uv/) for isolated Python environments, plus Git and Node.js if running JavaScript checks.
- Optional: Codex or Claude Code, already installed and configured with their own authentication, model and provider. Avalon does not create those accounts or force those tools through Ollama.

Ubuntu packages used by the application/media setup include:

```sh
sudo apt-get install git python3-gi python3-cairo gir1.2-gtk-4.0 \
  libportaudio2 avahi-utils ffmpeg pipewire-bin wireplumber espeak-ng
```

Use the existing graphical login's GNOME, PipeWire and user session bus. Do not launch the app as root. The `gnome-extensions`, `wpctl` and `systemctl --user` commands must work in that session. For pitch controls, the installed FFmpeg build must include its `rubberband` audio filter.

## Build and configure

Clone into a regular user-writable path, keeping the directory name free of spaces for the current service-file recipes:

```sh
git clone https://github.com/progretech-llc/project-avalon.git
cd project-avalon

uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt

python3 scripts/build-runtime.py
ollama list
```

The build script fetches the pinned LampOS source and checksum-verifies the pinned Go toolchain. It builds the gateway, probe, native OS host and encrypted Harness socket into ignored local folders. Keep the fetched upstream license files intact.

Choose a model name from **your** `ollama list` output. Replace the example below if it is not installed. The initial configuration requires a model that advertises tool support; choose an image-capable model too if you want camera questions.

```sh
.venv/bin/python scripts/configure-runtime.py \
  --state .runtime/agent --model qwen3.5:4b

uv venv --python 3.12 .lampos-venv
uv pip install --python .lampos-venv/bin/python -r requirements-lampos.txt
```

This creates Avalon-owned OpenCode configuration and state. Existing native Codex/Claude configuration is preserved. The native LampOS host provides robot skills, music and Harness pairing; its digital-body profile does not open a second microphone/camera or start a second conversational model. See [LampOS host details](LAMPOS.md).

## Optional voice and camera support

Run this explicitly if you want local voice, camera questions or camera attention:

```sh
python3 scripts/install-media.py
```

It installs a separate Python 3.12 media environment and downloads pinned supporting speech/speaker models and voices with recorded checksums. These are separate from your Ollama reasoning model. Their upstream model cards and licenses still apply. Installation does not turn on the camera or microphone. Initial setup requires network access; local speech inference does not require a cloud speech subscription.

## Install and launch

```sh
python3 scripts/install-control-center.py
```

The installer adds the **Project Avalon** application-menu/Desktop shortcut, on-demand user services and GNOME extension. It also updates the shared wallpaper guard in a sibling `constellation` checkout when present. Standalone Constellation is optional: Avalon's galaxy can animate without its scene export; populated memory navigation and the existing custom foreground require that separate app's data. Avalon does not install Constellation's collectors or change its settings. Full agent/folder refresh requires that sibling checkout, its configured sources and working `.venv/bin/python` environment. Avalon invokes the native collector into its own private output; the standalone app and timer need not run. See [galaxy source controls](CONSTELLATION.md#agents-and-folders).

Log out and back in normally to load newly installed GNOME JavaScript. Open **Project Avalon** from the application menu or Desktop. In the panel:

1. Select the runtime and model/session you want to use.
2. Choose **Avalon** in the wallpaper control and pick an appearance.
3. In **Devices**, select microphone, output and camera. Use **Wake up** only when you want capture active; **Go to sleep** releases Avalon's capture/playback.
4. Use **Robot** for native service status, music/volume and optional Harness pairing. Leave Harness unpaired if you do not use it.

Services start with Avalon; the installer does not enable login autostart. Existing port usage must allow the app (`8766`), selected gateway (`18893`), native OS (`18895`) and digital-body service (`5001`) on loopback. The encrypted Harness-only websocket is advertised on `18894` over the LAN while active. Native management APIs stay on loopback. Use your firewall/network policy as appropriate.

## Stop or disable

Use **Go to sleep** for media, the wallpaper selector/GNOME Extensions for the desktop renderer, and the following to stop the app and its owned services:

```sh
systemctl --user stop project-avalon.service
gnome-extensions disable avalon@progretech.com
```

Private configuration, chat/session state and downloaded models remain on disk; stopping does not erase them. Your separately installed agent tools remain usable. Avoid sharing `.runtime`, browser profiles, credentials or captured media in issue reports.

## Checks

```sh
uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
node tests/ownership.test.mjs
node tests/constellation.test.mjs
gjs -m tests/constellation-layout.js
.tools/go/bin/go test ./cmd/...
```

GNOME integration checks use a separate, guarded compositor. They are optional development checks; do not enable the test driver in your login Shell. See [Phase 1](PHASE-1.md#repeat-the-checks) for the isolated setup and [Phase 5](PHASE-5.md) for current evidence and remaining qualification gates.
