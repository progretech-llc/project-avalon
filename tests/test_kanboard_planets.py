import unittest
from unittest.mock import patch
from types import SimpleNamespace
from kanboard_planets import overlay, collect
from activity_browser import card_url


class BoardPlanetTests(unittest.TestCase):
    def test_collector_keeps_only_board_metadata_and_reads_only(self):
        methods=[]
        def call(method, params):
            methods.append(method)
            if method == 'getProjectActivity':
                return [dict(id=9,task_id=7,author_username='lyra',date_creation=500,event_name='task.move.column',
                             comment={'comment':'DO NOT EXPORT'},task=dict(column_title='Released',description='DO NOT EXPORT'))]
            if params['status_id'] == 0:return []
            return [dict(id=7,title='Task',column_id=8,owner_id=2,date_modification=500,description='DO NOT EXPORT')]
        client=SimpleNamespace(config=dict(projects={'work':1},columns={'work':{'Released':8}},users={'lyra':2},control_task_id=1,url='http://127.0.0.1:18765'),call=call)
        with patch('kanboard_planets.board',return_value=client):result=collect()
        self.assertEqual(result['cards'][0]['stage'],'production')
        self.assertNotIn('DO NOT EXPORT',str(result))
        self.assertTrue(all(m in {'getAllTasks','getProjectActivity'} for m in methods))

    def test_stages_actions_and_actual_actors(self):
        nodes=[dict(id='root:'+stage,root=stage,kind='Directory system',path='/mnt/PT-Storage/Projects/'+stage,x=i*3,y=0,z=0)
               for i,stage in enumerate(['development','quality','production'])]
        scene=dict(nodes=nodes,counts={})
        snapshot=dict(cards=[dict(id=7,title='Release candidate',stage='quality',column='Release Approval',updated_at=500,owner='mak')],
                      events=[dict(id=12,task_id=7,actor='lyra',at=600,action='task.move.column',stage='quality')],checked_at=700,url='http://127.0.0.1:18765')
        activity={};overlay(scene,snapshot,activity)
        self.assertEqual(scene['kanboard']['counts'],dict(development=0,quality=2,production=0))
        self.assertEqual(nodes[-1]['root'],'quality')
        self.assertEqual(nodes[-1]['memory'],'kanboard-task-7')
        self.assertEqual(activity['lyra']['at'],600)
        self.assertNotIn('mak',activity)
        self.assertNotIn('description',nodes[-1])

    def test_hidden_system_has_no_board_planets(self):
        scene=dict(nodes=[],counts={});snapshot=dict(cards=[dict(id=7,title='Title',stage='quality',column='Quality',updated_at=500)],events=[])
        overlay(scene,snapshot,{})
        self.assertEqual(scene['counts']['kanboard_planets'],0)

    def test_card_links_reject_arbitrary_urls_and_invalid_ids(self):
        self.assertIn('task_id=42',card_url('kanboard-task-42'))
        for identifier in ['https://example.com','kanboard-task-0','kanboard-task-42&x=bad']:
            with self.assertRaises(ValueError):card_url(identifier)
