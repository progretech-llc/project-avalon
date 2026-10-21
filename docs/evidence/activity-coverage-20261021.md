# Shared resource activity coverage

Owner: Ed. Native session: Codex `01a160d0-14a8-7661-ae15-3578d44dc37c`
on progretech-MS-S1-MAX; persistent owner PID 28322.
Projects: `/mnt/PT-Storage/Projects/project-avalon` and
`/mnt/PT-Storage/Projects/openharness`.

Grounding: current factory-baseline/README.md, task-ownership.md,
factory-expectations.html, Projects/AGENTS.md, OpenHarness/AGENTS.md,
Avalon docs/CONSTELLATION.md and shared-library working-principles.md.
RAG retrieval returned factory-architecture.html passages covering native activity,
current baseline authority and memory privacy. Hindsight search/list/read retrieved
“Factory agent memory and Constellation activity loop”; its private-path filtering
boundary was checked against the current collector. Its historical release and
deployment statements were not used as current evidence.

Implementation: native receipt parsing now keeps public shared-resource metadata
separate from usage/checkpoint data. Avalon overlays confirmed reads, tool execution
and Hindsight calls with recorded-owner attribution, selected-root matching and
fifteen-minute expiry. Cheap ten-second receipt updates reuse the original scene;
the two-minute memory collector remains unchanged. No standalone Constellation
source, Hermes/OpenClaw integration or renderer change is needed.

Validation: 87 affected Harness tests passed, TypeScript typecheck passed, and all
81 Avalon Python tests passed. Tests cover failure rejection, literal code mode,
private paths, native skill links, metadata-only export permissions, native-owner
attribution and preserving write metadata. Installation and live verification are
recorded below after execution.

Limits: only supported Harness-managed Codex/Claude receipts are observed. Unknown
shell/code paths and untracked clients stay unknown. A RAG request is not attributed
to a local book without source evidence. No synthetic activity is installed.

Rollback: revert the scoped source commits and reinstall the previous Harness CLI;
restart the Avalon control service. Existing folder selections remain intact.

## Installed verification

Harness source `0b3fe1907319468b33cca159699f986aa874ea4f` was pushed to
`progretech/monitor-singleton-cleanup` and verified against the live remote branch.
The installed local build is `0.4.41-dev.0b3fe1907`; its daemon restarted normally.
Avalon implementation `4023ad2bb01bceb9b73354316e7af2ae076cb942` was pushed to
`main` and independently matched against the live remote branch. The Avalon
control service restarted and is active. No extension reinstall or Shell restart.

Live verification found 50 separate native projection files, a refreshed scene
with 219 nodes less than ten seconds old, and no resource metadata error. The
100 retained native sessions had zero working sessions and zero fresh eligible
resource events at that check. This verifies installation and idle operation;
it does not claim a new live agent interaction occurred. Tests validate the
positive receipt/export/overlay paths without installing fabricated activity.

Existing unrelated OpenHarness AGENTS.md and diagnostic notes were preserved.
The standalone Constellation checkout was inspected but not changed.
