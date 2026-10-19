"""Authenticated, loopback-only Presence Control Center."""

import atexit
import fcntl
import hmac
import json
import os
import secrets
import signal
import subprocess
import threading
import time
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory, session
from waitress import serve

from control import Conflict, Controller, Unavailable
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
    from galaxy_sources import GalaxySources

    app.extensions["galaxy_sources"] = GalaxySources(state)
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
                if "Enabled: Yes" in result.stdout:
                    value = {
                        "mode": name,
                        "rendering": "State: ACTIVE" in result.stdout,
                    }
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

    @app.get("/api/constellation")
    @private
    def constellation_state():
        import constellation

        return jsonify(
            settings=constellation.settings(),
            scene=constellation.scene(),
            foreground=constellation.foreground() is not None,
        )

    @app.post("/api/constellation")
    @private
    def constellation_settings():
        import constellation

        return jsonify(settings=constellation.configure(request.get_json()))

    @app.get("/api/constellation/sources")
    @private
    def constellation_sources():
        return jsonify(app.extensions["galaxy_sources"].snapshot())

    @app.post("/api/constellation/sources")
    @private
    def constellation_sources_action():
        data = request.get_json()
        manager = app.extensions["galaxy_sources"]
        if data == {"action": "refresh"}:
            manager.request_refresh()
            return jsonify(manager.snapshot())
        if (
            isinstance(data, dict)
            and set(data) == {"action", "settings", "revision"}
            and data["action"] == "save"
        ):
            return jsonify(
                manager.save({key: data[key] for key in ("settings", "revision")})
            )
        raise ValueError("Choose a valid galaxy source action")

    @app.post("/api/constellation/folder")
    @private
    def constellation_choose_folder():
        if request.get_json() != {}:
            raise ValueError("Folder chooser accepts no path or command")
        try:
            selected = subprocess.run(
                ["/usr/bin/python3", str(ROOT / "scripts/choose-galaxy-folder.py")],
                capture_output=True,
                text=True,
                check=True,
                timeout=180,
            )
            result = json.loads(selected.stdout)
            if (
                not isinstance(result, dict)
                or set(result) != {"path"}
                or (result["path"] is not None and not isinstance(result["path"], str))
            ):
                raise ValueError("Invalid folder selection")
            return jsonify(result)
        except (subprocess.SubprocessError, OSError, ValueError):
            raise ValueError(
                "Folder chooser is unavailable. Paste an absolute folder path instead."
            ) from None

    @app.get("/api/constellation/foreground")
    @private
    def constellation_foreground():
        import constellation
        from flask import send_file, abort

        path = constellation.foreground()
        if path is None:
            abort(404)
        return send_file(path, mimetype="image/png", max_age=0)

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
        if type(data.get("vision", False)) is not bool:
            raise ValueError("Choose whether to attach the current camera view")
        return jsonify(
            turn=control.chat(data.get("text"), vision=data.get("vision", False))
        ), 202

    @app.get("/api/devices")
    @private
    def list_devices():
        from media import devices

        try:
            return jsonify(devices())
        except (OSError, subprocess.SubprocessError, ValueError):
            raise Unavailable(
                "PipeWire devices could not be read. Check the audio service and refresh."
            )

    @app.post("/api/devices")
    @private
    def device_settings():
        if not control.media:
            raise Unavailable("Media support is unavailable")
        with control.lock:
            control.media.configure(request.get_json())
            return jsonify(control.snapshot())

    @app.get("/api/robot")
    @private
    def robot_status():
        import lampos

        value = lampos.status()
        try:
            value["volume"] = lampos.output_volume(control.media.settings)["volume"]
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
        return jsonify(value)

    @app.post("/api/robot/body")
    @private
    def robot_body_action():
        import lampos

        data = request.get_json()
        if not isinstance(data, dict) or data.get("action") != "volume":
            raise ValueError("Unknown digital body action")
        return jsonify(lampos.output_volume(control.media.settings, data.get("volume")))

    @app.post("/api/robot")
    @private
    def robot_action():
        import lampos

        data = request.get_json()
        operation = data.get("action") if isinstance(data, dict) else None
        if operation == "start":
            return jsonify(lampos.start())
        if operation == "pair":
            return jsonify(lampos.request("/api/harness/pair", {}))
        if operation == "open_harness":
            subprocess.Popen(
                ["gtk-launch", "progretech-harness"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return jsonify(status="opened")
        if operation == "agents":
            return jsonify(
                lampos.request("/api/harness/request", {"type": "agents.list"})
            )
        if operation == "music_play":
            query = data.get("query")
            if not isinstance(query, str) or not 1 <= len(query.strip()) <= 500:
                raise ValueError("Enter a music search or local audio path")
            return jsonify(
                lampos.request("/audio/play", {"query": query.strip()}, hal=True)
            )
        if operation == "music_stop":
            return jsonify(lampos.request("/audio/stop", {}, hal=True))
        if operation == "volume":
            return jsonify(
                lampos.output_volume(control.media.settings, data.get("volume"))
            )
        raise ValueError("Unknown robot action")

    @app.post("/api/media")
    @private
    def media_action():
        if not control.media:
            raise Unavailable("Media support is unavailable")
        data = request.get_json()
        operation = data.get("action") if isinstance(data, dict) else None
        with control.lock:
            if operation == "wake":
                control.media.wake()
            elif operation == "sleep":
                control.media.stop()
            elif operation == "preview_voice":
                if control.active:
                    raise ValueError(
                        "Wait for the current turn before previewing a voice"
                    )
                control.media.speak("Hello. I am Avalon. This is my selected voice.")
            elif operation == "reset_owner":
                control.media.stop()
                control.media.state["notice"] = (
                    "Voice owner forgotten. Wake up and address Avalon to set a new owner."
                )
                control.publish()
            elif operation == "record":
                control.media.record()
            elif operation == "send_recording":
                control.media.finish()
            elif operation == "mute":
                control.media.stop() if control.media.awake else control.media.stop_audio()
            elif operation == "camera_on":
                control.media.enable_camera()
            elif operation == "camera_off":
                control.media.stop() if control.media.awake else control.media.stop_camera()
            elif operation == "read_reply":
                messages = control.store.messages(control.selected)
                replies = [
                    m
                    for m in messages
                    if m["role"] == "assistant" and m["status"] == "complete"
                ]
                if not replies or control.active:
                    raise ValueError("Finish a reply before reading it aloud")
                control.media.speak(replies[-1]["text"])
            else:
                raise ValueError("Unknown media action")
            return jsonify(control.snapshot())

    @app.post("/api/desktop-actions")
    @private
    def desktop_actions():
        data = request.get_json()
        return jsonify(
            control.set_desktop_actions(
                data.get("enabled") if isinstance(data, dict) else None
            )
        )

    @app.post("/api/approval")
    @private
    def approval():
        return jsonify(control.decide_action(request.get_json()))

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
    from media import Media

    controller.media = Media(controller)

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
    application = create_app(controller)
    sources = application.extensions["galaxy_sources"]
    sources.start()
    atexit.register(sources.close)
    serve(
        application,
        host="127.0.0.1",
        port=PORT,
        threads=8,
        clear_untrusted_proxy_headers=True,
    )


if __name__ == "__main__":
    main()
