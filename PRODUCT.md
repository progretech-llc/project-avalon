# Project Avalon

<!-- impeccable:product-schema 1 -->

## Platform

web

The full control center is a local web interface inside an Ubuntu desktop product. GNOME/Wayland integration owns the wallpaper. The on-demand application launcher opens the authenticated local Presence Control Center.

## Stack

Delegated: Ed accepted the recommended native Ubuntu integration and local control-center direction on 2026-10-18. Phase 1 uses a bounded GNOME GPU shader actor, a separate Go host for LampOS's exported gateway, and Python setup/diagnostics. Phase 2 uses Flask, Waitress and a local PWA with a WebGL preview; Python owns the single WebSocket runtime connection, SQLite stores private local sessions, and systemd reaps runtime children on cancellation.

## Users and purpose

Ed and Ubuntu users who want one autonomous AI represented as an animated digital robot, with voice, camera-driven attention, chat and explicit action controls.

## Operating context

Primary hardware is the MS-S1 Max. Discover installed Ollama models and devices on each installation machine. Use LampOS's supported runtime interfaces and existing Harness integration. Ubuntu GNOME 50/Wayland is the initial qualified desktop.

## Capabilities and constraints

Living Wallpaper and Presence Control Center share one selected CLI/model/session. Default target: OpenCode with Ollama and an installed local model; Codex, Claude Code and Hermes are alternatives. One reasoning model owns the robot. Camera tracking, selected microphone and default/selected output are required. Avalon and Constellation hand over desktop ownership in both directions. Preserve native action restrictions. Model downloads and cloud fallback require a user choice.

## Brand commitments

Name: Project Avalon. The owner's supplied concept PNG sets the visual target. Its luminous humanoid, sentinel, mascot and abstract forms guide later avatar production. The previous HTML is historical charter reference.

## Evidence on hand

See docs/SPECIFICATION.md, docs/DELIVERY.md and docs/PHASE-1.md. Phase 3 delivers four original live GPU avatar forms and appearance controls. See docs/PHASE-3.md for visual review and measured resource evidence; native login-session updates still require logout/login.

## Product principles

- One body, one active reasoning model and one active session.
- Real activity states and honest capability labels.
- Local model discovery and explicit device choices.
- Wallpaper handover preserves the desktop and unrelated agents.
