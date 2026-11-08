"""Avalon-owned display selection and bounded reuse of Constellation's collector."""

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time

from runtime_config import atomic_json

ROOT = Path(__file__).resolve().parent
HOME = Path.home()
SOURCE_CONFIG = (
    Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config"))
    / "constellation/sources.json"
)
CONFIG = (
    Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config"))
    / "project-avalon/constellation-sources.json"
)
SCENE = (
    Path(os.environ.get("XDG_STATE_HOME", HOME / ".local/state"))
    / "project-avalon/constellation-scene.json"
)
ENGINE = ROOT.parent / "constellation"
if not ENGINE.is_dir():
    ENGINE = ROOT.parent / "pt-constellation-factory-alt-dev"
AGENT_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}")


def read_json(path, fallback=None):
    try:
        if path.stat().st_size > 8 * 1024 * 1024:
            return fallback
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else fallback
    except (OSError, ValueError):
        return fallback


def revision(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:20]


def preferences(base):
    return dict(
        roots=copy.deepcopy(base.get("roots", [])),
        max_files=base.get("max_files", 160),
        max_directories=base.get("max_directories", 48),
        display_agents=None,
        show_memory=True,
        project_subfolders=True,
        openharness=False,
        harness_agent_limit=5,
        harness_sessions=False,
        excluded_project_roots=[],
        activity_memory_banks={},
        kanboard=False,
    )


def validate(data, previous):
    if not isinstance(data, dict) or set(data) != set(previous):
        raise ValueError("Unknown or missing galaxy source setting")
    selected = data["display_agents"]
    if selected is not None and (
        not isinstance(selected, list)
        or len(selected) > 100
        or any(not isinstance(x, str) or not AGENT_ID.fullmatch(x) for x in selected)
        or len(set(selected)) != len(selected)
    ):
        raise ValueError("Choose up to 100 unique agent identities")
    for key, maximum in [("max_files", 1000), ("max_directories", 200)]:
        if type(data[key]) is not int or not 1 <= data[key] <= maximum:
            raise ValueError("Invalid " + key.replace("_", " "))
    if type(data["show_memory"]) is not bool:
        raise ValueError("Choose whether to display the memory system")
    for key in ("project_subfolders", "openharness", "harness_sessions"):
        if key in data and type(data[key]) is not bool:
            raise ValueError("Choose whether to enable " + key)
    if "harness_agent_limit" in data and (type(data["harness_agent_limit"]) is not int or not 1 <= data["harness_agent_limit"] <= 100):
        raise ValueError("Choose between 1 and 100 frameworks")
    excluded = data.get("excluded_project_roots", [])
    if not isinstance(excluded, list) or len(excluded) > 200 or any(
        not isinstance(x, str) or not Path(x).is_absolute() or Path(x).parent != PROJECTS
        or Path(x).name.startswith('.') for x in excluded
    ):
        raise ValueError("Choose visible Projects subfolders")
    banks = data.get("activity_memory_banks", {})
    if not isinstance(banks, dict) or len(banks) > 100 or any(
        not AGENT_ID.fullmatch(k) or not isinstance(v, str) or not 1 <= len(v) <= 512
        or any(ord(c) < 32 for c in v) for k, v in banks.items()
    ):
        raise ValueError("Invalid activity bank mapping")
    if type(data.get("kanboard", False)) is not bool:
        raise ValueError("Choose whether to show Kanboard")
    roots = data["roots"]
    if not isinstance(roots, list) or not 1 <= len(roots) <= 12:
        raise ValueError("Choose between 1 and 12 folders")
    existing = {str(Path(x["path"]).expanduser().resolve()) for x in previous["roots"]}
    paths, labels, clean = set(), set(), []
    for entry in roots:
        if (
            not isinstance(entry, dict)
            or set(entry) != {"label", "path"}
            or not all(isinstance(x, str) for x in entry.values())
        ):
            raise ValueError("Each folder needs a name and absolute path")
        label = entry["label"].strip()
        path = Path(entry["path"]).expanduser()
        if (
            not label
            or len(label) > 80
            or any(ord(x) < 32 for x in label)
            or label.casefold() in labels
        ):
            raise ValueError("Use unique folder names of 1–80 characters")
        if not path.is_absolute() or any(ord(x) < 32 for x in str(path)):
            raise ValueError("Choose an absolute folder path")
        resolved = str(path.resolve())
        if resolved in paths:
            raise ValueError("Each folder can appear only once, including linked paths")
        if resolved not in existing and not path.is_dir():
            raise ValueError("A newly selected folder is unavailable")
        paths.add(resolved)
        labels.add(label.casefold())
        clean.append(dict(label=label, path=str(path)))
    return {**data, "roots": clean}


PROJECTS = Path("/mnt/PT-Storage/Projects")


def project_roots(prefs, *, include_hidden=False):
    if not prefs.get("project_subfolders", True) or not PROJECTS.is_dir():
        return prefs["roots"]
    from resource_activity import safe_path
    roots = [dict(label=path.name, path=str(path)) for path in sorted(PROJECTS.iterdir())
             if not path.is_symlink() and path.is_dir() and safe_path(str(path)) is not None]
    # The existing collector accepts at most twelve systems.
    if not include_hidden:
        roots = [r for r in roots if r["path"] not in prefs.get("excluded_project_roots", [])]
    if len(roots) > 12:
        raise ValueError("PT-Storage Projects has more than 12 solar systems; choose folders manually")
    return roots


def candidates(scene, base, discovered):
    items = {}

    def add(identity, name, source, current=False):
        if not isinstance(identity, str) or not AGENT_ID.fullmatch(identity):
            return
        item = items.setdefault(
            identity, dict(id=identity, name=str(name)[:80], current=False, sources=[])
        )
        item["current"] |= current
        if source not in item["sources"]:
            item["sources"].append(source)

    for identity in base.get("agents", []):
        add(identity, identity.replace("-", " ").title(), "Saved source configuration")
    for node in (scene or {}).get("nodes", []):
        if node.get("kind") == "Agent":
            add(
                str(node.get("id", "")).removeprefix("agent:"),
                node.get("name", ""),
                "Recorded galaxy identity",
            )
    for identity in (scene or {}).get("available_agents", []):
        add(identity, identity.replace("-", " ").title(), "Recorded activity")
    for item in discovered.get("agents", []):
        for source in item.get("sources", []):
            current = source.startswith(
                (
                    "OpenClaw · configured agent",
                    "Hermes · configured profile",
                    "Hermes · configured client",
                    "Codex · configured client",
                    "OpenCode · configured client",
                    "Claude Code · configured client",
                    "Goose · configured client",
                    "Native Harness · recorded owner",
                )
            )
            add(item.get("id"), item.get("name", ""), source, current)
    return sorted(
        (x for x in items.values() if x['current']), key=lambda x: (not x["current"], x["name"].casefold(), x["id"])
    )


def filter_scene(scene, selected, prefs):
    """Reindex every index-bearing field after hiding nodes, never reassign authors."""
    if not scene:
        return None
    result = copy.deepcopy(scene)
    keep = []
    roots = prefs["roots"]
    paths = [(x["label"], Path(x["path"]).expanduser().resolve()) for x in roots]
    paths.sort(key=lambda x: len(x[1].parts), reverse=True)
    memory_roots = {
        x.get("root")
        for x in scene["nodes"]
        if x.get("id") == "root:Hindsight"
        or str(x.get("id", "")).startswith("memory-system:")
    }
    for index, node in enumerate(scene["nodes"]):
        kind = node.get("kind")
        identity = str(node.get("id", "")).removeprefix("agent:")
        if kind == "Agent" and identity not in selected:
            continue
        if kind == "Memory planet" or node.get("root") in memory_roots:
            if not prefs["show_memory"]:
                continue
        elif kind not in ("Host", "Agent"):
            raw = node.get("path", "")
            if not raw:
                continue
            path = Path(raw).expanduser()
            if not path.is_absolute():
                continue
            path = path.resolve()
            matching = next(
                (
                    (label, root)
                    for label, root in paths
                    if path == root or path.is_relative_to(root)
                ),
                None,
            )
            if matching is None:
                continue
            if kind == "Directory system" and path != matching[1]:
                continue
            node = result["nodes"][index]
            node["root"] = matching[0]
            if kind == "Directory system":
                node["name"] = matching[0]
        keep.append(index)
    remap = {old: new for new, old in enumerate(keep)}
    result["nodes"] = [result["nodes"][i] for i in keep]
    result["links"] = [
        {**link, "from": remap[link["from"]], "to": remap[link["to"]]}
        for link in scene.get("links", [])
        if link.get("from") in remap and link.get("to") in remap
    ]
    result["agent_activity"] = []
    for activity in scene.get("agent_activity", []):
        if activity.get("agent") not in remap:
            continue
        entry = {**activity, "agent": remap[activity["agent"]]}
        for key in ("targets", "write_targets", "modified_targets", "context_targets"):
            entry[key] = [remap[i] for i in activity.get(key, []) if i in remap]
        entry["last_modified_root"] = remap.get(activity.get("last_modified_root"))
        result["agent_activity"].append(entry)
    counts = result.setdefault("counts", {})
    for key, kind in [
        ("agents", "Agent"),
        ("files", "Remembered file"),
        ("directories", "Remembered directory"),
        ("memory_planets", "Memory planet"),
    ]:
        counts[key] = sum(x.get("kind") == kind for x in result["nodes"])
    return result


class GalaxySources:
    def __init__(self, state):
        self.state = Path(state)
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.wake = threading.Event()
        self.roster = []
        self.busy = False
        self.notice = "Current identities have not been checked yet."
        self.last_checked = None
        self.thread = None
        self.frameworks = []
        self.harness_notice = ""
        self.memory_activity = {}
        self.board_snapshot = {}

    def base(self):
        return read_json(SOURCE_CONFIG, {})

    def prefs(self):
        return {**preferences(self.base()), **(read_json(CONFIG, {}) or {})}

    def available(self):
        return (
            (ENGINE / "wallpaper_scene.py").is_file()
            and (ENGINE / ".venv/bin/python").exists()
            and bool(self.base())
        )

    def snapshot(self):
        with self.lock:
            prefs = self.prefs()
            roster = self.roster or candidates(self.original_scene(), self.base(), {})
            selected = set(self.selected(prefs, roster))
            return dict(
                settings=prefs,
                project_folders=[{**r, "visible": r["path"] not in prefs.get("excluded_project_roots", [])}
                                 for r in project_roots({**prefs, "project_subfolders": True}, include_hidden=True)],
                board={k: v for k, v in self.board_snapshot.items() if k != "events"},
                frameworks=[{k: row[k] for k in ("name", "machine", "state", "updated_at")} for row in self.frameworks],
                revision=revision(prefs),
                agents=[{**x, "selected": x["id"] in selected} for x in roster],
                busy=self.busy,
                notice=self.notice + self.harness_notice,
                checked_at=self.last_checked,
                collector_available=self.available(),
            )

    def original_scene(self):
        import constellation

        return read_json(constellation.SOURCE_SCENE)

    @staticmethod
    def selected(prefs, roster):
        current = [x["id"] for x in roster if x["current"]]
        chosen = prefs["display_agents"]
        return current if chosen is None else [identity for identity in chosen if identity in current]


    def save(self, data):
        if not isinstance(data, dict) or set(data) != {"settings", "revision"}:
            raise ValueError("Expected source settings and revision")
        with self.lock:
            previous = self.prefs()
            if data["revision"] != revision(previous):
                raise ValueError(
                    "Galaxy sources changed elsewhere. Reload before saving."
                )
            prefs = validate(data["settings"], previous)
            allowed = {x["id"] for x in self.snapshot()["agents"]}
            if (
                not prefs.get("openharness")
                and prefs["display_agents"] is not None
                and set(prefs["display_agents"]) - allowed
            ):
                raise ValueError(
                    "Choose identities from the displayed roster; refresh if one is missing"
                )
            if not self.available() and prefs["roots"] != previous["roots"]:
                raise ValueError(
                    "Install the sibling Constellation collector before changing folder roots"
                )
            atomic_json(CONFIG, prefs)
            self.publish_filtered(prefs)
            self.notice = "Selection saved. Refreshing the Avalon memory scene…"
            self.request_refresh()
            return self.snapshot()

    def publish_filtered(self, prefs=None, scene=None):
        prefs = prefs or self.prefs()
        source = (
            scene
            or read_json(self.state / "galaxy-export-scene.json")
            or self.original_scene()
        )
        effective = {**prefs, "roots": project_roots(prefs)}
        selected = set(self.selected(prefs, self.roster))
        if prefs["openharness"] and prefs.get("harness_sessions"):
            selected = {"lyra", "mak", "progre", "codex"}
        result = filter_scene(source, set() if prefs["openharness"] and not prefs.get("harness_sessions") else selected, effective)
        if result and prefs.get("project_subfolders", True):
            result["galaxy"] = {"label": "Projects", "path": str(PROJECTS)}
            for node in result["nodes"]:
                if node.get("kind") == "Host":
                    node.update(name="Projects", path=str(PROJECTS))
        if result and prefs["openharness"]:
            from harness_constellation import read_frameworks, overlay as harness_overlay
            try:
                self.frameworks, failed = read_frameworks(prefs["harness_agent_limit"], workstation=CONFIG.with_name("laptop-galaxy.json").is_file(), sessions=prefs.get("harness_sessions", False))
                self.harness_notice = f" OpenHarness: {len(self.frameworks)} recent agents; {failed} machines unavailable."
            except (OSError, ValueError, subprocess.SubprocessError):
                self.frameworks = []
                self.harness_notice = " OpenHarness unavailable. Enable its connection or turn off the optional integration to show local agents."
            harness_overlay(result, self.frameworks)
        else:
            self.harness_notice = ""
        if result:
            from resource_activity import read_events, read_owners, overlay
            try:
                events = read_events()
                if events:
                    owners = read_owners()
                    if prefs["openharness"] and prefs.get("harness_sessions"):
                        owners.update({row["native_id"]: row["id"] for row in self.frameworks})
                    overlay(result, events, owners)
            except (OSError, ValueError, subprocess.SubprocessError):
                result['resource_activity_error'] = 'Native resource metadata unavailable'
            activity = dict(self.memory_activity)
            if prefs.get("kanboard") and self.board_snapshot:
                from kanboard_planets import overlay as board_overlay
                board_overlay(result, self.board_snapshot, activity)
                result["memory_source"]["browser_script"] = str(ROOT / "activity_browser.py")
            from recent_activity import overlay as recent_overlay
            recent_overlay(result, activity)
            atomic_json(SCENE, result, durable=False)

    def request_refresh(self):
        self.start()
        with self.lock:
            self.busy = True
            self.notice = (
                "Refreshing current identity metadata and the Avalon memory scene…"
            )
        self.wake.set()

    def start(self):
        with self.lock:
            if self.thread:
                return
            if not CONFIG.exists() and self.base().get("roots"):
                atomic_json(CONFIG, preferences(self.base()))
            self.publish_filtered()
            self.thread = threading.Thread(
                target=self.loop, name="avalon-galaxy-sources", daemon=True
            )
            self.thread.start()

    def close(self):
        self.stop.set()
        self.wake.set()

    def loop(self):
        while not self.stop.is_set():
            self.wake.clear()
            try:
                self.refresh()
            except (
                OSError,
                ValueError,
                KeyError,
                TypeError,
                subprocess.SubprocessError,
            ):
                with self.lock:
                    self.notice = "Scene refresh failed. Saved selections are retained; retry when the collector is available."
            finally:
                with self.lock:
                    self.busy = False
            # Cheap receipt-only updates between the existing two-minute memory refreshes.
            for _ in range(12):
                if self.stop.is_set() or self.wake.wait(10):
                    break
                try:
                    with self.lock:
                        self.publish_filtered()
                except (OSError, ValueError, KeyError, TypeError):
                    with self.lock:
                        self.notice = 'Resource refresh failed; retrying with the next scene refresh.'
                    break

    def refresh(self):
        with self.lock:
            self.busy = True
            prefs = self.prefs()
            expected = revision(prefs)
            base = self.base()
        self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not self.available():
            with self.lock:
                self.publish_filtered(prefs)
                self.notice = "Full scene rebuilding needs the sibling Constellation collector. Existing exported data is filtered."
            return
        config = {
            **base,
            **{k: prefs[k] for k in ("roots", "max_files", "max_directories")},
        }
        config["roots"] = project_roots(prefs)
        if not config["roots"]:
            with self.lock:
                self.publish_filtered(prefs)
                self.notice = "All Projects folder systems are hidden."
            return
        if prefs.get("project_subfolders", True):
            config["galaxy"] = {"label": "Projects", "path": str(PROJECTS)}
            config["host_name"] = "Projects"
        if prefs["openharness"]:
            config["native_harness"] = False
        config["roots"] = sorted(
            config["roots"], key=lambda x: len(Path(x["path"]).parts), reverse=True
        )
        snapshot = self.state / "galaxy-export-sources.json"
        atomic_json(snapshot, config)
        env = {**os.environ, "CONSTELLATION_CONFIG": str(snapshot.resolve())}
        python = str(ENGINE / ".venv/bin/python")
        discovery = subprocess.run(
            [
                python,
                "-c",
                "import json;from config import load_config;from agent_discovery import discover;print(json.dumps(discover(load_config(),activity_reader=lambda: [])))",
            ],
            cwd=ENGINE,
            env=env,
            capture_output=True,
            text=True,
            check=True,
            timeout=40,
        )
        discovered = json.loads(discovery.stdout)
        banks = prefs.get("activity_memory_banks", {})
        if banks:
            code = ("import json;from hindsight_api import _get;from config import load_config;"
                    "source=load_config()['memory'];result={};"
                    "\nfor agent,bank in " + repr(banks) + ".items():\n"
                    " try:\n  from urllib.parse import quote;d=_get(source,'/v1/default/banks/'+quote(bank,safe='')+'/stats');"
                    "result[agent]={'at':d.get('last_memory_write_at'),'source':'Hindsight'}\n"
                    " except (OSError,ValueError): pass\nprint(json.dumps(result))")
            try:
                presence = subprocess.run([python, "-c", code], cwd=ENGINE, env=env,
                                          capture_output=True, text=True, check=True, timeout=45)
                self.memory_activity = json.loads(presence.stdout)
            except (OSError, ValueError, subprocess.SubprocessError):
                self.memory_activity = {}
        if prefs.get("kanboard"):
            from kanboard_planets import collect
            try:
                self.board_snapshot = collect()
            except (OSError, ValueError, RuntimeError):
                self.board_snapshot = {"error": "Kanboard refresh unavailable", "cards": [], "events": []}
        roster = candidates(self.original_scene(), base, discovered)
        config["display_agents"] = self.selected(prefs, roster)
        config["agents"] = [x["id"] for x in roster if x["current"]]
        if prefs["openharness"] and prefs.get("harness_sessions"):
            config["agents"] = config["display_agents"] = ["lyra", "mak", "progre", "codex"]
            config["discover_agents"] = False
        if config.get("unlisted_agent") not in config["agents"]:
            config["unlisted_agent"] = ""
        atomic_json(snapshot, config)
        output = self.state / "galaxy-export-scene.json"
        code = (
            "from pathlib import Path;import wallpaper_scene as w;w.SETTINGS_PATH=Path("
            + repr(str(CONFIG.with_name("constellation.json")))
            + ");w.write_scene(Path("
            + repr(str(output.resolve()))
            + "))"
        )
        subprocess.run(
            [python, "-c", code],
            cwd=ENGINE,
            env=env,
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        with self.lock:
            if revision(self.prefs()) != expected:
                self.wake.set()
                return
            self.roster = roster
            self.publish_filtered(prefs, read_json(output))
            self.last_checked = int(time.time())
            warnings = discovered.get("warnings", [])
            self.notice = (
                "Avalon scene refreshed. Deleted and historical-only identities are excluded."
                + (
                    " Some local identity sources could not be checked."
                    if warnings
                    else ""
                )
            )
