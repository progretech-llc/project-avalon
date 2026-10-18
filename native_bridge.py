"""Translate unmodified LampOS Codex/Claude frames into Avalon's turn events."""

import json
import time
from collections import deque


class NativeSocket:
    def __init__(self, ws, platform):
        self.ws = ws
        self.platform = platform
        self.request = None
        self.pending = deque()
        self.has_text = False

    def send(self, raw):
        frame = json.loads(raw)
        if frame.get("type") == "message.send":
            self.request = frame["id"]
            self.has_text = False
        self.ws.send(raw)

    def close(self):
        self.ws.close()

    def recv(self, timeout=None):
        deadline = time.monotonic() + (timeout or 310)
        while not self.pending:
            raw = json.loads(
                self.ws.recv(timeout=max(0.01, deadline - time.monotonic()))
            )
            if self.platform == "codex" and raw.get("request_id") != self.request:
                continue
            for kind, part in self.translate(raw):
                self.pending.append(
                    json.dumps(
                        {
                            "type": kind,
                            "part": part,
                            "request_id": self.request,
                            "run_id": self.request,
                        }
                    )
                )
        return self.pending.popleft()

    def translate(self, frame):
        kind = frame.get("type")
        if kind in ("bridge.error", "bridge.rejected", "error", "turn.failed"):
            return [("bridge.error", {})]
        if self.platform == "codex":
            item = frame.get("item") or {}
            if kind == "item.completed":
                item_type = item.get("item_type") or item.get("type")
                if item_type in ("agent_message", "agentMessage"):
                    self.has_text = True
                    return [("text", {"text": item.get("text", "")})]
                if item_type in ("command_execution", "file_change", "mcp_tool_call"):
                    return [
                        (
                            "tool_use",
                            {"tool": item_type, "state": {"status": "completed"}},
                        )
                    ]
            if kind == "turn.completed":
                return [("session.idle", {})]
        else:
            if kind == "assistant":
                events = []
                for block in (frame.get("message") or {}).get("content", []):
                    if block.get("type") == "text":
                        self.has_text = True
                        events.append(("text", {"text": block.get("text", "")}))
                    elif block.get("type") == "tool_use":
                        events.append(
                            (
                                "tool_use",
                                {
                                    "tool": block.get("name", "tool"),
                                    "state": {"status": "running"},
                                },
                            )
                        )
                return events
            if kind == "result":
                if frame.get("is_error"):
                    return [("bridge.error", {})]
                result = []
                if not self.has_text and frame.get("result"):
                    result.append(("text", {"text": frame["result"]}))
                return result + [("session.idle", {})]
        return []
