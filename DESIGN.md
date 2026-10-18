---
name: Project Avalon
description: Observed Presence Control Center and owner-reference avatar visual system
colors:
  bg: "#090e16"
  surface: "#101721"
  raised: "#151e2a"
  border: "#293442"
  text: "#edf4fa"
  muted: "#a0b0c1"
  cyan: "#79dce8"
  purple: "#b4a1ee"
  gold: "#e4bf7a"
  red: "#ffaaa1"
  green: "#8dd7b1"
typography:
  headline:
    fontFamily: "Ubuntu Sans, Ubuntu, Noto Sans, sans-serif"
    fontSize: "1.8rem"
    fontWeight: 500
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Ubuntu Sans, Ubuntu, Noto Sans, sans-serif"
    fontSize: "1.08rem"
    fontWeight: 500
  body:
    fontFamily: "Ubuntu Sans, Ubuntu, Noto Sans, sans-serif"
    fontSize: "15px"
    lineHeight: 1.55
  label:
    fontFamily: "Ubuntu Sans, Ubuntu, Noto Sans, sans-serif"
    fontSize: "0.8rem"
rounded:
  control: "8px"
  radius: "12px"
spacing:
  compact: "8px"
  inline: "12px"
  standard: "16px"
  section: "20px"
  content: "24px"
  columns: "28px"
components:
  button-primary:
    backgroundColor: "{colors.cyan}"
    textColor: "#07141b"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  button-secondary:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  avatar-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.radius}"
    padding: "0"
  avatar-card-selected:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.radius}"
    padding: "0"
  conversation:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.radius}"
---
# Design System: Project Avalon

## Overview

Avalon uses quiet dark surfaces, precise borders and a luminous GPU avatar. The implemented interface supports one selected model and session with readable conversation, explicit access controls and visible runtime state. This document captures the existing system.

The supplied wide_cinematic_poster_mockup_layout_of_a_desktop.png establishes the luminous avatar family; docs/reference/progre-owner-reference.png is the latest authority for Progre. Progre uses a transparent raster cutout extracted from that image and animated by the shared GPU texture shader. Its anatomy is only a face with two tiny hands and two tiny feet directly adjoining it: side spheres are eyes, white slashes are the nose and the enclosed zigzag is the mouth. It has no torso, body, chest or neck. Cyan/gold Ethereal Human, violet Neon Sentinel and purple orbital Abstract Core retain procedural volume geometry. Surface composition stays in .impeccable/surfaces/control-center.md and appearance.md.

**Key Characteristics:**

- Dark tonal surfaces and thin structural borders.
- Native Ubuntu typography and original vector stroke icons.
- Runtime-linked avatar motion with text equivalents and a selected-avatar still fallback.

## Colors

### Primary

Cyan marks primary actions, keyboard focus, selected navigation and active status. Gold belongs to the core’s warm center. The WebGL shader has its own RGB light calculations; its luminous pixels are not flat CSS swatches.

### Secondary

Purple indicates switching, green completion and coral failure. Status always has a text label; color supplies additional information.

### Neutral

Background, surface and raised establish the dark hierarchy. Border separates panels and controls. Text and muted distinguish primary reading from supporting labels. Field grounds and strokes remain local component values in the sidecar examples.

**The Verified State Rule.** Core state, connection label and controls follow the same runtime state; visual energy must not imply fabricated activity.

## Typography

The installed Ubuntu Sans → Ubuntu → Noto Sans → sans-serif stack supplies every role; no external webfont is required. Headings are medium weight with restrained negative tracking. Conversation text uses 0.92rem and 1.65 line height with a 75ch maximum width. The main heading reduces to 1.55rem on phones. Small labels and help text remain sentence case, except the small existing PROGRETECH wordmark.

## Layout

The desktop shell uses a 196px rail and a flexible main area capped at 1640px, with 32px 36px 18px main padding. Presence uses unequal columns and a 28px gap; exact page composition belongs to its surface brief. Reading regions use 20px or 24px padding. Permissions keep a 650px form and an 850px activity list.

At 1150px the rail becomes 160px and spacing tightens. At 900px it becomes a 76px icon strip, the main surface stacks, and preview and target controls share a row. At 640px navigation becomes a top bar and preview, controls and conversation stack with 18px main side gutters. The phone preview reserves 128px below its canvas for status and caption, keeping copy clear of the mascot and its extremities. Mobile conversation is 580px tall with internal scrolling. Long paths, models and messages wrap.

## Elevation & Depth

Ordinary surfaces use tonal layering and thin borders without box shadows. Glow belongs to the shader core and halo. Buttons transition background and border color over 150ms. Reduced motion disables CSS transitions. Hidden documents and offscreen previews skip redraws. The selected 15/30/60 FPS limit caps animated drawing; economy, balanced and high detail control sampling and render scale. Still mode (explicit or following system reduced motion) freezes shader time and redraws only on state, settings or size changes.

## Shapes

Controls use gently curved control corners; preview and conversation use larger panel corners. Structural borders are 1px. Avatars supply humanoid, armored and orbital geometry alongside the owner-reference face-only mascot, while application containers remain rectangular. Original icons use unfilled 20px vectors, 1.5px rounded strokes and joins. The brand mark is a separate original inline vector.

## Components

### Buttons

Primary actions use cyan with dark text and medium weight. Secondary actions use the raised surface; quiet actions use transparency. Standard padding is 10px 16px. Text actions use cyan without a border. Hover and active colors differ. Disabled controls use 0.42 opacity and a not-allowed cursor. All keyboard targets receive a cyan 2px outline offset by 3px.

### Inputs / Fields

Native fields use a dark inset ground, visible stroke, control corners and 11px 12px padding. Labels sit above fields and help below. Selects reserve room for their native indicator. Checkboxes use cyan. The composer places send beside the textarea and the keyboard hint below.

### Navigation

Original icons accompany sentence-case labels. Selection has a tinted background, brighter border, cyan text and aria-current. Tablet labels hide visually; phone navigation moves to the top. Accessible names remain available when text collapses.

### Cards / Containers

Conversation uses the surface token, panel corners, a border and clipped contents. Header, turn status and composer keep visible boundaries. Sessions and activity use flat ruled rows. The current-session tag is plain cyan text, without a pill background.

### Avatar preview

The shared shader in static/presence.glsl renders three procedural volume avatars and the transparent owner-reference Progre texture, mounted in WebGL by static/core.js and used by the native wallpaper. Flowing cyan/gold rays remain on a clean near-black field, with no background star field for any avatar. Dense luminous speckles within the character remain material texture. Working, writing and executing increase shader activity; completion, failure and switching change accent light. The caption overlays a dark gradient for readable connection, heading and detail. When WebGL is unavailable or lost, the selected avatar still remains visible with textual runtime state; the still itself does not encode live state.

### Appearance selection and controls

Avatar buttons show original renderer captures at a 3:4 aspect ratio above a name and muted description. Surface background, 12px corners and a 1px border match existing panels. Selection uses aria-pressed, a cyan border and a 2px cyan outline offset by 3px. Caption padding is 16px, reducing to 12px on phones. The 1100px-wide appearance surface uses four cards with 18px gaps, two columns at 1050px and 14px gaps at 600px.

Labeled native selects expose Detail (Economy/Balanced/High), Frame limit (15/30/60 FPS) and Motion (Follow Ubuntu / browser, Animated, Still). The settings grid uses three columns with 24px gaps, two at 1050px and one at 600px. Save power while idle is a checked-by-default native checkbox spanning the settings grid, with supporting text below. It limits idle/disconnected animation to up to 15 FPS; agent and voice activity use the selected 15/30/60 FPS limit. Apply appearance reuses the primary button. Appearance changes preserve the active mind and conversation; newly installed native renderer code requires logout/login.

### Devices, voice and approval controls

Devices reuse native labeled selects, checkboxes and primary/quiet actions. Wake up / Go to sleep shares a wrapping row with textual status and a native audio meter (up to 160px × 12px); the action label stays on one line. Form columns and native fields shrink within the viewport. Voice and Vision use two columns with 32px row and 48px column gaps in a 1060px-wide surface, stacking at 700px. Camera actions wrap with 12px gaps. Missing saved devices remain explicitly unavailable; image capability is explained beside Vision.

The native desktop exposes Wake up / Go to sleep at the lower left, separate from desktop icons. Devices exposes the same action and an editable Listener phrase, defaulting to “hey progre” (pronounced PRO-Greh). Local VAD/Whisper and the pinned LampOS wake classifier match the configured phrase; addressed commands can include a fresh camera frame for the selected vision model. The default remains qwen3.5:4b. A ten-second follow-up window after playback can accept a command without repeating the phrase. Sleep, lock, model switching and logout release capture devices. New GNOME extension JavaScript loads after normal logout/login; isolated new-source native evidence does not establish activation in the current login session. Kokoro voice choice, pitch and tone customization remain deferred by the owner until stabilization.

The conversation voice toolbar wraps with 8px gaps, 12px labels, 36px minimum button height and 16px icons. Record command, Send recording, Mute / discard and Read reply follow actual capture, speech, connection and lock state. Stop all stays in the page header. Locked-state text explains that unlocking does not restart capture.

Workspace approval appears inline in the conversation on the existing surface, with a top border and 20px 24px padding. Its gold question, wrapping exact path, one-minute expiry text, primary Approve once and quiet Deny actions distinguish the request. Approve once is disabled while Ubuntu is locked. The separate Ubuntu actions permission reuses the checkbox and quiet apply action. Physical microphone, speaker and camera qualification and phase 3 CPU acceptance remain open.

## Do's and Don'ts

- Do preserve visible cyan keyboard focus and explicit field labels.
- Do keep runtime status readable independently of the GPU preview.
- Do preserve truthful selected-model, capability and permission labels.
- Do reuse the native Ubuntu font stack and original local vectors.

- Don’t treat a static avatar capture as proof of live runtime activity.
- Don’t invent telemetry, activity or available device capabilities.
- Don’t add decorative glow to ordinary controls and containers.
- Don’t replace the owner-pinned visual authority with a new identity.
- Don’t add a torso, body, chest or neck to Progre, or reinterpret its side-sphere eyes, slash nose and zigzag mouth.
- Don’t add a background star field; preserve character texture and flowing rays.

Evidence: extracted from static/app.css, templates/index.html, static/app.js, static/core.js and static/presence.glsl; visually checked against .impeccable/review/desktop.png, appearance-desktop.png, mobile.png and appearance-mobile.png, plus docs/evidence/phase-3/wallpaper-sentinel.png. PRODUCT.md and the confirmed control-center and appearance direction contracts establish scope and owner authority. Captures establish delivered geometry, selected-card treatment and responsive composition; still fallback and motion behavior are grounded in source, not inferred from still captures. Inherited extraction drift and detector color/font advisories remain outside this ordinary extension; existing palette and typography tokens are preserved.

Phase 4 extension evidence: PRODUCT.md, .impeccable/surfaces/devices.md, templates/index.html, static/app.css and static/app.js; opened .impeccable/review/devices-desktop.png, devices-mobile.png, devices-permissions.png, desktop.png and mobile.png, plus docs/evidence/phase-4/approval-request.png. Captures show locked device controls, responsive forms and toolbar, desktop-access settings and a real model-proposed workspace approval with Approve once disabled while locked. The supplied qualification record reports denial; the still establishes the pending request, not execution or denial. Existing palette/type extraction drift remains outside this extension and is preserved.

Idle-saver extension evidence: checked the latest templates/index.html, static/app.css and static/app.js and opened .impeccable/review/appearance-desktop.png and appearance-mobile.png. Both show the checked Save power while idle control and its explanatory copy in the existing form system. This setting does not establish that the fixed-30-FPS CPU acceptance target passed; that target remains open.

Owner-reference extension evidence: checked static/presence.glsl, static/core.js, static/app.css, templates/index.html, media.py, media_worker.py and gnome-extension/extension.js; opened .impeccable/review/native-desktop.png, appearance-desktop.png, and the recaptured mobile.png and devices-mobile.png. These show the face-only textured mascot, clean field, flowing rays, selected-card treatment and native lower-left Wake up control. Native evidence is an isolated new-source session, not proof that the current login loaded new extension JavaScript. Listener matching, follow-up and device lifecycle are source-grounded; still captures do not qualify live microphone, speaker, camera or animation behavior. The new phone Presence capture separates caption text from the complete mascot silhouette. The new Devices capture keeps the form and selects inside the 390px shell, with a one-line Wake up action; the supplied Chromium assertion confirms document scrollWidth does not exceed innerWidth at 390px. The final presence-finish review returned disposition ship for its three scored fixes: mobile Devices overflow, mobile mascot/caption separation and persisted owner-reference documentation. This is scoped to those fixes, not whole-app or live-hardware qualification. Existing unrelated palette/type extraction drift is preserved rather than canonized or repaired.
