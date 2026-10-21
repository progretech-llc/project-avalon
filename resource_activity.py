"""Overlay bounded native tool receipts; never read conversations or usage checkpoints."""
import hashlib
import json
import math
from pathlib import Path
import re
import time
import subprocess
from datetime import datetime
from itertools import islice

RECEIPTS = Path.home() / '.harness/cli/data/shared-resource-activity'
BLOCKED = re.compile(r'credential|secret|password|token|private.key', re.I)


def read_owners():
    """Match the native recorded owner, rather than guessing from a tool's brand."""
    result = subprocess.run(['harness', 'ps', '--all', '--json'], capture_output=True, text=True, timeout=5, check=True)
    if len(result.stdout) > 2_000_000:
        raise ValueError('Native metadata exceeds limit')
    return {row['id']: row['startedBy'] if row.get('startedBy') in {'lyra', 'mak', 'imagen'}
            else {'Codex': 'codex', 'Claude Code': 'claude'}.get(row.get('agent'))
            for row in json.loads(result.stdout).get('harnesses', []) if isinstance(row.get('id'), str)}


def safe_path(raw):
    if not isinstance(raw, str) or len(raw) > 4096 or any(ord(c) < 32 for c in raw):
        return None
    path = Path(raw)
    if not path.is_absolute():
        return None
    path = path.resolve()
    if any(p.startswith('.') or p.lower() in {'records', 'private', 'profiles', 'sessions', 'history', 'node_modules', '__pycache__', 'hermes', 'openclaw', 'hindsight'}
           or BLOCKED.search(p) for p in path.parts):
        return None
    if path.suffix.lower() in {'.db', '.sqlite', '.sqlite3', '.key', '.pem', '.pfx', '.env'}:
        return None
    return path


def read_events(directory=RECEIPTS, now=None):
    now = time.time() if now is None else now
    events = []
    if not directory.is_dir():
        return events
    for file in islice(directory.glob('*.json'), 512):
        try:
            if file.is_symlink() or file.stat().st_size > 128 * 1024 or now - file.stat().st_mtime > 900:
                continue
            value = json.loads(file.read_text())
            if value.get('schema') != 1 or value.get('engine') not in {'codex', 'claude'}:
                continue
            rows = value.get('events')
            if not isinstance(rows, list):
                continue
            for event in rows[:128]:
                if not isinstance(event, dict):
                    continue
                at = datetime.fromisoformat(event.get('at', '').replace('Z', '+00:00')).timestamp()
                if not 0 <= now - at <= 900:
                    continue
                kind = event.get('kind')
                if kind == 'memory' and event.get('service') in {'hindsight', 'knowledge'}:
                    events.append(dict(engine=value['engine'], agent_id=value.get('agent_id'), kind=kind, service=event['service'], at=at))
                elif kind in {'read', 'tool'} and (path := safe_path(event.get('path'))):
                    events.append(dict(engine=value['engine'], agent_id=value.get('agent_id'), kind=kind, path=str(path), at=at))
        except (OSError, ValueError, TypeError, AttributeError):
            continue
    return sorted(events, key=lambda e: e['at'], reverse=True)[:256]


def overlay(scene, events, owners=None):
    nodes = scene['nodes']
    agents = {n['id'].removeprefix('agent:'): i for i, n in enumerate(nodes) if n.get('kind') == 'Agent'}
    activity = {row['agent']: row for row in scene.get('agent_activity', [])}
    owners = owners or {}
    seen = set()
    for event in events:
        agent = agents.get(owners.get(event.get('agent_id')))
        if agent is None:
            continue
        entry = activity.setdefault(agent, dict(agent=agent, targets=[], write_targets=[]))
        if event['kind'] == 'memory':
            target = next((i for i, n in enumerate(nodes) if n.get('id') == 'root:Hindsight'
                           or str(n.get('id', '')).startswith('memory-system:')), None)
            # Knowledge retrieval is an API call, not proof of a local book read.
            if event.get('service') != 'hindsight':
                continue
        else:
            path = safe_path(event.get('path'))
            if path is None:
                continue
            roots = [(i, n) for i, n in enumerate(nodes) if n.get('kind') == 'Directory system'
                     and n.get('path') and path.is_relative_to(Path(n['path']).resolve())]
            if not roots:
                continue
            _, root = max(roots, key=lambda pair: len(pair[1]['path']))
            target = next((i for i, n in enumerate(nodes) if n.get('path') == str(path)), None)
            if target is None:
                if len(seen) >= 48:
                    continue
                phase = int(hashlib.sha256(str(path).encode()).hexdigest()[:8], 16) / 0xffffffff * math.tau
                target = len(nodes)
                nodes.append({**root, 'id': 'resource:' + str(path), 'kind': 'Remembered file',
                              'name': path.name, 'path': str(path), 'orbit_parent': root['id'],
                              'x': root['x'] + .8 * math.cos(phase), 'y': root['y'] + .8 * math.sin(phase),
                              'action': 'observed tool execution' if event['kind'] == 'tool' else 'observed read',
                              'memory': '', 'memory_author': '', 'memory_rank': 0})
        if target is None or (agent, target) in seen:
            continue
        seen.add((agent, target))
        # At most three recent resource targets leave room for the existing project context.
        recent = entry.setdefault('resource_targets', [])
        if len(recent) >= 3:
            continue
        recent.append(target)
        entry['targets'] = list(dict.fromkeys([*recent, *entry.get('targets', [])]))[:7]
        scene['links'].append({'from': agent, 'to': target, 'color': nodes[agent]['color']})
    scene['agent_activity'] = list(activity.values())
    scene['resource_event_count'] = len(seen)
    scene.setdefault('counts', {})['files'] = sum(n.get('kind') == 'Remembered file' for n in nodes)
    return scene
