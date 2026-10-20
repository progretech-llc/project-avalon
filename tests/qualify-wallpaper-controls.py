#!/usr/bin/env python3
"""Browser fixture: serve the repository on loopback :18766; API calls are intercepted."""
from playwright.sync_api import sync_playwright
import json
cfg=dict(enabled=False,placement='anchor-left',opacity=.72,x=.06,y=.60,read_aloud=False)
state=dict(revision=1,status='idle',runtime_status='idle',appearance=dict(avatar='ethereal',quality='balanced',fps=30,motion='system',idle_saver=True),desktop_chat=cfg,session=dict(id='fixture',title='Fixture conversation',platform='opencode',model='small:local',mode='chat',commands=False),messages=[],sessions=[],events=[],active_turn=None,detail='Local fixture',wallpaper=dict(mode='avalon'),csrf='fixture')
def route(r):
 p=r.request.url.split('18766',1)[1].split('?')[0]
 if p=='/api/desktop-chat':
  cfg.update(r.request.post_data_json);state['revision']+=1;x=state
 elif p=='/api/models':x=dict(models=[dict(name='small:local',tools=True,vision=False)],platforms=[dict(id='opencode',name='OpenCode',available=True)])
 elif p=='/api/devices':x=dict(inputs=[],outputs=[],cameras=[])
 elif p.startswith('/api/constellation'):x={}
 else:x=state
 r.fulfill(status=200,content_type='application/json',body=json.dumps(x))
with sync_playwright() as p:
 b=p.chromium.launch()
 for w in [1280,390]:
  page=b.new_page(viewport=dict(width=w,height=1050));errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.route('**/api/**',route);page.goto('http://127.0.0.1:18766/templates/index.html');page.wait_for_timeout(700)
  page.locator('#wallpaper-chat-enabled').scroll_into_view_if_needed()
  assert page.locator('#wallpaper-chat-enabled').is_checked()==cfg['enabled']
  page.locator('#wallpaper-chat-enabled').check();page.locator('#wallpaper-chat-options').wait_for(state='visible');page.locator('#wallpaper-chat-placement').select_option('movable');page.locator('#wallpaper-chat-opacity').fill('55');page.locator('#wallpaper-chat-opacity').dispatch_event('input')
  # Leave the form and allow multiple state polls before applying the draft.
  page.locator('h1').first.click();page.wait_for_timeout(2600)
  assert page.locator('#wallpaper-chat-placement').input_value()=='movable'
  assert page.locator('#wallpaper-chat-opacity').input_value()=='55'
  page.get_by_role('button',name='Apply chatbox settings').click();page.wait_for_timeout(150)
  assert cfg['enabled'] and cfg['placement']=='movable' and cfg['opacity']==.55
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  page.wait_for_timeout(1800);assert page.locator('#wallpaper-chat-placement').input_value()=='movable'
  cfg['placement']='anchor-right';page.wait_for_timeout(1800)
  assert page.locator('#wallpaper-chat-placement').input_value()=='anchor-right'
  assert not errors,errors
  page.close()
 b.close()
print('Presence control: default off, enable/save placement/opacity, unsaved choices survive blur and polling, persisted choice survives polling, responsive 390/1280px, no browser errors')
