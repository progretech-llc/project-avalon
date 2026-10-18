"""Avalon-only OpenCode configuration and explicit native action policy."""

import json
import os
import secrets
import shutil
import subprocess
import urllib.request
from pathlib import Path


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name("." + path.name + "." + secrets.token_hex(6))
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def permissions(workspace, mode, commands=False):
    if mode not in ("chat", "read", "edit") or not isinstance(commands, bool):
        raise ValueError("Unknown permission policy")
    if commands and mode == "chat":
        raise ValueError("Workspace access is required for status commands")
    root = str(Path(workspace).resolve())
    if any(character in root for character in "*?[]"):
        raise ValueError(
            "Workspace paths containing wildcard characters are unsupported"
        )
    policy = {"*": "deny", "external_directory": "deny"}
    if mode in ("read", "edit"):
        # OpenCode read checks absolute paths; edit checks worktree-relative paths.
        # Search permissions match patterns, not directories: keep them denied.
        policy["read"] = {"*": "deny", root + "/**": "allow"}
    if mode == "edit":
        result = subprocess.run(
            ["git", "-C", root, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        worktree = result.stdout.strip() if result.returncode == 0 else root
        relative = os.path.relpath(root, worktree)
        pattern = "*" if relative == "." else relative + "/**"
        policy["edit"] = {"*": "deny", pattern: "allow"}
    if commands:
        policy["bash"] = {
            "*": "deny",
            "pwd": "allow",
            "git status --short": "allow",
            "git diff --stat": "allow",
        }
    return policy


def configure(state, model, workspace=None, mode="chat", commands=False, vision=False):
    if type(vision) is not bool:
        raise ValueError("Invalid model vision capability")
    state = Path(state).resolve()
    with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as r:
        installed = {m["name"] for m in json.load(r)["models"]}
    if model not in installed:
        raise ValueError(f"Model is not installed locally: {model}")
    binary = shutil.which("opencode")
    if not binary:
        raise ValueError("OpenCode is not installed")
    workspace = Path(workspace or state / "workspace").resolve()
    if not workspace.is_absolute():
        raise ValueError("Workspace must be absolute")
    policy = permissions(workspace, mode, commands)
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    for path in [
        workspace,
        state / "attachments",
        state / "agent-home/.config/opencode",
        state / "agent-home/.local/share",
        state / "agent-home/.cache",
        state / "agent-home/.local/state",
    ]:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
    config = {
        "$schema": "https://opencode.ai/config.json",
        "model": f"ollama/{model}",
        "small_model": f"ollama/{model}",
        "enabled_providers": ["ollama"],
        "autoupdate": False,
        "share": "disabled",
        "permission": policy,
        "plugin": [],
        "provider": {
            "ollama": {
                "npm": "@ai-sdk/openai-compatible",
                "name": "Ollama (local)",
                "options": {"baseURL": "http://127.0.0.1:11434/v1"},
                "models": {
                    model: {"name": model, "limit": {"context": 32768, "output": 4096}}
                },
            }
        },
    }
    if vision:
        config["provider"]["ollama"]["models"][model].update(
            attachment=True, modalities={"input": ["text", "image"], "output": ["text"]}
        )
    atomic_json(state / "agent-home/.config/opencode/opencode.json", config)
    path = state / "gateway.json"
    gateway = (
        json.loads(path.read_text())
        if path.exists()
        else {"token": secrets.token_urlsafe(48)}
    )
    gateway.update(
        binary=binary,
        model=model,
        workspace=str(workspace),
        permission_mode=mode,
        status_commands=commands,
    )
    atomic_json(path, gateway)
    return gateway
