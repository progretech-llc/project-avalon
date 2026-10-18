# Avalon Constellation appearance

Constellation remains its own app. Avalon reuses scoped copies of its Cairo galaxy renderer, desktop interactions and memory viewer from progretech-llc/constellation revision `52a0da7ecbd4d932ba0b9fd63c06e15e196a063b`. No standalone source or configuration is modified.

Adaptations: independent Avalon constellation.json settings, no independent wallpaper ownership claim, camera attention offsets galaxy projection and hit testing together, local speech intensity changes transient glow/rays, and existing Avalon lock/wake/sleep ownership. The scene and foreground are read from the existing local Constellation export; no raw camera or voice content is written there. Folder/memory/agent orbits, hover/click, Alt focus, Ctrl folder access, solar rotation, labels and links remain the original implementation.

The GNOME extension requires a normal new login to load newly imported JavaScript modules in a session that cached the previous Avalon class. Disabling/re-enabling cannot clear GNOME's JavaScript module cache. Do not restart the login Shell to force this.

The native galaxy retains the same left-side Avalon name, runtime and activity status as the other appearances. Idle connected sessions show Sleeping when capture is asleep; active work/listening/speech statuses continue to update. The overlay is desktop text and does not move with camera attention.
