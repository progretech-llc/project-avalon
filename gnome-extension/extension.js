import Gio from 'gi://Gio';
import Clutter from 'gi://Clutter';
import Cogl from 'gi://Cogl';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import {claimWallpaper} from './ownership.js';

const PresenceEffect = GObject.registerClass(class PresenceEffect extends Shell.GLSLEffect {
    vfunc_build_pipeline() {
        this.add_glsl_snippet(Cogl.SnippetHook.FRAGMENT, `
            uniform float u_time;
            uniform float u_aspect;
            uniform float u_state;
            float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1,311.7)))*43758.5453); }
        `, `
            vec2 uv = cogl_tex_coord_in[0].xy;
            vec2 p = (uv - 0.5) * vec2(u_aspect, 1.0);
            vec3 color = vec3(0.012, 0.019, 0.045);
            float active = step(1.5,u_state)*step(u_state,4.5);
            float t = u_time * (1.0 + active*1.7);
            float radius = length(p);
            float breath = 0.19 + 0.008*sin(t*0.8);
            float ring = exp(-120.0*abs(radius-breath));
            float halo = exp(-8.0*radius);
            float angle = atan(p.y,p.x);
            float flow = 0.55 + 0.45*sin(angle*4.0-t*0.7+radius*14.0);
            vec3 accent = vec3(0.06,0.58,0.72);
            if (u_state > 4.5 && u_state < 5.5) accent = vec3(0.10,0.8,0.42);
            if (u_state > 5.5 && u_state < 6.5) accent = vec3(0.9,0.20,0.12);
            if (u_state > 7.5) accent = vec3(0.65,0.35,0.85);
            color += accent*ring*(0.7+flow)*(u_state < 0.5 ? 0.35 : 1.0);
            color += vec3(0.16,0.10,0.34)*halo;
            color += vec3(1.0,0.64,0.19)*exp(-38.0*radius)*(0.8+0.2*sin(t));
            vec2 grid = floor(uv*vec2(240.0*u_aspect,240.0));
            float star = step(0.997,hash(grid));
            color += star*vec3(0.22,0.44,0.56)*(0.5+0.5*sin(t+hash(grid)*6.28));
            cogl_color_out = vec4(color, 1.0);
        `, true);
    }

    update(time, aspect, state = 0) {
        this.set_uniform_float(this.get_uniform_location('u_time'), 1, [time]);
        this.set_uniform_float(this.get_uniform_location('u_aspect'), 1, [aspect]);
        this.set_uniform_float(this.get_uniform_location('u_state'), 1, [state]);
    }
});

export default class Avalon extends Extension {
    enable() {
        this._areas = [];
        this._release = claimWallpaper(this.uuid, () => this.disable());
        try {
            this._activity = 0;
            this._statePath = GLib.build_filenamev([GLib.get_user_state_dir(), 'project-avalon', 'visual-state.json']);
            this._readStatus();
            this._stateTick = GLib.timeout_add(GLib.PRIORITY_LOW, 250, () => {
                this._readStatus();
                return GLib.SOURCE_CONTINUE;
            });
            this._build();
            this._monitorId = Main.layoutManager.connect('monitors-changed', () => this._build());
            this._started = GLib.get_monotonic_time();
            this._tick = GLib.timeout_add(GLib.PRIORITY_LOW, 33, () => {
                const visible = !Main.overview.visible && !Main.screenShield.locked;
                for (const area of this._areas) {
                    area.visible = visible;
                    if (visible) {
                        area.get_effect('presence').update(
                            (GLib.get_monotonic_time() - this._started) / 1e6, area.width / area.height, this._activity);
                        area.queue_redraw();
                    }
                }
                return GLib.SOURCE_CONTINUE;
            });
        } catch (error) {
            this.disable();
            throw error;
        }
    }

    _readStatus() {
        try {
            const [ok, bytes] = GLib.file_get_contents(this._statePath);
            if (!ok || bytes.length > 4096) throw new Error('Invalid state');
            const data = JSON.parse(new TextDecoder().decode(bytes));
            const fresh = Number.isFinite(data.heartbeat) && Math.abs(Date.now()/1000-data.heartbeat)<10;
            const states = {disconnected:0,idle:1,working:2,writing:3,executing:4,completed:5,failed:6,cancelled:7,switching:8};
            this._activity = fresh && data.schema === 1 ? states[data.status] ?? 0 : 0;
        } catch (_error) { this._activity = 0; }
    }

    _build() {
        for (const actor of this._areas) actor.destroy();
        this._areas = [];
        for (const monitor of Main.layoutManager.monitors) {
            const actor = new Clutter.Actor({reactive: false,
                background_color: new Cogl.Color({red: 4, green: 7, blue: 15, alpha: 255})});
            actor.set_position(monitor.x, monitor.y);
            actor.set_size(monitor.width, monitor.height);
            actor.add_effect_with_name('presence', new PresenceEffect());
            actor.get_effect('presence').update(0, monitor.width / monitor.height);
            Main.layoutManager._backgroundGroup.add_child(actor);
            this._areas.push(actor);
        }
    }

    disable() {
        if (this._stateTick) GLib.Source.remove(this._stateTick);
        this._stateTick = null;
        if (this._tick) GLib.Source.remove(this._tick);
        this._tick = null;
        if (this._monitorId) Main.layoutManager.disconnect(this._monitorId);
        this._monitorId = null;
        for (const actor of this._areas ?? []) actor.destroy();
        this._areas = [];
        this._release?.();
        this._release = null;
    }
}
