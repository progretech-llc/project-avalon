#!/usr/bin/env python3
"""Synthetic API states → actual WebGL uniforms; never starts real devices."""

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.goto(
        "http://127.0.0.1:8766/#entry="
        + json.loads((ROOT / ".runtime/control-auth.json").read_text())["entry"]
    )
    page.locator("#access-note").wait_for(state="hidden")
    fixture = page.request.get("http://127.0.0.1:8766/api/state").json()
    fixture.update(
        status="listening",
        revision=fixture["revision"] + 1000,
        sensors={"gaze": [0.4, -0.2], "level": 0.6},
    )
    fixture["session"]["model"] = "qualification:sensory-fixture"
    fixture["appearance"]["motion"] = "full"
    fixture["devices"].update(recording=True, locked=False)
    polls = []

    def respond(route):
        polls.append(time.monotonic())
        route.fulfill(json=fixture)

    page.route("**/api/state*", respond)
    page.wait_for_function(
        '()=>document.querySelector("canvas").dataset.state==="listening"'
    )
    page.wait_for_timeout(1500)

    def uniform(name):
        return page.evaluate(
            '(name)=>{const g=document.querySelector("canvas").getContext("webgl"),p=g.getParameter(g.CURRENT_PROGRAM);return g.getUniform(p,g.getUniformLocation(p,"u_"+name));}',
            name,
        )

    assert abs(uniform("level") - 0.6) < 0.001
    assert abs(uniform("gaze_x") - 0.4) < 0.001
    assert abs(uniform("gaze_y") + 0.2) < 0.001
    intervals = [b - a for a, b in zip(polls, polls[1:])]
    assert len(intervals) >= 4 and max(intervals[-4:]) < 0.5, intervals
    fixture["appearance"]["motion"] = "reduced"
    fixture["revision"] += 1
    page.wait_for_timeout(500)
    assert uniform("level") == 0 and uniform("gaze_x") == 0
    count = page.locator("canvas").get_attribute("data-frames")
    fixture["sensors"] = {"gaze": [-0.3, 0.3], "level": 0.8}
    fixture["revision"] += 1
    page.wait_for_timeout(600)
    assert page.locator("canvas").get_attribute("data-frames") == count
    browser.close()
    result = {
        "actual_webgl_sensory_uniforms": True,
        "still_mode_ignores_tracking_and_amplitude": True,
        "active_poll_intervals_seconds": intervals,
        "method": "Clearly synthetic browser-only API fixture; real WebGL GPU. Production devices and selected model untouched.",
    }
    (ROOT / "docs/evidence/phase-4/sensory-browser.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result, indent=2))
