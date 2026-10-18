"""Digital-body adaptation: native HAL music, actual Ubuntu output volume."""

import asyncio
import http.cookiejar
import json
import threading
import urllib.request
from pathlib import Path
from hal.server import app as native_hal

ROOT = Path(__file__).resolve().parent
_guard = threading.Lock()
_opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
)
_csrf = ""


def volume(data):
    global _csrf
    base = "http://127.0.0.1:8766"

    def request(path, value):
        req = urllib.request.Request(
            base + path,
            data=json.dumps(value).encode(),
            headers={
                "Origin": base,
                "Content-Type": "application/json",
                "X-CSRF-Token": _csrf,
            },
        )
        with _opener.open(req, timeout=5) as response:
            return json.load(response)

    with _guard:
        if not _csrf:
            token = json.loads((ROOT / ".runtime/control-auth.json").read_text())[
                "entry"
            ]
            _csrf = request("/api/auth", {"token": token})["csrf"]
        return request("/api/robot/body", {"action": "volume", **data})


class DigitalBody:
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] != "/audio/volume":
            return await native_hal(scope, receive, send)
        if dict(scope.get("headers", [])).get(b"origin"):
            await send({"type": "http.response.start", "status": 403, "headers": []})
            await send({"type": "http.response.body", "body": b"Forbidden"})
            return
        status = 200
        try:
            data = b""
            while True:
                message = await receive()
                data += message.get("body", b"")
                if len(data) > 1024:
                    raise ValueError("Request too large")
                if not message.get("more_body"):
                    break
            if scope["method"] not in ("GET", "POST"):
                raise ValueError("Unsupported method")
            body = json.loads(data) if data else {}
            result = await asyncio.to_thread(volume, body)
        except Exception:
            status = 503
            result = {"detail": "Ubuntu volume control is unavailable"}
        payload = json.dumps(result).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"cache-control", b"no-store"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": payload})


app = DigitalBody()
