"""Bounded local voice synthesis and a private, warm CPU model process."""

import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import textwrap

ROOT = Path(__file__).resolve().parent
MODELS = ROOT / ".runtime/media/models"
DEFAULTS = {
    "voice_engine": "kokoro",
    "voice_style": "female",
    "voice_pitch": 0.0,
    "voice_speed": 1.0,
}


def validate(settings):
    if settings["voice_engine"] not in ("kokoro", "piper"):
        raise ValueError("Choose Kokoro or Piper")
    if settings["voice_style"] not in ("male", "female", "robotic"):
        raise ValueError("Choose a male, female or robotic voice")
    for key, low, high in [("voice_pitch", -12, 12), ("voice_speed", 0.65, 1.6)]:
        value = settings[key]
        if (
            type(value) not in (int, float)
            or not math.isfinite(value)
            or not low <= value <= high
        ):
            raise ValueError(
                "Voice pitch must be -12 to +12 semitones; speed must be 0.65 to 1.6"
            )


def clean_text(text):
    text = re.sub(
        r"```.*?```", " Code is shown in the conversation. ", text, flags=re.S
    )
    text = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", text)
    return re.sub(r"[*#`]", "", text).strip()[:4000]


class Synthesizer:
    def __init__(self):
        self.kokoro = None
        self.piper = None

    def prepare(self, engine):
        if engine == "kokoro" and self.kokoro is None:
            import onnxruntime as ort
            from kokoro_onnx import Kokoro

            options = ort.SessionOptions()
            options.intra_op_num_threads = 4
            options.inter_op_num_threads = 1
            session = ort.InferenceSession(
                str(MODELS / "kokoro/kokoro-v1.0.onnx"),
                options,
                providers=["CPUExecutionProvider"],
            )
            self.kokoro = Kokoro.from_session(
                session, str(MODELS / "kokoro/voices-v1.0.bin")
            )
        if engine == "piper" and self.piper is None:
            from hal.drivers.voice.tts.piper import PiperTTSBackend

            self.piper = PiperTTSBackend(
                voice="en_US-ljspeech-medium",
                voices_dir=str(MODELS / "piper/en/en_US/ljspeech/medium"),
                binary=str(ROOT / ".media-venv/bin/piper"),
            )

    def chunks(self, request):
        import numpy as np

        validate(request)
        self.prepare(request["voice_engine"])
        # Sentence chunks begin playback before a whole paragraph is synthesized.
        sentences = re.split(r"(?<=[.!?])\s+|\n+", clean_text(request["text"]))
        for sentence in [
            part for sentence in sentences for part in textwrap.wrap(sentence, 220)
        ]:
            if not sentence.strip():
                continue
            if request["voice_engine"] == "kokoro":
                voices = {
                    "female": "af_heart",
                    "male": "am_michael",
                    "robotic": "am_adam",
                }
                audio, rate = self.kokoro.create(
                    sentence,
                    voice=voices[request["voice_style"]],
                    speed=request["voice_speed"],
                    lang="en-us",
                )
                pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()
            else:
                pcm = b"".join(
                    self.piper.stream_pcm(sentence, "", "", request["voice_speed"])
                )
                rate = self.piper.sample_rate
            filters = []
            if request["voice_pitch"]:
                filters.append(
                    "rubberband=pitch=" + str(2 ** (request["voice_pitch"] / 12))
                )
            if request["voice_style"] == "robotic":
                filters.append("tremolo=f=45:d=0.75")
            if filters or rate != 24000:
                args = [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-f",
                    "s16le",
                    "-ar",
                    str(rate),
                    "-ac",
                    "1",
                    "-i",
                    "pipe:0",
                ]
                if filters:
                    args += ["-af", ",".join(filters)]
                pcm = subprocess.run(
                    [*args, "-f", "s16le", "-ar", "24000", "-ac", "1", "pipe:1"],
                    input=pcm,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    check=True,
                    timeout=30,
                ).stdout
            yield pcm


def serve():
    path = Path(sys.argv[2])
    engine = sys.argv[3]
    synth = Synthesizer()
    synth.prepare(engine)
    path.unlink(missing_ok=True)
    with socket.socket(socket.AF_UNIX) as server:
        server.bind(str(path))
        path.chmod(0o600)
        server.listen(1)
        try:
            while True:
                conn, _ = server.accept()
                with conn:
                    try:
                        stream = conn.makefile("rb")
                        line = stream.readline(65537)
                        stream.close()
                        if len(line) > 65536:
                            continue
                        request = {**DEFAULTS, **json.loads(line)}
                        if (
                            not isinstance(request.get("text"), str)
                            or not 1 <= len(request["text"]) <= 4000
                        ):
                            continue
                        for pcm in synth.chunks(request):
                            conn.sendall(pcm)
                    except (BrokenPipeError, ConnectionError):
                        pass
        finally:
            path.unlink(missing_ok=True)


def client(request, path):
    with socket.socket(socket.AF_UNIX) as conn:
        conn.settimeout(45)
        conn.connect(str(path))
        conn.sendall((json.dumps(request) + "\n").encode())
        while chunk := conn.recv(4800):
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
