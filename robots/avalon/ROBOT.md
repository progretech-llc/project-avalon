---
schema: autonomous.device.v1
id: avalon
name: Avalon Digital Robot
type: desktop_robot
boards: [sim]
gateway: { default: opencode }
voice: { tts_provider: piper, wakeword: true }
capabilities:
  audio: { routes: [audio, speaker, voice], required: true }
  vision: { routes: [camera], driver: opencv, required: true }
  expression: { routes: [emotion], required: true }
  media: { routes: [music], required: true }
  system: { routes: [system], required: true }
soul_ref: SOUL.md
safety_ref: SAFETY.md
---

# Avalon Digital Robot

An Ubuntu desktop presence. The screen avatar is its body. It has the selected host microphone, speakers and camera, and no mechanical actuators, GPIO LEDs or Bluetooth ownership. Run using LampOS's declared virtual board with host media; this does not imply physical robot hardware exists.
