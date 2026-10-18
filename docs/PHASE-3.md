# Phase 3 — Embodiment and visual finish

**Acceptance status:** implementation and visual/functional qualification delivered; CPU acceptance remains open. The final three consecutive 30-second samples average **3.51% incremental CPU**, above the <3% one-core target. Earlier lower samples are not used to claim a pass. An explicit idle-power mode now caps idle/disconnected animation at 15 FPS and preserves the selected cap during agent/voice activity; its separate measurement does not erase the fixed-30 result. Fixed-30 optimization and login-session measurement remain required.

## What changed

Four original live GPU avatars now share the same geometry/material shader on the desktop and in the Presence Control Center:

- **Ethereal Human:** a dimensional cyan/gold humanoid with a sculpted head, torso, shoulders, arms and hands, luminous particles, a chest core and flowing energy.
- **Neon Sentinel:** a projecting tapered hood around a recessed face, angular shoulder mantle, segmented chest/abdominal armor and gauntlets in violet light.
- **Progre Mascot:** an original friendly teal/gold robot, metallic ear pieces, a rounded visor, blinking eyes and a smile.
- **Abstract Core:** intersecting orbital light volumes around a central nucleus.

The signed-distance volume is raymarched live, with breathing, small head turns, moving surface light and energy filaments. It is not a rendered poster/video loop. All forms use the same nine verified runtime states and share completion/failure/switching colors and activity intensity. Idle gestures are authored animation; they do not claim camera tracking or listening. Microphone and camera remain off until phase 4.

Appearance offers persistent avatar selection, economy/balanced/high quality, 15/30/60 FPS targets and system/animated/still motion. Changes neither restart the runtime nor cancel the conversation. Still mode updates when the state changes, with no continuous GPU redraw. The browser stops drawing when hidden/offscreen; the desktop hides and pauses in overview/lock. Ubuntu's `enable-animations` setting controls system motion on the desktop; the browser follows its own reduced-motion preference.

A lost/unavailable browser GPU displays an actual still capture of the selected avatar and a visible explanation. WebGL restoration recreates GPU resources and resumes the live preview. Missing/malformed/stale desktop state becomes disconnected. No prompts or camera/audio data enter the compositor; it reads only a small private state file. The original wallpaper ownership guard is preserved.

## Rendering and resource budget

The same original `presence.glsl` source is shipped in `static/` and the GNOME extension. A regression check keeps both copies identical. Browser previews and desktop rendering use bounded 36/52/72 ray steps by quality; browser quality also caps pixel density. Native rendering now uses a direct `Clutter.Content` / `Cogl.Pipeline` paint node, removing the intermediate source-texture pass; uniform locations/values are cached and only changed values are sent. Earlier offscreen measurements are retained separately. Frame scheduling follows the selected cap rather than polling at an unrelated frequency.

Measurements use a disposable native GPU GNOME Shell 50.1 on this MS-S1 Max, at the attached monitor's **1920×1080, scale 1, one-monitor** mode. Mutter selected its existing NVIDIA boot-VGA compositor renderer; the desktop GPU selection was not changed. Ollama inference remains on the Radeon under workstation policy. These are real native GPU compositor measurements at the physical monitor's resolution; physical scanout, long-run login-session performance and multi-monitor lifecycle remain phase 5 checks.

- Frame metric: [Clutter Stage after-paint](https://gnome.pages.gitlab.gnome.org/mutter/clutter/signal.Stage.after-paint.html), which occurs before physical presentation. Thirty-second disabled baseline and three consecutive thirty-second animated samples after ten seconds of warmup; default humanoid/balanced, selected cap 30 FPS and explicit idle saver at 15 FPS. Separate fixed-30 samples preserve the original failing case.
- CPU metric: `/proc` user+system ticks; **100% means one CPU core**, with the disabled baseline subtracted. No normalization over the machine's 32 logical CPUs hides the cost.
- Latency metric: 36 atomic sanitized fixture writes to the applied native shader state, sampled every 5 ms; this covers all four avatars × nine states. Separate real-model checks prove the actual event path. Physical input-to-display latency is not claimed.
- Resident memory metric: sum of Linux `smaps_rollup` **PSS** for the compositor increment over a cold disabled baseline, the entire fresh Chromium tree displaying the panel, controller and gateway. The baseline is measured before any avatar pipeline exists, and the process identity must match. Only ordinary GNOME base memory, Ollama inference and test instrumentation are excluded; full fresh-browser overhead is included. Both full-process and incremental counts are retained. The initial full-GNOME count exceeded 750 MiB (`memory-full-process.json`); that includes the existing desktop, so the Avalon footprint uses the measured cold-baseline increment. This is a single-panel idle measurement, not a peak/concurrent-window guarantee.

The default idle-power mode measured **14.89 FPS and 1.83% incremental CPU** across three consecutive 30-second intervals at 1920×1080. Active states use the selected cap, exercised separately. The fixed-30 result is retained as `performance-fixed-30-final.json` and remains above the original CPU target; the idle policy is explicit, not presented as a fixed-30 pass. Exact samples, duration, accounting and gate results are in `evidence/phase-3/performance.json`, `renderer.json` and `memory.json`. Optional 15/60 FPS modes are exercised, with actual rates recorded rather than promised.

## Qualification

- Controller/API unit tests cover appearance persistence, invalid settings, authentication/CSRF, no runtime restart/cancellation during a turn, and identical desktop/browser shader sources. Existing runtime permissions and session tests continue to pass.
- The installed OpenCode + `qwen3-coder:30b` completed a real greeting while all four avatars were selected. The same active turn and gateway PID persisted; each form showed real native working state and completion was observed. Evidence: `live-events.json`.
- Native checks cover all 36 avatar/state combinations, all quality settings, frame caps, still-mode state changes, overview pause, a simulated lock-rendering branch, and malformed/stale data. The simulated lock checks the renderer's branch; a physical lock/unlock lifecycle is not claimed.
- Existing both-direction/concurrent Constellation handover, cleanup, desktop layering and re-enable checks pass against the final renderer.
- Chromium checks 1920×1080, 1440×1000 and 390×844; all avatars selectable, session/history unchanged, explicit and system reduced motion, hidden-view pause, context loss/restoration, unavailable-GPU fallback, offline fallback, no private API caching and no page errors/horizontal overflow.
- The visual review compares the supplied concept image with actual UI and native wallpaper captures. It identified Sentinel's initial similarity to the humanoid; the final form has its own hood, mantle and segmented armor. Final verdict and scope are recorded alongside screenshots.

The native fixture driver enables unsafe Eval **only in the isolated test compositor**, guarded by its environment/runtime directory. It is never installed into the login session. Fixture wallpaper captures identify a synthetic qualification model; user-facing activity is not fabricated.

## Installed state and remaining scope

The control-center update is installed and immediately visible through the Project Avalon application shortcut. Its default remains OpenCode with a locally installed Ollama model. Avatar art is original procedural geometry/material code; thumbnail PNGs are deterministic captures of that same shader, with provenance in ASSETS.md.

GNOME caches imported modules and its renderer module. The installed desktop extension is now version 3, while the existing login session can continue using its previously loaded version. **Log out/in once to load the new desktop avatars.** No forced logout, Shell replacement, driver change or production unsafe-Eval mode was used. Avalon remains the selected wallpaper; Constellation remains disabled.

The older GNOME crash report predates this phase; its cause remains unresolved, and this renderer work does not claim to fix it. Phase 4 remains voice, camera, device selection and Ubuntu action/approval integration; phase 5 retains reboot/suspend, real-login lifecycle, multi-monitor and release packaging qualification. Alternative CLI targets retain their explicit phase 2 blockers.

## Reproduce

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
# Disposable compositor only; never point the fixture driver at the login Shell.
AVALON_TEST_MONITOR=1920x1080 bash scripts/test-desktop.sh
# Enable avalon-test@progretech.com only on .runtime/test-bus, as in PHASE-1.md.
python3 tests/measure-renderer.py
python3 tests/qualify-shell.py --bus-file .runtime/test-bus --out docs/evidence/phase-3/shell
python3 tests/qualify-embodiment.py
python3 scripts/qualify-live-avatars.py
.venv/bin/python scripts/qualify-visuals.py
.venv/bin/python scripts/measure-resident-memory.py
```

Live qualifiers create synthetic conversations or change the selected appearance. Preview capture: `.venv/bin/python scripts/render-avatar-previews.py`. Installation: `python3 scripts/install-control-center.py`. The installer packages the new shader and preserves existing wallpaper/model configuration.
