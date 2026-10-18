#!/usr/bin/env python3
"""Real model proposal and explicit denial. Never dispatches a desktop action."""

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidence/phase-4"
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True)
    page = b.new_page(viewport={"width": 1440, "height": 1000})
    page.goto(
        "http://127.0.0.1:8766/#entry="
        + json.loads((ROOT / ".runtime/control-auth.json").read_text())["entry"]
    )
    page.locator("#access-note").wait_for(state="hidden")
    before = page.request.get("http://127.0.0.1:8766/api/state").json()
    assert not before["active_turn"]
    headers = {"Origin": "http://127.0.0.1:8766", "X-CSRF-Token": before["csrf"]}

    def api(path, data):
        r = page.request.post(
            "http://127.0.0.1:8766" + path, data=data, headers=headers
        )
        assert r.ok, r.text()
        return r.json()

    try:
        api(
            "/api/select",
            {
                "model": before["session"]["model"],
                "title": "Phase 4 approval qualification",
            },
        )
        api("/api/desktop-actions", {"enabled": True})
        api(
            "/api/chat",
            {
                "text": "Please propose opening the current workspace in Ubuntu Files with exactly the Avalon desktop action protocol marker on its own line. Do not run tools or execute the action."
            },
        )
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            state = page.request.get("http://127.0.0.1:8766/api/state").json()
            if not state["active_turn"]:
                break
            time.sleep(0.25)
        assert state["pending_action"], state["messages"][-1]["text"]
        page.locator("#approval-panel").wait_for(state="visible")
        page.screenshot(path=str(OUT / "approval-request.png"), full_page=True)
        if state["devices"]["locked"]:
            assert page.locator("#approve-action").is_disabled()
        page.locator("#deny-action").click()
        page.locator("#approval-panel").wait_for(state="hidden")
        denied = page.request.get("http://127.0.0.1:8766/api/state").json()
        assert any(e["kind"] == "denied" for e in denied["events"])
        (OUT / "approvals.json").write_text(
            json.dumps(
                {
                    "real_model_proposal": True,
                    "selected_model": state["session"]["model"],
                    "explicit_denial_recorded": True,
                    "locked_approval_button_disabled": state["devices"]["locked"],
                    "no_desktop_action_dispatched": True,
                    "method": "Real LampOS/OpenCode model proposal through production controller; owner denial. Successful native Files dispatch is covered by scoped unit fixture, not a physical locked-session test.",
                },
                indent=2,
            )
            + "\n"
        )
        print("Real model proposal and explicit denial passed", flush=True)
    finally:
        api("/api/desktop-actions", {"enabled": before["desktop_actions"]})
        api(
            "/api/select",
            {"session_id": before["session"]["id"], "cancel_current": True},
        )
        b.close()
