from playwright.sync_api import sync_playwright
import json
from pathlib import Path
state=dict(revision=1,status='idle',runtime_status='idle',appearance=dict(avatar='constellation',quality='balanced',fps=30,motion='system',idle_saver=True),session=dict(id='fixture',title='Fixture',platform='opencode',model='small:local',mode='chat',commands=False),messages=[],sessions=[],events=[],active_turn=None,detail='Fixture',wallpaper=dict(mode='avalon'),csrf='fixture')
sources=dict(settings=dict(roots=[dict(label='Saved local folders',path='/home/test/Projects')],max_files=160,max_directories=48,display_agents=None,show_memory=True,openharness=False,project_subfolders=True,harness_agent_limit=5),frameworks=[dict(name='Codex',machine='Other machine',state='working',updated_at='2026-11-07T20:00:00Z')],revision='fixture',agents=[dict(id='codex',name='Codex',current=True,selected=True,sources=['Codex · configured client'])],busy=False,notice='Fixture metadata',collector_available=True)
saves=[]
def route(r):
 p=r.request.url.split('18766',1)[1].split('?')[0]
 if p=='/api/constellation/sources':
  if r.request.method=='POST':
   data=r.request.post_data_json
   if data.get('action')=='save':
    saves.append(data['settings']);sources['settings']=data['settings']
  x=sources
 elif p=='/api/constellation':x=dict(settings={},scene=None,foreground=False)
 elif p=='/api/models':x=dict(models=[dict(name='small:local',tools=True,vision=False)],platforms=[dict(id='opencode',name='OpenCode',available=True)])
 elif p=='/api/devices':x=dict(inputs=[],outputs=[],cameras=[])
 else:x=state
 r.fulfill(status=200,content_type='application/json',body=json.dumps(x))
with sync_playwright() as p:
 b=p.chromium.launch()
 for width in [1280,390]:
  sources['settings'].update(openharness=False,harness_agent_limit=5,project_subfolders=True)
  page=b.new_page(viewport=dict(width=width,height=1050));errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.route('**/api/**',route)
  page.goto('http://127.0.0.1:18766/templates/index.html');page.wait_for_timeout(500)
  page.locator('[data-page="appearance"]').click()
  page.locator('#galaxy-sources-form').wait_for(state='visible')
  assert page.locator('#galaxy-project-subfolders').is_checked()
  assert page.locator('#galaxy-local-agents').is_visible()
  page.locator('#galaxy-openharness').check()
  assert not page.locator('#galaxy-local-agents').is_visible()
  assert page.locator('#galaxy-harness-agent-limit').input_value()=='5'
  page.locator('#galaxy-harness-agent-limit').fill('3')
  page.locator('#galaxy-source-save').click();page.wait_for_timeout(200)
  assert saves[-1]['openharness'] and saves[-1]['harness_agent_limit']==3
  assert saves[-1]['display_agents'] is None
  page.locator('#galaxy-openharness').scroll_into_view_if_needed()
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  page.screenshot(path=f'/tmp/avalon-harness-{width}.png')
  page.locator('#galaxy-openharness').uncheck()
  assert page.locator('#galaxy-local-agents').is_visible()
  page.locator('#galaxy-project-subfolders').uncheck()
  page.locator('#galaxy-source-save').click();page.wait_for_timeout(200)
  assert not saves[-1]['openharness'] and not saves[-1]['project_subfolders']
  assert not errors,errors
  page.close()
 b.close()
print('Desktop/mobile: defaults, integration toggle, count save, local roster restoration, folder toggle, no overflow or browser errors passed.')
