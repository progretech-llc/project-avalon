# Wallpaper chat

In **Presence → Wallpaper chat**, enable **Show the floating chatbox**. It is off on a fresh installation. Pick Anchored left, Anchored right or Movable, choose background opacity and apply. Movable mode lets you drag the message area (input and buttons keep their normal actions); the normalized position is saved for the primary monitor. Both anchors and movable positions respect the GNOME work area, leaving clearance for Ubuntu’s fixed dock and panel. Unsaved placement and opacity choices survive background state refreshes until Apply succeeds. The two visible bubbles show the latest input/output pair, while the existing selected session retains its history. Enter sends; Escape leaves text focus. Long messages scroll, with a bounded wallpaper excerpt for extremely long text; the control center keeps the stored message.

The speaker button toggles automatic final-reply readout for wallpaper requests. Muting wallpaper replies does not change ordinary voice conversation settings. Turning the overlay off hides its message projection; it does not cancel the selected agent's work or clear history. Switching sessions changes the displayed pair and rejects an in-flight submission aimed at a stale session. Device capture and the active model remain separately controlled. Speech uses the installed local voice path and its selected output.

The overlay is desktop-only: it hides in Overview, while locked, when the controller heartbeat expires, and when an ordinary window covers it. It is one interactive native actor on the primary monitor. Native controls use the existing local authentication, origin checks and CSRF-protected API through the installed helper; no new web service, model or transcript store is introduced.

Install using `python3 scripts/install-foundation.py`. Refresh the control-center page for the new controls. A normal logout/login is required to load new extension JavaScript in the login Shell; installing source alone does not activate the overlay in an already running Shell. Do not force-restart the user's GNOME session.

## Qualification

- Python regression covers strict settings, off default, bounded text projection, authenticated/CSRF routes, stale/busy turn refusal, two turns retaining one native runtime/session, and wallpaper speech independent of ordinary voice replies.
- `tests/qualify-wallpaper-chat.py` runs only in the guarded disposable GNOME Shell from `scripts/test-desktop.sh`. It uses real virtual pointer and keyboard events for text entry, Enter send, speaker activation and dragging. The test stubs command transport; it never submits to the real account/model. It checks both anchors, opacity, default/off/stale/Overview hiding and wallpaper-owner cleanup.
- Native UI receipt and screenshot: `docs/evidence/wallpaper-chat/`. Browser Presence controls checked at 390 and 1280 pixels. Backend and installed helper checks qualify transport separately. Physical speaker output was not requalified for this feature.
- Avalon was idle during the control-service refresh. Its selected session and stored message count were preserved; the overlay remained off.

## Codex permissions

Ed explicitly requested full access on 20 October 2026. The native Codex app server's effective configuration for Avalon's actual workspace reports `approval_policy: never` and `sandbox_mode: danger-full-access`. The pinned native gateway also starts new Codex threads with those settings. This was already configured; no second Codex home, wrapper or global authentication change was needed. No model turn was started for this check. See `codex-permissions.json` and the [official app-server reference](https://learn.chatgpt.com/docs/app-server). Ordinary OS file permissions still apply.
