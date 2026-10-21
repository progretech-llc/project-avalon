import json
from pathlib import Path
import tempfile
import time
import unittest

from resource_activity import overlay, read_events


class ResourceActivityTests(unittest.TestCase):
    def test_recent_receipts_only_and_private_paths_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'receipt.json'
            p.write_text(json.dumps(dict(schema=1, engine='codex', agent_id='native', events=[
                dict(kind='read', path='/mnt/PT-Storage/Tools & Assets/skills/test/SKILL.md', at='2026-10-21T20:00:00Z'),
                dict(kind='read', path='/mnt/PT-Storage/Tools & Assets/private/data.txt', at='2026-10-21T20:00:00Z'),
                dict(kind='memory', service='hindsight', at='2026-10-21T19:00:00Z')])) )
            from datetime import datetime
            events = read_events(Path(d), datetime.fromisoformat('2026-10-21T20:01:00+00:00').timestamp())
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]['kind'], 'read')

    def test_resource_targets_preserve_writes_and_require_native_owner(self):
        scene = dict(nodes=[dict(id='root:tools', kind='Directory system', path='/mnt/PT-Storage/Tools & Assets',
                                 root='Tools', x=0, y=0, z=0, color='#fff'),
                            dict(id='agent:lyra', kind='Agent', color='#fff')], links=[],
                     agent_activity=[dict(agent=1, targets=[0], write_targets=[])])
        event = dict(engine='codex', agent_id='native', kind='read', path='/mnt/PT-Storage/Tools & Assets/skills/test/SKILL.md', at=time.time())
        overlay(scene, [event], {})
        self.assertEqual(len(scene['nodes']), 2)
        overlay(scene, [event], {'native': 'lyra'})
        self.assertEqual(scene['nodes'][2]['action'], 'observed read')
        self.assertEqual(scene['agent_activity'][0]['targets'], [2, 0])
        self.assertEqual(scene['agent_activity'][0]['write_targets'], [])


if __name__ == '__main__':
    unittest.main()
