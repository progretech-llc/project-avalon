#!/usr/bin/env python3
"""Use Avalon's existing authenticated loopback API; no credentials in argv or output."""
import http.cookiejar
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request


def send(action, data):
    if action not in ('settings', 'send'):
        raise ValueError('Unknown wallpaper chat action')
    state = (Path.home() / '.local/state/project-avalon').resolve().parent
    file = state / 'control-auth.json'
    stat = file.lstat()
    if not file.is_file() or file.is_symlink() or stat.st_uid != os.getuid() or stat.st_mode & 0o077 or stat.st_size > 4096:
        raise ValueError('Reopen Avalon to restore its private local connection')
    token = json.loads(file.read_text())['entry']
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    origin = 'http://127.0.0.1:8766'
    def request(path, payload, csrf=''):
        req = urllib.request.Request(origin + path, data=json.dumps(payload, ensure_ascii=False).encode(),
            headers={'Content-Type': 'application/json', 'Origin': origin, 'X-CSRF-Token': csrf})
        with client.open(req, timeout=10) as response:
            return json.load(response)
    csrf = request('/api/auth', {'token': token})['csrf']
    request('/api/desktop-chat' + ('/send' if action == 'send' else ''), data, csrf)
    return {'ok': True}


if __name__ == '__main__':
    try:
        raw = sys.stdin.read(65537)
        if len(raw) > 65536:
            raise ValueError('Wallpaper request is too long')
        print(json.dumps(send(sys.argv[1], json.loads(raw))))
    except urllib.error.HTTPError as error:
        try:
            message = json.loads(error.read(4096)).get('error', 'Avalon could not accept this request')
        except (ValueError, OSError):
            message = 'Avalon could not accept this request'
        print(json.dumps({'ok': False, 'error': message}))
    except (OSError, ValueError, KeyError, IndexError):
        print(json.dumps({'ok': False, 'error': 'Open Avalon and connect your agent, then retry'}))
