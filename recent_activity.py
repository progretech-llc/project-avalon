"""Movement from bounded activity metadata, without inventing file writes."""
from datetime import datetime
import time
import math

RECENT_SECONDS = 48 * 60 * 60


def timestamp(value):
    try:
        result = float(value) if isinstance(value, (int, float)) else datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
        return result if math.isfinite(result) else 0
    except (ValueError, TypeError, AttributeError, OverflowError):
        return 0


def overlay(scene, activity, now=None):
    now = time.time() if now is None else now
    entries = {r['agent']: r for r in scene.get('agent_activity', [])}
    systems = [i for i, n in enumerate(scene['nodes']) if n.get('kind') == 'Directory system']
    memory = next((i for i in systems if scene['nodes'][i]['id'] == 'root:Hindsight'), None)
    for i, node in enumerate(scene['nodes']):
        if node.get('kind') != 'Agent':
            continue
        identity = node['id'].removeprefix('agent:')
        evidence = activity.get(identity, {})
        at = max(timestamp(evidence.get('at')), timestamp(node.get('session_updated_at')))
        if at <= 0 or not 0 <= now - at <= RECENT_SECONDS:
            continue
        node['recent_activity_at'] = at
        node['recent_activity_source'] = evidence.get('source', 'OpenHarness session')
        node['alpha'] = max(node.get('alpha', .42), .65 + .31 * (1 - (now-at)/RECENT_SECONDS))
        entry = entries.setdefault(i, dict(agent=i, targets=[], write_targets=[], modified_targets=[], last_modified_root=None))
        targets = [t for t in evidence.get('targets', []) if t in range(len(scene['nodes']))]
        if not targets and evidence.get('source') == 'Hindsight' and memory is not None:
            targets = [memory]
        # Recent activity gives asteroid destinations only. Satellite write targets stay intact.
        entry['targets'] = list(dict.fromkeys([*targets, *entry.get('targets', [])])) or systems
    scene['agent_activity'] = list(entries.values())
    return scene
