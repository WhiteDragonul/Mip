# -*- coding: utf-8 -*-
"""Voice tuner: plays several robot-voice presets so you can pick the EMO one.

Run:  python tune_voice.py
Listen, then tell me which PRESET number sounds most like EMO.
"""
import asyncio, tempfile, os, time
import numpy as np
import edge_tts
import pygame

SENTENCE = "Hi! I'm MIP, your little robot friend. This is how I sound."

# (label, edge_voice, pitch, mod_hz, mod_depth, drive, chorus)
PRESETS = [
    ("1 - chirpy robot",   "en-US-AvaNeural",    1.18, 90,  0.30, 0.0, 0.0),
    ("2 - heavy robot",    "en-US-AvaNeural",    1.12, 110, 0.45, 0.0, 0.0),
    ("3 - vocoder edge",   "en-US-AvaNeural",    1.15, 75,  0.35, 0.4, 0.0),
    ("4 - chorus robot",   "en-US-AvaNeural",    1.15, 85,  0.25, 0.0, 0.5),
    ("5 - metallic high",  "en-US-AvaNeural",    1.25, 130, 0.40, 0.2, 0.0),
    ("6 - male robot",     "en-US-AndrewNeural", 1.22, 95,  0.32, 0.2, 0.3),
]


def effect(audio, rate, pitch, mod_hz, depth, drive, chorus):
    audio = audio.astype(np.float32)
    # pitch shift via resample
    if abs(pitch - 1.0) > 1e-3 and len(audio) > 2:
        n = len(audio)
        idx = np.arange(0, n - 1, pitch)
        lo = np.clip(np.floor(idx).astype(np.int32), 0, n - 2); frac = idx - lo
        audio = audio[lo] * (1 - frac) + audio[lo + 1] * frac
    # chorus: add a slightly detuned, delayed copy (synthetic shimmer)
    if chorus > 0:
        d = int(rate * 0.012)
        delayed = np.zeros_like(audio); delayed[d:] = audio[:-d]
        audio = audio + chorus * delayed
    # ring modulation: the robot buzz
    if depth > 0:
        t = np.arange(len(audio)) / rate
        carrier = np.sin(2 * np.pi * mod_hz * t)
        audio = audio * ((1 - depth) + depth * carrier)
    # drive: soft clip for a digital/robotic edge
    if drive > 0:
        g = 1 + drive * 6
        audio = np.tanh(audio / (np.max(np.abs(audio)) or 1.0) * g)
    peak = np.max(np.abs(audio)) or 1.0
    return (audio / peak * 31000.0).astype(np.int16)


def synth(voice):
    path = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
    asyncio.run(edge_tts.Communicate(SENTENCE, voice, rate="+6%").save(path))
    return path


def main():
    pygame.mixer.init()
    freq, _f, channels = pygame.mixer.get_init()
    cache = {}
    for label, voice, pitch, hz, depth, drive, chorus in PRESETS:
        if voice not in cache:
            p = synth(voice)
            arr = pygame.sndarray.array(pygame.mixer.Sound(p))
            cache[voice] = arr.mean(axis=1) if arr.ndim == 2 else arr.astype(np.float32)
            os.remove(p)
        mono = cache[voice]
        out = effect(mono, freq, pitch, hz, depth, drive, chorus)
        if channels == 2:
            out = np.repeat(out[:, None], 2, axis=1)
        out = np.ascontiguousarray(out)
        print(">>> PRESET", label)
        snd = pygame.sndarray.make_sound(out)
        ch = snd.play()
        while ch.get_busy():
            time.sleep(0.05)
        time.sleep(0.6)
    print("\nWhich preset number sounded most like EMO? Tell me and I'll set it.")


if __name__ == "__main__":
    main()
