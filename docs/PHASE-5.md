# Phase 5 — stabilization and release qualification

Phase 5 remains in progress. This iteration replaces the static Progre portrait with a procedural light-being, adds camera attention, local session speaker matching and customizable Kokoro speech. Earlier evidence records the preceding implementation and must not be treated as current artwork or current voice behavior.

## Current behavior

The selected installed vision/tool model remains the only conversational model. Voice and image questions use that same LampOS/OpenCode/Ollama session. No reasoning model is downloaded. Chat mode disables extended reasoning and includes current local time; spoken/awake replies request concise speech. Typed replies are spoken too while awake when Speak replies is enabled.

Wake starts selected capture, local Whisper/Silero recognition and local synthesis. The default listener phrase is `hey avalon`; the owner's saved phrase is preserved. A bare wake phrase permits one following command. Ten-second follow-ups are enabled by default and renew after each accepted turn; the timer begins after processing and speaker playback finish. The owner can disable follow-ups. Speech endpoint silence is 0.9 seconds. Capture is suppressed while the model or speaker is busy.

With session voice matching enabled, the first addressed utterance enrolls a local NeMo SpeakerNet embedding held only in listener RAM. Later commands must match; unrelated ambient speech cannot enroll. Sleep/reset discards ownership. This reduces accidental pickup; it is not identity authentication or proof that every similar speaker will be rejected.

Devices offers Kokoro/Piper, female/male/robotic style, pitch from -12 to +12 semitones, speed 0.65–1.6 and a saved-settings preview. Kokoro provides the distinct male/female voices; Piper retains its existing voice. Rubber Band changes pitch without changing duration; robotic adds modulation. Apply devices saves changes and sleeps capture. Kokoro is CPU-only and warm while awake; it is released on sleep. There is no additional conversational model.

PCM output is 24 kHz. PipeWire backpressure clocks playback with a 150 ms buffer. Redundant per-block sleeps caused audible breaks and were removed. Visual heartbeat writes remain atomic but skip durable disk sync; saved settings retain durable writes. The owner confirmed the revised preview sounded smooth through the selected HDMI speakers.

Camera attention holds a detected face, otherwise follows meaningful foreground movement, then eases back to center. All four procedural avatars consume gaze. Progre is one face with lateral sphere eyes, slash nose, enclosed zigzag mouth, tiny hands and feet, without a torso. Its rounded rectangular face now uses a polygonal cyan/magenta laser-grid material and animated retro sunset, mountains and floor backdrop. The orbit ring is removed; the other appearances keep their existing materials. The old PNG remains only for compatibility with GNOME's cached version 5 module. No background star field is drawn.

Sleep, Stop all, lock, model/session switch and shutdown release owned capture/playback. The Chrome control panel uses its own profile and graphical-session-bound service; shared Firefox is untouched. The native corner wake button remains. Normal disable/enable loads the new shader into cached version 5 without a forced logout; version 6 drops the unused texture setup at the next normal login.

## Current evidence

- `voice-customization.json`: actual local Kokoro female/male/robotic/pitched synthesis; warm first PCM about 0.13–0.16 s. Authored 220 Hz tone becomes 440 Hz at +12 semitones with duration preserved. Synthetic same/different speaker comparisons pass the configured threshold. This is not live owner calibration.
- `kokoro-output.json`: actual preview through the selected physical HDMI sink, in-memory monitor reduced to RMS, plus owner confirmation of smooth playback. Cold preview startup about 0.73 s after text is ready; this excludes conversational model response time.
- `camera-motion.json`: synthetic foreground motion maps left/right correctly; no frames retained.
- `camera-live.json`: real Logitech capture opens, publishes attention and releases. No camera content is committed.
- `motion/`: disposable real GNOME compositor renders all four avatars with time-separated gaze/speech fixtures. These are synthetic attention inputs, not a measurement of physical gaze accuracy.
- `shell-motion/`: exclusive wallpaper ownership, switching, ten concurrent starts, cleanup and re-enable pass in the disposable compositor.
- `motion-finish-review.md`: fresh independent visual review; desktop/mobile controls and procedural anatomy accepted.
- 58 Python tests and ownership JavaScript checks pass. Syntax and focused fatal-error lint pass. Broad advisory lint still reports pre-existing and style findings; it is not claimed clean.

## Remaining release gates

Live owner wake/speaker calibration in ordinary room conversation; physical unplug/replug and default-route changes; logout/lock during real capture; long-session recovery/resource tests; update/uninstall and diagnostics delivery. Phase 3's fixed-30-FPS CPU gate remains open. No additional project phase is introduced. Current handoff keeps `hey avalon`, the owner's selected avatar, and capture asleep.

## Native robot integration update

Speech remains local Whisper/Kokoro by owner choice. No cloud realtime recognition connection is configured. The Robot page exposes native LampOS service status, music play/stop, selected PipeWire output volume, encrypted Harness pairing/discovery and existing agent discovery. Avatar capture remains owned by Avalon, with no duplicate HAL microphone/camera capture. The native HAL profile is a virtual digital body; its diagnostic camera flags do not prove physical capture.

Codex and Claude use upstream LampOS native gateway packages with their own configured providers, models, authentication and tools. Real Codex inference passed. Claude connected but its currently configured gpt-oss:20b did not return within the 90-second qualification window; no native provider setting was changed. Hermes still needs its native API configured and a qualified Avalon route.

Harness paired and reconnected using the native encrypted protocol. Agent discovery passed. A stale terminal rejected input before execution; a different existing Monitor target reported unknown/not_submitted. Neither produced a correlated final result. Unconfirmed tasks are never resent automatically. Final-result and spoken-summary logic exists, but live task completion remains an open qualification gate. See harness-native.json, harness-rejection.json and native-platforms.json.

Native local-file music playback produced a real HDMI monitor signal (RMS 565.63, 35,813 samples) through the selected output; only numerical signal evidence was retained. Online music search is not yet qualified.

## Independent Constellation appearance

Avalon adds a fifth appearance using scoped copies of the existing Constellation renderer. The standalone application and its settings stay independent. Avalon settings live at `~/.config/project-avalon/constellation.json`; its existing local memory scene and optional foreground are read without modification. The appearance retains native folder/memory navigation, hover, Alt focus, agent motion modes, solar rotation/direction, labels, links, density and recorded write lights. The panel preview renders the same scene code through Canvas and has no folder/memory click actions.

Local speech level increases galaxy glow and rays. Camera attention offsets galaxy projection and its pointer hit testing together. Synthetic fixture checks passed in a disposable real GNOME Shell, including switch-away cleanup of the delegated renderer; these fixtures do not measure physical camera tracking accuracy. Standalone Constellation layout/navigation/activity/rotation regression checks pass against Avalon's scoped copy. The current login may keep the earlier cached Avalon class: a normal logout/login is needed for the new imported renderer, with no forced Shell restart.

64 Python tests pass, plus JavaScript ownership and galaxy projection tests. Physical HDMI music playback passed with a numerical output-monitor signal. Native Harness worker completion, Claude's current provider/model responsiveness and native Hermes API setup remain open; connected/discovered does not mean completed.
