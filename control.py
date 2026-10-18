"""One selected LampOS session, with native permissions and fenced events."""

import json
import os
import re
import secrets
import shutil
import sqlite3
import subprocess
import threading
import time
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

from websockets.sync.client import connect

from runtime_config import atomic_json, configure

ROOT = Path(__file__).resolve().parent
RUNTIME_SERVICE = "project-avalon-runtime.service"


class Conflict(Exception):
    pass


class Unavailable(Exception):
    pass


def local_json(path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/" + path,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=5) as r:
        raw = r.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise Unavailable("Ollama response exceeded the supported size")
        return json.loads(raw)


class Catalog:
    def __init__(self):
        self.items = []
        self.updated = 0
        self.lock = threading.Lock()
        self.error = None

    def models(self, refresh=False):
        with self.lock:
            if self.updated and not refresh and time.monotonic() - self.updated < 60:
                return list(self.items)
            try:
                models = local_json("tags")["models"]

                def inspect(model):
                    try:
                        details = local_json("show", {"model": model["name"]})
                        caps = details.get("capabilities", [])
                        if "embedding" in caps and "completion" not in caps:
                            return None
                        if "completion" not in caps:
                            return None
                        return {
                            "name": model["name"],
                            "size": model.get("size", 0),
                            "capabilities": caps,
                            "tools": "tools" in caps,
                            "vision": "vision" in caps,
                        }
                    except Exception:
                        return None

                with ThreadPoolExecutor(max_workers=4) as pool:
                    self.items = [item for item in pool.map(inspect, models) if item]
                self.items.sort(key=lambda item: item["name"])
                self.updated = time.monotonic()
                self.error = None
            except Exception:
                self.error = "Ollama is unavailable. Start it on this computer and refresh the model list."
                raise Unavailable(self.error)
            return list(self.items)

    def choose(self):
        models = [m for m in self.models() if m["tools"] and m.get("vision")]
        if not models:
            raise Unavailable(
                "No installed vision-and-tool-capable local model is available. Install one or explicitly select a text model for conversation without camera questions. No model was downloaded."
            )
        memory = next(
            (
                int(line.split()[1]) * 1024
                for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemAvailable:")
            ),
            0,
        )
        fitting = [m for m in models if not memory or m["size"] < memory * 0.7]
        if not fitting:
            raise Unavailable(
                "Installed models exceed the available-memory selection limit. Choose one explicitly after freeing memory."
            )
        return min(
            fitting,
            key=lambda m: (
                m["name"].startswith("experiment-"),
                m["name"] != "qwen3.5:4b",
                m["size"],
            ),
        )["name"]

    def validate(self, name, mode):
        model = next((m for m in self.models() if m["name"] == name), None)
        if not model:
            raise ValueError("Choose an installed completion model from this computer")
        if mode != "chat" and not model["tools"]:
            raise ValueError(
                "This model does not advertise tool support; use conversation-only access"
            )
        return model

    def platforms(self):
        return [
            {
                "id": "opencode",
                "name": "OpenCode",
                "installed": bool(shutil.which("opencode")),
                "available": bool(shutil.which("opencode")),
                "reason": ""
                if shutil.which("opencode")
                else "Install OpenCode through its native installer first.",
            },
            {
                "id": "codex",
                "name": "Codex",
                "installed": bool(shutil.which("codex")),
                "available": False,
                "reason": "The pinned LampOS Codex bridge requests unrestricted execution. Avalon is withholding it until its action restrictions and cancellation are qualified.",
            },
            {
                "id": "claudecode",
                "name": "Claude Code",
                "installed": bool(shutil.which("claude")),
                "available": False,
                "reason": "The pinned LampOS Claude bridge bypasses native approvals. A restricted connection and native authentication must be qualified before activation.",
            },
            {
                "id": "hermes",
                "name": "Hermes",
                "installed": bool(shutil.which("hermes")),
                "available": False,
                "reason": "No qualified LampOS/Hermes connection is configured. Configure Hermes through its native GUI; Avalon does not install a custom Hermes integration.",
            },
        ]


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,title TEXT NOT NULL,model TEXT NOT NULL,workspace TEXT NOT NULL,mode TEXT NOT NULL,commands INTEGER NOT NULL DEFAULT 0,native TEXT,created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,session TEXT NOT NULL,role TEXT NOT NULL,text TEXT NOT NULL,status TEXT NOT NULL,created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,kind TEXT NOT NULL,label TEXT NOT NULL,created REAL NOT NULL);
            """)
            db.execute(
                "UPDATE messages SET status='interrupted' WHERE status='streaming'"
            )
        os.chmod(self.path, 0o600)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, key, default=None):
        with self.db() as db:
            row = db.execute(
                "SELECT value FROM settings WHERE key=?", (key,)
            ).fetchone()
        return json.loads(row["value"]) if row else default

    def set(self, key, value):
        with self.db() as db:
            db.execute(
                "INSERT OR REPLACE INTO settings VALUES(?,?)", (key, json.dumps(value))
            )

    def session(self, identifier):
        with self.db() as db:
            row = db.execute(
                "SELECT * FROM sessions WHERE id=?", (identifier,)
            ).fetchone()
        return dict(row) if row else None

    def sessions(self):
        with self.db() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT id,title,model,workspace,mode,commands,created FROM sessions ORDER BY created DESC"
                )
            ]

    def create_session(
        self, model, workspace, mode="chat", commands=False, title="New conversation"
    ):
        identifier = uuid.uuid4().hex
        with self.db() as db:
            db.execute(
                "INSERT INTO sessions VALUES(?,?,?,?,?,?,NULL,?)",
                (
                    identifier,
                    title,
                    model,
                    str(workspace),
                    mode,
                    int(commands),
                    time.time(),
                ),
            )
        return identifier

    def save_native(self, identifier, native):
        with self.db() as db:
            db.execute("UPDATE sessions SET native=? WHERE id=?", (native, identifier))

    def update_session(self, identifier, title, mode, commands):
        with self.db() as db:
            db.execute(
                "UPDATE sessions SET title=?,mode=?,commands=? WHERE id=?",
                (title, mode, int(commands), identifier),
            )

    def message(self, identifier, role, text, status="complete"):
        with self.db() as db:
            cur = db.execute(
                "INSERT INTO messages(session,role,text,status,created) VALUES(?,?,?,?,?)",
                (identifier, role, text, status, time.time()),
            )
            return cur.lastrowid

    def replace_message(self, identifier, text, status):
        with self.db() as db:
            db.execute(
                "UPDATE messages SET text=?,status=? WHERE id=?",
                (text, status, identifier),
            )

    def messages(self, identifier):
        with self.db() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM (SELECT * FROM messages WHERE session=? ORDER BY id DESC LIMIT 100) ORDER BY id",
                    (identifier,),
                )
            ]

    def event(self, kind, label):
        with self.db() as db:
            db.execute(
                "INSERT INTO events(kind,label,created) VALUES(?,?,?)",
                (kind, label, time.time()),
            )
            db.execute(
                "DELETE FROM events WHERE id <= (SELECT COALESCE(MAX(id),0)-1000 FROM events)"
            )

    def events(self):
        with self.db() as db:
            return [
                dict(row)
                for row in db.execute("SELECT * FROM events ORDER BY id DESC LIMIT 30")
            ]


class Runtime:
    def __init__(self, state):
        self.state = Path(state)
        self.ws = None

    def stop(self):
        # systemd's control-group kill also reaps independently grouped CLI children.
        result = subprocess.run(
            ["systemctl", "--user", "stop", RUNTIME_SERVICE],
            capture_output=True,
            text=True,
            timeout=12,
        )
        if result.returncode:
            raise Unavailable(
                "Could not stop the previous local runtime; refusing to start another"
            )
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        self.ws = None

    def start(self):
        result = subprocess.run(
            ["systemctl", "--user", "start", RUNTIME_SERVICE],
            capture_output=True,
            text=True,
            timeout=12,
        )
        if result.returncode:
            raise Unavailable(
                "Local gateway could not start. Reinstall the Avalon user service and retry."
            )
        token = json.loads((self.state / "gateway.json").read_text())["token"]
        deadline = time.monotonic() + 8
        while True:
            try:
                ws = connect(
                    "ws://127.0.0.1:18893/opencode/ws/",
                    additional_headers={"Authorization": "Bearer " + token},
                    open_timeout=1,
                    close_timeout=1,
                    max_size=4 * 1024 * 1024,
                    proxy=None,
                )
                ready = json.loads(ws.recv(timeout=3))
                if (
                    ready.get("type") != "bridge.status"
                    or ready.get("state") != "ready"
                ):
                    ws.close()
                    raise Unavailable("The selected gateway is not ready")
                self.ws = ws
                return ws
            except Exception:
                if time.monotonic() > deadline:
                    raise Unavailable("The local gateway did not become ready")
                time.sleep(0.1)

    def native(self):
        path = self.state / "session.json"
        if not path.exists():
            return None
        raw = path.read_text()
        data = json.loads(raw)
        return (
            raw if isinstance(data.get("session_id"), str) and len(raw) < 4096 else None
        )

    def restore(self, raw):
        path = self.state / "session.json"
        if raw:
            atomic_json(path, json.loads(raw))
        else:
            path.unlink(missing_ok=True)


class Controller:
    def __init__(self, state, catalog=None, runtime=None, visual=None):
        self.state = Path(state).resolve()
        self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.state.chmod(0o700)
        self.catalog = catalog or Catalog()
        self.store = Store(self.state / "control.sqlite")
        self.runtime = runtime or Runtime(self.state / "agent")
        self.lock = threading.RLock()
        self.visual = (
            Path(visual) if visual else self.state / "desktop/visual-state.json"
        )
        self.media = None
        self.pending_action = None
        self.desktop_actions = self.store.get("desktop_actions", False)
        self.generation = 0
        self.revision = 0
        self.active = None
        self.ws = None
        self.status = "disconnected"
        self.detail = "Connect a local model to begin."
        self.selected = self.store.get("active_session")
        self.appearance = {
            "idle_saver": True,
            **self.store.get(
                "appearance",
                {
                    "avatar": "ethereal",
                    "quality": "balanced",
                    "fps": 30,
                    "motion": "system",
                },
            ),
        }
        self.closing = threading.Event()
        self.store.event(
            "startup", "Control center started; no previous task was replayed"
        )
        self.publish()
        self.heartbeat = threading.Thread(target=self._heartbeat, daemon=True)
        self.heartbeat.start()

    def _heartbeat(self):
        while not self.closing.wait(2):
            with self.lock:
                self.publish(increment=False)

    def publish(self, increment=True):
        if increment:
            self.revision += 1
        current = self.store.session(self.selected) if self.selected else None
        atomic_json(
            self.visual,
            {
                "schema": 1,
                "status": self.visible_status(),
                "sensors": self.visual_sensors(),
                "awake": bool(self.media and getattr(self.media, "awake", False)),
                "platform": "opencode",
                "model": current["model"] if current else "",
                "session": self.selected,
                "generation": self.generation,
                "heartbeat": time.time(),
                "appearance": self.appearance,
            },
        )

    def visual_sensors(self):
        if not self.media:
            return {"gaze": [0.0, 0.0], "level": 0.0}
        return {
            "gaze": list(self.media.state["gaze"]),
            "level": self.media.state["level"],
        }

    def visible_status(self):
        if self.pending_action and time.time() < self.pending_action["expires"]:
            return "approval"
        if self.media:
            if self.media.state["speaking"]:
                return "speaking"
            if not self.active and (
                self.media.state["recording"] or getattr(self.media, "awake", False)
            ):
                return "listening"
        return self.status

    def set_status(self, status, detail, event=True):
        self.status = status
        self.detail = detail
        if event:
            self.store.event(status, detail)
        self.publish()

    def snapshot(self, revision=None):
        with self.lock:
            response = {
                "revision": self.revision,
                "appearance": dict(self.appearance),
                "status": self.visible_status(),
                "runtime_status": self.status,
                "sensors": self.visual_sensors(),
                "devices": self.media.snapshot() if self.media else None,
                "desktop_actions": self.desktop_actions,
                "pending_action": self.pending_action
                if self.pending_action and time.time() < self.pending_action["expires"]
                else None,
                "detail": {
                    "listening": "Microphone capture is active",
                    "speaking": "Playing a local voice response",
                    "approval": "A workspace action needs your decision",
                }.get(self.visible_status(), self.detail),
                "active_turn": self.active["id"] if self.active else None,
                "generation": self.generation,
                "session": self.store.session(self.selected) if self.selected else None,
            }
            if response["session"]:
                response["session"].pop("native", None)
            if revision != self.revision:
                response.update(
                    sessions=self.store.sessions(),
                    messages=self.store.messages(self.selected)
                    if self.selected
                    else [],
                    events=self.store.events(),
                )
            return response

    def set_appearance(self, data):
        if not isinstance(data, dict) or set(data) - {
            "avatar",
            "quality",
            "fps",
            "motion",
            "idle_saver",
        }:
            raise ValueError("Unknown appearance setting")
        with self.lock:
            candidate = {**self.appearance, **data}
            if candidate["avatar"] not in (
                "ethereal",
                "sentinel",
                "mascot",
                "abstract",
            ):
                raise ValueError("Choose an available avatar")
            if candidate["quality"] not in ("economy", "balanced", "high"):
                raise ValueError("Choose a valid rendering quality")
            if type(candidate["fps"]) is not int or candidate["fps"] not in (
                15,
                30,
                60,
            ):
                raise ValueError("Choose 15, 30 or 60 FPS")
            if candidate["motion"] not in ("system", "full", "reduced"):
                raise ValueError("Choose a valid motion preference")
            if type(candidate["idle_saver"]) is not bool:
                raise ValueError("Choose whether idle power saving is enabled")
            self.appearance = candidate
            self.store.set("appearance", candidate)
            self.publish()
            return self.snapshot()

    def _save_current(self):
        if self.selected:
            native = self.runtime.native()
            if native:
                self.store.save_native(self.selected, native)

    def _stop(self, label):
        # Fence events before closing the old connection or stopping its process.
        self.generation += 1
        self.pending_action = None
        if self.media:
            self.media.stop()
        if self.active:
            job = self.active
            self.store.replace_message(job["message_id"], job["text"], "cancelled")
            self.store.event("cancelled", label)
        self.active = None
        self.ws = None
        self.runtime.stop()
        self._save_current()

    def select(self, data):
        if not isinstance(data, dict):
            raise ValueError("Expected an object")
        platform = data.get("platform", "opencode")
        target = next(
            (p for p in self.catalog.platforms() if p["id"] == platform), None
        )
        if not target:
            raise ValueError("Unknown target platform")
        if not target["available"]:
            raise Unavailable(target["reason"])
        identifier = data.get("session_id")
        existing = self.store.session(identifier) if identifier else None
        if identifier and not existing:
            raise ValueError("Session not found")
        model = (
            existing["model"]
            if existing
            else data.get("model") or self.catalog.choose()
        )
        mode = data.get("mode", existing["mode"] if existing else "chat")
        commands = data.get(
            "commands", bool(existing["commands"]) if existing else False
        )
        if mode not in ("chat", "read", "edit") or not isinstance(commands, bool):
            raise ValueError("Choose a valid permission policy")
        if commands and mode == "chat":
            raise ValueError("Enable workspace access before allowing status commands")
        capabilities = self.catalog.validate(model, mode)
        if existing:
            workspace = Path(existing["workspace"])
        elif data.get("workspace"):
            if (
                not isinstance(data["workspace"], str)
                or not Path(data["workspace"]).is_absolute()
            ):
                raise ValueError("Workspace must be an absolute existing folder")
            workspace = Path(data["workspace"]).resolve()
            if not workspace.is_dir():
                raise ValueError("Workspace is not an available folder")
        else:
            workspace = self.state / "workspaces" / uuid.uuid4().hex
        title = data.get("title", existing["title"] if existing else "New conversation")
        if not isinstance(title, str) or not title.strip() or len(title) > 80:
            raise ValueError("Session title must contain 1–80 characters")
        with self.lock:
            if self.active and data.get("cancel_current") is not True:
                raise Conflict(
                    "A turn is running. Stop it before switching or explicitly cancel it with this switch."
                )
            self.set_status("switching", "Switching the selected session")
            try:
                self._stop("Cancelled by session/model switch")
                if not existing:
                    identifier = self.store.create_session(
                        model, workspace, mode, commands, title.strip()
                    )
                    existing = self.store.session(identifier)
                else:
                    self.store.update_session(identifier, title.strip(), mode, commands)
                configure(
                    self.state / "agent",
                    model,
                    workspace,
                    mode,
                    commands,
                    vision=bool(capabilities.get("vision")),
                )
                self.runtime.restore(existing["native"])
                self.selected = identifier
                self.store.set("active_session", identifier)
                self.ws = self.runtime.start()
                self.set_status("idle", "OpenCode connected to " + model)
            except Exception:
                self.set_status(
                    "disconnected",
                    "The selected runtime could not connect. Check the target and retry.",
                )
                raise
            return self.snapshot()

    def resume(self):
        return (
            self.select({"session_id": self.selected})
            if self.selected
            else self.select({})
        )

    def chat(self, text, spoken=False, vision=False):
        if not isinstance(text, str) or not text.strip() or len(text) > 16000:
            raise ValueError("Message must contain 1–16,000 characters")
        with self.lock:
            if self.active:
                raise Conflict(
                    "This robot already has an active turn. Stop it or wait for its response."
                )
            if not self.ws or not self.selected:
                raise Conflict("Connect a local model before sending a message")
            if (
                self.media
                and (self.media.state["recording"] or self.media.state["transcribing"])
                and not spoken
            ):
                raise Conflict(
                    "Send or discard the microphone recording before chatting"
                )
            # Addressed speech can refer to the current view without naming a
            # vision mode. Capture once per turn, never stream frames to the LLM.
            vision = vision or bool(
                spoken and self.media and self.media.state["camera"]
            )
            attachments = (
                self.media.vision_attachment() if vision and self.media else []
            )
            if vision and not self.media:
                raise ValueError("Camera support is unavailable")
            if self.media:
                self.media.stop_audio()
            self.pending_action = None
            self.store.message(self.selected, "user", text.strip())
            message_id = self.store.message(self.selected, "assistant", "", "streaming")
            self.generation += 1
            identifier = uuid.uuid4().hex
            generation = self.generation
            job = {
                "id": identifier,
                "generation": generation,
                "message_id": message_id,
                "text": "",
                "session": self.selected,
                "spoken": spoken,
            }
            self.active = job
            self.set_status("working", "OpenCode is working on your message")
            try:
                self.ws.send(
                    json.dumps(
                        {
                            "type": "message.send",
                            "id": identifier,
                            "run_id": identifier,
                            "payload": {
                                "content": text.strip()
                                + (
                                    "\n\nAvalon desktop action protocol: if the user asks you to open this conversation workspace folder, propose it by writing exactly [[avalon:open_workspace]] on a line by itself. This only requests user approval; do not use shell tools to open anything. No other desktop actions are supported."
                                    if self.desktop_actions
                                    else ""
                                ),
                                "attachments": attachments,
                            },
                        }
                    )
                )
            except Exception:
                self.store.replace_message(message_id, "", "failed")
                self.active = None
                self.ws = None
                self.set_status(
                    "disconnected",
                    "The local connection was lost before dispatch completed. The message was not retried.",
                )
                raise Unavailable(self.detail)
            threading.Thread(
                target=self._read_turn, args=(job, self.ws), daemon=True
            ).start()
            return identifier

    def _read_turn(self, job, ws):
        try:
            while True:
                frame = json.loads(ws.recv(timeout=310))
                if (
                    frame.get("request_id") != job["id"]
                    or frame.get("run_id") != job["id"]
                ):
                    continue
                with self.lock:
                    if self.generation != job["generation"] or self.active is not job:
                        return
                    kind = frame.get("type")
                    part = frame.get("part") or {}
                    if kind in (
                        "bridge.error",
                        "error",
                        "session.error",
                        "bridge.rejected",
                    ):
                        raise Unavailable(
                            "The selected runtime returned an error. Retry after checking the model or its native configuration."
                        )
                    if kind == "text":
                        text = part.get("text", "")
                        if not isinstance(text, str):
                            raise Unavailable("Invalid text received from the runtime")
                        if len(job["text"]) + len(text) > 128000:
                            raise Unavailable(
                                "The response exceeded the supported size"
                            )
                        job["text"] += text
                        self.store.replace_message(
                            job["message_id"], job["text"], "streaming"
                        )
                        self.publish()
                    elif kind == "tool_use":
                        name = str(part.get("tool", "tool"))[:60]
                        tool_status = (part.get("state") or {}).get("status", "unknown")
                        if tool_status in ("pending", "running"):
                            state = (
                                "writing"
                                if name in ("write", "edit", "patch", "apply_patch")
                                else "executing"
                            )
                            self.set_status(state, "OpenCode tool: " + name)
                        else:
                            self.set_status(
                                "working", "OpenCode tool " + name + ": " + tool_status
                            )
                    elif kind == "session.idle":
                        marker = r"(?m)^\[\[avalon:open_workspace\]\]$"
                        proposal = self.desktop_actions and re.search(
                            marker, job["text"]
                        )
                        display_text = (
                            re.sub(
                                marker,
                                "Requested to open this workspace in Ubuntu Files. Your approval is required.",
                                job["text"],
                            )
                            if proposal
                            else job["text"]
                        )
                        self.store.replace_message(
                            job["message_id"], display_text, "complete"
                        )
                        self._save_current()
                        self.active = None
                        if proposal:
                            current = self.store.session(self.selected)
                            self.pending_action = {
                                "id": secrets.token_urlsafe(24),
                                "kind": "open_workspace",
                                "session": self.selected,
                                "generation": self.generation,
                                "turn": job["id"],
                                "path": str(Path(current["workspace"]).resolve()),
                                "expires": time.time() + 60,
                            }
                            self.store.event(
                                "approval",
                                "Open workspace requested; waiting for your approval",
                            )
                        self.set_status("completed", "Response completed")
                        if (
                            job.get("spoken")
                            and self.media
                            and self.media.settings["spoken_replies"]
                            and not self.pending_action
                        ):
                            try:
                                self.media.speak(job["text"])
                            except ValueError as exc:
                                self.media.state["notice"] = str(exc)
                                self.publish()
                        timer = threading.Timer(
                            2, self._settle, args=(job["generation"],)
                        )
                        timer.daemon = True
                        timer.start()
                        return
        except Exception as exc:
            with self.lock:
                if self.generation != job["generation"] or self.active is not job:
                    return
                self.store.replace_message(job["message_id"], job["text"], "failed")
                self.active = None
                self.ws = None
                try:
                    self.runtime.stop()
                except Exception:
                    pass
                self.set_status(
                    "failed",
                    str(exc)
                    if isinstance(exc, Unavailable)
                    else "The runtime connection ended. No request was replayed; reconnect to continue.",
                )

    def _settle(self, generation):
        with self.lock:
            if (
                self.generation == generation
                and not self.active
                and self.status == "completed"
            ):
                self.set_status("idle", "Ready for your next message", event=False)

    def set_desktop_actions(self, enabled):
        if type(enabled) is not bool:
            raise ValueError("Choose whether workspace opening is allowed")
        with self.lock:
            self.pending_action = None
            self.desktop_actions = enabled
            self.store.set("desktop_actions", enabled)
            self.store.event(
                "permissions",
                "Workspace opening "
                + (
                    "enabled; every action requires approval" if enabled else "disabled"
                ),
            )
            self.publish()
            return self.snapshot()

    def decide_action(self, data):
        if not isinstance(data, dict) or type(data.get("approve")) is not bool:
            raise ValueError("Approve or deny the exact requested action")
        with self.lock:
            action = self.pending_action
            if not action or data.get("id") != action["id"]:
                raise Conflict("This approval is no longer available")
            self.pending_action = None
            if not data["approve"]:
                self.store.event("denied", "Workspace opening denied by the user")
            else:
                if (
                    not self.desktop_actions
                    or action["expires"] < time.time()
                    or action["session"] != self.selected
                    or action["generation"] != self.generation
                    or self.active
                ):
                    self.publish()
                    raise Conflict(
                        "This approval expired or belongs to an earlier turn"
                    )
                from media import screen_locked

                if screen_locked():
                    self.publish()
                    raise Conflict("Unlock Ubuntu and request the action again")
                current = self.store.session(self.selected)
                path = Path(current["workspace"]).resolve()
                if (
                    action["kind"] != "open_workspace"
                    or str(path) != action["path"]
                    or not path.is_dir()
                ):
                    self.publish()
                    raise Conflict("The workspace changed; request the action again")
                subprocess.Popen(
                    ["xdg-open", str(path)],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                self.store.event(
                    "executing", "Approved workspace opening dispatched to Ubuntu Files"
                )
            self.publish()
            return self.snapshot()

    def cancel(self):
        with self.lock:
            self._stop("Turn stopped by the user")
            self.set_status("cancelled", "Turn stopped. Reconnect when you are ready.")
            return self.snapshot()

    def disconnect(self):
        with self.lock:
            self._stop("Stopped when disconnecting")
            self.set_status("disconnected", "Local runtime stopped")
            return self.snapshot()

    def close(self):
        self.closing.set()
        with self.lock:
            try:
                self._stop("Control center stopped")
            finally:
                self.set_status("disconnected", "Control center stopped", event=False)
