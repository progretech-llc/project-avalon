#!/usr/bin/env python3
"""Idle PSS: compositor increment + whole fresh browser tree + Avalon services."""

import json, subprocess, time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def pid_for(unit):
    return int(
        subprocess.check_output(
            ["systemctl", "--user", "show", unit, "-p", "MainPID", "--value"], text=True
        )
    )


def pss(pid):
    try:
        return next(
            int(line.split()[1]) * 1024
            for line in Path(f"/proc/{pid}/smaps_rollup").read_text().splitlines()
            if line.startswith("Pss:")
        )
    except (FileNotFoundError, ProcessLookupError, StopIteration):
        return 0


before = {p.name for p in Path("/proc").iterdir() if p.name.isdigit()}
compositor = int(
    subprocess.check_output(
        ["pgrep", "-f", "^gnome-shell --headless --virtual-monitor=1920x1080"],
        text=True,
    )
)
assert "avalon-proof" in Path(f"/proc/{compositor}/cmdline").read_text()
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto(
        "http://127.0.0.1:8766/#entry="
        + json.loads((ROOT / ".runtime/control-auth.json").read_text())["entry"]
    )
    page.locator("#access-note").wait_for(state="hidden")
    page.wait_for_function(
        '()=>Number(document.querySelector("canvas").dataset.frames)>5'
    )
    page.wait_for_timeout(1500)
    assert (
        page.request.get("http://127.0.0.1:8766/api/state").json()["active_turn"]
        is None
    )
    chrome = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit() or proc.name in before:
            continue
        try:
            if proc.joinpath("comm").read_text().strip().startswith("chrome"):
                chrome.append(int(proc.name))
        except (FileNotFoundError, ProcessLookupError):
            pass
    performance = json.loads(
        (ROOT / "docs/evidence/phase-3/performance.json").read_text()
    )
    assert performance["compositor_pid"] == compositor, (
        "Cold baseline belongs to another compositor"
    )
    baseline = performance["baseline"]["pss_bytes"]
    whole_compositor = pss(compositor)
    groups = {
        "incremental_compositor": max(0, whole_compositor - baseline),
        "whole_fresh_browser_tree": sum(pss(pid) for pid in chrome),
        "controller": pss(pid_for("project-avalon.service")),
        "gateway": pss(pid_for("project-avalon-runtime.service")),
    }
    result = {
        "metric": "Linux smaps_rollup Pss, bytes; compositor increment over cold disabled baseline plus entire fresh browser tree/controller/gateway; excludes GNOME base and Ollama inference",
        "compositor_disabled_baseline_bytes": baseline,
        "whole_compositor_bytes": whole_compositor,
        "full_process_total_bytes": whole_compositor
        + sum(
            value for key, value in groups.items() if key != "incremental_compositor"
        ),
        "state": "idle",
        "resolution": [1920, 1080],
        "browser_process_count": len(chrome),
        "groups": groups,
        "total_bytes": sum(groups.values()),
        "total_mib": sum(groups.values()) / 1024**2,
        "budget_mib": 750,
    }
    (ROOT / "docs/evidence/phase-3/memory.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result, indent=2))
    browser.close()
    assert result["total_mib"] < 750
