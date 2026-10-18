"""Bounded native devices, capture and playback, fenced to one Avalon session."""

import array
import base64
import json
import math
import os
import signal
import subprocess
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKER = [str(ROOT / ".media-venv/bin/python"), str(ROOT / "media_worker.py")]


def devices():
    nodes = json.loads(subprocess.check_output(["pw-dump"], text=True, timeout=4))
    result = {"inputs": [], "outputs": [], "cameras": []}
    for node in nodes:
        props = node.get("info", {}).get("props", {})
        kind = {"Audio/Source": "inputs", "Audio/Sink": "outputs"}.get(
            props.get("media.class")
        )
        if kind and isinstance(props.get("node.name"), str):
            result[kind].append(
                {
                    "id": props["node.name"],
                    "name": props.get("node.description", props["node.name"]),
                }
            )
    for path in sorted(Path("/dev/v4l/by-id").glob("*video-index0")):
        name = Path("/sys/class/video4linux", path.resolve().name, "name")
        result["cameras"].append(
            {
                "id": str(path),
                "name": name.read_text().strip() if name.exists() else "USB camera",
            }
        )
    return result


def screen_locked():
    try:
        result = subprocess.check_output(
            [
                "gdbus",
                "call",
                "--session",
                "--dest",
                "org.gnome.ScreenSaver",
                "--object-path",
                "/org/gnome/ScreenSaver",
                "--method",
                "org.gnome.ScreenSaver.GetActive",
            ],
            text=True,
            timeout=2,
        )
        return result.strip() != "(false,)"
    except (OSError, subprocess.SubprocessError):
        return True


def terminate(proc):
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=3)
    except ProcessLookupError:
        pass
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=2)


def rms(data):
    pcm = array.array("h")
    pcm.frombytes(data[: len(data) // 2 * 2])
    return min(1.0, math.sqrt(sum(x * x for x in pcm) / max(1, len(pcm))) / 32768 * 5)


class Media:
    def __init__(self, controller):
        self.control = controller
        self.path = controller.state / "media"
        self.path.mkdir(parents=True, exist_ok=True, mode=0o700)
        defaults = {
            "input": "default",
            "output": "default",
            "camera": "",
            "spoken_replies": True,
            "listener_phrase": "hey progre",
        }
        saved = controller.store.get("devices", {})
        self.settings = {key: saved.get(key, value) for key, value in defaults.items()}
        if not saved:
            controller.store.set("devices", self.settings)
        self.state = {
            "recording": False,
            "transcribing": False,
            "camera": False,
            "speaking": False,
            "face": False,
            "level": 0.0,
            "gaze": [0.0, 0.0],
            "notice": "",
        }
        self.epoch = 0
        self.listener = None
        self.awake = False
        self.followup = 0.0
        self.listener_paused = True
        self.listener_ready = False
        self.camera_epoch = 0
        self.capture = self.recognizer = self.synthesis = self.player = self.camera = (
            None
        )
        self.pcm = bytearray()
        self.record_fence = None
        self.locked = True
        self.frame = self.path / "view.jpg"
        self.frame.unlink(missing_ok=True)
        self.frame.with_suffix(".tmp").unlink(missing_ok=True)
        self.path.chmod(0o700)
        self.monitor = threading.Thread(target=self._monitor, daemon=True)
        self.monitor.start()

    def _spawn(self, args, **kwargs):
        return subprocess.Popen(
            args, start_new_session=True, stderr=subprocess.DEVNULL, **kwargs
        )

    def snapshot(self):
        return {
            **self.state,
            "awake": self.awake,
            "listener_ready": self.listener_ready,
            "recording_ready": bool(self.pcm),
            "audio_busy": self.synthesis is not None,
            "camera_starting": self.camera is not None and not self.state["camera"],
            "settings": dict(self.settings),
            "locked": self.locked,
            "speech_ready": (ROOT / ".media-venv/bin/piper").exists()
            and (self.path / "models/whisper-base.en/model.bin").exists()
            and (
                self.path
                / "models/piper/en/en_US/ljspeech/medium/en_US-ljspeech-medium.onnx"
            ).exists(),
        }

    def _changed(self):
        self.control.publish()

    def _monitor(self):
        while not self.control.closing.wait(0.5):
            locked = screen_locked()
            with self.control.lock:
                if locked != self.locked:
                    self.locked = locked
                    if locked:
                        self.stop()
                        self.control.pending_action = None
                    self._changed()
                if self.awake:
                    if (
                        not self.listener_ready
                        and time.monotonic() - self.wake_started > 30
                    ):
                        self.stop()
                        self.state["notice"] = (
                            "Local listener did not start. Check voice installation and wake Progre again."
                        )
                    elif not self.camera or self.camera.poll() is not None:
                        self.stop()
                        self.state["notice"] = (
                            "Presence slept because the camera stopped."
                        )
                    else:
                        self._pause_listener(
                            bool(self.control.active or self.synthesis or self.player)
                        )

    def configure(self, data):
        if not isinstance(data, dict) or set(data) - set(self.settings):
            raise ValueError("Unknown device setting")
        candidate = {**self.settings, **data}
        available = devices()
        for key, group in [
            ("input", "inputs"),
            ("output", "outputs"),
            ("camera", "cameras"),
        ]:
            if not isinstance(candidate[key], str) or candidate[key] not in (
                {"default"} if key != "camera" else {""}
            ) | {x["id"] for x in available[group]}:
                raise ValueError(
                    "That device is unavailable. Refresh and choose an available device."
                )
        if type(candidate["spoken_replies"]) is not bool:
            raise ValueError("Choose whether voice replies are enabled")
        phrase = candidate["listener_phrase"]
        if (
            not isinstance(phrase, str)
            or not 1 <= len(phrase.strip()) <= 80
            or not any(c.isalnum() for c in phrase)
        ):
            raise ValueError(
                "Listener phrase must contain 1–80 characters including a letter or number"
            )
        candidate["listener_phrase"] = phrase.strip()
        self.stop()
        self.settings = candidate
        self.control.store.set("devices", candidate)
        self._changed()

    def _unlocked(self):
        # Recheck at dispatch; do not rely on a potentially stale monitor sample.
        if screen_locked():
            self.locked = True
            raise ValueError(
                "Ubuntu is locked. Unlock it before using devices or desktop actions."
            )
        self.locked = False

    def _target(self, kind):
        key, group = ("input", "inputs") if kind == "input" else ("output", "outputs")
        chosen = self.settings[key]
        if chosen == "default":
            return []
        if chosen not in {x["id"] for x in devices()[group]}:
            raise ValueError(
                "The selected device disconnected. Select it again or explicitly choose the system default."
            )
        return [
            "--target",
            chosen,
            "--properties",
            "{ node.dont-reconnect=true node.dont-fallback=true }",
        ]

    def record(self):
        if self.awake:
            raise ValueError("Put Progre to sleep before recording manually")
        self._unlocked()
        if self.control.active or not self.control.ws:
            raise ValueError(
                "Connect a model and finish its current turn before recording"
            )
        if not self.snapshot()["speech_ready"]:
            raise ValueError("Install local voice components before recording")
        self.stop_audio()
        self.state["notice"] = ""
        self.pcm = bytearray()
        self.record_fence = (self.control.selected, self.control.generation, self.epoch)
        proc = self.capture = self._spawn(
            [
                "pw-record",
                "--raw",
                "--rate",
                "16000",
                "--channels",
                "1",
                "--format",
                "s16",
                "--sample-count",
                "240000",
                *self._target("input"),
                "-",
            ],
            stdout=subprocess.PIPE,
        )
        self.state["recording"] = True
        self._changed()
        threading.Thread(
            target=self._read_audio, args=(proc, self.epoch), daemon=True
        ).start()

    def _read_audio(self, proc, epoch):
        while chunk := proc.stdout.read(1600):
            with self.control.lock:
                if epoch != self.epoch or self.capture is not proc:
                    return
                if len(self.pcm) + len(chunk) <= 480000:
                    self.pcm.extend(chunk)
                self.state["level"] = rms(chunk)
                self._changed()
        with self.control.lock:
            if epoch == self.epoch and self.capture is proc:
                self.state["recording"] = False
                self.state["level"] = 0.0
                if proc.wait() != 0 and len(self.pcm) < 480000:
                    self.state["notice"] = (
                        "Microphone capture failed. Check the selected input and retry."
                    )
                    self.pcm.clear()
                else:
                    self.state["notice"] = (
                        "Recording reached fifteen seconds. Send it or discard it."
                    )
                self._changed()

    def finish(self):
        self._unlocked()
        if self.record_fence != (
            self.control.selected,
            self.control.generation,
            self.epoch,
        ):
            raise ValueError("This recording belongs to an expired session")
        proc, self.capture = self.capture, None
        terminate(proc)
        data = bytes(self.pcm)
        self.pcm.clear()
        self.state.update(recording=False, level=0.0)
        if len(data) < 3200:
            self._changed()
            raise ValueError(
                "No usable recording. Check your microphone and try again."
            )
        fence = self.record_fence
        self.state["transcribing"] = True
        worker = self.recognizer = self._spawn(
            [*WORKER, "transcribe"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
        )
        self._changed()
        threading.Thread(
            target=self._transcribe, args=(worker, data, fence), daemon=True
        ).start()

    def _transcribe(self, worker, data, fence):
        try:
            output, _ = worker.communicate(data, timeout=60)
            if worker.returncode:
                raise ValueError(
                    "Local speech recognition failed. Check voice installation and retry."
                )
            text = json.loads(output)["text"]
            with self.control.lock:
                if fence != (
                    self.control.selected,
                    self.control.generation,
                    self.epoch,
                ):
                    return
                self._unlocked()
                self.state["transcribing"] = False
                if not text:
                    raise ValueError(
                        "No speech detected. Try speaking closer to the selected microphone."
                    )
                self.control.chat(text, spoken=True)
                self.state["notice"] = "Recording sent to your selected model."
                self._changed()
        except Exception as exc:
            terminate(worker)
            with self.control.lock:
                if fence == (
                    self.control.selected,
                    self.control.generation,
                    self.epoch,
                ):
                    self.state.update(
                        transcribing=False,
                        notice=str(exc)
                        if isinstance(exc, ValueError)
                        else "Speech recognition could not finish. Try again.",
                    )
                    self._changed()

    def speak(self, text):
        self._unlocked()
        if not self.snapshot()["speech_ready"]:
            raise ValueError("Install local voice components before playback")
        self.stop_audio()
        epoch = self.epoch
        targets = self._target("output")
        worker = self.synthesis = self._spawn(
            [*WORKER, "speak"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
        )
        worker.stdin.write(text[:4000].encode())
        worker.stdin.close()
        self.state["notice"] = "Preparing local speech…"
        self._changed()
        threading.Thread(
            target=self._play, args=(worker, targets, epoch), daemon=True
        ).start()

    def _play(self, worker, targets, epoch):
        player = None
        try:
            while chunk := worker.stdout.read(2204):
                with self.control.lock:
                    if epoch != self.epoch:
                        return
                    if player is None:
                        self._unlocked()
                        player = self.player = self._spawn(
                            [
                                "pw-play",
                                "--raw",
                                "--rate",
                                "22050",
                                "--channels",
                                "1",
                                "--format",
                                "s16",
                                "--latency",
                                "50ms",
                                *targets,
                                "-",
                            ],
                            stdin=subprocess.PIPE,
                        )
                        os.set_blocking(player.stdin.fileno(), False)
                        self.state.update(speaking=True, notice="")
                    if player.poll() is not None:
                        raise ValueError(
                            "Audio output disconnected. Check the selected speaker."
                        )
                    try:
                        if os.write(player.stdin.fileno(), chunk) != len(chunk):
                            raise ValueError("Audio output stalled; playback stopped.")
                    except BlockingIOError:
                        raise ValueError("Audio output stalled; playback stopped.")
                    self.state["level"] = rms(chunk)
                    self._changed()
                time.sleep(len(chunk) / 44100)
            if player:
                player.stdin.close()
                player.wait(timeout=5)
            if worker.wait(timeout=5) or player is None:
                raise ValueError(
                    "Local voice could not produce audio. Check voice installation."
                )
        except Exception as exc:
            with self.control.lock:
                if epoch == self.epoch:
                    self.state["notice"] = (
                        str(exc)
                        if isinstance(exc, ValueError)
                        else "Playback stopped. Check the selected output and retry."
                    )
        finally:
            terminate(player)
            terminate(worker)
            with self.control.lock:
                if epoch == self.epoch:
                    self.player = self.synthesis = None
                    self.state.update(speaking=False, level=0.0)
                    self._changed()

    def enable_camera(self):
        self._unlocked()
        path = self.settings["camera"]
        if path not in {x["id"] for x in devices()["cameras"]}:
            raise ValueError("Choose an available camera first")
        if self.camera:
            return
        epoch = self.camera_epoch
        proc = self.camera = self._spawn(
            [*WORKER, "camera", path, str(self.frame)], stdout=subprocess.PIPE
        )
        self.state["notice"] = "Opening camera…"
        threading.Thread(
            target=self._read_camera, args=(proc, epoch), daemon=True
        ).start()
        self._changed()

    def _read_camera(self, proc, epoch):
        try:
            for line in proc.stdout:
                event = json.loads(line)
                with self.control.lock:
                    if epoch != self.camera_epoch:
                        return
                    self.state.update(
                        camera=bool(event.get("camera")),
                        gaze=event.get("gaze", [0.0, 0.0]),
                        face=bool(event.get("face")),
                        notice="",
                    )
                    self._changed()
        finally:
            with self.control.lock:
                if epoch == self.camera_epoch:
                    self.stop_camera()
                    self.state["notice"] = (
                        "Camera stopped. Check the device and enable it again."
                    )
                    self._changed()

    def vision_attachment(self):
        self._unlocked()
        if (
            not self.state["camera"]
            or not self.frame.exists()
            or time.time() - self.frame.stat().st_mtime > 3
        ):
            raise ValueError("Enable a connected camera before asking about its view")
        current = self.control.store.session(self.control.selected)
        model = self.control.catalog.validate(current["model"], current["mode"])
        if not model.get("vision"):
            raise ValueError(
                "The selected model has no vision capability. Camera gaze still works; select an installed vision model to ask about images."
            )
        data = self.frame.read_bytes()
        if len(data) > 512000:
            raise ValueError("Camera image exceeds the supported size")
        return [
            {
                "type": "image",
                "url": "data:image/jpeg;base64," + base64.b64encode(data).decode(),
            }
        ]

    def stop_audio(self):
        self.epoch += 1
        for key in ("capture", "recognizer", "synthesis", "player"):
            proc = getattr(self, key)
            setattr(self, key, None)
            terminate(proc)
        self.pcm.clear()
        self.record_fence = None
        self.state.update(
            recording=False, transcribing=False, speaking=False, level=0.0
        )
        self._changed()

    def stop_camera(self):
        self.camera_epoch += 1
        proc, self.camera = self.camera, None
        terminate(proc)
        self.frame.unlink(missing_ok=True)
        self.frame.with_suffix(".tmp").unlink(missing_ok=True)
        self.state.update(camera=False, face=False, gaze=[0.0, 0.0])
        self._changed()

    def stop(self):
        self.awake = False
        self.listener_ready = False
        self.followup = 0.0
        worker, self.listener = self.listener, None
        terminate(worker)
        self.stop_audio()
        self.stop_camera()

    def wake(self):
        self._unlocked()
        if self.awake:
            return
        if not self.control.ws or self.control.active:
            raise ValueError(
                "Connect a vision model and finish its turn before waking Progre"
            )
        current = self.control.store.session(self.control.selected)
        if not self.control.catalog.validate(current["model"], current["mode"]).get(
            "vision"
        ):
            raise ValueError("Select an installed vision model before waking Progre")
        if not self.snapshot()["speech_ready"]:
            raise ValueError("Install local voice components before waking Progre")
        if not self.settings["camera"]:
            cameras = devices()["cameras"]
            if len(cameras) != 1:
                raise ValueError(
                    "Choose a connected camera in Devices before waking Progre"
                )
            self.settings["camera"] = cameras[0]["id"]
            self.control.store.set("devices", self.settings)
        self._target("output")
        inventory = devices()
        if not inventory["outputs"] or not inventory["inputs"]:
            raise ValueError("Connect a microphone and speakers before waking Progre")
        target = self._target("input")
        self.stop()
        try:
            self.enable_camera()
            self.listener_paused = True
            worker = self.listener = self._spawn(
                [
                    *WORKER,
                    "listen",
                    json.dumps(
                        {"phrase": self.settings["listener_phrase"], "target": target}
                    ),
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
            self.awake = True
            self.wake_started = time.monotonic()
            self.state["notice"] = "Waking up: opening camera and local listener…"
            threading.Thread(target=self._listen, args=(worker,), daemon=True).start()
            self._changed()
        except Exception:
            self.stop()
            raise

    def _pause_listener(self, paused):
        if (
            not self.listener_ready
            or not self.listener
            or paused == self.listener_paused
        ):
            return
        try:
            self.listener.stdin.write((json.dumps({"pause": paused}) + "\n").encode())
            self.listener.stdin.flush()
            self.listener_paused = paused
            if not paused:
                if self.followup == float("inf"):
                    self.followup = time.monotonic() + 10
                self.state["notice"] = (
                    "Listening for “" + self.settings["listener_phrase"] + "”"
                )
            self._changed()
        except (BrokenPipeError, OSError):
            self.stop()
            self.state["notice"] = (
                "Local listener stopped. Check the microphone and wake Progre again."
            )

    def _listen(self, worker):
        try:
            for line in worker.stdout:
                event = json.loads(line)
                with self.control.lock:
                    if self.listener is not worker or not self.awake:
                        return
                    self._unlocked()
                    if event.get("ready"):
                        self.listener_ready = True
                        self._pause_listener(False)
                        continue
                    if "level" in event and not self.listener_paused:
                        self.state["level"] = max(0.0, min(1.0, float(event["level"])))
                        self._changed()
                        continue
                    if self.listener_paused or self.control.active or self.synthesis:
                        continue
                    text = event.get("text", "")
                    if not text or not (
                        event.get("addressed") or time.monotonic() < self.followup
                    ):
                        continue
                    self._pause_listener(True)
                    self.followup = float("inf")
                    if event.get("bare"):
                        self.speak("Yes? I'm listening.")
                    else:
                        self.control.chat(text, spoken=True)
            raise ValueError(
                "Local listener disconnected. Check the selected microphone and wake Progre again."
            )
        except Exception as exc:
            with self.control.lock:
                if self.listener is worker:
                    self.stop()
                    self.state["notice"] = (
                        str(exc)
                        if isinstance(exc, ValueError)
                        else "Local listener failed. Wake Progre again."
                    )
                    self._changed()
