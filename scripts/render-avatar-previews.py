#!/usr/bin/env python3
"""Capture original GPU-rendered avatar thumbnails; no external image assets."""

from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True)
    page = browser.new_page(
        viewport={"width": 600, "height": 800}, device_scale_factor=1
    )
    page.goto("http://127.0.0.1:8766/")
    page.evaluate("""async () => {
        document.body.replaceChildren();
        const canvas=document.createElement('canvas');canvas.id='asset';canvas.style.cssText='position:fixed;inset:0;width:100vw;height:100vh';document.body.append(canvas);
        window.setAvatar=(await import('/static/core.js')).mountCore(canvas);
    }""")
    for avatar in ("ethereal", "sentinel", "mascot", "abstract"):
        page.evaluate(
            'avatar => window.setAvatar("idle", {avatar,quality:"high",motion:"reduced",fps:30})',
            avatar,
        )
        page.wait_for_function(
            'avatar => document.querySelector("canvas").dataset.avatar === avatar',
            arg=avatar,
        )
        page.locator("canvas").screenshot(
            path=str(ROOT / "static/avatars" / f"{avatar}.png")
        )
    print("Captured four original 600×800 GPU previews")
    browser.close()
