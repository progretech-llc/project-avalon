# Feasibility findings — 2026-10-18

These are source/installation observations, not a live Avalon test.

## Local inspection

- The Avalon folder initially contained only the supplied HTML charter and concept PNG; no Git repository or application.
- Session is Wayland; `gnome-shell --version` reports **GNOME Shell 50.1**.
- Local Constellation has a GNOME 50 extension, UUID `factory-observatory@progretech.com`, using Shell background actors and Cairo. Its inspected enable path has no Avalon handover. Both applications need cooperation for bidirectional exclusivity.
- `opencode` and `ollama` are installed. Local Ollama `/api/tags` responds with installed models, including `qwen3-coder:30b` and `qwen3.5:9b`, alongside vision and embedding models. This is discovery evidence only; no model/tool compatibility or memory-fit benchmark was run.
- No `lamp` or `os-server` command was found on PATH. No existing LampOS installation was established; PATH absence does not prove none exists elsewhere.
- Existing HTML references Open WebUI, multiple simultaneous agent states, fake telemetry and demonstration controls. These are superseded product assumptions; original file remains intact.

## Upstream baseline

Repository: https://github.com/autonomous-ai/lampOS

Inspected main revision: `f3f708859d175a8a271e1a7b5e17dca9dee50361`. Re-check and pin before implementation; main moves.

| Source | Finding | Consequence |
| --- | --- | --- |
| [Simulator documentation](https://github.com/autonomous-ai/lampOS/blob/f3f708859d175a8a271e1a7b5e17dca9dee50361/docs/simulator.md) | Host-media laptop stack exists, but the documented off-device agent target is Codex only; development config seeding rewrites runtime selection | Do not claim OpenCode/Ollama is a turnkey supported Ubuntu development install. Phase 1/2 must establish and test it |
| [OpenCode backend](https://github.com/autonomous-ai/lampOS/blob/f3f708859d175a8a271e1a7b5e17dca9dee50361/docs/agentic/opencode.md) | Existing runtime bridge serializes per-turn subprocesses; device path uses root-owned files, presync and automatic approval | Reuse the gateway contract, but prove per-user Ubuntu paths and enforceable permissions before shipping |
| [Makefile](https://github.com/autonomous-ai/lampOS/blob/f3f708859d175a8a271e1a7b5e17dca9dee50361/Makefile) | Production OS build explicitly targets Linux ARM64; simulation supports host media | Build for this machine using documented development paths; never run board installer as the Ubuntu installation plan |
| [Board profiles](https://github.com/autonomous-ai/lampOS/blob/f3f708859d175a8a271e1a7b5e17dca9dee50361/hal/board/boards.json) | Explicit `host` and `sim` board profiles exist | Device declaration and media ownership need a scoped Avalon desktop profile; fake GPIO/motor capabilities are not product requirements |
| [OS endpoints](https://github.com/autonomous-ai/lampOS/blob/f3f708859d175a8a271e1a7b5e17dca9dee50361/docs/os-server.md) | Runtime-selection/configuration, sensing and monitoring interfaces exist; liveness/readiness alone do not prove gateway readiness | Implement a narrow server-side bridge and verify the active gateway with a turn |
| [Flow Monitor](https://github.com/autonomous-ai/lampOS/blob/f3f708859d175a8a271e1a7b5e17dca9dee50361/docs/flow-monitor.md) | Lifecycle/tool events have run correlation and provenance considerations | Preserve turn identity and reject stale events; missing detail becomes `working`, not fabricated `writing` |
| [Ollama list models](https://docs.ollama.com/api/tags) | Local installed inventory is exposed by `GET /api/tags` | Discover on the installation machine, then inspect capabilities and validate runtime compatibility |

## Unproven items that must be resolved

1. Native Ubuntu desktop host that provides the image's rendering quality without expensive work in Shell.
2. OpenCode/Ollama using LampOS off-device without appliance-root assumptions or configuration rewrites.
3. Enforceable approval/deny controls despite the upstream OpenCode auto-approval execution path.
4. Ubuntu PipeWire camera/audio selection in LampOS host mode, including stable device identities.
5. Voice provider availability: upstream laptop setup documents external speech credentials. A local Ollama selection does not make these available offline.
6. One reasoning-model operation across agent turns, background tasks, realtime voice and vision. Turn off secondary reasoning paths until the invariant is proven.
7. Bidirectional Constellation exclusion for direct Shell enable and concurrent starts, not just control-center launch.
8. Actual latency, idle resource use and full hardware behavior. None has been measured for Avalon.

## Working-practice grounding

Read `codecraft.pdf`, physical PDF p42, SHA256 `59e7c6c48f27ccb8c530d901e3a3f68b60b1072de6ef0e2017f873a5c9fa0dd0` from the shared library. Applied its practical emphasis on clear names, defensive error handling and testable code to the explicit failure/exit gates above. This is a scoped passage review, not a whole-book claim or source of current API facts.
