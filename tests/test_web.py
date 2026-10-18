import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app import create_app, credentials
from test_control import FakeCatalog

HOST = "127.0.0.1:8766"
ORIGIN = "http://" + HOST


class FakeController:
    def __init__(self):
        self.catalog = FakeCatalog()
        self.mutations = 0

    def snapshot(self, revision=None):
        return {
            "revision": 0,
            "status": "disconnected",
            "messages": [],
            "session": None,
            "events": [],
            "sessions": [],
            "active_turn": None,
        }

    def set_appearance(self, data):
        self.mutations += 1
        return {"appearance": data}

    def chat(self, text):
        self.mutations += 1
        return "turn"


class WebTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"AVALON_STATE_DIR": self.directory.name})
        self.env.start()
        self.controller = FakeController()
        self.app = create_app(self.controller, {"TESTING": True})
        self.client = self.app.test_client()
        self.process = patch("app.subprocess.run")
        self.process.start()

    def tearDown(self):
        self.process.stop()
        self.env.stop()
        self.directory.cleanup()

    def auth(self):
        token = credentials(Path(self.directory.name))["entry"]
        r = self.client.post(
            "/api/auth",
            base_url=ORIGIN,
            json={"token": token},
            headers={"Origin": ORIGIN},
        )
        self.assertEqual(r.status_code, 200)
        return r.json["csrf"]

    def test_private_api_requires_user_bootstrap(self):
        r = self.client.get("/api/state", base_url=ORIGIN)
        self.assertEqual(r.status_code, 401)
        root = self.client.get("/", base_url=ORIGIN)
        self.assertEqual(root.status_code, 200)
        self.assertNotIn(
            credentials(Path(self.directory.name))["entry"].encode(), root.data
        )

    def test_cross_origin_and_host_attacks_are_denied(self):
        token = self.auth()
        for host, origin in [
            (ORIGIN, "https://attacker.example"),
            ("http://evil.test:8766", "http://evil.test:8766"),
        ]:
            r = self.client.post(
                "/api/chat",
                base_url=host,
                json={"text": "attack"},
                headers={"Origin": origin, "X-CSRF-Token": token},
            )
            self.assertEqual(r.status_code, 403)
        self.assertEqual(self.controller.mutations, 0)

    def test_csrf_is_required_and_valid_request_dispatches_once(self):
        token = self.auth()
        r = self.client.post(
            "/api/chat",
            base_url=ORIGIN,
            json={"text": "hello"},
            headers={"Origin": ORIGIN},
        )
        self.assertEqual(r.status_code, 403)
        r = self.client.post(
            "/api/chat",
            base_url=ORIGIN,
            json={"text": "hello"},
            headers={"Origin": ORIGIN, "X-CSRF-Token": token},
        )
        self.assertEqual(r.status_code, 202)
        self.assertEqual(self.controller.mutations, 1)

    def test_appearance_requires_authentication_and_csrf(self):
        r = self.client.post(
            "/api/appearance",
            base_url=ORIGIN,
            json={"avatar": "mascot"},
            headers={"Origin": ORIGIN},
        )
        self.assertEqual(r.status_code, 401)
        token = self.auth()
        r = self.client.post(
            "/api/appearance",
            base_url=ORIGIN,
            json={"avatar": "mascot"},
            headers={"Origin": ORIGIN, "X-CSRF-Token": token},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.controller.mutations, 1)

    def test_private_responses_are_not_cached(self):
        self.auth()
        r = self.client.get("/api/state", base_url=ORIGIN)
        self.assertEqual(r.headers["Cache-Control"], "no-store")
        self.assertIn("frame-ancestors 'none'", r.headers["Content-Security-Policy"])

    def test_manifest_icons_and_worker_scope(self):
        r = self.client.get("/manifest.webmanifest", base_url=ORIGIN)
        self.assertEqual(r.mimetype, "application/manifest+json")
        self.assertEqual(r.json["scope"], "/")
        import struct

        for icon in r.json["icons"]:
            response = self.client.get(icon["src"], base_url=ORIGIN)
            self.assertEqual(response.mimetype, "image/png")
            size = int(icon["sizes"].split("x")[0])
            self.assertEqual(struct.unpack(">II", response.data[16:24]), (size, size))
            response.close()
        worker = self.client.get("/sw.js", base_url=ORIGIN)
        self.assertEqual(worker.headers["Service-Worker-Allowed"], "/")
        self.assertNotIn("/api/state", worker.text)
        worker.close()

    def test_large_and_non_json_mutations_are_rejected(self):
        token = self.auth()
        headers = {"Origin": ORIGIN, "X-CSRF-Token": token}
        r = self.client.post("/api/chat", base_url=ORIGIN, data="x", headers=headers)
        self.assertEqual(r.status_code, 415)
        r = self.client.post(
            "/api/chat", base_url=ORIGIN, json={"text": "x" * 70000}, headers=headers
        )
        self.assertEqual(r.status_code, 413)


if __name__ == "__main__":
    unittest.main()
