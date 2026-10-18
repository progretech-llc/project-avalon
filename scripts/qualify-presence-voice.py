#!/usr/bin/env python3
"""Synthetic voices only: no microphone capture, physical playback or saved signatures."""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from speech import Synthesizer, DEFAULTS
from speaker import VoiceOwner

synth = Synthesizer()
t = time.monotonic()
synth.prepare('kokoro')
load = time.monotonic() - t
rows = []
audio = {}
for style, pitch in [('female', 0), ('female', 4), ('male', 0), ('robotic', 0)]:
    t = time.monotonic()
    chunks = synth.chunks({**DEFAULTS, 'text': 'Hello. I am Avalon, and I am ready to help you today.', 'voice_style': style, 'voice_pitch': pitch})
    first = next(chunks)
    first_time = time.monotonic()-t
    pcm = first + b''.join(chunks)
    samples = np.frombuffer(pcm, dtype='<i2').astype(np.float32)/32768
    assert len(samples) > 24000 and np.sqrt(np.mean(samples**2)) > .005
    audio[style, pitch] = samples
    rows.append({'style':style,'pitch':pitch,'first_pcm_seconds':round(first_time,3),'audio_seconds':round(len(samples)/24000,3)})
assert not np.array_equal(audio['female',0],audio['female',4]), 'Pitch effect had no effect'
owner = VoiceOwner()
def resample(samples):
    return np.interp(np.arange(int(len(samples)*16000/24000))*24000/16000,np.arange(len(samples)),samples).astype(np.float32)
a=owner.embedding(resample(audio['female',0]))
b=owner.embedding(resample(audio['male',0]))
assert a is not None and b is not None
assert not owner.accepts(a,False), 'Ambient voice claimed ownership'
assert owner.accepts(a,True)
other = b''.join(synth.chunks({**DEFAULTS,'text':'Please explain what the camera is looking at, in a short sentence.'}))
c=owner.embedding(resample(np.frombuffer(other,dtype='<i2').astype(np.float32)/32768))
same=float(np.dot(a,c));different=float(np.dot(a,b))
assert owner.accepts(c,False), (same,different)
assert not owner.accepts(b,True), (same,different)
# Verify actual pitch transformation against an authored sine, independent of voice content.
class Tone:
    def create(self,*args,**kwargs):
        return np.sin(np.arange(48000)*2*np.pi*220/24000).astype(np.float32)*.2,24000
synth.kokoro=Tone()
pcm=b''.join(synth.chunks({**DEFAULTS,'text':'A test tone.','voice_pitch':12}))
samples=np.frombuffer(pcm,dtype='<i2').astype(np.float32)
frequencies=np.fft.rfftfreq(len(samples),1/24000)
peak=float(frequencies[np.argmax(abs(np.fft.rfft(samples)))])
assert 435<peak<445 and abs(len(samples)/24000-2)<.15,peak
result={'method':'Actual CPU Kokoro ONNX and FFmpeg; synthetic voices, no recording/playback. Actual local speaker embeddings held in memory only.', 'model_load_seconds':round(load,3),'presets':rows,'speaker_same_voice_cosine':round(same,3),'speaker_other_voice_cosine':round(different,3),'speaker_threshold':.65,'ambient_enrollment_rejected':True,'different_speaker_rejected':True,'pitch_octave_test_hz':round(peak,2),'pitch_preserves_duration':True}
(ROOT/'docs/evidence/phase-5/voice-customization.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
