# Asset provenance

| Asset | Source | Use | Distribution status |
| --- | --- | --- | --- |
| `wide_cinematic_poster_mockup_layout_of_a_desktop.png` | Owner-supplied project file and chat reference, 2026-10-18 | Visual target/reference; original preserved | Owner-supplied reference; no third-party license inferred |
| `ProgreTech_Presence_Concept_Charter.html` | Owner-supplied project file | Historical charter, original preserved | Reference only; product assumptions superseded by specification |

Local library inventory was searched before proposing generated assets. The inspected `3Dassetpack/Finalized_meshes_final` inventory includes environment props such as buildings, bottles and an AC unit; it does not establish a suitable humanoid or mascot. No pack assets have been copied or licensed for distribution by this project yet. Inspect actual candidate meshes/images and terms before use; catalog listings are not proof of suitability.

Phase 3 records each selected font, icon, mesh, texture or generated avatar with original path/URL, hash, license/terms, adaptation and project output path. Keep library originals intact and copy only selected assets into this repository. Store exact generation prompts and model/workflow provenance for generated assets. The reference poster is not an animation asset and must not substitute for the real renderer.

The phase 1 energy-core shader in `gnome-extension/extension.js` is original procedural code, with no external raster/mesh/font dependency. Qualification PNGs in `docs/evidence/phase-1` capture the isolated test desktop and synthetic window/icon. They are evidence, not final avatar art.

Phase 2 uses original authored SVG geometry for navigation/status icons in `templates/index.html` and an original geometric A mark rasterized as `static/icons/avalon-{192,512}.png`. The WebGL preview in `static/core.js` is original procedural code based on the same core vocabulary as the desktop shader. Ubuntu Sans/Noto Sans/system sans are resolved from the host; no font files are redistributed. The shared-library/catalog workflow was consulted; no third-party creative pack was copied. Phase 2 screenshots contain synthetic qualification conversations and are evidence rather than reusable avatar assets.

## Phase 3 original avatar assets

`static/presence.glsl` is original procedural signed-distance geometry and GPU material/lighting code. `gnome-extension/presence.glsl` is an identical runtime copy. The four forms are independently authored from the owner’s concept direction: cyan/gold humanoid, hooded violet sentinel, teal/gold mascot and orbital abstract core. No external mesh, texture, font or model output was imported. Native geometry, light, particles and time/state uniforms produce the animation; no image/video is used as the live body.

`static/avatars/{ethereal,sentinel,mascot,abstract}.png` are 600×800 deterministic still captures of this exact renderer at idle, high detail, still motion/time zero. Reproduce with `scripts/render-avatar-previews.py`. They serve as selection thumbnails and unavailable-GPU fallbacks. Their inputs and renderer source are versioned; local book/creative-pack originals remain intact. The shared asset inventory was searched; no third-party pack asset was selected or license inferred. The actual owner reference was inspected directly.

The native and UI PNGs under `docs/evidence/phase-3` are qualification screenshots, with synthetic state fixtures or the recorded real local-model greeting. The compositor fixtures run only in a disposable guarded test Shell. These are evidence, not photographed/generated textures.

## Phase 4 supporting media

- Camera/STT interface/Piper backend: unmodified pinned LampOS leaf modules under `.deps/lampos`; revision in PHASE-1.md. Avalon does not start the appliance HAL or its separate realtime LLM.
- Piper CLI: OHF-Voice `piper-tts` 1.8.0, GPL-3.0, [official project/CLI](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/CLI.md). Invoked as a separate local supporting process through LampOS's existing backend.
- Voice: `rhasspy/piper-voices`, `en_US-ljspeech-medium`; actual MODEL_CARD inspected, names the [LJ Speech public-domain dataset](https://keithito.com/LJ-Speech-Dataset/). Source card/hash retained in model-sources.json. No Lessac/Ryan voice is used.
- Recognition: SYSTRAN faster-whisper 1.2.1, [official project](https://github.com/SYSTRAN/faster-whisper); `Systran/faster-whisper-base.en`, derived from MIT-licensed Whisper. CPU/int8, English, explicit pinned download, no network at inference time.
- Tracking: OpenCV 5.0.0.93 and its bundled frontal-face Haar cascade, Apache-2.0 distribution; native LampOS capture and deterministic damped positions, no additional VLM.
- Device routing: native `pw-dump`, `pw-record`, `pw-play`; [PipeWire node routing properties](https://pipewire.pages.freedesktop.org/pipewire/page_man_pipewire-props_7.html) and installed WirePlumber `linking/find-defined-target.lua` inspected for explicit-target no-fallback behavior.
- Original phase 3 avatar PNG reused only as an explicitly authored semantic-vision test fixture. Phase 4 ships no new third-party visual raster. No physical camera frame or microphone recording enters source/evidence. Synthetic PCM is kept only in ignored private runtime storage during tests.

## Progre owner reference, October 18 refinement

`reference/progre-owner-reference.png` is a scoped copy of the latest artwork supplied by the owner in this session (`codex-clipboard-9giiSg.png`); the original clipboard file remains intact. Progre has no torso: the lateral spheres are eyes, the white slashes are nose and the enclosed zigzag is mouth, with tiny hands/feet directly attached.

`static/art/progre.png` and identical `gnome-extension/progre.png` are a transparent background extraction prepared with the built-in Imagegen tool from that reference. The selected generated source is preserved at `/home/progretech/.codex/generated_images/01a1502f-f4e5-70b3-84e6-d0fca69ca723/exec-f9cba0db-e3e3-4a85-b8b0-736bdf77e66a.png`. Runtime display uses bounded shared GPU texture animation; this is a reference-derived 2.5D asset, not an original 3D reconstruction. Generated previews in `static/avatars` are captures of the actual shared renderer. Background star dots were removed from all variants.

OpenCV is pinned to `opencv-python-headless==4.13.0.92` because the previously installed 5.0 wheel lacked `CascadeClassifier`; real camera capture and face-driver initialization were rechecked. [Upstream package documentation](https://pypi.org/project/opencv-python-headless/) documents the Haar cascade interface.
