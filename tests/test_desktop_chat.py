import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from control import Controller, Conflict
from desktop_chat import DEFAULTS, validate, latest_exchange
from test_control import FakeCatalog, FakeRuntime
from app import create_app, credentials


class DesktopChatTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runtime = FakeRuntime()
        self.config = patch('control.configure', return_value={})
        self.config.start(); self.addCleanup(self.config.stop)
        self.control = Controller(Path(self.temp.name), FakeCatalog(), self.runtime)
        self.addCleanup(self.control.close)

    def test_default_off_and_strict_settings(self):
        self.assertFalse(self.control.snapshot()['desktop_chat']['enabled'])
        for changes in [{'enabled': 1}, {'opacity': float('nan')}, {'opacity': 0}, {'x': True}, {'placement':'anywhere'}, {'token':'secret'}]:
            with self.assertRaises(ValueError): self.control.set_desktop_chat(changes)
        self.control.set_desktop_chat(dict(enabled=True, placement='movable', x=.2, y=.4))
        self.assertEqual(self.control.store.get('desktop_chat')['x'], .2)
        self.assertTrue(self.control.snapshot()['desktop_chat']['enabled'])

    def test_latest_pair_preserves_session_history_and_rejects_stale_session(self):
        self.control.select({'model':'small:local'})
        session=self.control.selected
        old_user=self.control.store.message(session,'user','old question')
        self.control.store.message(session,'assistant','old answer','complete')
        with self.assertRaises(Conflict): self.control.desktop_chat_send({'session':session,'text':'off'})
        self.control.set_desktop_chat({'enabled':True})
        with self.assertRaises(Conflict): self.control.desktop_chat_send({'session':'other','text':'no'})
        self.control.desktop_chat_send({'session':session,'text':'new question'})
        scene=json.loads(self.control.visual.read_text())['desktop_chat']
        self.assertEqual(scene['user']['text'],'new question')
        self.assertEqual(scene['reply']['text'],'')
        self.assertNotIn('old answer',json.dumps(scene))
        self.assertEqual(self.control.selected,session)
        self.assertEqual(len(self.control.store.messages(session)),4)
        with self.assertRaises(Conflict):self.control.desktop_chat_send({'session':session,'text':'duplicate'})
        self.control.set_desktop_chat({'enabled':False})
        scene=json.loads(self.control.visual.read_text())['desktop_chat']
        self.assertIsNone(scene['user']);self.assertIsNone(scene['reply'])
        self.assertEqual(len(self.control.store.messages(session)),4)

    def test_two_overlay_turns_reuse_one_runtime_and_keep_only_latest_pair(self):
        self.control.select({'model':'small:local'})
        session=self.control.selected
        self.control.set_desktop_chat({'enabled':True})
        for prompt,answer in [('first','first answer'),('continue','continued answer')]:
            self.control.desktop_chat_send({'session':session,'text':prompt})
            self.runtime.current.emit('text',{'text':answer})
            self.runtime.current.emit('session.idle')
            deadline=time.monotonic()+2
            while self.control.active and time.monotonic()<deadline:time.sleep(.01)
            self.assertIsNone(self.control.active)
        self.assertEqual(self.runtime.starts,1)
        self.assertEqual(self.control.selected,session)
        self.assertEqual(len(self.control.store.messages(session)),4)
        pair=json.loads(self.control.visual.read_text())['desktop_chat']
        self.assertEqual(pair['user']['text'],'continue')
        self.assertEqual(pair['reply']['text'],'continued answer')
        self.assertNotIn('first answer',json.dumps(pair))
        self.assertEqual(self.control.store.get('desktop_chat')['enabled'],True)

    def test_display_projection_is_bounded_and_never_mixes_turns(self):
        msgs=[dict(id=1,role='user',text='old',status='complete'),dict(id=2,role='assistant',text='previous',status='complete'),dict(id=3,role='user',text='🟦'*16000,status='complete')]
        pair=latest_exchange(msgs)
        self.assertIsNone(pair['reply'])
        self.assertLess(len(json.dumps(pair).encode()),30000)
        self.assertEqual(len(msgs[-1]['text']),16000)

    def test_overlay_speaker_is_independent_of_voice_replies(self):
        media=SimpleNamespace(epoch=5,awake=True,settings={'spoken_replies':True},speak=Mock())
        c=SimpleNamespace(media=media,desktop_chat={**DEFAULTS,'enabled':True},pending_action=None,selected='s',generation=1)
        job=dict(wallpaper=True,media_epoch=5)
        Controller._speak_reply(c,job,'muted');media.speak.assert_not_called()
        c.desktop_chat['read_aloud']=True
        media.awake=False;media.settings['spoken_replies']=False
        Controller._speak_reply(c,job,'final');media.speak.assert_called_once_with('final')
        media.speak.reset_mock();c.desktop_chat['enabled']=False
        Controller._speak_reply(c,job,'disabled');media.speak.assert_not_called()
        media.awake=True;media.settings['spoken_replies']=True
        Controller._speak_reply(c,dict(media_epoch=5,spoken=True),'voice');media.speak.assert_called_once_with('voice')

    def test_existing_authentication_and_csrf_protect_overlay_routes(self):
        with patch.dict('os.environ',{'AVALON_STATE_DIR':self.temp.name}):
            app=create_app(self.control,{'TESTING':True});client=app.test_client()
        origin='http://127.0.0.1:8766'
        for path in ['/api/desktop-chat','/api/desktop-chat/send']:
            self.assertEqual(client.post(path,base_url=origin,json={},headers={'Origin':origin}).status_code,401)
        r=client.post('/api/auth',base_url=origin,json={'token':credentials(Path(self.temp.name))['entry']},headers={'Origin':origin})
        csrf=r.json['csrf']
        self.assertEqual(client.post('/api/desktop-chat',base_url=origin,json={},headers={'Origin':origin}).status_code,403)
        r=client.post('/api/desktop-chat',base_url=origin,json={'enabled':True},headers={'Origin':origin,'X-CSRF-Token':csrf})
        self.assertEqual(r.status_code,200)
        self.assertTrue(r.json['desktop_chat']['enabled'])
