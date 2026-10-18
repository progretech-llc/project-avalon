import assert from 'node:assert/strict';
import {WallpaperOwnership} from '../gnome-extension/ownership-core.js';
const registry = new WallpaperOwnership();
let live = new Set();
const start = uuid => {
    const release = registry.claim(uuid, () => live.delete(uuid));
    live.add(uuid);
    assert.equal(live.size, 1);
    return () => { live.delete(uuid); release(); };
};
const old = start('constellation');
const newer = start('avalon');
old(); // An old disable cannot release the new generation.
assert.equal(registry.owner.uuid, 'avalon');
start('constellation');
newer();
assert.equal(registry.owner.uuid, 'constellation');
for (let i = 0; i < 200; i++) start(i % 2 ? 'avalon' : 'constellation');
registry.claim('broken', () => { throw new Error('still drawing'); });
assert.throws(() => registry.claim('avalon', () => {}), /still drawing/);
assert.equal(registry.owner.uuid, 'broken');
const restartedShell = new WallpaperOwnership();
assert.equal(restartedShell.owner, null);
console.log('Ownership: bidirectional, repeated starts, stale release, failed stop, fresh Shell passed');
