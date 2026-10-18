# License scope

Copyright © 2026 ProgreTech LLC.

Avalon source code, scripts, tests and documentation are licensed under **GNU GPL version 3 only** (`GPL-3.0-only`), except material explicitly identified below. The complete license is in [LICENSE](LICENSE). You may use, study, modify and redistribute the GPL-covered work under those terms, including commercial use. When distributing a covered modified work or binaries, follow the GPL's license, notice and corresponding-source requirements.

## Scope and exceptions

| Material | Terms |
| --- | --- |
| Original Avalon source, including procedural GLSL geometry and rendering code; scripts, tests and prose documentation | GPL-3.0-only |
| Scoped Constellation renderer, ownership and memory-viewer code and its adapted regression cases | Original MIT terms and copyright retained in [LICENSES/Constellation-MIT.txt](LICENSES/Constellation-MIT.txt); file list and modifications in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Avalon may distribute these compatible components within its GPL-covered work. |
| LampOS Go runtime packages and other material outside its `hal/` directory, fetched during setup | Apache-2.0; original source, notices and license preserved. [License copy](LICENSES/Apache-2.0.txt). |
| LampOS HAL modules fetched during setup and imported/adapted by Avalon | GPL-3.0 under upstream terms. The Avalon source license accommodates this integration. |
| Named ProgreTech brand raster assets and supplied visual references | Separate [visual asset terms](ASSET-LICENSE.md); excluded from the source-code license. |
| Downloaded model weights, voices, Python packages, CLIs and host system components | Their own upstream terms; these are not relicensed by Avalon or bundled as model binaries in this repository. |

GPLv3 is used because Avalon imports and adapts GPLv3 HAL modules. LampOS's Apache-2.0 components can be included in a GPLv3 work while preserving their notices; see the [Apache Software Foundation's compatibility guidance](https://apache.org/licenses/GPL-compatibility.html). Source fetching does not waive dependency obligations if you later distribute a built bundle.

## Branding

“ProgreTech,” “Progre,” the mascot likeness and official Avalon marks identify ProgreTech's project. The code license grants no trademark ownership or right to imply endorsement. Forks may identify their origin truthfully, but should use their own product identity when presenting a changed release. This does not restrict rights granted in the GPL-covered renderer code.

See [third-party notices](THIRD_PARTY_NOTICES.md) and [asset provenance](docs/ASSETS.md) before redistributing assets or a combined installation.
