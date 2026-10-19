# Avalon Constellation appearance

Constellation remains its own app. Avalon reuses scoped copies of its Cairo galaxy renderer, desktop interactions and memory viewer from progretech-llc/constellation revision `52a0da7ecbd4d932ba0b9fd63c06e15e196a063b`. No standalone source or configuration is modified.

Adaptations: independent Avalon constellation.json settings, no independent wallpaper ownership claim, camera attention offsets galaxy projection and hit testing together, local speech intensity changes transient glow/rays, and existing Avalon lock/wake/sleep ownership. Avalon publishes its own filtered scene at `~/.local/state/project-avalon/constellation-scene.json`. The existing Constellation export seeds the display; its optional foreground is reused. No raw camera or voice content is written there. Folder/memory/agent orbits, hover/click, Alt focus, Ctrl folder access, solar rotation, labels and links remain the original implementation.

The GNOME extension requires a normal new login to load newly imported JavaScript modules in a session that cached the previous Avalon class. Disabling/re-enabling cannot clear GNOME's JavaScript module cache. Do not restart the login Shell to force this.

The native galaxy retains the same left-side Avalon name, runtime and activity status as the other appearances. Idle connected sessions show Sleeping when capture is asleep; active work/listening/speech statuses continue to update. The overlay is desktop text and does not move with camera attention.

## Agents and folders

Open **Appearance → Constellation → Agents and folders in this galaxy**. Automatic mode displays identities found in current local configuration; this does not imply they are running. Historical-only names from saved configuration or recorded activity are hidden automatically. Expand Historical identities to select them explicitly, or use Hide all. These are display choices, not agent creation, deletion or execution permissions.

Add folders by absolute path or the native folder chooser, rename their display labels, remove them from the galaxy, and set file/subfolder limits. The memory-system checkbox controls its visibility. Removing an item never deletes the underlying folder or memory. Apply saves independent preferences in `~/.config/project-avalon/constellation-sources.json`, initially seeded once from standalone Constellation settings. Reload saved selections discards an unsaved draft; refresh preserves it.

With a sibling `constellation` checkout and its working `.venv/bin/python`, Avalon reuses that project's native discovery and bounded scene collector. It refreshes while Avalon runs, every two minutes or on request. It reads existing configuration and reviewed memory metadata without changing standalone settings or scanning arbitrary file contents. Private collector inputs and unfiltered output stay in Avalon's ignored runtime directory. No standalone UI or collector timer needs to be running. Without the collector, existing exported scene data can still be filtered, but adding folder sources requires installing the collector.

New native scene-path code takes effect after a normal logout/login. The panel controls are available after refreshing the panel. Do not restart GNOME Shell to force a reload.
