// Scoped Constellation renderer hosted inside Avalon's one wallpaper owner.
import GLib from 'gi://GLib';
import Constellation from './constellation-wallpaper.js';
export function createConstellation(owner) {
    const galaxy = new Constellation(owner.metadata);
    let lastPaint = 0, previousStill;
    galaxy._repaintAllowed = () => {
        const now=GLib.get_monotonic_time();
        if(now-lastPaint < 1e6/owner._frameLimit()) return false;
        lastPaint=now; return true;
    };
    galaxy._presence = () => {
        const still = owner._appearance.motion === 'reduced' ||
            (owner._appearance.motion === 'system' && !owner._systemMotion);
        const hidden = owner._appearance.avatar !== 'constellation' || !owner._visible;
        const base = galaxy._baseSettings ?? {};
        const level = owner._activity === 10 && !still ? owner._sensors.level : 0;
        galaxy._settings = {...base, enabled: !hidden, paused: still || base.paused,
            density: (base.density ?? .72) * (owner._appearance.quality === "economy" ? .6 : 1),
            avalon_base_glow: base.glow ?? .82,
            glow: Math.min(1.8, (base.glow ?? .82) * (1 + level * .8)),
            rays: Math.min(1.8, (base.rays ?? .72) + level * .65),
            avalon_gaze: still ? [0, 0] : owner._sensors.gaze};
        for (const area of galaxy._areas) area.visible = !hidden;
        if(previousStill !== still) for(const area of galaxy._areas) area.queue_repaint();
        previousStill=still;
        if (hidden) { galaxy._tooltip?.hide(); galaxy._clickTarget?.hide(); }
    };
    const reload = galaxy._reload.bind(galaxy);
    galaxy._reload = () => { reload(); galaxy._baseSettings = {...galaxy._settings}; galaxy._presence(); };
    galaxy._enableWallpaper();
    return galaxy;
}
