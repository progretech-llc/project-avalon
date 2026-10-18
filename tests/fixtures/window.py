#!/usr/bin/env python3
import gi
gi.require_version('Gtk','4.0')
from gi.repository import Gtk
app=Gtk.Application(application_id='com.progretech.AvalonProof')
def activate(app):
    window=Gtk.ApplicationWindow(application=app,title='Avalon desktop layering proof')
    window.set_default_size(440,220)
    label=Gtk.Label(label='Ordinary Ubuntu window\n\nThe animated wallpaper stays below this window.\nDesktop icons remain above the wallpaper.')
    label.set_margin_start(24);label.set_margin_end(24)
    window.set_child(label);window.present()
app.connect('activate',activate)
raise SystemExit(app.run())
