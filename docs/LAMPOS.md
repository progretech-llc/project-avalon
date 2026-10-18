# Native LampOS host

Speech stays local (Whisper/Kokoro); camera and microphone capture belong to Avalon Media. The native OS hosts skills and encrypted Harness. Its digital HAL uses virtual physical diagnostics and the native music player with a PipeWire output adapter. No motors, GPIO or extra conversational model run.

Install on Linux x86_64 after the standard Avalon Python/media setup:

```sh
python3 scripts/build-runtime.py
sudo apt-get install libportaudio2 avahi-utils
uv venv --python 3.12 .lampos-venv
uv pip install --python .lampos-venv/bin/python -r requirements-lampos.txt
python3 scripts/install-control-center.py
```

Installation prepares a private git-archive copy of the pinned source. The original dependency checkout is preserved. Copied Python localhost OS URLs move from occupied port 5000 to 18895; the copied HAL imports AvalonMusicService for selected PipeWire output. The upstream Go OS/gateway packages and Harness cryptography remain unchanged. Scoped profile sources live in robots/avalon. Private credentials, recordings, journals and runtime state are ignored by Git.

The app starts these on demand: native OS loopback 18895, digital body loopback 5001, encrypted Harness-only socket 18894 and mDNS discovery. Port 18894 exposes only the native authenticated websocket, never OS management APIs. They stop with Avalon or the graphical session. Existing physical services must not already own these ports.

Pair from Robot → Generate pairing code, then Harness → Settings → Devices. Existing agent readiness is reported by Harness and can be stale. Resolve questions/permissions in Harness; never retry an unconfirmed delivery until its receipt is resolved. The selected main runtime stays in Avalon; the native skill host does not run an idle second model.

Current qualification and remaining gates are in PHASE-5.md.
