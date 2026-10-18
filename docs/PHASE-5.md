# Phase 5 — stabilization and release qualification

Phase 5 remains in progress. This iteration replaces the static Progre portrait with a procedural light-being, adds camera attention, local session speaker matching and customizable Kokoro speech. Earlier evidence records the preceding implementation and must not be treated as current artwork or current voice behavior.

## Current behavior

The selected installed vision/tool model remains the only conversational model. Voice and image questions use that same LampOS/OpenCode/Ollama session. No reasoning model is downloaded. Chat mode disables extended reasoning and includes current local time; spoken/awake replies request concise speech. Typed replies are spoken too while awake when Speak replies is enabled.

Wake starts selected capture, local Whisper/Silero recognition and local synthesis. The default listener phrase is `hey avalon`; the owner's saved phrase is preserved. A bare wake phrase permits one following command. After a normal reply another wake phrase is required unless ten-second follow-ups are explicitly enabled. Speech endpoint silence is 0.9 seconds. Capture is suppressed while the model or speaker is busy.

With session voice matching enabled, the first addressed utterance enrolls a local NeMo SpeakerNet embedding held only in listener RAM. Later commands must match; unrelated ambient speech cannot enroll. Sleep/reset discards ownership. This reduces accidental pickup; it is not identity authentication or proof that every similar speaker will be rejected.

Devices offers Kokoro/Piper, female/male/robotic style, pitch from -12 to +12 semitones, speed 0.65–1.6 and a saved-settings preview. Kokoro provides the distinct male/female voices; Piper retains its existing voice. Rubber Band changes pitch without changing duration; robotic adds modulation. Apply devices saves changes and sleeps capture. Kokoro is CPU-only and warm while awake; it is released on sleep. There is no additional conversational model.

PCM output is 24 kHz. PipeWire backpressure clocks playback with a 150 ms buffer. Redundant per-block sleeps caused audible breaks and were removed. Visual heartbeat writes remain atomic but skip durable disk sync; saved settings retain durable writes. The owner confirmed the revised preview sounded smooth through the selected HDMI speakers.

Camera attention holds a detected face, otherwise follows meaningful foreground movement, then eases back to center. All four procedural avatars consume gaze. Progre is one face with lateral sphere eyes, slash nose, enclosed zigzag mouth, tiny hands and feet, without a torso. It uses the humanoid's particle/light material and live motion. The old PNG remains only for compatibility with GNOME's cached version 5 module. No background star field is drawn.

Sleep, Stop all, lock, model/session switch and shutdown release owned capture/playback. The Chrome control panel uses its own profile and graphical-session-bound service; shared Firefox is untouched. The native corner wake button remains. Normal disable/enable loads the new shader into cached version 5 without a forced logout; version 6 drops the unused texture setup at the next normal login.

## Current evidence

- `voice-customization.json`: actual local Kokoro female/male/robotic/pitched synthesis; warm first PCM about 0.13–0.16 s. Authored 220 Hz tone becomes 440 Hz at +12 semitones with duration preserved. Synthetic same/different speaker comparisons pass the configured threshold. This is not live owner calibration.
- `kokoro-output.json`: actual preview through the selected physical HDMI sink, in-memory monitor reduced to RMS, plus owner confirmation of smooth playback. Cold preview startup about 0.73 s after text is ready; this excludes conversational model response time.
- `camera-motion.json`: synthetic foreground motion maps left/right correctly; no frames retained.
- `camera-live.json`: real Logitech capture opens, publishes attention and releases. No camera content is committed.
- `motion/`: disposable real GNOME compositor renders all four avatars with time-separated gaze/speech fixtures. These are synthetic attention inputs, not a measurement of physical gaze accuracy.
- `shell-motion/`: exclusive wallpaper ownership, switching, ten concurrent starts, cleanup and re-enable pass in the disposable compositor.
- `motion-finish-review.md`: fresh independent visual review; desktop/mobile controls and procedural anatomy accepted.
- 50 Python tests and ownership JavaScript checks pass. Syntax and focused fatal-error lint pass. Broad advisory lint still reports pre-existing and style findings; it is not claimed clean.

## Remaining release gates

Live owner wake/speaker calibration in ordinary room conversation; physical unplug/replug and default-route changes; logout/lock during real capture; long-session recovery/resource tests; update/uninstall and diagnostics delivery. Phase 3's fixed-30-FPS CPU gate remains open. No additional project phase is introduced. Current handoff keeps `hey avalon`, the owner's humanoid avatar, and capture asleep.
