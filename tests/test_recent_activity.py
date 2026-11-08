import unittest
from recent_activity import overlay, RECENT_SECONDS


class RecentActivityTests(unittest.TestCase):
    def scene(self):
        return dict(nodes=[dict(id='host', kind='Host'),
                           dict(id='root:Hindsight', kind='Directory system'),
                           dict(id='agent:mak', kind='Agent', alpha=.42)],
                    agent_activity=[dict(agent=2, targets=[], write_targets=[], last_modified_root=None)])

    def test_recent_memory_moves_agent_without_changing_satellite_or_writes(self):
        scene = overlay(self.scene(), {'mak':dict(at=990,source='Hindsight')}, now=1000)
        self.assertEqual(scene['agent_activity'][0]['targets'], [1])
        self.assertIsNone(scene['agent_activity'][0]['last_modified_root'])
        self.assertEqual(scene['agent_activity'][0]['write_targets'], [])
        self.assertGreater(scene['nodes'][2]['alpha'], .9)

    def test_expired_or_future_activity_is_not_active(self):
        for at in [1000-RECENT_SECONDS-1, 2000, 'bad']:
            scene = overlay(self.scene(), {'mak':dict(at=at,source='Hindsight')}, now=1000)
            self.assertEqual(scene['agent_activity'][0]['targets'], [])
            self.assertNotIn('recent_activity_at', scene['nodes'][2])

    def test_recent_sessions_roam_without_claiming_file_updates(self):
        scene=self.scene();scene['nodes'][2]['session_updated_at']=990
        overlay(scene,{},now=1000)
        self.assertEqual(scene['agent_activity'][0]['targets'],[1])
        self.assertEqual(scene['agent_activity'][0]['write_targets'],[])
