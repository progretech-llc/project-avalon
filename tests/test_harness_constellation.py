import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import galaxy_sources as gs
import harness_constellation as hc


class HarnessConstellationTest(unittest.TestCase):
    def test_cross_machine_frameworks_are_unique_and_sorted_by_real_timestamps(self):
        machines = [dict(machineId='one'), dict(machineId='two')]
        sessions = {
            'one': [dict(agent='Codex', machine='One', lastActive='2026-11-07T15:00:00-05:00'),
                    dict(agent='Claude Code', machine='One', lastActive='2026-11-07T19:30:00Z')],
            'two': [dict(agent='Codex', machine='Two', lastActive='2026-11-07T20:01:00Z'),
                    dict(agent='Hermes', machine='Two', lastActive='invalid')],
        }
        def run(argv, **kwargs):
            data = '\n'.join(json.dumps(m) for m in machines) if argv[1] == 'machines' else json.dumps({'harnesses': sessions[argv[3]]})
            return SimpleNamespace(stdout=data)
        rows, failed = hc.read_frameworks(2, run=run)
        self.assertEqual([r['name'] for r in rows], ['Codex', 'Claude Code'])
        self.assertEqual(rows[0]['machine'], 'Two')
        self.assertEqual(failed, 0)
        self.assertEqual(len(hc.read_frameworks(1, run=run)[0]), 1)

    def test_sessions_keep_same_framework_separate_and_preserve_named_agents(self):
        def run(argv, **kwargs):
            if argv[1] == 'machines':
                return SimpleNamespace(stdout=json.dumps([dict(machineId='one')]))
            return SimpleNamespace(stdout=json.dumps({'harnesses': [
                dict(id=str(i), name='Worker '+str(i), agent='OpenCode', machine='One',
                     lastActive=f'2026-11-07T20:0{i}:00Z') for i in range(6)]}))
        rows, failed = hc.read_frameworks(5, sessions=True, run=run)
        self.assertEqual([r['native_id'] for r in rows], ['5', '4', '3', '2', '1'])
        self.assertEqual(len({r['id'] for r in rows}), 5)
        scene = dict(nodes=[dict(id='host', kind='Host'),
                           dict(id='agent:lyra', kind='Agent')], links=[], agent_activity=[])
        hc.overlay(scene, rows)
        self.assertEqual(scene['counts']['agents'], 6)
        self.assertIn('lyra', scene['available_agents'])

    def test_unavailable_machine_keeps_reachable_frameworks(self):
        def run(argv, **kwargs):
            if argv[1] == 'machines':
                return SimpleNamespace(stdout=json.dumps([dict(machineId='online'), dict(machineId='offline')]))
            if argv[3] == 'offline':
                raise OSError('unreachable')
            return SimpleNamespace(stdout=json.dumps({'harnesses': [dict(agent='OpenCode', lastActive='2026-11-07T20:00:00Z')]}))
        rows, failed = hc.read_frameworks(run=run)
        self.assertEqual(len(rows), 1)
        self.assertEqual(failed, 1)

    def test_context_targets_do_not_claim_writes_or_require_remote_folder_locally(self):
        scene = dict(nodes=[dict(id='host', kind='Host'), dict(id='root:Development', kind='Directory system', path='/mnt/PT-Storage/Projects/development')], links=[], agent_activity=[])
        rows = [dict(id='harness-test', name='Codex', folder='/mnt/PT-Storage/Projects/development/missing-on-this-machine', state='working', machine='Other', updated_at='2026-11-07T20:00:00Z')]
        result = hc.overlay(scene, rows)
        self.assertEqual(result['agent_activity'][0]['targets'], [1])
        self.assertEqual(result['agent_activity'][0]['write_targets'], [])
        self.assertEqual(result['counts']['agents'], 1)
        self.assertEqual(result['nodes'][2]['machine'], 'Other')

    def test_project_children_toggle_offline_fallback_and_no_recursive_scan(self):
        with tempfile.TemporaryDirectory() as temp:
            projects = Path(temp) / 'Projects'
            projects.mkdir()
            (projects / 'development').mkdir()
            (projects / 'quality').mkdir()
            (projects / '.private').mkdir()
            (projects / 'development' / 'nested').mkdir()
            prefs = dict(roots=[dict(label='Saved', path='/saved')], project_subfolders=True)
            with patch.object(gs, 'PROJECTS', projects):
                self.assertEqual([r['label'] for r in gs.project_roots(prefs)], ['development', 'quality'])
                self.assertEqual(gs.project_roots({**prefs, 'project_subfolders': False}), prefs['roots'])
            with patch.object(gs, 'PROJECTS', projects / 'unavailable'):
                self.assertEqual(gs.project_roots(prefs), prefs['roots'])

    def test_preference_migration_and_invalid_integration_values(self):
        prefs = gs.preferences({'roots': [dict(label='Saved', path='/saved')]})
        self.assertFalse(prefs['openharness'])
        self.assertEqual(prefs['harness_agent_limit'], 5)
        for key, value in [('openharness', 1), ('project_subfolders', 'yes'), ('harness_agent_limit', True), ('harness_agent_limit', 0), ('harness_agent_limit', 101)]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                gs.validate({**prefs, key: value}, prefs)


if __name__ == '__main__':
    unittest.main()
