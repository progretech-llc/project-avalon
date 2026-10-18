# Project Avalon — specification

Owner: Ed / ProgreTech. Written 2026-10-18 from the owner's brief.

## Purpose and scope

Avalon gives one autonomous AI a visible body on an Ubuntu desktop. LampOS supplies the agent orchestration, voice, vision and existing Harness integration. Avalon supplies its visual embodiment, desktop lifecycle and companion controls. This is a desktop application project, not a website or a replacement operating system.

Two interfaces share one session and one state:

1. **Living Wallpaper:** an animated humanoid, abstract entity or Progre mascot behind ordinary windows and desktop icons. Reacts to real listening, reasoning, writing, executing, approval, speaking, completion and failure events.
2. **Presence Control Center:** selects the target AI platform and model, changes avatars, chats, manages sessions, monitors activity, selects devices and configures enforceable action permissions.

The supplied image sets the visual ambition: luminous particles, convincing humanoid volume, flowing energy, a bright chest core and polished avatar art. The supplied HTML is a previous charter, not a fidelity target. Open WebUI is not a required backend.

## Invariants

- Exactly one selected platform/model represents Avalon's robot. Unrelated terminal sessions are not attached or stopped automatically.
- Avalon and Constellation cannot be enabled together. Starting either must hand over wallpaper ownership and verify the other is disabled before rendering.
- The default target is **OpenCode → Ollama → an installed local model**, discovered on the machine where Avalon is installed. Never silently download a model or switch to a cloud provider.
- Alternatives are Codex, Claude Code and Hermes through LampOS's existing runtime support. Authenticate using each platform's supported flow; do not copy credentials into Avalon source or browser storage.
- Capability availability must come from the selected runtime/model/device. An unavailable camera, missing credential or disconnected runtime is an explicit state.
- Local operation is the baseline. Speech-provider network requirements must be visible; choosing a local reasoning model does not imply upstream LampOS speech is offline.

## Platform and proposed architecture

Initial qualification target: Ubuntu GNOME 50 on Wayland, matching this workstation. Other GNOME versions and X11 require explicit qualification before support is claimed.

Architecture delegated by the owner on 2026-10-18: native GNOME desktop integration, bounded GPU shader effects, an isolated LampOS runtime process and a web-based control center. The phase 1 Go host links LampOS's unmodified exported gateway; Python provides setup and native foundation diagnostics. Asset generation and agent work stay outside the compositor. A desktop launcher opens the control center without terminal use. Use existing installed libraries before adding dependencies. A PWA/browser alone cannot own the Wayland desktop layer.

| Component | Responsibility |
| --- | --- |
| GNOME integration | Attach the visual below windows/icons, lifecycle, monitors, pause/lock/overview, wallpaper ownership |
| Renderer | Animated avatar, particles, gaze, audio response, quality and reduced-motion modes |
| Local Avalon service | One session owner, serialized switching, settings, sanitized event stream, device preferences, authorization boundary |
| LampOS | Existing gateway/runtime, conversation, voice/vision pipeline, Harness routing |
| Control center | Session, platform/model, chat, avatars, devices, activity, permissions and diagnostics |

Keep expensive rendering and network work out of GNOME Shell's main thread. Phase 1 proved the native GPU shader actor technique; phase 3 still must meet the image's avatar quality and performance targets. Reusing Constellation's Cairo animation path is not sufficient evidence that it can deliver the image's avatar quality.

Use a pinned LampOS revision in an isolated project environment. Prefer configuration and documented interfaces. Maintain any necessary portability patch in a canonical ProgreTech fork, with tests and an upstream revision reference. Never install the ARM appliance scripts blindly onto Ubuntu or overwrite existing agent configuration.

## Single runtime and model ownership

The selection is a tuple: platform, provider, model, session. Switching is a serialized operation:

1. Enter `switching`; stop accepting new turns.
2. Cancel or finish the active turn as explicitly selected by the user; stop microphone-to-agent dispatch during transition.
3. Verify the old managed runtime has stopped; unload only an Ollama model owned by Avalon if needed. Never unload another app's model.
4. Validate the new platform, credentials and model availability/capabilities.
5. Start or connect the new runtime and verify a real gateway round trip.
6. Commit the new selection atomically. Failure leaves the robot disconnected or restores the previously verified selection; never show a new model as ready on configuration alone.

A process lock and persisted generation/session identity protect against duplicate control-center windows, queued turns, delayed old events and service restart races. Only the active generation can change the avatar or complete a request. Never replay an executable turn automatically after reconnect.

One model means one **agent reasoning model** owned by Avalon. Disable LampOS's separate realtime conversational LLM in this mode; speech recognition, voice synthesis, VAD and deterministic camera tracking are supporting components, not extra reasoning agents. Show any supporting models/services in diagnostics. No hidden second VLM: semantic image understanding uses the selected model if it supports images; otherwise explain the limitation. Background runtime tasks must use the same selected model and serialized queue, or remain disabled.

## Model discovery and first run

Read the installation machine's loopback Ollama `GET /api/tags`, then use model details/capability inspection and a controlled runtime probe. Exclude embedding-only models from the agent selector. Show names, installed size, capabilities and incompatibility reasons. Do not assume the MS-S1 Max's model list exists on another computer.

First run selects OpenCode and Ollama. Prefer an installed model advertising both vision and tool capabilities that fits available memory. The image-qualified qwen3.5:4b is preferred when present; otherwise choose a fitting nonexperimental capable model. Preserve existing sessions and explicit text-only choices. If no compatible model exists, keep this default target and show setup guidance with refresh. The user chooses downloads outside the automatic discovery flow. A selected model disappearing is a recoverable error, not permission to pick another provider.

Codex/Claude/Hermes selections show their own supported model/provider choices; do not pretend all providers can use every Ollama model. Retain platform preferences separately from the active selection. Persist user configuration under XDG config, private session state under XDG state, and credentials in a supported secret store/restricted runtime configuration.

## Wallpaper ownership with Constellation

Known Constellation UUID: `factory-observatory@progretech.com`. Avalon will have its own stable extension identity.

Exclusivity requires changes on **both** sides, covering extension enable, GUI launch, service restart, autostart and manual `gnome-extensions enable`. A check only in Avalon's button is insufficient. Use one shared per-Shell synchronous ownership registry and stop-before-start handover. A private per-user runtime record reports ownership but never authorizes it; a restarted Shell creates a fresh registry. This phase 1 mechanism covers both extensions and direct enable paths. Disable previous rendering, verify it stopped, transfer ownership, then start the new renderer. Simultaneous starts must serialize; losing startup stays stopped and reports the owner. Stale records require verified recovery. Do not rely on PID alone or kill broad process-name matches.

Disabling or uninstalling Avalon releases its resources and restores the ordinary wallpaper. Restoring Constellation is an explicit handover, without creating an automatic enable loop. Exclusivity applies to the running wallpaper application, not permission to kill unrelated agents or alter their work.

## Event and animation contract

Every normalized event identifies source, runtime, model, session, turn, generation, sequence and timestamp. Retain a bounded local history; redact prompts, camera frames and secrets from public wallpaper text by default.

| Visible state | Required evidence | Visual behavior |
| --- | --- | --- |
| Disconnected / stale | No verified gateway or expired heartbeat | Quiet dim body, clear connection status |
| Idle | Verified connection with no active turn | Slow breathing and subtle particles |
| Listening | Capture actually active | Responsive ear/core glow and input waveform |
| Reasoning | Lifecycle/thinking event | Inward energy movement, focused core |
| Writing | Explicit write/edit tool event | Directional particle flow |
| Executing | Tool execution event | Controlled faster energy pulses |
| Awaiting approval | Runtime permission request | Held amber pulse and control-center action |
| Speaking | Output audio playback actually active | Mouth/core amplitude synchronized with output |
| Completed | Successful terminal event for active turn | Brief completion flourish, then idle |
| Failed / cancelled | Explicit error/cancel terminal event | Distinct bounded feedback; never success |

Where a backend cannot distinguish reasoning from writing, show a truthful general `working` state. Never infer success from silence or use randomized fake telemetry outside a clearly labeled preview. Avatar form and animation state are independent.

## Camera, voice and audio

- Enumerate actual cameras and audio endpoints using Ubuntu/PipeWire-supported interfaces. Persist stable device identities, not transient numeric indexes.
- Input follows Ubuntu's selected microphone; Devices can explicitly select the MS-S1 Max input or another connected microphone. Physical hardware presence alone does not establish a usable microphone, and a noisy analog input must not override the owner's OS selection. Output follows the OS default sink unless overridden.
- A missing saved device produces a visible choice to use the current default; do not silently capture from a different microphone/camera.
- Camera tracking maps detected positions to damped head/eye direction. On face/object loss return to neutral smoothly. Local tracking may use ordinary CV without another reasoning model. Semantic vision uses the same selected vision-capable model. A fresh camera image accompanies each addressed spoken command while vision is enabled; missing/stale images fail visibly before dispatch.
- Microphone RMS/VAD drives listening animation; generated output RMS drives speaking animation. Avoid feedback loops and handle interruption. Device use must follow the controls shown in the panel.
- Camera and mic have persistent visible activity indicators, independent mute/disable controls and a stop-all action. Lock pauses capture and output and hides sensitive overlays. Resume follows the user's settings; an explicit manual off remains off.
- Stop-all cancels the managed turn, stops further action dispatch and releases capture/playback. Report any command already outside Avalon's cancellation boundary rather than claiming it was undone.

## Control-center workflows

The first view shows the avatar, real connection status, active platform/model, current session, chat and a concise recent activity list. Separate controls cover avatar/quality, devices, permissions and diagnostics. Allow multiple saved sessions but one active robot session. Switching avatars never launches another model.

The target image's bright cyan/gold humanoid, purple sentinel, Progre mascot and abstract core are the avatar family. For Progre, the latest owner reference in docs/reference/progre-owner-reference.png supersedes the generic concept: a face only, tiny hands/feet, no torso/chest; side spheres are eyes, white slashes nose and central zigzag mouth. Preserve that artwork as an animated textured cutout. Remove the background star field while retaining flowing rays. At least one convincing animated humanoid is required before the visual phase passes; cards, emoji, a flat outline or a looping poster do not meet it. Each shipped avatar must support all meaningful states. Use the owner's image for comparison and record all sourced/generated asset provenance.

Permission controls cover workspace scope, file writes, commands, desktop automation, camera, microphone and network/provider access. Runtime-native controls must enforce them; displaying a switch is not enforcement. Preserve platform restrictions and surface unsupported controls as unavailable. Approvals bind to exact session/turn/action; stale approvals cannot authorize a new request. Do not enable bypass flags to make the demo work. No arbitrary privileged execution endpoint exposed to the renderer.

## Reliability and quality gates

Bind the application service to loopback. Validate Origin/Host, authenticate state-changing requests, protect against CSRF and validate settings at the service boundary. A local webpage is not automatically trusted. Keep credentials server-side and agent tool access scoped. Raw upstream admin endpoints, shell execution and factory reset are not renderer APIs.

Renderer crash must preserve the desktop and runtime; service crash must not duplicate a task. Bound queues, event history, framebuffers and reconnection backoff. Pause animation on lock/hidden desktop and offer reduced motion/static fallback. Qualify multi-monitor scaling, display hotplug, suspend/resume, logout/login and default-device changes.

Measure on the MS-S1 Max: target 30 FPS, optional 60 FPS; event-to-animation latency p95 under 500 ms; desktop-idle incremental CPU below 3% and combined Avalon resident memory below 750 MiB excluding inference. These are acceptance targets, not measured claims. Record CPU accounting, resolution, monitor count, quality, memory metric and sample duration with results. Keep inference on the Radeon 8060S and CUDA asset generation on the RTX 5060 Ti under workstation policy.

Ship a documented per-user installer, app-list/Desktop launcher, on-demand startup by default, update and uninstall paths, reversible wallpaper handover, and a diagnostics export without secrets. Distinguish source pushed, app packaged, installed and hardware-qualified in every status report.
