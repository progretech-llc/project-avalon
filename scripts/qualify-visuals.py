#!/usr/bin/env python3
"""Exercise the installed avatar UI and its GPU/static/offline paths with synthetic data."""

import json, subprocess, time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".impeccable/review"
OUT.mkdir(parents=True, exist_ok=True)
entry = (
    "http://127.0.0.1:8766/#entry="
    + json.loads((ROOT / ".runtime/control-auth.json").read_text())["entry"]
)


def runtime_pid():
    return subprocess.check_output(
        [
            "systemctl",
            "--user",
            "show",
            "project-avalon-runtime.service",
            "-p",
            "MainPID",
            "--value",
        ],
        text=True,
    ).strip()


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True)
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(entry)
    page.locator("#access-note").wait_for(state="hidden")
    page.wait_for_function(
        '() => Number(document.querySelector("canvas").dataset.frames)>0'
    )
    before = page.request.get("http://127.0.0.1:8766/api/state").json()
    pid = runtime_pid()
    assert not before["active_turn"]
    for avatar in ("sentinel", "mascot", "abstract", "ethereal"):
        page.locator('[data-page="appearance"]').click()
        button = page.locator('[data-avatar="' + avatar + '"]')
        button.click()
        page.wait_for_function(
            'a=>document.querySelector(`[data-avatar="${a}"]`).getAttribute("aria-pressed")==="true"',
            arg=avatar,
        )
        page.locator('[data-page="presence"]').click()
        page.wait_for_function(
            'a=>document.querySelector("canvas").dataset.avatar===a', arg=avatar
        )
        page.wait_for_timeout(150)
        assert runtime_pid() == pid
    page.locator('[data-page="appearance"]').click()
    page.locator("#render-motion").select_option("reduced")
    page.locator("#appearance-form").evaluate("form=>form.requestSubmit()")
    page.wait_for_timeout(300)
    page.locator('[data-page="presence"]').click()
    page.wait_for_timeout(300)
    frames = page.locator("canvas").get_attribute("data-frames")
    page.wait_for_timeout(1000)
    assert page.locator("canvas").get_attribute("data-frames") == frames
    page.locator('[data-page="appearance"]').click()
    page.locator("#render-motion").select_option("system")
    page.locator("#render-quality").select_option("balanced")
    page.locator("#render-fps").select_option("30")
    page.locator("#appearance-form").evaluate("form=>form.requestSubmit()")
    page.wait_for_timeout(350)
    page.locator('[data-page="presence"]').click()
    page.emulate_media(reduced_motion="reduce")
    page.wait_for_timeout(350)
    frames = page.locator("canvas").get_attribute("data-frames")
    page.wait_for_timeout(600)
    assert page.locator("canvas").get_attribute("data-frames") == frames
    page.emulate_media(reduced_motion="no-preference")
    page.locator('[data-page="sessions"]').click()
    page.wait_for_timeout(300)
    frames = page.locator("canvas").get_attribute("data-frames")
    page.wait_for_timeout(600)
    assert page.locator("canvas").get_attribute("data-frames") == frames
    page.locator('[data-page="presence"]').click()
    page.evaluate(
        '() => {window.loss=document.querySelector("canvas").getContext("webgl").getExtension("WEBGL_lose_context");window.loss.loseContext();}'
    )
    page.locator("#avatar-fallback").wait_for(state="visible")
    page.wait_for_timeout(1000)
    page.evaluate("() => window.loss.restoreContext()")
    page.locator("#avatar-fallback").wait_for(state="hidden")
    page.wait_for_timeout(300)
    page.screenshot(path=str(OUT / "desktop.png"), full_page=True)
    page.locator('[data-page="appearance"]').click()
    page.screenshot(path=str(OUT / "appearance-desktop.png"), full_page=True)
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.locator('[data-page="presence"]').click()
    page.wait_for_timeout(300)
    page.screenshot(path=str(OUT / "desktop-1440.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(300)
    page.screenshot(path=str(OUT / "mobile.png"), full_page=True)
    assert not page.evaluate("document.documentElement.scrollWidth>innerWidth")
    page.locator('[data-page="appearance"]').click()
    page.screenshot(path=str(OUT / "appearance-mobile.png"), full_page=True)
    assert not page.evaluate("document.documentElement.scrollWidth>innerWidth")
    after = page.request.get("http://127.0.0.1:8766/api/state").json()
    assert after["session"]["id"] == before["session"]["id"]
    assert after["messages"] == before["messages"]
    assert runtime_pid() == pid
    page.evaluate("async () => {await navigator.serviceWorker.ready;}")
    page.reload()
    page.wait_for_function("()=>navigator.serviceWorker.controller!==null")
    cached = page.evaluate(
        "async()=>{let all=[];for(const name of await caches.keys())for(const r of await (await caches.open(name)).keys())all.push(new URL(r.url).pathname);return all;}"
    )
    assert not any(x.startswith("/api/") for x in cached)
    context.set_offline(True)
    page.goto("http://127.0.0.1:8766/offline-check")
    assert "offline" in page.locator("body").inner_text().lower()
    fallback = browser.new_context(viewport={"width": 1440, "height": 1000})
    fallback.add_init_script(
        'const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(kind,...args){return kind==="webgl"?null:original.call(this,kind,...args)};'
    )
    static = fallback.new_page()
    static.goto(entry)
    static.locator("#avatar-fallback").wait_for(state="visible")
    static.locator("#access-note").wait_for(state="hidden")
    static.screenshot(path=str(OUT / "static-fallback.png"), full_page=True)
    assert not errors, errors
    result = {
        "avatars_selectable": 4,
        "runtime_restarts_on_appearance": 0,
        "session_history_unchanged": True,
        "reduced_and_system_motion_stop_frames": True,
        "hidden_preview_stops_frames": True,
        "context_loss_and_restore": True,
        "no_webgl_static_avatar": True,
        "mobile_overflow": False,
        "offline_fallback": True,
        "private_api_cached": False,
        "page_errors": errors,
        "viewports": [[1920, 1080], [1440, 1000], [390, 844]],
    }
    (ROOT / "docs/evidence/phase-3/browser.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result, indent=2))
    browser.close()
