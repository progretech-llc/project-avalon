#!/usr/bin/env python3
"""Explicit optional CPU speech/CV setup. Never called by model discovery."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    python = ROOT / ".media-venv/bin/python"
    if not python.exists():
        subprocess.run(
            ["uv", "venv", "--python", "3.12", str(ROOT / ".media-venv")], check=True
        )
    subprocess.run(
        [
            str(python),
            "-c",
            'import sys; assert sys.version_info[:2] == (3, 12), "Media environment must use Python 3.12"',
        ],
        check=True,
    )
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            "-r",
            str(ROOT / "requirements-media.txt"),
        ],
        check=True,
    )
    sources = json.loads(
        (ROOT / "docs/evidence/phase-4/model-sources.json").read_text()
    )
    request = ROOT / ".runtime/media/download.json"
    request.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    request.write_text(json.dumps(sources))
    subprocess.run(
        [
            str(python),
            "-c",
            """
import hashlib,json
from pathlib import Path
from huggingface_hub import hf_hub_download
root=Path.cwd(); sources=json.loads((root/'.runtime/media/download.json').read_text())
models=root/'.runtime/media/models'
for relative, expected in sources['files'].items():
    if relative.startswith('whisper-base.en/'):
        repo='Systran/faster-whisper-base.en'; name=relative.split('/',1)[1]; target=models/'whisper-base.en'
    else:
        repo='rhasspy/piper-voices';name=relative.split('/',1)[1];target=models/'piper'
    path=Path(hf_hub_download(repo,name,revision=sources['revisions'][repo],local_dir=str(target)))
    if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise RuntimeError('Media model checksum mismatch')
print('Installed pinned local speech/CV components. Camera and microphone remain off.')
""",
        ],
        cwd=ROOT,
        check=True,
    )
    request.unlink()


if __name__ == "__main__":
    main()
