/** One opt-in desktop composer, sharing Avalon's current conversation and native API. */
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Pango from 'gi://Pango';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

export class ChatOverlay {
    constructor(path) {
        this.path = path;
        this.actor = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL,
            reactive: true, can_focus: true, accessible_name: 'Avalon wallpaper chat'});
        const header = new St.BoxLayout({reactive: true, style: 'spacing: 12px; padding-bottom: 8px;'});
        this.title = new St.Label({text: 'Avalon', x_expand: true,
            style: 'font-family: Ubuntu Sans; font-size: 18px; font-weight: 500; color: #edf4fa;'});
        header.add_child(this.title);
        this.speaker = this.button('audio-volume-muted-symbolic', 'Read final replies aloud', () =>
            this.command('settings', {read_aloud: !this.data.read_aloud}));
        header.add_child(this.speaker);
        this.actor.add_child(header);
        this.user = this.bubble('You');
        this.reply = this.bubble('Avalon');
        this.actor.add_child(this.user.box);
        this.actor.add_child(this.reply.box);
        const composer = new St.BoxLayout({style: 'spacing: 8px; padding-top: 10px;'});
        this.entry = new St.Entry({hint_text: 'Ask something. Give it a task.', can_focus: true,
            x_expand: true, accessible_name: 'Message Avalon',
            style: 'font-family: Ubuntu Sans; font-size: 15px; color: #edf4fa; background-color: rgba(9,14,22,0.7); border: 1px solid #506276; border-radius: 8px; padding: 10px;'});
        this.entry.clutter_text.set_max_length(16000);
        this.entry.clutter_text.connect('activate', () => this.send());
        this.entry.clutter_text.connect('key-press-event', (_a, event) => {
            if (event.get_key_symbol() === Clutter.KEY_Escape) {
                global.stage.set_key_focus(null); return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_PROPAGATE;
        });
        this.sendButton = this.button('go-next-symbolic', 'Send message', () => this.send());
        composer.add_child(this.entry); composer.add_child(this.sendButton);
        this.actor.add_child(composer);
        this.status = new St.Label({text: '', style: 'font-size: 12px; color: #a0b0c1; padding-top: 6px;'});
        this.status.clutter_text.line_wrap = true;
        this.actor.add_child(this.status);
        this.capture = this.actor.connect('captured-event', (_a, event) => this.dragEvent(event));
        // Fullscreen tracking would let Shell show this actor even when chat is off.
        Main.layoutManager.addChrome(this.actor, {affectsStruts: false});
        this.overviewShowing = Main.overview.connect('showing', () => this.update(this.data, this.fresh));
        this.overviewHidden = Main.overview.connect('hidden', () => this.update(this.data, this.fresh));
        this.actor.hide();
    }
    button(icon, name, callback) {
        const b = new St.Button({can_focus:true, reactive:true, accessible_name:name,
            style:'padding: 10px; border-radius: 8px; background-color: rgba(121,220,232,0.12); color: #79dce8;'});
        b.set_child(new St.Icon({icon_name:icon, icon_size:18}));
        b.connect('clicked', callback); return b;
    }
    bubble(name) {
        const box = new St.BoxLayout({orientation:Clutter.Orientation.VERTICAL,
            style:'padding: 10px 12px; margin-bottom: 8px; border-radius: 10px; background-color: rgba(16,23,33,0.42); spacing: 5px;'});
        const label = new St.Label({text:name, style:'font-size: 12px; color: #79dce8;'});
        const text = new St.Label({text:'', style:'font-family: Ubuntu Sans; font-size: 15px; color: #edf4fa;'});
        text.clutter_text.line_wrap = true; text.clutter_text.line_wrap_mode = Pango.WrapMode.WORD_CHAR;
        const scroll = new St.ScrollView({style:'max-height: 210px;'});
        scroll.set_policy(St.PolicyType.NEVER, St.PolicyType.AUTOMATIC);
        const content = new St.BoxLayout({orientation:Clutter.Orientation.VERTICAL});
        content.add_child(text); scroll.set_child(content); box.add_child(label); box.add_child(scroll);
        return {box,label,text,scroll};
    }
    send() {
        const text = this.entry.get_text();
        if (!text.trim() || this.pending || this.data?.active || !this.data?.connected) return;
        const session = this.data.session;
        this.command('send', {text, session}, () => {
            if (this.entry.get_text() === text) this.entry.set_text('');
        });
    }
    command(action, data, success=null) {
        if (this.pending || this.destroyed) return;
        this.pending = true; this.error = ''; this.status.text = action === 'send' ? 'Sending…' : 'Saving…';
        try {
            const child = Gio.Subprocess.new(['/usr/bin/python3', this.path + '/chat-client.py', action],
                Gio.SubprocessFlags.STDIN_PIPE | Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE);
            this.child = child;
            child.communicate_utf8_async(JSON.stringify(data), null, (proc,result) => {
                if (this.destroyed) return;
                this.pending = false; this.child = null;
                try {
                    const [, out] = proc.communicate_utf8_finish(result);
                    if (out.length > 8192) throw Error();
                    const reply = JSON.parse(out);
                    if (!reply.ok) this.error = reply.error || 'Request failed. Try again.';
                    else success?.();
                } catch { this.error = 'Avalon did not confirm this request. Check the control center before retrying.'; }
                this.status.text = this.error;
            });
        } catch {this.pending=false;this.error='Open Avalon to restore the local connection.';}
    }
    bounds() {
        const area = Main.layoutManager.getWorkAreaForMonitor(Main.layoutManager.primaryIndex);
        // Respect panel/dock struts and leave a small gap at every usable edge.
        return {x:area.x+16, y:area.y+16, width:Math.max(1,area.width-32), height:Math.max(1,area.height-32)};
    }
    dragEvent(event) {
        if (!this.drag) {
            if (event.type() !== Clutter.EventType.BUTTON_PRESS || event.get_button() !== 1 ||
                this.data?.placement !== 'movable') return Clutter.EVENT_PROPAGATE;
            const [x,y] = event.get_coords();
            for (const control of [this.entry,this.sendButton,this.speaker]) {
                const [cx,cy] = control.get_transformed_position();
                if (x>=cx && x<cx+control.width && y>=cy && y<cy+control.height) return Clutter.EVENT_PROPAGATE;
            }
            this.drag = {x,y,left:this.actor.x,top:this.actor.y};
            this.grab = global.stage.grab(this.actor);
            return Clutter.EVENT_STOP;
        }
        if (event.type() === Clutter.EventType.MOTION) {
            const [x,y] = event.get_coords(), m = this.bounds();
            this.actor.set_position(Math.max(m.x,Math.min(m.x+m.width-this.actor.width,this.drag.left+x-this.drag.x)),
                Math.max(m.y,Math.min(m.y+m.height-this.actor.height,this.drag.top+y-this.drag.y)));
            return Clutter.EVENT_STOP;
        }
        if (event.type() === Clutter.EventType.BUTTON_RELEASE ||
            (event.type() === Clutter.EventType.KEY_PRESS && event.get_key_symbol() === Clutter.KEY_Escape)) {
            const m=this.bounds();
            const position={x:Math.max(0,Math.min(1,(this.actor.x-m.x)/Math.max(1,m.width-this.actor.width))),
                y:Math.max(0,Math.min(1,(this.actor.y-m.y)/Math.max(1,m.height-this.actor.height)))};
            this.drag=null;this.grab?.dismiss();this.grab=null;
            this.command('settings',position);return Clutter.EVENT_STOP;
        }
        return Clutter.EVENT_STOP;
    }
    update(data, fresh) {
        this.data=data;
        this.fresh=fresh;
        if (!data?.enabled || !fresh || Main.overview.visible || Main.screenShield.locked) {
            this.grab?.dismiss();this.grab=null;this.drag=null;const focus = global.stage.get_key_focus();
            if (focus && this.actor.contains(focus)) global.stage.set_key_focus(null);
            this.actor.hide();return;
        }
        const m=this.bounds();
        this.actor.width=Math.min(420,m.width-40);
        for (const bubble of [this.user,this.reply]) bubble.scroll.set_style(`max-height: ${Math.max(40,Math.min(210,(m.height-260)/2))}px;`);
        const opacity=Number.isFinite(data.opacity)?Math.max(.25,Math.min(.95,data.opacity)):.72;
        this.actor.set_style(`padding: 14px; border-radius: 12px; spacing: 2px; background-color: rgba(9,14,22,${opacity}); border: 1px solid rgba(160,176,193,0.3);`);
        this.title.text=data.placement==='movable'?'Avalon · drag to move':'Avalon';
        this.speaker.child.icon_name=data.read_aloud?'audio-volume-high-symbolic':'audio-volume-muted-symbolic';
        this.speaker.accessible_name=data.read_aloud?'Mute final replies':'Read final replies aloud';
        this.user.text.text=data.user?.text || 'Your latest message appears here.';
        this.reply.label.text='Avalon' + (data.platform?' · '+data.platform:'');
        this.reply.text.text=data.reply?.text || (data.active?'Working…':'Ready for your next message.');
        this.sendButton.reactive=!!data.connected&&!data.active&&!this.pending;
        this.entry.reactive=!data.active&&!this.pending;
        this.status.text=this.error || (this.pending?'Sending…':data.active?'Working…':!data.connected?'Connect an agent in Presence.':'Enter to send · Esc to leave chat');
        if (!this.drag) {
            const x=data.placement==='anchor-right'?m.width-this.actor.width:data.placement==='movable'?Math.max(0,Math.min(1,data.x??.06))*(m.width-this.actor.width):0;
            const y=data.placement==='movable'?Math.max(0,Math.min(1,data.y??.60))*(m.height-this.actor.height):m.height-this.actor.height;
            this.actor.set_position(Math.round(m.x+x),Math.round(Math.max(m.y,m.y+y)));
        }
        const covered=global.display.get_tab_list(Meta.TabList.NORMAL_ALL,global.workspace_manager.get_active_workspace()).some(w=>{
            if(w.minimized||w.get_window_type()===Meta.WindowType.DESKTOP)return false;
            const r=w.get_frame_rect();return r.x<this.actor.x+this.actor.width&&r.x+r.width>this.actor.x&&r.y<this.actor.y+this.actor.height&&r.y+r.height>this.actor.y;
        });
        this.actor.visible=!covered||!!this.drag;
    }
    destroy() {
        this.destroyed=true;this.grab?.dismiss();this.grab=null;
        Main.overview.disconnect(this.overviewShowing);
        Main.overview.disconnect(this.overviewHidden);
        if(this.capture)this.actor.disconnect(this.capture);
        // Never kill an admitted request to infer cancellation; its native turn remains authoritative.
        Main.layoutManager.removeChrome(this.actor);this.actor.destroy();
    }
}
