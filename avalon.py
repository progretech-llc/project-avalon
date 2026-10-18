#!/usr/bin/env python3
"""Small native foundation launcher; the full Presence Control Center is phase 2."""
import json
from pathlib import Path
import subprocess
import gi

gi.require_version('Gtk','4.0')
from gi.repository import Gio, GLib, Gtk

ROOT=Path(__file__).resolve().parent
UUID='avalon@progretech.com'
SERVICE='project-avalon-runtime.service'

class Foundation(Gtk.ApplicationWindow):
    def __init__(self,app):
        super().__init__(application=app,title='Project Avalon — Foundation')
        self.set_default_size(560,420)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14)
        for side in ['top','bottom','start','end']:getattr(box,'set_margin_'+side)(24)
        self.set_child(box)
        title=Gtk.Label(label='Project Avalon',xalign=0);title.add_css_class('title-1');box.append(title)
        box.append(Gtk.Label(label='Foundation preview · Camera and microphone are off',xalign=0,wrap=True))
        self.status=Gtk.Label(xalign=0,wrap=True,selectable=True);box.append(self.status)
        self.message=Gtk.Label(xalign=0,wrap=True,selectable=True)
        for caption,argv in [
            ('Enable Avalon wallpaper',['gnome-extensions','enable',UUID]),
            ('Return to Constellation',['gnome-extensions','enable','factory-observatory@progretech.com']),
            ('Disable Avalon wallpaper',['gnome-extensions','disable',UUID]),
            ('Start local runtime',['systemctl','--user','start',SERVICE]),
            ('Test local connection',[str(ROOT/'.tools/avalon-probe'),'--state',str(ROOT/'.runtime/agent')]),
            ('Stop local runtime',['systemctl','--user','stop',SERVICE]),
        ]:
            button=Gtk.Button(label=caption)
            button.connect('clicked',lambda widget,args=argv:self.run(widget,args))
            box.append(button)
        box.append(self.message)
        self.refresh()

    def run(self,button,argv):
        button.set_sensitive(False);self.message.set_text('Working…')
        try:
            proc=Gio.Subprocess.new(argv,Gio.SubprocessFlags.STDOUT_PIPE|Gio.SubprocessFlags.STDERR_PIPE)
            def finished(proc,result):
                button.set_sensitive(True)
                try:
                    _,out,err=proc.communicate_utf8_finish(result)
                    if not proc.get_successful():raise ValueError(err.strip() or out.strip() or 'Action failed')
                    self.message.set_text(out.strip() or 'Request accepted. Wallpaper handover is handled by GNOME.')
                except (GLib.Error,ValueError) as e:self.message.set_text(str(e)[:600])
                self.refresh()
            proc.communicate_utf8_async(None,None,finished)
        except GLib.Error as e:
            button.set_sensitive(True);self.message.set_text(str(e)[:600])

    def refresh(self):
        active=subprocess.run(['systemctl','--user','is-active',SERVICE],capture_output=True,text=True).stdout.strip()
        try:
            model=json.loads((ROOT/'.runtime/agent/gateway.json').read_text())['model']
        except (OSError,ValueError,KeyError):model='Not configured'
        shell=Gio.Settings.new('org.gnome.shell')
        enabled=UUID in shell.get_strv('enabled-extensions') and UUID not in shell.get_strv('disabled-extensions')
        self.status.set_text(f'Local runtime: {active or "not installed"}\nOpenCode / Ollama: {model}\nWallpaper requested: {"Avalon" if enabled else "off"}\nIf newly installed, log out and back in before enabling the wallpaper.')

class App(Gtk.Application):
    def __init__(self):super().__init__(application_id='com.progretech.Avalon')
    def do_activate(self):
        window=self.props.active_window or Foundation(self);window.present()

if __name__=='__main__':raise SystemExit(App().run())
