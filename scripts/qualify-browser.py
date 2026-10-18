#!/usr/bin/env python3
"""Explicit live qualification; uses synthetic data in the installed local service."""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
(root / ".impeccable/review").mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True)
    context = b.new_context(viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(
        "http://127.0.0.1:8766/#entry="
        + json.loads((root / ".runtime/control-auth.json").read_text())["entry"]
    )
    page.locator("#access-note").wait_for(state="hidden")
    page.wait_for_timeout(500)
    page.locator("#platform").select_option("codex")
    assert page.locator("#connect").is_disabled()
    assert "unrestricted" in page.locator("#platform-note").inner_text()
    page.locator("#platform").select_option("opencode")
    page.locator('[data-page="permissions"]').click()
    assert page.locator("#permission-form").is_visible()
    page.screenshot(
        path=str(root / ".impeccable/review/permissions.png"), full_page=True
    )
    page.locator('[data-page="sessions"]').click()
    assert page.locator("#session-list").is_visible()
    page.locator('[data-page="presence"]').click()
    page.screenshot(path=str(root / ".impeccable/review/desktop.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(root / ".impeccable/review/mobile.png"), full_page=True)
    assert not page.evaluate("document.documentElement.scrollWidth>innerWidth")
    page.evaluate("async () => { await navigator.serviceWorker.ready; }")
    page.reload()
    page.wait_for_function("() => navigator.serviceWorker.controller !== null")
    private_cached = page.evaluate(
        'async () => { const all=await caches.keys();let found=[];for(const key of all){for(const r of await (await caches.open(key)).keys()){if(new URL(r.url).pathname.startsWith("/api/"))found.push(r.url)}}return found;}'
    )
    assert not private_cached
    context.set_offline(True)
    page.goto("http://127.0.0.1:8766/unavailable")
    assert "offline" in page.locator("body").inner_text().lower()
    print(
        json.dumps(
            {
                "browser_errors": errors,
                "mobile_overflow": False,
                "blocked_target": True,
                "permissions_sessions": True,
                "private_cached": private_cached,
                "offline": True,
            }
        )
    )
    assert not errors
    b.close()
