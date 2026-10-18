# Third-party notices

Avalon is built by ProgreTech LLC and integrates independent projects. Names below identify compatibility and provenance; they do not imply endorsement.

## Constellation by ProgreTech

Source: [progretech-llc/constellation](https://github.com/progretech-llc/constellation). Copyright © 2026 ProgreTech LLC. MIT license; complete original notice and permission text: [LICENSES/Constellation-MIT.txt](LICENSES/Constellation-MIT.txt).

Scoped copies/adaptations include `gnome-extension/galaxy.js`, `static/galaxy.js`, `gnome-extension/constellation-wallpaper.js`, `gnome-extension/memory_viewer.py`, `gnome-extension/ownership.js`, `gnome-extension/ownership-core.js`, and `tests/constellation-layout.js`. The galaxy import revision and adaptations are recorded in [docs/CONSTELLATION.md](docs/CONSTELLATION.md). Avalon adds its own settings, voice pulse, camera attention, shared status overlay, Canvas backend and wallpaper lifecycle integration. The independent Constellation application and its assets retain their own licenses. Its protected foreground artwork is not copied into this repository.

## LampOS

Source: [autonomous-ai/lampOS](https://github.com/autonomous-ai/lampOS), pinned in [dependencies.json](dependencies.json). Upstream authors retain their copyrights.

- Everything outside upstream `hal/`: Apache License 2.0; [complete license](LICENSES/Apache-2.0.txt).
- Upstream `hal/`: GNU GPL version 3; original `hal/LICENSE` is retained in the fetched source.
- Upstream [CREDITS.md](https://github.com/autonomous-ai/lampOS/blob/f3f708859d175a8a271e1a7b5e17dca9dee50361/CREDITS.md) describes additional components and license boundaries.

The repository stores integration source and build recipes, not the dependency checkout or compiled executables. Setup fetches the pinned unmodified tree into ignored `.deps/lampos`. A separate private source copy relocates the native localhost OS port and imports Avalon's PipeWire music adapter; details are in [docs/LAMPOS.md](docs/LAMPOS.md). The original source and licenses remain intact. Go gateway/OS packages are used without upstream source edits. A distributor of combined sources or binaries must retain applicable upstream notices and meet corresponding-source requirements.

## Supporting software and model files

Python/Go dependencies, OpenCode, Ollama, Codex, Claude Code, GNOME, PipeWire and related tools retain their own terms. Application dependencies are recorded in `requirements.txt`, `requirements-media.txt`, `requirements-lampos.txt` and `go.mod`/`go.sum`. System fonts are resolved on the host; no font files are redistributed.

Local speech/camera support uses Whisper/faster-whisper, Piper, Kokoro, sherpa-onnx/SpeakerNet and OpenCV. Model/voice hashes and sources are recorded in [phase-4 model sources](docs/evidence/phase-4/model-sources.json), [phase-5 voice sources](docs/evidence/phase-5/voice-model-sources.json) and [asset provenance](docs/ASSETS.md). Their weights and voices are downloaded separately into ignored private storage and remain subject to their own model cards and licenses. No Ollama reasoning-model weights, provider credentials, personal camera frames or microphone recordings are distributed here.
