"""Bounded OpenHarness framework metadata across the account's machines."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import shlex
import subprocess

from resource_activity import safe_path


def read_frameworks(limit=5, *, workstation=False, sessions=False, run=subprocess.run):
    def call(args, remote=False):
        command = ['harness', *args]
        if remote:
            command = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=3', 'factory',
                       'bash -lc ' + shlex.quote(shlex.join(command))]
        result = run(command, capture_output=True, text=True, timeout=12, check=True)
        if len(result.stdout) > 2_000_000:
            raise ValueError('OpenHarness metadata exceeds limit')
        return result.stdout

    remote = False
    if workstation:
        try:
            call(['ps', '--json'])
        except (OSError, subprocess.SubprocessError):
            remote = True
    try:
        listing = call(['machines', '--json'], remote)
    except (OSError, subprocess.SubprocessError):
        if not workstation:
            raise
        remote = True
        listing = call(['machines', '--json'], remote=True)
    try:
        machines = json.loads(listing)
        machines = machines if isinstance(machines, list) else machines.get('machines', [machines])
    except ValueError:
        machines = [json.loads(line) for line in listing.splitlines() if line.strip()]
    if not isinstance(machines, list) or len(machines) > 100:
        raise ValueError('Invalid OpenHarness machine list')
    machines = [m for m in machines if isinstance(m, dict) and isinstance(m.get('machineId'), str)]
    failures = []

    def fetch(machine):
        try:
            data = json.loads(call(['ps', *([] if machine.get('current') else ['--machine', machine.get('name') or machine['machineId']]), '--all', '--json'], remote))
            rows = data['harnesses']
            if not isinstance(rows, list):
                raise ValueError('Invalid OpenHarness sessions')
            return rows[:1000]
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            failures.append(machine['machineId'])
            return []

    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = [row for batch in pool.map(fetch, machines) for row in batch]
    clean = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name, updated = row.get('agent'), row.get('lastActive')
        if not isinstance(name, str) or not name.strip() or len(name) > 80:
            continue
        try:
            timestamp = datetime.fromisoformat(updated.replace('Z', '+00:00'))
            if timestamp.tzinfo is None:
                continue
            timestamp = timestamp.timestamp()
        except (AttributeError, ValueError, TypeError):
            continue
        native_id = row.get('id')
        if sessions and (not isinstance(native_id, str) or not native_id):
            continue
        key = (str(row.get('machine', '')) + ':' + native_id) if sessions else name.strip().casefold()
        identity = 'harness-' + hashlib.sha256(key.encode()).hexdigest()[:16]
        clean.append(dict(id=identity, native_id=native_id, name=str(row.get('name') or name).strip()[:80] if sessions else name.strip(), current=True, sources=['OpenHarness · latest framework activity'],
                          machine=str(row.get('machine', ''))[:120], state=str(row.get('state', 'unknown'))[:40],
                          updated_at=updated, timestamp=timestamp, folder=row.get('folder', '')))
    latest = {}
    for row in sorted(clean, key=lambda x: (-x['timestamp'], x['id'], x['machine'])):
        latest.setdefault(row['id'], row)
    return list(latest.values())[:limit], len(failures)


def overlay(scene, frameworks):
    """Session folders are context, never evidence that files were modified."""
    nodes = scene['nodes']
    for index, row in enumerate(frameworks):
        phase = int(hashlib.sha256(row['id'].encode()).hexdigest()[:8], 16) / 0xffffffff * math.tau
        color = ['#79dce8', '#b4a1ee', '#e4bf7a', '#8dd7b1', '#ffaaa1'][index % 5]
        agent = len(nodes)
        nodes.append(dict(id='agent:' + row['id'], name=row['name'], kind='Agent', root='', path='',
                          x=3*math.cos(phase), y=3*math.sin(phase), z=.5, color=color, alpha=.96,
                          orbit_parent='host', memory='', memory_rank=0, action='',
                          session_state=row['state'], session_updated_at=row['updated_at'],
                          detail=row['name']+' · '+row['machine']+' · '+row['state'], machine=row['machine']))
        entry = dict(agent=agent, targets=[], context_targets=[], write_targets=[], modified_targets=[], last_modified_root=None)
        path = safe_path(row.get('folder'))
        roots = [(i, node) for i, node in enumerate(nodes) if node.get('kind') == 'Directory system'
                 and node.get('path') and path is not None and path.is_relative_to(Path(node['path']))]
        if roots:
            target, _ = max(roots, key=lambda pair: len(pair[1]['path']))
            entry['targets'] = entry['context_targets'] = [target]
            scene['links'].append({'from': agent, 'to': target, 'color': color})
        scene.setdefault('agent_activity', []).append(entry)
    scene.setdefault('counts', {})['agents'] = sum(n.get('kind') == 'Agent' for n in nodes)
    scene['available_agents'] = [n['id'].removeprefix('agent:') for n in nodes if n.get('kind') == 'Agent']
    scene['source'] = 'openharness-framework-session-metadata'
    return scene
