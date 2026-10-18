---
name: Project Avalon
description: Observed phase 2 Presence Control Center visual system
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
  conversation:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.radius}"
---
# Design System: Project Avalon

## Overview

Avalon uses quiet dark surfaces, precise borders and a cyan and gold living energy core. The implemented phase 2 interface supports one selected model and session with readable conversation, explicit access controls and visible runtime state. This document captures the existing system.

The owner’s supplied wide_cinematic_poster_mockup_layout_of_a_desktop.png remains the ultimate luminous avatar reference. The phase 2 abstract core is a technical visualization; full humanoid, sentinel and mascot embodiment remains phase 3. Surface composition stays in .impeccable/surfaces/control-center.md.

**Key Characteristics:**

- Dark tonal surfaces and thin structural borders.
- Native Ubuntu typography and original vector stroke icons.
- Runtime-linked core motion with text equivalents.

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

At 1150px the rail becomes 160px and spacing tightens. At 900px it becomes a 76px icon strip, the main surface stacks, and preview and target controls share a row. At 640px navigation becomes a top bar and preview, controls and conversation stack with 18px main side gutters. Mobile conversation is 580px tall with internal scrolling. Long paths, models and messages wrap.

## Elevation & Depth

Ordinary surfaces use tonal layering and thin borders without box shadows. Glow belongs to the shader core and halo. Buttons transition background and border color over 150ms. Reduced motion disables CSS transitions; the shader freezes time and reduces drawing cadence. Hidden documents skip core redraws.

## Shapes

Controls use gently curved control corners; preview and conversation use larger panel corners. Structural borders are 1px. The core supplies circular geometry while application containers remain rectangular. Original icons use unfilled 20px vectors, 1.5px rounded strokes and joins. The brand mark is a separate original inline vector.

## Components

### Buttons

Primary actions use cyan with dark text and medium weight. Secondary actions use the raised surface; quiet actions use transparency. Standard padding is 10px 16px. Text actions use cyan without a border. Hover and active colors differ. Disabled controls use 0.42 opacity and a not-allowed cursor. All keyboard targets receive a cyan 2px outline offset by 3px.

### Inputs / Fields

Native fields use a dark inset ground, visible stroke, control corners and 11px 12px padding. Labels sit above fields and help below. Selects reserve room for their native indicator. Checkboxes use cyan. The composer places send beside the textarea and the keyboard hint below.

### Navigation

Original icons accompany sentence-case labels. Selection has a tinted background, brighter border, cyan text and aria-current. Tablet labels hide visually; phone navigation moves to the top. Accessible names remain available when text collapses.

### Cards / Containers

Conversation uses the surface token, panel corners, a border and clipped contents. Header, turn status and composer keep visible boundaries. Sessions and activity use flat ruled rows. The current-session tag is plain cyan text, without a pill background.

### Core preview

The ring, warm center and sparse star field are original shader code in static/core.js. Connection, heading and detail remain textual when WebGL fails. Working, writing and executing increase shader activity; completion, failure and switching change accent light. Phase 2 does not establish final avatar geometry.

## Do's and Don'ts

- Do preserve visible cyan keyboard focus and explicit field labels.
- Do keep runtime status readable independently of the GPU preview.
- Do preserve truthful selected-model, capability and permission labels.
- Do reuse the native Ubuntu font stack and original local vectors.

- Don’t present the phase 2 core as a finished avatar.
- Don’t invent telemetry, activity or available device capabilities.
- Don’t add decorative glow to ordinary controls and containers.
- Don’t replace the owner-pinned visual authority with a new identity.

Evidence: extracted from static/app.css, templates/index.html, static/app.js and static/core.js; visually checked against .impeccable/review/desktop.png, mobile.png and permissions.png. PRODUCT.md and the confirmed control-center direction contract establish scope and owner authority. Captures show the implemented layout and visible tool-error detail; they do not prove every runtime action succeeds.
