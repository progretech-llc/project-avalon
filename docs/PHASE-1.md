# Phase 1 — foundation and compatibility

Completed 2026-10-18 on Ubuntu / GNOME Shell 50.1 / Wayland, x86_64. Companion Constellation change: [9e745c2](https://github.com/progretech-llc/constellation/commit/9e745c2).

## Delivered

- Pinned LampOS `f3f708859d175a8a271e1a7b5e17dca9dee50361`, checksum-verified Go toolchain and reproducible build. No upstream source changes or appliance installer required.
- A separate per-user Go process hosts LampOS's exported OpenCode gateway. Private token, config, session, attachments and workspace stay in ignored Avalon state. A kernel process lock prevents a second runtime owner.
- A native GNOME desktop actor runs the bounded GLSL energy-core proof. It is click-through and below ordinary windows and DING desktop icons. Per-monitor actors rebuild on monitor changes; redraw pauses in Overview and on lock. Final avatar art and activity-driven motion remain later phases.
- Shared synchronous ownership code in Avalon and Constellation: stop the old renderer, claim a generation-specific lease, disable its extension, then render the new wallpaper. A private owner record is diagnostic only. Shell restart creates a fresh registry, so stale disk records cannot block it.
- Constellation's native power switch now requests an actual extension enable/disable and follows external handovers. Direct GNOME enable restores its power setting while retaining appearance settings.
- On-demand runtime service, native foundation controls and app-menu/Desktop launchers. No login autostart enabled. Camera and microphone remain off.

## Evidence and checks

| Gate | Observed result |
| --- | --- |
| Real LampOS turn on Ubuntu | OpenCode 1.19.3 → local Ollama `gpt-oss:20b` returned `AVALON_42`; latest attributed turn took 14,038 ms and emitted four correlated events. Model was already installed and loaded; no download or cloud fallback |
| Actual animated desktop | Real isolated GNOME 50.1 Wayland compositor, 1600×900, with DING and a normal Wayland window. Two frames differed at 133,890 pixels in a 1,050,000-pixel region excluding the clock |
| Bidirectional handover | Avalon → Constellation → Avalon: exactly one wallpaper actor, previous extension inactive, owner matches renderer |
| Concurrent requests | Ten concurrent enable pairs settled to one owner and one renderer |
| Failure cleanup | Stale lease release cannot clear the new owner; failed stop refuses takeover; disable destroys actors and timers |
| Compositor recovery | Disposable Shell killed with SIGKILL; replacement Shell loaded the extensions, replaced the stale PID record and passed handover tests again |
| Runtime recovery | Installed service killed with SIGKILL; systemd restarted it and a real resumed model turn passed. A second runtime process was rejected by the kernel lock |
| Configuration isolation | `strace` attributed file operations to Avalon and every descendant during a real turn: zero writes to global OpenCode, Codex or Constellation configuration. Other active CLI sessions changed global files during broad fingerprint checks; those checks were not counted as passes |
| Existing Constellation behavior | 50 Python tests and existing GJS layout/navigation checks passed; four new native power/handover tests passed |
| Avalon boundaries | Ownership tests, two configuration tests, upstream LampOS OpenCode gateway tests, Go vet, Python compile and Git whitespace checks passed |
| Original references | Original HTML and PNG retained unchanged; their hashes match the initial commit |

[Desktop/window/icon capture](evidence/phase-1/desktop-with-window.png) · [two animation frames](evidence/phase-1/animated-desktop-a.png) / [second frame](evidence/phase-1/animated-desktop-b.png) · [Shell results](evidence/phase-1/shell-results.json) · [recovery/layering](evidence/phase-1/recovery-and-layering.json) · [final runtime turn](evidence/phase-1/final-runtime-turn.json) · [write attribution](evidence/phase-1/config-isolation.json).

The qualification driver permits Shell inspection only inside the disposable test session. It refuses the real login session and is never installed by the foundation installer. No debug/unsafe mode was enabled in the login session.

## Build and install

From this checkout, with existing OpenCode, Ollama, GNOME 50, Python GTK bindings and Git:

```bash
python3 scripts/build-runtime.py
python3 scripts/configure-runtime.py --state .runtime/agent --model gpt-oss:20b
python3 scripts/install-foundation.py
```

Use an installed model name from your own Ollama inventory in place of the example. This phase's explicit configuration argument is not the phase 2 automatic model picker. The model and small-model setting are identical; tool permissions are explicitly denied. The pinned gateway's upstream `--auto` flag still exists: interactive approval forwarding is not qualified and remains a phase 2 gate.

The installer updates both local wallpaper extension packages when the sibling Constellation checkout is present. It preserves source settings and installs `project-avalon-runtime.service` without enabling autostart. It does not run Constellation's full installer or change agent configuration.

**Installed state on this workstation:** launcher and service installed; both extension packages installed. New JavaScript loads in the real Wayland login session after logout/login. The current desktop was left running Constellation; no logout or restart was forced. Qualification was performed in a real, separate GNOME compositor, not in the live login session. The runtime and test compositor are stopped after qualification to keep the foundation on demand.

Open **Project Avalon** from the application menu or Desktop. After logout/login, its buttons enable Avalon, return to Constellation, start/stop the local gateway and run a text-only connection check. The initial energy core is a foundation proof, not the final humanoid.

## Repeat the checks

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.test.mjs
.tools/go/bin/go test go.autonomous.ai/os/runtimes/opencode/gatewayd
.tools/go/bin/go vet ./cmd/...
```

In another terminal, `scripts/test-desktop.sh` starts the isolated compositor. Enable its qualification driver and run the integration checks:

```bash
gdbus call --address "$(cat .runtime/test-bus)" --dest org.gnome.Shell \
  --object-path /org/gnome/Shell --method org.gnome.Shell.Extensions.EnableExtension \
  avalon-test@progretech.com
/usr/bin/python3 tests/qualify-shell.py --bus-file .runtime/test-bus --out .runtime/evidence
```

The native test driver is deliberately excluded from installation packages. Use Ctrl+C in the test terminal to stop the compositor. Ownership source copies in both repositories must remain identical.

## Rollback / disable

Disable Avalon with GNOME Extensions or the foundation controls; enable `factory-observatory@progretech.com` to return to Constellation. `systemctl --user stop project-avalon-runtime.service` releases the gateway and its process lock. Neither operation unloads another application's model.

Removing the foundation means stopping that service, uninstalling `avalon@progretech.com` through GNOME Extensions, and removing only Avalon's user service/launcher files. Keep private runtime data until the owner chooses to discard it. The shared Constellation guard is harmless when Avalon is absent.

## Deliberate scope limits

This validates the native desktop host, ownership protocol and LampOS **gateway** path. It does not claim a full os-server/HAL installation, speech pipeline, camera path, Harness task, model switching, production approval flow or finished avatar. Those are explicit later-phase deliverables. Hardware multi-monitor hotplug, suspend/resume, real-login lifecycle, long-run GPU resource targets and the final visual comparison remain phase 5 qualification gates. No performance target is claimed from a headless compositor capture.
