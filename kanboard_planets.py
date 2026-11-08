"""Read-only Kanboard metadata projected into Avalon's existing planet renderer."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import math
from pathlib import Path
import time

HELPER = Path(__file__).resolve().parent.parent / 'pt-workstation-agent-skills-factory-alt-dev/tools/factory_board/cli.py'
STAGES = {'Quality': 'quality', 'Release Approval': 'quality', 'Released': 'production'}


def board():
    spec = importlib.util.spec_from_file_location('avalon_native_board', HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Board('lyra')


def collect():
    client = board()
    project = client.config['projects']['work']
    columns = {int(v): k for k, v in client.config['columns']['work'].items()}
    users = {int(v): k for k, v in client.config['users'].items()}
    cards = []
    for status in (1, 0):
        for row in client.call('getAllTasks', {'project_id': project, 'status_id': status})[:200]:
            if int(row['id']) == client.config['control_task_id']:
                continue
            column = columns.get(int(row['column_id']), 'Unknown')
            cards.append(dict(id=int(row['id']), title=str(row['title'])[:160], column=column,
                              stage=STAGES.get(column, 'development'), owner=users.get(int(row.get('owner_id') or 0), ''),
                              updated_at=int(row.get('date_modification') or 0), active=bool(status)))
    events = []
    for row in client.call('getProjectActivity', {'project_id': project})[:50]:
        task = row.get('task') or {}
        column = task.get('column_title', 'Unknown')
        # No descriptions, comments, HTML, attachments or account fields enter the wallpaper.
        events.append(dict(id=int(row['id']), task_id=int(row['task_id']),
                           actor=str(row.get('author_username') or '')[:80],
                           at=int(row.get('date_creation') or 0), action=str(row.get('event_name') or '')[:80],
                           column=column, stage=STAGES.get(column, 'development')))
    return dict(cards=cards, events=events, checked_at=int(time.time()), url=client.config['url'])


def overlay(scene, snapshot, activity):
    from recent_activity import timestamp
    nodes = scene['nodes']
    systems = {n.get('path', '').rstrip('/').split('/')[-1]: (i, n) for i, n in enumerate(nodes)
               if n.get('kind') == 'Directory system' and n.get('path')}
    cards = {c['id']: c for c in snapshot.get('cards', [])}
    counts = dict(development=0, quality=0, production=0)
    items = [('card', c['id'], c, c['updated_at'], c['column']) for c in cards.values()]
    items += [('event', e['id'], cards[e['task_id']], e['at'], e['action'])
              for e in snapshot.get('events', [])[:20] if e['task_id'] in cards]
    for kind, key, card, at, label in items:
        if card['stage'] not in systems:
            continue
        parent, root = systems[card['stage']]
        index = len(nodes)
        seed = int(hashlib.sha256(f'{kind}:{key}'.encode()).hexdigest()[:8], 16) / 0xffffffff
        angle = seed * math.tau
        radius = .65 + (seed * 7 % 1) * 1.05
        stamp = datetime.fromtimestamp(at, timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        nodes.append(dict(id=f'kanboard:{kind}:{key}', kind='Memory planet', source_kind='Kanboard '+kind,
                          name=f'#{card["id"]} · {label} · {card["title"]}',
                          detail=f'Kanboard {kind} · {card["column"]} · {stamp} · {card["title"]}',
                          path='', root=root['root'], orbit_parent=root['id'],
                          x=root['x']+radius*math.cos(angle), y=root['y']+radius*math.sin(angle), z=root['z']+.4,
                          color='#e4bf7a' if kind == 'card' else '#8dd7b1', alpha=.95,
                          action='', memory=f'kanboard-task-{card["id"]}', memory_rank=0,
                          board_url=snapshot.get('url', '')+f'/?controller=TaskViewController&action=show&task_id={card["id"]}&project_id=1'))
        counts[card['stage']] += 1
        # Assignment alone is not activity. Actual event authors drive recent movement.
        if kind == 'event':
            event = next(e for e in snapshot['events'] if e['id'] == key)
            actor = event['actor']
            if actor and at >= timestamp(activity.get(actor, {}).get('at')):
                activity[actor] = dict(at=at, source='Kanboard', targets=[index, parent])
    # Control-card actions still count as real agent activity without adding control planets.
    from recent_activity import timestamp
    for event in snapshot.get('events', []):
        actor = event['actor']
        if actor and event['at'] > timestamp(activity.get(actor, {}).get('at')):
            stage = systems.get(event['stage'])
            activity[actor] = dict(at=event['at'], source='Kanboard', targets=[stage[0]] if stage else [])
    scene['kanboard'] = dict(counts=counts, checked_at=snapshot.get('checked_at'), error=snapshot.get('error'))
    scene.setdefault('counts', {})['kanboard_planets'] = sum(counts.values())
    return scene
