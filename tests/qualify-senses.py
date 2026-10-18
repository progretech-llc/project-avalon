#!/usr/bin/env python3
"""Synthetic sanitized sensory state in an isolated real GPU compositor."""
import importlib.util
import json
from pathlib import Path
import time

spec=importlib.util.spec_from_file_location('q',Path(__file__).with_name('qualify-shell.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sh=m.Shell(Path('.runtime/test-bus').read_text());assert sh.evaluate("GLib.getenv('AVALON_TEST_SHELL')")=='1'
sh.enable(m.AVALON);sh.wait_owner(m.AVALON)
path=Path('.runtime/shell-state/project-avalon/sensory-fixture.json').resolve()
sh.evaluate("Main.extensionManager.lookup('avalon@progretech.com').stateObj._statePath="+json.dumps(str(path)))
out=Path('docs/evidence/phase-4');out.mkdir(parents=True,exist_ok=True)
settings={'avatar':'ethereal','quality':'balanced','fps':30,'motion':'full'}

def value(code):return sh.evaluate("(()=>{let e=Main.extensionManager.lookup('avalon@progretech.com').stateObj;return "+code+"})()")
def write(state='listening',sensor=None):
 data={'schema':1,'status':state,'model':'sensory-qualification:fixture','heartbeat':time.time(),'appearance':settings,'sensors':sensor if sensor is not None else {'gaze':[.65,-.35],'level':.72}}
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data));tmp.replace(path)
def wait(fn):
 until=time.monotonic()+3
 while time.monotonic()<until:
  if fn():return
  time.sleep(.01)
 raise AssertionError('Sensory uniforms did not update')

matrix=[]
for avatar in ('ethereal','sentinel','mascot','abstract'):
 settings['avatar']=avatar
 for state,index in [('listening',9),('speaking',10),('approval',11)]:
  write(state);wait(lambda:value('e._areas[0]._effect._values.state')==index)
  wait(lambda:abs(value('e._areas[0]._effect._values.gaze_x')-.65)<.001)
  assert abs(value('e._areas[0]._effect._values.level')-.72)<.001
  matrix.append([avatar,state])
settings['avatar']='ethereal';write();time.sleep(.3);sh.capture(out/'sensory-native-fixture.png')
settings['idle_saver'] = False
write('idle')
wait(lambda:value('e._timerFps') == 30)
settings['idle_saver'] = True
write('idle')
wait(lambda:value('e._timerFps') == 15)
write('listening')
wait(lambda:value('e._timerFps') == 30)

for bad in ({'gaze':[2,0],'level':.3},{'gaze':['bad',0],'level':.3},{'gaze':[0,0],'level':-1}):
 write(sensor=bad);wait(lambda:value('e._areas[0]._effect._values.level')==0)
 assert value('e._areas[0]._effect._values.gaze_x')==0
settings['motion']='reduced';write();wait(lambda:value('e._appearance.motion')=='reduced');time.sleep(.3)
assert value('e._areas[0]._effect._values.gaze_x')==0
frames=value('e._frames');write(sensor={'gaze':[-.5,.4],'level':.2});time.sleep(.4)
assert value('e._frames')==frames,'Still mode redrew for tracking/amplitude alone'
write('speaking');wait(lambda:value('e._areas[0]._effect._values.state')==10)
sh.evaluate("Main.extensionManager.lookup('avalon@progretech.com').stateObj._statePath="+json.dumps(str(Path('.runtime/desktop/visual-state.json').resolve())))
result={'fixture_matrix':matrix,'idle_saver_and_active_frame_limits':True,'gaze_and_amplitude_applied':True,'invalid_sensors_neutral':True,'still_mode_ignores_tracking_but_updates_state':True,'method':'Synthetic state files → actual native Cogl uniforms. Not physical camera or microphone qualification.'}
(out/'sensory-renderer.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
