"""Authenticated, loopback-only Presence Control Center."""

import atexit
import fcntl
from functools import wraps
import hmac
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import threading
import time
from urllib.parse import urlparse

from flask import Flask, jsonify, request, session, render_template, send_from_directory
from waitress import serve
from control import Catalog, Conflict, Controller, Unavailable
from runtime_config import atomic_json

ROOT = Path(__file__).resolve().parent
PORT = 8766
ALLOWED_HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}


def credentials(state):
    path = Path(state) / "control-auth.json"
    if not path.exists():
        atomic_json(
            path, {"signing": secrets.token_hex(48), "entry": secrets.token_urlsafe(48)}
        )
    return json.loads(path.read_text())


def create_app(controller=None, test_config=None):
    app = Flask(__name__)
    state = Path(os.environ.get("AVALON_STATE_DIR", ROOT / ".runtime")).resolve()
    auth = credentials(state)
    app.config.update(
        SECRET_KEY=auth["signing"],
        SESSION_COOKIE_NAME="avalon_presence",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        MAX_CONTENT_LENGTH=65536,
    )
    if test_config:
        app.config.update(test_config)
    control = controller or Controller(state)
    app.extensions["avalon"] = control
    wallpaper_cache = {"at": 0, "value": {"mode": "desktop"}}
    wallpaper_lock = threading.Lock()

    def wallpaper_status(refresh=False):
        with wallpaper_lock:
            if not refresh and time.monotonic() - wallpaper_cache["at"] < 2:
                return wallpaper_cache["value"]
            value = {"mode": "desktop"}
            for name, uuid in [
                ("constellation", "factory-observatory@progretech.com"),
                ("avalon", "avalon@progretech.com"),
            ]:
                result = subprocess.run(
                    ["gnome-extensions", "info", uuid],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    env={**os.environ, "LC_ALL": "C"},
                )
                if "State: ACTIVE" in result.stdout:
                    value = {"mode": name}
            wallpaper_cache.update(at=time.monotonic(), value=value)
            return value

    @app.before_request
    def boundary():
        if request.host not in ALLOWED_HOSTS:
            return jsonify(error="Invalid host"), 403
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            origin = request.headers.get("Origin")
            if origin not in {"http://" + host for host in ALLOWED_HOSTS}:
                return jsonify(error="Invalid request origin"), 403
            if not request.is_json:
                return jsonify(error="JSON requests are required"), 415

    def private(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            if not session.get("authorized"):
                return jsonify(
                    error="Open Project Avalon from its application shortcut to connect this browser."
                ), 401
            if request.method != "GET" and not hmac.compare_digest(
                request.headers.get("X-CSRF-Token", ""),
                session.get("csrf", "unavailable"),
            ):
                return jsonify(
                    error="The browser session expired. Reopen Project Avalon."
                ), 403
            return function(*args, **kwargs)

        return wrapped

    @app.after_request
    def headers(response):
        response.headers["Cache-Control"] = (
            "no-store"
            if request.path.startswith("/api/") or request.path == "/"
            else "public,max-age=300"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        return response

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/api/auth")
    def authenticate():
        data = request.get_json()
        token = data.get("token", "") if isinstance(data, dict) else ""
        if not isinstance(token, str) or not hmac.compare_digest(token, auth["entry"]):
            return jsonify(
                error="Open Project Avalon from its application shortcut."
            ), 401
        session.clear()
        session["authorized"] = True
        session["csrf"] = secrets.token_urlsafe(32)
        return jsonify(csrf=session["csrf"])

    @app.get("/api/state")
    @private
    def status():
        value = control.snapshot(request.args.get("revision", type=int))
        value.update(csrf=session["csrf"], wallpaper=wallpaper_status())
        return jsonify(value)

    @app.get("/api/models")
    @private
    def models():
        return jsonify(
            models=control.catalog.models(request.args.get("refresh") == "1"),
            platforms=control.catalog.platforms(),
        )

    @app.post("/api/select")
    @private
    def select():
        return jsonify(control.select(request.get_json()))

    @app.post("/api/connect")
    @private
    def connect():
        return jsonify(control.resume())

    @app.post("/api/appearance")
    @private
    def appearance():
        return jsonify(control.set_appearance(request.get_json()))

    @app.post("/api/chat")
    @private
    def chat():
        data = request.get_json()
        if not isinstance(data, dict):
            raise ValueError("Expected an object")
        return jsonify(turn=control.chat(data.get("text"))), 202

    @app.post("/api/stop")
    @private
    def stop():
        return jsonify(control.cancel())

    @app.post("/api/disconnect")
    @private
    def disconnect():
        return jsonify(control.disconnect())

    @app.post("/api/wallpaper")
    @private
    def wallpaper():
        data = request.get_json()
        mode = data.get("mode") if isinstance(data, dict) else None
        if mode not in ("avalon", "constellation", "desktop"):
            raise ValueError("Unknown wallpaper mode")
        argv = [
            "gnome-extensions",
            "enable",
            (
                "avalon@progretech.com"
                if mode == "avalon"
                else "factory-observatory@progretech.com"
            ),
        ]
        if mode == "desktop":
            for uuid in ["avalon@progretech.com", "factory-observatory@progretech.com"]:
                result = subprocess.run(
                    ["gnome-extensions", "disable", uuid],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode:
                    raise Unavailable("GNOME could not disable the wallpaper")
        else:
            result = subprocess.run(argv, capture_output=True, text=True, timeout=5)
            if result.returncode:
                raise Unavailable(
                    "GNOME could not switch wallpapers. Log out/in if the extension was just installed."
                )
        return jsonify(requested=mode, wallpaper=wallpaper_status(True))

    @app.get("/manifest.webmanifest")
    def manifest():
        response = jsonify(
            id="/",
            name="Project Avalon",
            short_name="Avalon",
            start_url="/",
            scope="/",
            display="standalone",
            background_color="#090e16",
            theme_color="#090e16",
            icons=[
                {
                    "src": f"/static/icons/avalon-{n}.png",
                    "sizes": f"{n}x{n}",
                    "type": "image/png",
                }
                for n in [192, 512]
            ],
        )
        response.mimetype = "application/manifest+json"
        return response

    @app.get("/sw.js")
    def worker():
        response = send_from_directory(
            ROOT / "static", "sw.js", mimetype="application/javascript"
        )
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Service-Worker-Allowed"] = "/"
        return response

    @app.errorhandler(ValueError)
    def bad_request(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(Conflict)
    def conflict(error):
        return jsonify(error=str(error)), 409

    @app.errorhandler(Unavailable)
    def unavailable(error):
        return jsonify(error=str(error)), 503

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(error="The request is too large"), 413

    @app.errorhandler(500)
    def failure(error):
        return jsonify(
            error="The control center could not complete this action. Check the local service and retry."
        ), 500

    return app


def main():
    state = Path(os.environ.get("AVALON_STATE_DIR", ROOT / ".runtime")).resolve()
    state.mkdir(exist_ok=True, mode=0o700)
    lock = (state / "controller.lock").open("a")
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    controller = Controller(state)

    def start_selected():
        try:
            controller.resume()
        except Exception:
            with controller.lock:
                controller.set_status(
                    "disconnected", "Choose an available local model and connect."
                )

    threading.Thread(target=start_selected, daemon=True).start()
    atexit.register(controller.close)

    def stop(*_):
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    serve(
        create_app(controller),
        host="127.0.0.1",
        port=PORT,
        threads=8,
        clear_untrusted_proxy_headers=True,
    )


if __name__ == "__main__":
    main()
