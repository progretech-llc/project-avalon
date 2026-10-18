import Clutter from "gi://Clutter";
import Cogl from "gi://Cogl";
import Gio from "gi://Gio";
import GLib from "gi://GLib";
import GObject from "gi://GObject";
import Shell from "gi://Shell";
import St from "gi://St";
import Meta from "gi://Meta";
import * as Main from "resource:///org/gnome/shell/ui/main.js";
import { Extension } from "resource:///org/gnome/shell/extensions/extension.js";
import { createConstellation } from "./constellation-presence.js";
import { claimWallpaper } from "./ownership.js";

let source = "";
const STATES = {
  disconnected: 0,
  idle: 1,
  working: 2,
  writing: 3,
  executing: 4,
  completed: 5,
  failed: 6,
  cancelled: 7,
  switching: 8,
  listening: 9,
  speaking: 10,
  approval: 11,
};
const AVATARS = { constellation: 4, ethereal: 0, sentinel: 1, mascot: 2, abstract: 3 };
const LABELS = [
  "Disconnected",
  "Ready",
  "Working",
  "Writing",
  "Executing",
  "Completed",
  "Needs attention",
  "Stopped",
  "Switching",
  "Listening",
  "Speaking",
  "Waiting for approval",
];
const DEFAULTS = {
  avatar: "ethereal",
  quality: "balanced",
  fps: 30,
  motion: "system",
  idle_saver: true,
};
const PresenceContent = GObject.registerClass(
  { Implements: [Clutter.Content] },
  class PresenceContent extends GObject.Object {
    _init() {
      super._init();
      this.pipeline = Cogl.Pipeline.new(
        global.stage.context.get_backend().get_cogl_context(),
      );
      this.pipeline.set_layer_null_texture(0);
      const snippet = Cogl.Snippet.new(
        Cogl.SnippetHook.FRAGMENT,
        "uniform float u_time,u_aspect,u_state,u_avatar,u_quality;\n" + source,
        "",
      );
      snippet.set_replace(
        "cogl_color_out=vec4(avalon(vec2(cogl_tex_coord_in[0].x,1.0-cogl_tex_coord_in[0].y),u_aspect,u_time,u_state,u_avatar,u_quality),1.0);",
      );
      this.pipeline.add_snippet(snippet);
    }
    vfunc_paint_content(actor, node, _context) {
      const child = Clutter.PipelineNode.new(this.pipeline);
      child.add_rectangle(actor.get_content_box());
      node.add_child(child);
    }
    queue_repaint() {
      this.invalidate();
    }
    _uniform(key, value) {
      if (this._values[key] === value) return;
      this._locations[key] ??= this.pipeline.get_uniform_location("u_" + key);
      this.pipeline.set_uniform_1f(this._locations[key], value);
      this._values[key] = value;
    }
    update(time, aspect, state, appearance, sensors) {
      this._locations ??= {};
      this._values ??= {};
      this._uniform("time", time);
      if (
        this._lastAspect === aspect &&
        this._lastState === state &&
        this._lastAppearance === appearance &&
        this._lastSensors === sensors
      )
        return;
      this._uniform("aspect", aspect);
      this._uniform("state", state);
      this._uniform("gaze_x", sensors.gaze[0]);
      this._uniform("gaze_y", sensors.gaze[1]);
      this._uniform("level", sensors.level);
      this._uniform("avatar", AVATARS[appearance.avatar]);
      this._uniform(
        "quality",
        ["economy", "balanced", "high"].indexOf(appearance.quality),
      );
      this._lastAspect = aspect;
      this._lastState = state;
      this._lastAppearance = appearance;
      this._lastSensors = sensors;
    }
  },
);

export default class Avalon extends Extension {
  enable() {
    this._areas = [];
    this._frames = 0;
    this._activity = 0;
    this._appearance = { ...DEFAULTS };
    this._model = "";
    this._sensors = { gaze: [0, 0], level: 0 };
    this._dirty = true;
    this._release = claimWallpaper(this.uuid, () => this.disable());
    try {
      source = new TextDecoder().decode(
        GLib.file_get_contents(this.path + "/presence.glsl")[1],
      );
      if (source.length > 32000)
        throw new Error("Avatar source exceeded size limit");
      this._statePath = GLib.build_filenamev([
        GLib.get_user_state_dir(),
        "project-avalon",
        "visual-state.json",
      ]);
      this._accessibility = new Gio.Settings({
        schema_id: "org.gnome.desktop.interface",
      });
      this._systemMotion = this._accessibility.get_boolean("enable-animations");
      this._motionId = this._accessibility.connect(
        "changed::enable-animations",
        () => {
          this._systemMotion =
            this._accessibility.get_boolean("enable-animations");
          this._dirty = true;
        },
      );
      this._readStatus();
      this._build();
      this._started = GLib.get_monotonic_time();
      this._lastFrame = 0;
      this._monitorId = Main.layoutManager.connect("monitors-changed", () =>
        this._build(),
      );
      this._stateTick = GLib.timeout_add(GLib.PRIORITY_LOW, 200, () => {
        this._readStatus();
        this._updateWakeButton();
        return GLib.SOURCE_CONTINUE;
      });
      this._setFrameTimer();
    } catch (error) {
      this.disable();
      throw error;
    }
  }
  _frameLimit() {
    return this._appearance.idle_saver && this._activity <= 1
      ? Math.min(15, this._appearance.fps)
      : this._appearance.fps;
  }
  _setFrameTimer() {
    if (this._tick) GLib.Source.remove(this._tick);
    this._timerFps = this._frameLimit();
    this._tick = GLib.timeout_add(
      GLib.PRIORITY_LOW,
      Math.round(1000 / this._timerFps),
      () => {
        this._render();
        return GLib.SOURCE_CONTINUE;
      },
    );
  }
  _readStatus() {
    this._awake = false;
    let activity = 0,
      appearance = { ...DEFAULTS },
      model = "",
      sensors = { gaze: [0, 0], level: 0 };
    try {
      const [ok, bytes] = GLib.file_get_contents(this._statePath);
      if (!ok || bytes.length > 4096) throw new Error("Invalid visual state");
      const data = JSON.parse(new TextDecoder().decode(bytes));
      this._awake = data.awake === true && Math.abs(Date.now() / 1000 - data.heartbeat) < 10;
      const settings = data.appearance ?? {};
      // Persist the user's appearance even when the controller heartbeat expires.
      if (Object.prototype.hasOwnProperty.call(AVATARS, settings.avatar))
        appearance.avatar = settings.avatar;
      if (["economy", "balanced", "high"].includes(settings.quality))
        appearance.quality = settings.quality;
      if ([15, 30, 60].includes(settings.fps)) appearance.fps = settings.fps;
      if (typeof settings.idle_saver === "boolean")
        appearance.idle_saver = settings.idle_saver;
      if (["system", "full", "reduced"].includes(settings.motion))
        appearance.motion = settings.motion;
      if (
        data.schema === 1 &&
        Number.isFinite(data.heartbeat) &&
        Math.abs(Date.now() / 1000 - data.heartbeat) < 10
      ) {
        activity = Number.isInteger(STATES[data.status])
          ? STATES[data.status]
          : 0;
        const input = data.sensors;
        if (
          Array.isArray(input?.gaze) &&
          input.gaze.length === 2 &&
          input.gaze.every((x) => Number.isFinite(x) && Math.abs(x) <= 1) &&
          Number.isFinite(input.level) &&
          input.level >= 0 &&
          input.level <= 1
        )
          sensors = { gaze: input.gaze, level: input.level };
        model = typeof data.model === "string" ? data.model.slice(0, 100) : "";
      }
    } catch {
      /* A missing or malformed status never stops the desktop. */
    }
    if (
      JSON.stringify(sensors) !== JSON.stringify(this._sensors) ||
      activity !== this._activity ||
      JSON.stringify(appearance) !== JSON.stringify(this._appearance) ||
      model !== this._model
    ) {
      const still =
        appearance.motion === "reduced" ||
        (appearance.motion === "system" && !this._systemMotion);
      this._dirty ||=
        activity !== this._activity ||
        model !== this._model ||
        JSON.stringify(appearance) !== JSON.stringify(this._appearance) ||
        !still;
      this._sensors = sensors;
      this._activity = activity;
      this._appearance = appearance;
      this._model = model;
      if (this._tick && this._timerFps !== this._frameLimit())
        this._setFrameTimer();
      for (const area of this._areas) {
        area._model.text = model
          ? "OpenCode / " + model
          : "Open Project Avalon to connect";
      }
    }
    for (const area of this._areas) area._status.text = this._statusLabel();
  }
  _statusLabel() {
    return this._activity === 1 && !this._awake ? "Sleeping" : LABELS[this._activity];
  }
  _render() {
    const visible = !Main.overview.visible && !Main.screenShield.locked;
    if (visible !== this._visible) {
      for (const area of this._areas) area.visible = visible;
      this._visible = visible;
    }
    if (!visible) {
      this._dirty = true;
      return;
    }
    if (this._appearance.avatar === "constellation") {
      if (!this._galaxy) this._galaxy = createConstellation(this);
      this._galaxy._presence();
      // Keep the shared status overlay above the galaxy, hiding only its avatar.
      if (this._hudGalaxyAreas !== this._galaxy._areas) {
        for (const area of this._areas)
          area.get_parent().set_child_above_sibling(area, null);
        this._hudGalaxyAreas = this._galaxy._areas;
      }
      for (const area of this._areas) {
        area.visible = visible;
        area._canvas.visible = false;
      }
      return;
    }
    if (this._galaxy) {
      this._galaxy.disable();
      this._galaxy = null;
      this._hudGalaxyAreas = null;
      for (const area of this._areas) {
        area.visible = visible;
        area._canvas.visible = true;
      }
    }
    const still =
      this._appearance.motion === "reduced" ||
      (this._appearance.motion === "system" && !this._systemMotion);
    const now = GLib.get_monotonic_time();
    if (
      (still && !this._dirty) ||
      (!this._dirty && now - this._lastFrame < 1e6 / this._timerFps - 1000)
    )
      return;
    for (const area of this._areas) {
      const effect = area._effect;
      effect.update(
        still ? 0 : (now - this._started) / 1e6,
        area.width / area.height,
        this._activity,
        this._appearance,
        still ? { gaze: [0, 0], level: 0 } : this._sensors,
      );
      // Paint the procedural pipeline directly; no source/offscreen texture pass.
      effect.queue_repaint();
    }
    this._frames++;
    this._lastFrame = now;
    this._dirty = false;
  }
  _build() {
    if (this._wakeButton) {
      Main.layoutManager.removeChrome(this._wakeButton);
      this._wakeButton.destroy();
    }
    const monitor = Main.layoutManager.primaryMonitor;
    if (monitor) {
      this._wakeButton = new St.Button({label: "Wake up", reactive: true, can_focus: true,
        style: "background-color: #10252d; color: #d9f9ff; border: 1px solid #67cbdc; border-radius: 12px; padding: 12px 24px; font-size: 16px;"});
      this._wakeButton.set_position(monitor.x + 90, monitor.y + monitor.height - 84);
      this._wakeButton.set_size(174, 48);
      this._wakeButton.connect("clicked", () => {
        try {
          Gio.Subprocess.new(["systemctl", "--user", "start", "project-avalon-presence-toggle.service"], Gio.SubprocessFlags.NONE);
        } catch (error) { console.error("Avalon presence toggle failed", error); }
      });
      Main.layoutManager.addChrome(this._wakeButton, {affectsStruts: false, trackFullscreen: true});
    }
    for (const actor of this._areas) actor.destroy();
    this._areas = [];
    for (const monitor of Main.layoutManager.monitors) {
      const group = new Clutter.Actor({ reactive: false });
      group.set_position(monitor.x, monitor.y);
      group.set_size(monitor.width, monitor.height);
      const canvas = new Clutter.Actor({
        reactive: false,
        background_color: new Cogl.Color({
          red: 3,
          green: 5,
          blue: 10,
          alpha: 255,
        }),
      });
      canvas.set_size(monitor.width, monitor.height);
      const effect = new PresenceContent();
      canvas.set_content(effect);
      group.add_child(canvas);
      group._canvas = canvas;
      group._effect = effect;
      const hud = new St.BoxLayout({
        orientation: Clutter.Orientation.VERTICAL,
        reactive: false,
        style: "spacing: 16px;",
      });
      hud.set_position(
        Math.round(monitor.width * 0.065),
        Math.round(monitor.height * 0.27),
      );
      hud.set_width(Math.min(360, Math.round(monitor.width * 0.26)));
      hud.add_child(
        new St.Label({
          text: "Avalon",
          style:
            "font-family: Ubuntu Sans; font-size: 38px; font-weight: 500; color: #edf4fa;",
        }),
      );
      hud.add_child(
        new St.Label({
          text: "Your AI, here with you.",
          style: "font-size: 17px; color: #a0b0c1;",
        }),
      );
      const status = new St.Label({
        text: this._statusLabel(),
        style: "padding-top: 28px; font-size: 20px; color: #79dce8;",
      });
      const model = new St.Label({
        text: this._model
          ? "OpenCode / " + this._model
          : "Open Project Avalon to connect",
        style: "font-size: 13px; color: #a0b0c1;",
      });
      hud.add_child(status);
      hud.add_child(model);
      group.add_child(hud);
      group._status = status;
      group._model = model;
      // Keep desktop text away from the body on portrait/small monitors.
      hud.visible =
        monitor.width / monitor.height > 1.3 && monitor.width >= 1100;
      Main.layoutManager._backgroundGroup.add_child(group);
      this._areas.push(group);
    }
    this._hudGalaxyAreas = null;
    this._visible = undefined;
    this._dirty = true;
  }
  _updateWakeButton() {
    const button = this._wakeButton;
    if (!button) return;
    button.label = this._awake ? "Go to sleep" : "Wake up";
    const [x,y] = button.get_transformed_position();
    const covered = global.display.get_tab_list(Meta.TabList.NORMAL_ALL, global.workspace_manager.get_active_workspace()).some(w => {
      if (w.minimized || w.get_window_type() === Meta.WindowType.DESKTOP) return false;
      const r = w.get_frame_rect();
      return r.x < x + button.width && r.x + r.width > x && r.y < y + button.height && r.y + r.height > y;
    });
    button.visible = !Main.overview.visible && !Main.screenShield.locked && !covered;
  }
  disable() {
    this._galaxy?.disable();
    this._galaxy = null;
    this._hudGalaxyAreas = null;
    if (this._wakeButton) {
      Main.layoutManager.removeChrome(this._wakeButton);
      this._wakeButton.destroy();
      this._wakeButton = null;
    }
    for (const key of ["_tick", "_stateTick"]) {
      if (this[key]) GLib.Source.remove(this[key]);
      this[key] = null;
    }
    if (this._monitorId) Main.layoutManager.disconnect(this._monitorId);
    this._monitorId = null;
    if (this._motionId) this._accessibility?.disconnect(this._motionId);
    this._motionId = null;
    this._accessibility = null;
    for (const actor of this._areas ?? []) actor.destroy();
    this._areas = [];
    const release = this._release;
    this._release = null;
    release?.();
  }
}
