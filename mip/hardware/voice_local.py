# -*- coding: utf-8 -*-
"""Local audio backend: microphone (SpeechRecognition) + speakers (pyttsx3).

Cute robot voice
----------------
pyttsx3 uses the OS voice, which sounds human. To get a cute little-robot
voice we (optionally) post-process the synthesized audio:
  1. pyttsx3 renders the speech to a temporary WAV file (save_to_file),
  2. we pitch it up a touch (cuter) and apply light ring modulation
     (the classic "robot buzz"),
  3. we play the result.

If numpy / a WAV player isn't available, we gracefully fall back to plain
pyttsx3 speech, so the app still talks.

USB audio (laptop or Pi) works through this same backend unchanged.
"""

import os
import gc
import sys
import wave
import tempfile

try:
    import speech_recognition as sr
except Exception:
    sr = None
try:
    import pyttsx3
except Exception:
    pyttsx3 = None
try:
    import numpy as np
except Exception:
    np = None
try:
    import sounddevice as sd
except Exception:
    sd = None
try:
    import asyncio
    import edge_tts
except Exception:
    edge_tts = None

from .base import Voice
from .. import config


def _play_audio_file(path, state=None):
    """Play an mp3/wav, blocking until done, using pygame's mixer.

    pygame is already a dependency (the face window), and its mixer plays mp3,
    which is what edge-tts produces. Runs fine from the speaking thread.
    """
    import time
    import pygame
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    pygame.mixer.music.load(path)
    if state is not None:
        state.talking = True
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.05)
    if state is not None:
        state.talking = False
    pygame.mixer.music.unload()


class _SoundDeviceMic:
    """Microphone capture via sounddevice (bundles PortAudio -> no PyAudio/compiler).

    Records one spoken utterance using simple energy-based endpointing and
    returns a speech_recognition.AudioData ready for recognize_google().
    Used as the preferred mic when PyAudio isn't available (e.g. Python 3.14).
    """

    RATE = 16000          # Hz, mono 16-bit -> what Google STT likes
    BLOCK = 0.1           # seconds per read block
    MAX_SECONDS = 15.0    # hard cap on one utterance
    SILENCE_HANG = 1.2    # stop after this much trailing silence

    def __init__(self):
        self.ok = False
        self._floor = 300.0   # noise floor (RMS), calibrated below
        if sd is None or np is None or sr is None:
            return
        try:
            sd.check_input_settings(samplerate=self.RATE, channels=1)
            self._calibrate()
            self.ok = True
        except Exception as e:
            print("[voice] sounddevice mic unavailable:", e)
            self.ok = False

    def _rms(self, block):
        return float(np.sqrt(np.mean(block.astype(np.float32) ** 2)) + 1e-6)

    def _calibrate(self):
        n = int(self.RATE * 1.0)
        rec = sd.rec(n, samplerate=self.RATE, channels=1, dtype="int16")
        sd.wait()
        self._floor = max(150.0, self._rms(rec.flatten()))

    def listen(self):
        bs = int(self.RATE * self.BLOCK)
        threshold = self._floor * 1.25
        captured = []
        started = False
        silence = 0.0
        elapsed = 0.0
        with sd.InputStream(samplerate=self.RATE, channels=1, dtype="int16",
                            blocksize=bs) as stream:
            while elapsed < self.MAX_SECONDS:
                block, _ = stream.read(bs)
                block = block.flatten()
                level = self._rms(block)
                if not started:
                    if level > threshold:
                        started = True
                        captured.append(block)
                    # else: keep waiting for speech to begin
                else:
                    captured.append(block)
                    if level < threshold:
                        silence += self.BLOCK
                        if silence >= self.SILENCE_HANG:
                            break
                    else:
                        silence = 0.0
                    elapsed += self.BLOCK
        if not captured:
            return None
        audio = np.concatenate(captured).astype(np.int16)
        return sr.AudioData(audio.tobytes(), self.RATE, 2)


def _play_wav(path):
    """Play a WAV file, blocking until done. Tries winsound (Windows),
    then simpleaudio, then aplay (Linux/Pi)."""
    if sys.platform.startswith("win"):
        import winsound
        winsound.PlaySound(path, winsound.SND_FILENAME)  # blocks
        return True
    try:
        import simpleaudio
        wave_obj = simpleaudio.WaveObject.from_wave_file(path)
        wave_obj.play().wait_done()
        return True
    except Exception:
        pass
    if os.system(f'aplay -q "{path}" 2>/dev/null') == 0:
        return True
    return False


def _apply_effect(audio, rate, pitch, mod_hz, depth, chorus=0.0):
    """The EMO 'cute robot' effect, on a mono float array. Returns mono float
    (int16-ranged). Pitch up -> cuter; chorus -> synthetic shimmer;
    ring mod -> robotic buzz."""
    audio = audio.astype(np.float32)

    # 1) pitch up by resampling (shifts pitch -> "cute")
    pitch = max(0.5, float(pitch))
    if abs(pitch - 1.0) > 1e-3 and len(audio) > 2:
        n = len(audio)
        idx = np.arange(0, n - 1, pitch)
        lo = np.floor(idx).astype(np.int32)
        lo = np.clip(lo, 0, n - 2)          # guard fp overshoot -> lo+1 always valid
        frac = idx - lo
        audio = audio[lo] * (1 - frac) + audio[lo + 1] * frac

    # 2) chorus: add a slightly delayed copy -> synthetic, doubled shimmer
    chorus = float(chorus)
    if chorus > 0:
        d = int(rate * 0.012)
        if d < len(audio):
            delayed = np.zeros_like(audio)
            delayed[d:] = audio[:-d]
            audio = audio + chorus * delayed

    # 3) ring modulation -> robotic buzz
    depth = float(depth)
    if depth > 0:
        t = np.arange(len(audio)) / rate
        carrier = np.sin(2 * np.pi * mod_hz * t)
        audio = audio * ((1 - depth) + depth * carrier)

    # normalize to avoid clipping
    peak = np.max(np.abs(audio)) or 1.0
    return (audio / peak) * 32000.0


class LocalVoice(Voice):
    def __init__(self):
        # ---- microphone ----
        # Two capture paths: sounddevice (preferred -- no PyAudio needed, works
        # on Python 3.14) and the classic PyAudio-backed sr.Microphone.
        self._recognizer = None
        self._mic = None          # PyAudio path
        self._sd_mic = None       # sounddevice path
        if sr is not None:
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = 150
            self._recognizer.dynamic_energy_threshold = False
            # 1) try sounddevice first
            sd_mic = _SoundDeviceMic()
            if sd_mic.ok:
                self._sd_mic = sd_mic
                print("[voice] Microphone ready (sounddevice). Talk to me!")
            else:
                # 2) fall back to PyAudio if installed
                try:
                    self._mic = sr.Microphone()
                    with self._mic as src:
                        self._recognizer.adjust_for_ambient_noise(src, duration=0.8)
                    self._recognizer.energy_threshold = min(220, max(80, self._recognizer.energy_threshold))
                    self._recognizer.dynamic_energy_threshold = False
                    print("[voice] Microphone ready (PyAudio). Talk to me!")
                except Exception as e:
                    print("[voice] No microphone (install sounddevice or pyaudio):", e)
                    self._mic = None
        else:
            print("[voice] SpeechRecognition not installed -> can't listen.")

        # ---- speakers ----
        # Preferred: edge-tts neural voices (human-sounding, needs internet).
        # Fallback: offline pyttsx3 (Windows SAPI -- robotic but always there).
        #
        # pyttsx3 Windows gotchas, handled by building a FRESH engine per
        # utterance (see _make_engine):
        #  1) SAPI5 COM objects are bound to the creating thread.
        #  2) Reusing one engine makes the SECOND runAndWait() hang.
        self._edge_ok = (edge_tts is not None) and (config.TTS_ENGINE == "edge")
        self._tts_available = pyttsx3 is not None
        self._voice_id = None          # resolved once, then reused
        self._voice_resolved = False
        if self._edge_ok:
            print(f"[tts] Neural voice ready ({config.EDGE_VOICE}).")
        elif config.TTS_ENGINE == "edge" and edge_tts is None:
            print("[tts] edge-tts not installed -> using offline voice. "
                  "(pip install edge-tts)")
        if not self._edge_ok and not self._tts_available:
            print("[tts] no TTS available -> can't speak.")

    def _make_engine(self):
        """Create a fresh, configured pyttsx3 engine on the current thread."""
        if not self._tts_available:
            return None
        try:
            eng = pyttsx3.init()
            eng.setProperty("rate", config.TTS_RATE)
            eng.setProperty("volume", config.TTS_VOLUME)
            self._resolve_voice(eng)
            if self._voice_id:
                eng.setProperty("voice", self._voice_id)
            return eng
        except Exception as e:
            print("[tts] init failed:", e)
            return None

    def _resolve_voice(self, eng):
        """Pick a higher / female-ish voice once -> sounds cuter once robotized."""
        if self._voice_resolved:
            return
        self._voice_resolved = True
        try:
            for v in eng.getProperty("voices"):
                name = (getattr(v, "name", "") or "").lower()
                if any(k in name for k in ("zira", "female", "hazel", "eva", "susan")):
                    self._voice_id = v.id
                    break
        except Exception:
            pass

    # ---- interface ----
    def can_listen(self):
        return self._recognizer is not None and (
            self._sd_mic is not None or self._mic is not None
        )

    def can_speak(self):
        return self._edge_ok or self._tts_available

    def listen(self, language):
        if not self.can_listen():
            return None
        # capture one utterance via whichever backend we have
        try:
            if self._sd_mic is not None:
                audio = self._sd_mic.listen()
            else:
                with self._mic as src:
                    audio = self._recognizer.listen(src, phrase_time_limit=15)
        except Exception:
            return None
        if audio is None:
            return None
        try:
            return self._recognizer.recognize_google(audio, language=language).strip()
        except Exception:
            return None

    def speak(self, text, state=None):
        # 1) preferred: neural edge-tts voice
        if self._edge_ok and self._speak_edge(text, state):
            return
        # 2) fallback: offline pyttsx3
        self._speak_pyttsx3(text, state)

    def _speak_edge(self, text, state=None):
        """Synthesize with edge-tts (neural), apply the EMO cute-robot effect,
        and play it. Returns True on success."""
        path = None
        try:
            path = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name

            async def _gen():
                comm = edge_tts.Communicate(text, config.EDGE_VOICE,
                                            rate=config.EDGE_RATE)
                await comm.save(path)

            asyncio.run(_gen())
            if not (os.path.exists(path) and os.path.getsize(path) > 0):
                return False

            if config.VOICE_EFFECT and np is not None and self._play_with_effect(path, state):
                return True
            # no effect (or effect failed) -> play the clean neural mp3
            _play_audio_file(path, state)
            return True
        except Exception as e:
            print("[tts] neural voice failed, using offline:", e)
            return False
        finally:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

    def _play_with_effect(self, mp3_path, state=None):
        """Load the mp3 samples via pygame, apply the EMO effect, play. -> bool."""
        try:
            import time
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            freq, _fmt, channels = pygame.mixer.get_init()

            snd = pygame.mixer.Sound(mp3_path)
            arr = pygame.sndarray.array(snd)            # int16, mixer format
            mono = arr.mean(axis=1) if arr.ndim == 2 else arr.astype(np.float32)

            out = _apply_effect(mono, freq, config.EFFECT_PITCH,
                                config.EFFECT_MOD_HZ, config.EFFECT_MOD_DEPTH,
                                config.EFFECT_CHORUS)
            out = out.astype(np.int16)
            if channels == 2:                            # mixer wants stereo
                out = np.repeat(out[:, None], 2, axis=1)
            out = np.ascontiguousarray(out)

            new_snd = pygame.sndarray.make_sound(out)
            if state is not None:
                state.talking = True
            ch = new_snd.play()
            while ch.get_busy():
                time.sleep(0.05)
            if state is not None:
                state.talking = False
            return True
        except Exception as e:
            print("[tts] effect failed, playing clean voice:", e)
            return False

    def _speak_pyttsx3(self, text, state=None):
        eng = self._make_engine()
        if eng is None:
            return
        try:
            if state is not None:
                state.talking = True
            eng.say(text)
            eng.runAndWait()
        except Exception as e:
            print("[tts] speak failed:", e)
        finally:
            if state is not None:
                state.talking = False
            # drop the engine so the next call gets a clean one (avoids the
            # second-runAndWait hang); clear pyttsx3's weakref cache via gc.
            try:
                eng.stop()
            except Exception:
                pass
            del eng
            gc.collect()

    def close(self):
        # engines are created and disposed per-utterance, nothing to clean up
        pass
