import GLib from 'gi://GLib';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
export default class TestDriver extends Extension {
    enable() {
        if (GLib.getenv('AVALON_TEST_SHELL') !== '1' || !GLib.get_user_runtime_dir().endsWith('/avalon-test'))
            throw new Error('Qualification driver refused outside isolated test Shell');
        this._previous = global.context.unsafe_mode;
        global.context.unsafe_mode = true;
    }
    disable() { global.context.unsafe_mode = this._previous ?? false; }
}
