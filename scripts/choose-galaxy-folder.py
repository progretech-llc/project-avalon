#!/usr/bin/env python3
"""Native directory chooser requested explicitly from the local control panel."""

import json
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

Gtk.init()
loop = GLib.MainLoop()
dialog = Gtk.FileChooserNative.new(
    "Add a folder to the Avalon galaxy",
    None,
    Gtk.FileChooserAction.SELECT_FOLDER,
    "Choose folder",
    "Cancel",
)


def selected(chooser, response):
    item = chooser.get_file() if response == Gtk.ResponseType.ACCEPT else None
    print(json.dumps({"path": item.get_path() if item else None}), flush=True)
    chooser.destroy()
    loop.quit()


dialog.connect("response", selected)
dialog.show()
loop.run()
