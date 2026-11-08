# Avalon Constellation appearance

Constellation remains its own app. Avalon reuses scoped copies of its Cairo galaxy renderer, desktop interactions and memory viewer from progretech-llc/constellation revision `52a0da7ecbd4d932ba0b9fd63c06e15e196a063b`. No standalone source or configuration is modified.

Adaptations: independent Avalon constellation.json settings, no independent wallpaper ownership claim, camera attention offsets galaxy projection and hit testing together, local speech intensity changes transient glow/rays, and existing Avalon lock/wake/sleep ownership. Avalon publishes its own filtered scene at `~/.local/state/project-avalon/constellation-scene.json`. The existing Constellation export seeds the display; its optional foreground is reused. No raw camera or voice content is written there. Folder/memory/agent orbits, hover/click, Alt focus, Ctrl folder access, solar rotation, labels and links remain the original implementation.

The GNOME extension requires a normal new login to load newly imported JavaScript modules in a session that cached the previous Avalon class. Disabling/re-enabling cannot clear GNOME's JavaScript module cache. Do not restart the login Shell to force this.

The native galaxy retains the same left-side Avalon name, runtime and activity status as the other appearances. Idle connected sessions show Sleeping when capture is asleep; active work/listening/speech statuses continue to update. The overlay is desktop text and does not move with camera attention.

## Agents and folders

Open **Appearance → Constellation → Agents and folders in this galaxy**. Automatic mode displays identities found in current local configuration; this does not imply they are running. Deleted and historical-only identities are excluded from the roster and from saved manual selections. Use Hide all to hide the current agents. Their previous memory records remain available. These are display choices, not agent creation, deletion or execution permissions.

Add folders by absolute path or the native folder chooser, rename their display labels, remove them from the galaxy, and set file/subfolder limits. The memory-system checkbox controls its visibility. Removing an item never deletes the underlying folder or memory. Apply saves independent preferences in `~/.config/project-avalon/constellation-sources.json`, initially seeded once from standalone Constellation settings. Reload saved selections discards an unsaved draft; refresh preserves it.

With a sibling `constellation` checkout and its working `.venv/bin/python`, Avalon reuses that project's native discovery and bounded scene collector. It refreshes while Avalon runs, every two minutes or on request. It reads existing configuration and reviewed memory metadata without changing standalone settings or scanning arbitrary file contents. Private collector inputs and unfiltered output stay in Avalon's ignored runtime directory. No standalone UI or collector timer needs to be running. Without the collector, existing exported scene data can still be filtered, but adding folder sources requires installing the collector.

New native scene-path code takes effect after a normal logout/login. The panel controls are available after refreshing the panel. Do not restart GNOME Shell to force a reload.

## Shared resource activity

The workstation Harness fork exports a separate, bounded metadata projection at
`~/.harness/cli/data/shared-resource-activity/`. Its existing native Codex/Claude
receipt parser confirms successful direct file reads, literal single-command
`cat`, `head`, `tail`, `sed` reads, Python tool-script executions, and Hindsight
calls. Skill discovery links resolve to their original Tools & Assets paths.
Only public shared-resource paths, service categories, native owner IDs and
timestamps leave that parser; commands, queries, results and conversations do not.
Private paths, runtime profiles, databases, credentials and Records are excluded.

Avalon reads this projection every ten seconds between its existing two-minute
scene rebuilds. Up to three recent resource targets per visible agent supplement
the existing project targets. Successful Hindsight calls target the visible
Hindsight system; file reads target their selected folder system. These are
observed interactions, never verified writes. Events expire after fifteen minutes.
The native recorded owner must match a visible agent, and folder/memory visibility
choices still apply. No GNOME JavaScript update or logout is required for this
collector change.

Coverage is limited to receipts understood by the native parser in Harness-managed
Codex/Claude sessions. Compound or dynamic shell code, untracked external clients,
Hermes/OpenClaw/OpenCode tool events, and mapping RAG API calls back to individual
books are not inferred. Quiet folders remain quiet when there is no eligible event.

## PT-Storage and optional OpenHarness integration

The PT-Storage subfolders option uses the immediate directories inside
`/mnt/PT-Storage/Projects` as solar systems when that folder is available.
It is enabled by default. Saved manual folder choices are retained and used
when the shared folder is unavailable or the option is off. Hidden, sensitive
and linked directories are excluded. The existing limit is twelve systems;
folder contents are not recursively scanned.

Enable **Integration with OpenHarness (optional)** in the same Constellation
settings to replace local agent identities with recent agent frameworks.
The count defaults to five and accepts 1–100. Avalon checks the account's
machines through `harness machines --json` and `harness ps --machine … --all
--json`, orders sessions by their actual activity timestamps, and displays
each framework once using its newest session. The settings show its machine,
state and timestamp. A recently stopped framework may appear; recency does
not imply it is still working. Unreachable machines are counted in the status.

Framework movement targets the visible solar system containing its latest
reported session folder, even when that folder belongs to another machine.
This is session context, without file-write lights or reassigned memory authors.
Frameworks outside the visible systems keep their normal orbit. Only metadata
is published; prompts and answers are discarded. The laptop's existing verified
Factory connection can supply Harness metadata when its local daemon is down.
Switching the integration off restores the saved local-agent choices.

The collector also supports the staged sibling checkout
`pt-constellation-factory-alt-dev`. Refresh the control panel after updating;
these source and settings changes require no new GNOME extension code.


## Projects with individual session agents

The workstation uses Projects as the galaxy center and its visible immediate
subfolders as solar systems. Avalon keeps Lyra, Mak, Progre and Codex visible
alongside the five most recent individual OpenHarness sessions when
`harness_sessions` and `openharness` are enabled in its source settings. Sessions
retain separate identities even when they use the same framework. Their names,
machines, states and activity times come from native Harness metadata. A stopped
session can remain among the latest five; displaying it does not start it.

Satellite mode follows reviewed file updates and observed Hindsight calls.
Session folders supply context for asteroid movement; they do not count as file
writes. Native receipt coverage is still limited to the Codex/Claude event parser.
Other frameworks can retain and retrieve Hindsight memory without producing that
receipt format, so a quiet satellite alone does not show whether memory worked.

The installer repairs a dangling desktop-state symlink after a project move.
It preserves an existing state directory or a link to another available directory.
