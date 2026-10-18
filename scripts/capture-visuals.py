#!/usr/bin/env python3
"""Capture the current installed UI without changing conversations or appearance."""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".impeccable/review"
OUT.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True)
    page = b.new_page(viewport={"width": 1920, "height": 1080})
    page.goto(
        "http://127.0.0.1:8766/#entry="
        + json.loads((ROOT / ".runtime/control-auth.json").read_text())["entry"]
    )
    page.locator("#access-note").wait_for(state="hidden")
    page.wait_for_function(
        '()=>Number(document.querySelector("canvas").dataset.frames)>0'
    )
    page.wait_for_timeout(300)
    for width, height, presence, appearance in [
        (1920, 1080, "desktop.png", "appearance-desktop.png"),
        (1440, 1000, "desktop-1440.png", None),
        (390, 844, "mobile.png", "appearance-mobile.png"),
    ]:
        page.set_viewport_size({"width": width, "height": height})
        page.locator('[data-page="presence"]').click()
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / presence), full_page=True)
        if appearance:
            page.locator('[data-page="appearance"]').click()
            page.screenshot(path=str(OUT / appearance), full_page=True)
    b.close()
    print("Captured current real conversation at all required viewports")
