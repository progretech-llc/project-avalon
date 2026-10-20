#!/usr/bin/env python3
"""Real input and lifecycle checks in the isolated test Shell; transport is stubbed, never live chat."""
import argparse
import importlib.util
import json
from pathlib import Path
import time

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('shell_check',ROOT/'tests/qualify-shell.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
p=argparse.ArgumentParser();p.add_argument('--bus-file',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
sh=module.Shell(args.bus_file.read_text())
assert sh.evaluate("GLib.getenv('AVALON_TEST_SHELL')")=='1','Refusing the login Shell'
args.out.mkdir(parents=True,exist_ok=True)
fixture=(args.out/'visual-state.json').resolve()
data=dict(schema=1,heartbeat=time.time(),status='idle',platform='codex',model='native',
    appearance=dict(avatar='ethereal',motion='reduced',fps=15),
    desktop_chat=dict(enabled=False,placement='anchor-left',opacity=.72,x=.06,y=.60,
        read_aloud=False,connected=True,active=False,session='fixture',platform='codex',
        user=dict(id=1,text='Can we continue the same conversation?',status='complete'),
        reply=dict(id=2,text='Yes. This chat uses the session already selected in Presence.',status='complete')))
def write(**changes):
    data['desktop_chat'].update(changes);data['heartbeat']=time.time();fixture.write_text(json.dumps(data));time.sleep(.3)
def value(code):
    return sh.evaluate("(()=>{const c=Main.extensionManager.lookup('avalon@progretech.com').stateObj._chat;"+code+"})()")
sh.enable(module.AVALON);sh.wait_owner(module.AVALON)
sh.evaluate('Main.overview.hide();true')
write();sh.evaluate("Main.extensionManager.lookup('avalon@progretech.com').stateObj._statePath="+json.dumps(str(fixture)));time.sleep(.3)
assert value('return c.actor.visible;') is False
write(enabled=True)
assert value('return c.actor.visible;') is True
assert value('return c.user.text.text;')==data['desktop_chat']['user']['text']
assert value('return c.reply.text.text;')==data['desktop_chat']['reply']['text']
sh.capture(args.out/'wallpaper-chat.png')
# Only synthetic commands are intercepted, so this test cannot reach the real account or model.
value('''globalThis.__chatRequests=[];c.command=(action,payload,done)=>{
 __chatRequests.push({action,payload});
 if(action==='settings'){
  const file=Main.extensionManager.lookup('avalon@progretech.com').stateObj._statePath;
  const d=JSON.parse(new TextDecoder().decode(GLib.file_get_contents(file)[1]));
  Object.assign(d.desktop_chat,payload);d.heartbeat=Date.now()/1000;GLib.file_set_contents(file,JSON.stringify(d));
 }
 done?.();
};
const C=imports.gi.Clutter,seat=global.stage.context.get_backend().get_default_seat();
globalThis.__chatPointer=seat.create_virtual_device(C.InputDeviceType.POINTER_DEVICE);
globalThis.__chatKeyboard=seat.create_virtual_device(C.InputDeviceType.KEYBOARD_DEVICE);
return true;''')
def click(x,y):
    sh.evaluate(f'__chatPointer.notify_absolute_motion(GLib.get_monotonic_time(),{x},{y});true');time.sleep(.05)
    for state in ['PRESSED','RELEASED']:
        sh.evaluate(f'__chatPointer.notify_button(GLib.get_monotonic_time(),1,imports.gi.Clutter.ButtonState.{state});true');time.sleep(.05)
x,y=value('return c.entry.get_transformed_position();');click(x+30,y+15)
assert value('return global.stage.get_key_focus()===c.entry.clutter_text;'),'Pointer click did not focus text entry'
for key in ['h','i','Return']:
    sh.evaluate(f'''(()=>{{const C=imports.gi.Clutter,t=GLib.get_monotonic_time();__chatKeyboard.notify_keyval(t,C.KEY_{key},C.KeyState.PRESSED);__chatKeyboard.notify_keyval(t+1000,C.KEY_{key},C.KeyState.RELEASED);return true;}})()''');time.sleep(.04)
assert sh.evaluate('__chatRequests[0]')==dict(action='send',payload=dict(text='hi',session='fixture'))
x,y=value('return c.speaker.get_transformed_position();');click(x+15,y+15);time.sleep(.3)
assert sh.evaluate('__chatRequests[1]')==dict(action='settings',payload=dict(read_aloud=True))
assert value('return c.speaker.child.icon_name;')=='audio-volume-high-symbolic'
write(placement='movable')
x,y=value('return c.title.get_parent().get_transformed_position();')
sh.evaluate(f'__chatPointer.notify_absolute_motion(GLib.get_monotonic_time(),{x+60},{y+14});true');time.sleep(.05)
sh.evaluate('__chatPointer.notify_button(GLib.get_monotonic_time(),1,imports.gi.Clutter.ButtonState.PRESSED);true');time.sleep(.05)
assert value('return !!c.drag;')
sh.evaluate('__chatPointer.notify_absolute_motion(GLib.get_monotonic_time(),750,400);true');time.sleep(.1)
assert value('return c.actor.x;')>400
sh.evaluate('__chatPointer.notify_button(GLib.get_monotonic_time(),1,imports.gi.Clutter.ButtonState.RELEASED);true');time.sleep(.3)
assert value('return !!c.drag;') is False
assert value('return c.actor.x;')>400
position=sh.evaluate('__chatRequests.at(-1)');assert position['action']=='settings' and 0<=position['payload']['x']<=1 and 0<=position['payload']['y']<=1
write(placement='anchor-right',opacity=.35)
assert value('return c.actor.x;')>800
assert value('return c.actor.get_style().includes("0.35");')
sh.evaluate('Main.overview.show();true');time.sleep(.5);assert value('return c.actor.visible;') is False
sh.evaluate('Main.overview.hide();true');time.sleep(.5)
data['heartbeat']=time.time()-30;fixture.write_text(json.dumps(data));time.sleep(.3);assert value('return c.actor.visible;') is False
write(enabled=False);assert value('return c.actor.visible;') is False
sh.enable(module.CONSTELLATION);sh.wait_owner(module.CONSTELLATION)
assert sh.evaluate("Main.extensionManager.lookup('avalon@progretech.com').stateObj?._chat??null") is None
proof=dict(default_off=True,two_bubbles=True,real_pointer_focus_and_keyboard_send=True,
    preserved_session_id=True,real_pointer_speaker_toggle=True,real_pointer_drag_and_normalized_position=True,
    anchor_right=True,translucency=True,overview_hidden=True,stale_controller_hidden=True,
    disable_and_wallpaper_handover_cleanup=True,
    limitation='Native UI commands use a synthetic transport stub. Authenticated transport, turn fencing and session continuity have separate backend checks; physical speech output is not asserted.')
(args.out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
