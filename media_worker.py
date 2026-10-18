"""Private CPU media worker; LampOS leaf drivers, never its second conversational LLM."""

import json
import os
import signal
import sys
import threading
import time
import subprocess
import queue
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".deps/lampos"))
MODELS = ROOT / ".runtime/media/models"


def listen():
    """Keep the CPU recognizer warm; discard room audio during agent playback."""
    import numpy as np
    from faster_whisper import WhisperModel
    from faster_whisper.vad import get_vad_model
    from hal.drivers.voice._internal.speaker_decorate import SpeakerDecorator

    options = json.loads(sys.argv[2])
    decorator = SpeakerDecorator([options["phrase"]], 0, enable_people_perception=False)
    model = WhisperModel(
        str(MODELS / "whisper-base.en"),
        device="cpu",
        compute_type="int8",
        cpu_threads=4,
        local_files_only=True,
    )
    vad = get_vad_model()
    paused = threading.Event()
    paused.set()
    chunks = queue.Queue(maxsize=32)
    stopped = threading.Event()
    output_lock = threading.Lock()

    def emit(event):
        with output_lock:
            print(json.dumps(event), flush=True)

    proc = subprocess.Popen(
        [
            "pw-record",
            "--raw",
            "--rate",
            "16000",
            "--channels",
            "1",
            "--format",
            "s16",
            *options["target"],
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    def controls():
        for line in sys.stdin:
            if json.loads(line).get("pause", True):
                paused.set()
            else:
                paused.clear()
        stopped.set()

    def capture():
        last_level = 0.0
        while data := proc.stdout.read(3200):
            if not paused.is_set() and time.monotonic() - last_level > 0.2:
                samples = np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768
                emit(
                    {"level": min(1.0, float(np.sqrt(np.mean(samples * samples))) * 5)}
                )
                last_level = time.monotonic()
            try:
                chunks.put_nowait(None if paused.is_set() else data)
            except queue.Full:
                pass  # Never accumulate stale microphone audio behind inference.
        stopped.set()

    threading.Thread(target=controls, daemon=True).start()
    threading.Thread(target=capture, daemon=True).start()
    emit({"ready": True})
    data = bytearray()
    recent = bytearray()
    quiet = 0
    try:
        while not stopped.is_set():
            try:
                chunk = chunks.get(timeout=0.3)
            except queue.Empty:
                continue
            if chunk is None or paused.is_set():
                data.clear()
                recent.clear()
                quiet = 0
                continue
            pcm = np.frombuffer(chunk, dtype="<i2").astype(np.float32) / 32768
            recent.extend(chunk)
            del recent[:-32000]
            window = np.frombuffer(recent, dtype="<i2").astype(np.float32) / 32768
            window = np.pad(window, (0, (-len(window)) % 512))
            speech = bool(np.max(vad(window)[-4:]) > 0.6)
            if speech and not data:
                data.extend(recent[: -len(chunk)])
            if speech or data:
                data.extend(chunk)
                quiet = quiet + 1 if not speech else 0
            if data and (quiet >= 25 or len(data) >= 480000):
                audio = np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768
                data.clear()
                quiet = 0
                segments, _ = model.transcribe(
                    audio,
                    language="en",
                    beam_size=3,
                    vad_filter=True,
                    condition_on_previous_text=False,
                    initial_prompt=options["phrase"] + ".",
                    hotwords=options["phrase"],
                )
                text = " ".join(s.text.strip() for s in segments).strip()
                if text and not paused.is_set():
                    emit(
                        {
                            "text": text[:16000],
                            "addressed": decorator.starts_with_wake_word(text),
                            "bare": decorator.is_bare_wake_phrase(text),
                        }
                    )
    finally:
        proc.terminate()
        proc.wait(timeout=3)


def transcribe():
    import numpy as np
    from faster_whisper import WhisperModel
    from hal.drivers.voice.stt.provider import STTSession

    class LocalSession(STTSession):
        def __init__(self):
            self.data = bytearray()
            self.closed = False

        def start(self, on_transcript):
            self.callback = on_transcript
            return True

        def send_audio(self, data):
            if self.closed or len(self.data) + len(data) > 16000 * 2 * 15:
                raise ValueError("Recording exceeds fifteen seconds")
            self.data.extend(data)

        def close(self):
            if self.closed:
                return
            self.closed = True
            audio = np.frombuffer(self.data, dtype="<i2").astype(np.float32) / 32768
            if len(audio) < 1600 or np.sqrt(np.mean(audio * audio)) < 0.001:
                self.callback("", True)
                return
            model = WhisperModel(
                str(MODELS / "whisper-base.en"),
                device="cpu",
                compute_type="int8",
                cpu_threads=4,
                local_files_only=True,
            )
            segments, _ = model.transcribe(
                audio,
                language="en",
                beam_size=3,
                vad_filter=True,
                condition_on_previous_text=False,
            )
            self.callback(" ".join(s.text.strip() for s in segments).strip(), True)
            self.data.clear()

        def is_closed(self):
            return self.closed

    session = LocalSession()
    session.start(
        lambda text, final: print(
            json.dumps({"text": text[:16000], "final": final}), flush=True
        )
    )
    session.send_audio(sys.stdin.buffer.read(16000 * 2 * 15 + 1))
    session.close()


def speak():
    from hal.drivers.voice.tts.piper import PiperTTSBackend

    voice_dir = MODELS / "piper/en/en_US/ljspeech/medium"
    backend = PiperTTSBackend(
        voice="en_US-ljspeech-medium",
        voices_dir=str(voice_dir),
        binary=str(ROOT / ".media-venv/bin/piper"),
    )
    text = sys.stdin.read(4001)
    if len(text) > 4000:
        raise ValueError("Speech text is too long")
    if not backend.available:
        raise RuntimeError("Local voice is not installed")
    try:
        for chunk in backend.stream_pcm(text, "", "", 1.0):
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
    finally:
        # The upstream backend maintains a warm spare. This one-shot worker owns
        # it; reap it here instead of leaving an idle voice process behind.
        with backend._spare_lock:
            if backend._spare is not None:
                backend._spare.kill()
                backend._spare.wait(timeout=2)


def camera():
    import cv2
    from hal.drivers.camera.host_capture_device import HostVideoCaptureDevice
    from hal.drivers.camera.models import VideoCaptureDeviceInfo

    path = sys.argv[2]
    snapshot = Path(sys.argv[3])
    if not path.startswith("/dev/v4l/by-id/") or not path.endswith("video-index0"):
        raise ValueError("Camera must be an enumerated stable device")
    camera = HostVideoCaptureDevice(
        VideoCaptureDeviceInfo(device_id=path, max_width=640, max_height=480, fps=15)
    )
    detector = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    stopped = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    gaze = [0.0, 0.0]
    camera.acquire_consumer()
    camera.start()
    last_snapshot = 0.0
    started = time.monotonic()
    try:
        while not stopped.wait(0.12):
            frame = camera.last_frame
            if time.monotonic() - max(camera.last_frame_ts, started) > 3:
                raise RuntimeError(
                    "Camera disconnected; enable it again after reconnecting"
                )
            if frame is None:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = detector.detectMultiScale(
                gray, scaleFactor=1.2, minNeighbors=5, minSize=(48, 48)
            )
            target = [0.0, 0.0]
            if len(faces):
                x, y, w, h = max(faces, key=lambda r: r[2] * r[3])
                target = [
                    1 - 2 * (x + w / 2) / frame.shape[1],
                    1 - 2 * (y + h / 2) / frame.shape[0],
                ]
            gaze = [a + (b - a) * 0.22 for a, b in zip(gaze, target)]
            # One replaceable private frame for an explicit selected-model vision
            # request; never send a camera frame to the browser/compositor.
            if time.monotonic() - last_snapshot > 1:
                ok, data = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                if ok:
                    tmp = snapshot.with_suffix(".tmp")
                    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                    with os.fdopen(fd, "wb") as f:
                        f.write(data.tobytes())
                    tmp.replace(snapshot)
                last_snapshot = time.monotonic()
            print(
                json.dumps({"camera": True, "gaze": gaze, "face": bool(len(faces))}),
                flush=True,
            )
    finally:
        camera.release_consumer()
        camera.stop()
        snapshot.unlink(missing_ok=True)


if __name__ == "__main__":
    {"transcribe": transcribe, "speak": speak, "camera": camera, "listen": listen}[
        sys.argv[1]
    ]()
