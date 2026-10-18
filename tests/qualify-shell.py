#!/usr/bin/env python3
"""Integration assertions against an isolated GNOME Shell, never the user's Shell."""
import argparse
import concurrent.futures
import json
from pathlib import Path
import time
import gi
from gi.repository import Gio, GLib

AVALON='avalon@progretech.com'
CONSTELLATION='factory-observatory@progretech.com'

class Shell:
    def __init__(self,address):
        self.bus=Gio.DBusConnection.new_for_address_sync(address,Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT|Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,None,None)
    def call(self,method,args=None):
        return self.bus.call_sync('org.gnome.Shell','/org/gnome/Shell','org.gnome.Shell.Extensions',method,args,None,Gio.DBusCallFlags.NONE,10000,None).unpack()
    def evaluate(self,code):
        ok, result=self.bus.call_sync('org.gnome.Shell','/org/gnome/Shell','org.gnome.Shell','Eval',GLib.Variant('(s)',(code,)),None,Gio.DBusCallFlags.NONE,15000,None).unpack()
        assert ok,result
        return json.loads(result) if result else None
    def snapshot(self):
        return self.evaluate('''(() => {
            const manager=Main.extensionManager;
            const a=manager.lookup('avalon@progretech.com');
            const c=manager.lookup('factory-observatory@progretech.com');
            const areas=e=>(e?.stateObj?._areas??[]).filter(x=>!x.is_destroyed?.());
            return {owner:globalThis[Symbol.for('com.progretech.wallpaper-owner.v1')]?.owner?.uuid??null,
                avalon:{state:a?.state,count:areas(a).length}, constellation:{state:c?.state,count:areas(c).length},
                monitors:Main.layoutManager.monitors.length,
                behindWindows:areas(a).every(x=>x.get_parent()===Main.layoutManager._backgroundGroup),
                clickThrough:areas(a).every(x=>!x.reactive)};
        })()''')
    def wait_owner(self,uuid):
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            s=self.snapshot()
            if s['owner']==uuid and s['avalon']['count']+s['constellation']['count']==s['monitors']:
                loser='constellation' if uuid==AVALON else 'avalon'
                if s[loser]['count']==0 and s[loser]['state']!=1:
                    assert s['behindWindows'] and s['clickThrough'],s
                    return s
            time.sleep(.1)
        raise AssertionError(s)
    def enable(self,uuid):self.call('EnableExtension',GLib.Variant('(s)',(uuid,)))
    def capture(self,path):
        result=self.bus.call_sync('org.gnome.Shell.Screenshot','/org/gnome/Shell/Screenshot','org.gnome.Shell.Screenshot','Screenshot',GLib.Variant('(bbs)',(False,False,str(path.resolve()))),None,Gio.DBusCallFlags.NONE,15000,None).unpack()
        assert result[0],result

def main():
    p=argparse.ArgumentParser();p.add_argument('--bus-file',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    sh=Shell(a.bus_file.read_text())
    assert sh.evaluate("GLib.getenv('AVALON_TEST_SHELL')")=='1','Refusing real session'
    sh.evaluate('Main.overview.hide(); Main.messageTray._banner?.close(); true')
    results={}
    sh.evaluate("""(() => {
        const dir=GLib.build_filenamev([GLib.get_user_config_dir(),'factory-observatory']);
        GLib.mkdir_with_parents(dir,0o700);
        GLib.file_set_contents(GLib.build_filenamev([dir,'wallpaper.json']),JSON.stringify({enabled:false,rotation_speed:0.7}));
        return true;
    })()""")
    for uuid,name in [(AVALON,'avalon_start'),(CONSTELLATION,'avalon_to_constellation'),(AVALON,'constellation_to_avalon')]:
        sh.enable(uuid);results[name]=sh.wait_owner(uuid)
    restored=sh.evaluate("""JSON.parse(new TextDecoder().decode(GLib.file_get_contents(GLib.build_filenamev([GLib.get_user_config_dir(),'factory-observatory','wallpaper.json']))[1]))""")
    assert restored['enabled'] is True and restored['rotation_speed']==0.7,restored
    results['direct_enable_restores_power_preserves_appearance']=True
    for i in range(10):
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            list(pool.map(sh.enable,[AVALON,CONSTELLATION]))
        time.sleep(.2)
        s=sh.snapshot();assert s['owner'] in (AVALON,CONSTELLATION),s
        sh.wait_owner(s['owner'])
    results['concurrent_starts']=10
    sh.enable(AVALON);sh.wait_owner(AVALON)
    sh.evaluate("Main.extensionManager.lookup('avalon@progretech.com').stateObj.disable(); true")
    s=sh.snapshot();assert s['owner'] is None and s['avalon']['count']==0,s
    results['resource_cleanup']=True
    sh.call('DisableExtension',GLib.Variant('(s)',(AVALON,)))
    time.sleep(.3)
    sh.enable(AVALON);results['reenable_after_stop']=sh.wait_owner(AVALON)
    time.sleep(.5)
    sh.capture(a.out/'animated-desktop-a.png')
    time.sleep(.7)
    sh.capture(a.out/'animated-desktop-b.png')
    results['rendering']=sh.snapshot()
    (a.out/'shell-results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
