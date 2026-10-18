# Five-phase delivery plan

No phase 0 and no additional phase for release. Each phase ends with inspectable artifacts and recorded checks. Status on 2026-10-18: the specification/research portion of phase 1 is delivered; implementation and runtime qualification have not started.

| Phase | Deliverables | Exit gate | Current status |
| --- | --- | --- | --- |
| **1. Foundation and compatibility** | Authoritative spec; pinned LampOS dependency plan; isolated Ubuntu runtime spike; desktop-host proof; shared wallpaper ownership protocol implemented in Avalon and Constellation | A real LampOS turn on Ubuntu; an actual animated desktop layer behind icons/windows; starts in both directions and simultaneous-start/crash recovery prove only one wallpaper runs; no existing configuration overwritten | Specification and source research done; runtime/desktop/exclusivity proofs pending |
| **2. One brain and control center** | Real platform/model picker, local Ollama discovery, chat, one active session, event normalization, serialized switching, persisted settings; native permission enforcement for selected runtime | OpenCode + a locally installed Ollama model completes a task; a second start cannot create a second owner; switching cancels/drains and fences old events; Codex/Claude/Hermes each pass real authentication/chat/cancel checks or show an explicit blocking reason; denied actions remain denied | Pending |
| **3. Embodiment and visual finish** | GPU avatar renderer, luminous humanoid plus sentinel/mascot/abstract forms, state animations, control-center polish, reduced motion, performance controls; scoped assets and provenance | Desktop and control center visually reviewed against the supplied image at actual monitor sizes; every shipped avatar reacts to real events; no fake activity presented as real; measured resource/latency targets pass | Pending |
| **4. Voice, vision and Ubuntu actions** | LampOS capture/playback integration, PipeWire device selection, camera-driven gaze, selected-model vision support, interruption, action scopes and approvals, stop-all | Real microphone command → selected agent → audible response; user-selected/default devices work; camera gaze tracks and recovers; unavailable vision is honest; device hotplug, lock, mute, interruption and denied/stale approvals pass; no second conversational model | Pending |
| **5. Qualification and release** | Installer, launchers, on-demand services, update/uninstall, diagnostics and user guide; pinned package and release evidence | Clean installation and removal; reboot/login, suspend/resume, multi-monitor, conflict, crash, offline and permission tests; hardware performance report; source pushed and verified against live GitHub; installed/deployed status recorded separately | Pending |

## Why this order

Prove Ubuntu and wallpaper ownership before investing in avatar art. Establish real events and one runtime before animating them. Finish the visual body before connecting always-on sensing. Package only after the integrated robot survives failure and device lifecycle tests.

## Rules for calling a phase complete

Record the commit, environment, commands/checks, observed results and remaining limitations. A screenshot cannot establish model integration, and a successful API probe cannot establish visual quality. Source research is not a runtime test. Explicitly carry a blocked gate forward; do not relabel it complete to fit the five-phase count.

No completion dates are promised before the phase 1 runtime spike measures the LampOS Ubuntu port. The default OpenCode off-device path and native action permissions are known integration risks, not a reason to substitute Codex silently.
