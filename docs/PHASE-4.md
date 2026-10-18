# Phase 4 — Voice, vision, devices and Ubuntu actions

## Delivered implementation

Devices adds real PipeWire input/output enumeration, stable device choices and native webcam discovery through `/dev/v4l/by-id`. On the MS-S1 Max, first run prefers its onboard analog capture endpoint when identifiable. Other computers follow their default input. Output follows Ubuntu's default unless explicitly selected. A missing saved endpoint stays unavailable; it never becomes another microphone automatically. Explicit targets set PipeWire's `node.dont-reconnect` and WirePlumber's `node.dont-fallback`; device reconnection requires enabling capture again.

**Record command** captures at most 15 seconds of 16 kHz mono PCM into bounded memory. **Send recording** transcribes locally and dispatches once to the currently selected session. Capture is explicit and half duplex: recording stops speech, a busy agent rejects a new recording, and only voice-origin turns are automatically read aloud when that preference is enabled. **Read reply** reads the last completed reply. **Mute / discard** cancels recording, recognition and playback. **Stop all** also cancels the managed agent and releases the camera. An already dispatched external desktop action cannot be undone by stop-all.

Supporting components run on CPU in a separate Python 3.12 environment: faster-whisper base.en speech recognition, the pinned LampOS STT session interface, LampOS's unmodified Piper backend, and a public-domain-dataset LJSpeech voice. No remote speech API, wake-word service, separate realtime conversational LLM or secondary vision model runs. Supporting media processes start on demand and are reaped on interruption; no speech/CV model remains resident while idle. English push-to-talk is the initial speech scope.

Camera gaze uses LampOS's unmodified `HostVideoCaptureDevice`, OpenCV's frontal-face cascade and damped face-center positions. On face loss, the gaze decays toward neutral; stale frames/device failure stop the camera instead of choosing a replacement. One private replaceable JPEG supports an explicit **Ask about this view** request. Only the selected model receives that image, through the existing LampOS attachment protocol. Ollama-advertised vision capability is also passed into OpenCode's model metadata. Non-vision models keep camera gaze but cannot accept a view request. Sending a view can retain it in the native OpenCode conversation history; capture files are removed on stop/lock, and no raw media is committed to Git.

Real capture/playback status drives listening/speaking states and core brightness; camera coordinates drive head direction. Awaiting approval has a separate amber state. The same sensory uniforms run in the native renderer and browser, validated before entering GNOME. Still mode ignores gaze/amplitude changes, preserving state updates without continuous tracking motion. A new explicit idle-power preference caps idle/disconnected animation at 15 FPS; active agent/listening/speaking states use the selected 15/30/60 cap. It defaults on and can be disabled in Appearance. Fixed-30 idle CPU samples remain in the evidence; this policy does not claim that the original fixed-30 CPU target passed.

Ubuntu lock state is checked at each device/action dispatch and polled every 500 ms while running. Lock or an unavailable lock service fails closed: capture, recognition and playback stop; pending approvals are revoked. Unlock never resumes devices. Restart never resumes capture or an executable task. Session/model switches fence old transcripts, stop media and revoke approvals before starting the next runtime. Multi-window controls share the same service-side state.

## Enforced Ubuntu scope

Workspace read/edit/status-command restrictions from phase 2 remain native OpenCode permissions. Additional desktop access defaults off and supports exactly one typed action: **open this conversation's workspace folder in Ubuntu Files**. A model proposal is inert until the owner approves its exact path for the current session/generation/turn, within 60 seconds. Denial, permission revocation, lock, expiry, new turns and switches invalidate it. The approval is consumed once. Dispatch uses fixed `xdg-open` arguments without a shell. Arbitrary commands, keyboard/mouse automation, other folders, camera/microphone agent tools and additional network providers remain unavailable. Existing alternative-platform blockers are unchanged.

## Qualification and open gates

Automated checks cover device/settings validation, no fallback for missing saved inputs, lock denial, capture cleanup, one-time fenced transcript dispatch, late audio suppression, model vision denial, stop/switch cleanup, approval denial/revocation/expiry/lock/switch and single-use approval. All private media/action endpoints retain host/origin/authentication/CSRF checks. The 36 Python unit checks pass, along with native ownership/48 state-form combinations, motion/uniform checks, and Chromium GPU/static/offline paths. A browser-only sensory fixture also verifies actual WebGL gaze/amplitude uniforms, still-mode suppression, and roughly 200 ms active polling; it never starts physical devices. Default idle mode measures 1.83% incremental CPU; combined idle PSS is about 526 MiB including a fresh full browser tree and excluding ordinary GNOME base/inference. Exact results and synthetic/native evidence are in `evidence/phase-4/` and phase 3 resource records.

Real local speech synthesis → real local ASR → real selected OpenCode/Ollama conversation → generated response PCM passes. This uses a synthesized command and **does not establish physical microphone capture or audible speaker output**. A real agent proposal to open its workspace also passed the explicit denial flow, with approval disabled during lock and no desktop action dispatched. A separately selected installed `qwen3.5:4b` correctly described the authored robot avatar through the actual controller/gateway attachment path; the production owner was stopped before that isolated test, then resumed with its original session/model. No second reasoning runtime ran concurrently.

**The phase 4 hardware exit gate remains open.** Ubuntu was locked while the owner was away, and capture/playback correctly refused to run. Real spoken microphone → agent → audible speaker, physical face tracking/loss recovery, actual device unplug/default changes, and lock during physical capture still require qualification in an unlocked session. The synthesized pipeline, unit fixtures and native sensory-uniform checks are explicitly distinct from these physical checks. The phase 3 CPU acceptance status is recorded independently in PHASE-3.md.

The updated control center and local media components are installed. The login Shell still caches its older extension module; version 4 loads after one normal logout/login. No forced logout, Shell replacement, driver change or autostart was introduced. Both wallpaper extensions remain exclusive. A locked session may report its selected extension as enabled but temporarily not rendering.

## Reproduce and operate

```sh
python3 scripts/install-media.py  # explicit auxiliary-model download, checksum pinned
python3 scripts/install-control-center.py
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
.venv/bin/python scripts/qualify-media.py  # synthesized audio, real selected model
.venv/bin/python scripts/qualify-vision.py # temporarily stops production owner; fixture image
# Guarded disposable GNOME compositor only:
python3 tests/qualify-senses.py
```

Open Project Avalon from the application menu/Desktop. Devices selects the microphone, speaker and camera. Apply devices leaves capture off. Record command then Send recording runs a spoken command; Mute / discard releases audio. Enable camera gaze starts tracking; Camera off releases it. Ask about this view becomes available only for an installed image-capable selected model and an active camera. Stop all releases media and stops the agent; Connect resumes the selected runtime.

The installer downloads only the explicitly requested supporting speech models, not an Ollama reasoning model. Model revisions/checksums are in `evidence/phase-4/model-sources.json`. Dependency provenance is in ASSETS.md. Update/uninstall, diagnostics and physical lifecycle/release qualification remain phase 5.
