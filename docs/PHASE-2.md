# Phase 2 — One brain and Presence Control Center

## Delivered behavior

The Project Avalon app-menu/Desktop shortcut starts the local control service on demand and opens an authenticated Presence Control Center. It discovers completion models already installed in local Ollama, labels tool and vision capabilities, and defaults to an installed coding model that fits the available-memory selection budget. Nothing is pulled automatically. The selected runtime remains OpenCode through the pinned, unmodified LampOS gateway.

One controller owns one gateway connection and one active turn. SQLite retains conversations, permission choices, the selected session and native OpenCode session identifiers. Switching or changing access stops the complete systemd runtime control group before another connection starts. Generations and request/run identifiers fence late events. An interrupted turn is recorded; the controller does not replay it on restart. The pinned upstream gateway itself retains its native missing-session retry behavior.

The interface includes real chat, saved-session resume, model selection, stop/disconnect, recent activity, workspace permission changes and a wallpaper selector. The WebGL preview reads actual runtime states. The desktop extension reads a small private, sanitized state file with a heartbeat; missing/stale input becomes disconnected. A completed tool event is recorded as completed/error rather than inventing a running tool state. The current CLI often reports tools only after they finish, so a long tool execution can remain “working.” Full avatars remain phase 3.

## Native permissions

Conversation-only starts with every tool denied. Read mode allows native file reads within the selected workspace. Edit mode adds native edits within that workspace. Search/list tools remain denied because their permission patterns describe searches rather than a reliable directory boundary. Web tools and additional agents remain denied. Optional status commands are limited to `pwd`, `git status --short`, and `git diff --stat`; the UI restarts the connection when access changes.

OpenCode 1.19.3 checks reads using absolute paths and edits using worktree-relative paths. Avalon derives that relative edit pattern; paths containing wildcard characters are rejected. Project and Claude configuration inheritance are disabled and the gateway uses an isolated HOME/XDG configuration. `model` and `small_model` select the same local model. This is native CLI permission enforcement, not an operating-system sandbox. A user-selected repository and its own files remain trusted inputs.

The upstream permission behavior is also described in the [OpenCode issue documenting absolute read and worktree-relative edit patterns](https://github.com/anomalyco/opencode/issues/26524). Runtime evidence is authoritative for the installed version; current V2 documentation describes a different permission schema.

## Other target platforms

The picker exposes installed-platform status and explicit blocking reasons. These targets are withheld from activation:

- Codex: the pinned LampOS adapter requests `approvalPolicy: never` and `sandbox: danger-full-access`; restricted action controls and cancellation have not been qualified.
- Claude Code: the pinned adapter uses `--dangerously-skip-permissions`; a restricted connection and native authentication have not been qualified.
- Hermes: no qualified configured LampOS connection; configure through its native GUI. Avalon does not add a custom Hermes integration.

The phase 2 exit gate explicitly permits an honest blocking reason for these alternatives. Their chat/cancellation is not claimed to work. Voice, vision, device selection and broader Ubuntu actions remain phase 4.

## Browser boundary and offline behavior

Waitress listens only on `127.0.0.1:8766`. A private launcher bootstrap token in the URL fragment is exchanged for an HttpOnly, SameSite Strict signed session, then removed from the address bar. Private mutations require allowed Host, Origin, JSON and a CSRF token. Private API responses are `no-store`; CSP disallows inline/eval scripts and framing. Runtime/auth files and session databases stay private and ignored by Git.

The PWA caches public shell assets and an offline fallback, never authenticated API data, prompts or POST requests. It does not queue/replay offline actions. Offline navigation explains how to reopen the local app. No autostart was enabled.

## Constellation off-switch repair

The desktop background settings still referenced the historical `Tools & Assets/Constellation/data/progretech-constellation.png`. Stopping its animation exposed that static image. The off switch and shared wallpaper ownership guard now replace only that known legacy URI with the GNOME schema default. Unrelated custom backgrounds remain untouched. No earlier background backup existed, so recovery used Ubuntu's native light/dark defaults rather than claiming to restore an unknown prior image.

## Checks and evidence

- 19 Avalon Python controller/configuration/web tests; Go build/tests; JavaScript ownership test and syntax checks.
- 53 Constellation Python tests in its venv and four native GTK control tests through system Python.
- Real local OpenCode/Ollama chat; file editing, permission revocation and process-group cancellation in a dedicated ignored qualification workspace. Results: `evidence/phase-2/runtime.json`.
- Duplicate controller and gateway processes reject a second owner using held flock locks. Real model switching reaps the old gateway and CLI children; a control-service restart preserves the selected session/history without replay. Results: `evidence/phase-2/lifecycle.json`.
- Isolated GNOME Shell: both handover directions, ten concurrent starts, actor cleanup, re-enable, desktop layering, all nine state values, stale heartbeat, legacy-background reset and preservation of a custom dark wallpaper. Results: `evidence/phase-2/shell/`. Its screenshot unsafe-mode banner belongs only to the disposable, guarded test compositor; the test driver is never installed into the login session.
- Chromium: 1440×1000 desktop and 390×844 mobile, no page errors or horizontal overflow, target-blocking reasons, Sessions/Permissions views, offline fallback, no private API in caches. Visual review disposition: **ship**, scoped to the phase 2 control center; motion inspected in source. Screenshots: `evidence/phase-2/ui/`.

Live qualification commands (they create synthetic conversations and change the selected test session):

```sh
.venv/bin/python scripts/qualify-controller.py
.venv/bin/python scripts/qualify-browser.py
.venv/bin/python scripts/qualify-lifecycle.py
# First launch scripts/test-desktop.sh in a disposable process, then enable
# avalon-test@progretech.com only on that isolated bus, never the login session.
python3 tests/qualify-shell.py --bus-file .runtime/test-bus --out docs/evidence/phase-2/shell
python3 tests/qualify-phase2-shell.py
```

## Installed state and limits

Avalon is active in the login session and Constellation is disabled. The installed phase 2 extension files are version 2; GNOME's current process still holds the version 1 module loaded at login. The visible abstract core is therefore active now; its new live activity-state behavior loads at the next logout/login. The control-center preview updates immediately. No forced logout or Shell restart was performed.

The user's GNOME crash dialog reports `/usr/bin/gnome-shell`, SIGABRT, dated **2026-10-18 14:01:43**, before this phase 2 runtime. The stack includes Mesa `libgallium`; that alone does not establish the cause. The existing report was preserved. This delivery does not claim to fix the desktop crash or change Ubuntu drivers.

Installation is on-demand and local, not a packaged release. Phase 5 still qualifies clean installation, upgrades/uninstall, reboot/suspend/multiple monitors and measured hardware performance. Source push verification is separate from installation and desktop activation.
