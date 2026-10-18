import json
import unittest
from unittest.mock import Mock
from native_bridge import NativeSocket


class NativeBridgeTest(unittest.TestCase):
    def test_codex_ignores_old_turn_and_normalizes_native_completion(self):
        ws = Mock()
        bridge = NativeSocket(ws, "codex")
        bridge.send(json.dumps({"type": "message.send", "id": "current"}))
        ws.recv.side_effect = [
            json.dumps(
                {
                    "type": "item.completed",
                    "request_id": "old",
                    "item": {"type": "agent_message", "text": "stale"},
                }
            ),
            json.dumps(
                {
                    "type": "item.completed",
                    "request_id": "current",
                    "item": {"type": "agent_message", "text": "answer"},
                }
            ),
            json.dumps({"type": "turn.completed", "request_id": "current"}),
        ]
        self.assertEqual(json.loads(bridge.recv())["part"]["text"], "answer")
        self.assertEqual(json.loads(bridge.recv())["type"], "session.idle")

    def test_claude_result_does_not_duplicate_assistant_text(self):
        b = NativeSocket(Mock(), "claudecode")
        self.assertEqual(
            b.translate(
                {
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": "hello"}]},
                }
            ),
            [("text", {"text": "hello"})],
        )
        self.assertEqual(
            b.translate({"type": "result", "result": "hello"}), [("session.idle", {})]
        )
        self.assertEqual(
            b.translate({"type": "result", "is_error": True}), [("bridge.error", {})]
        )
