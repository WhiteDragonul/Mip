# -*- coding: utf-8 -*-
"""Wires the backends together and runs MIP's main animation loop.

THIS is the one place you change when porting to the Raspberry Pi:
swap the hardware backends below (display / camera / voice) for the Pi ones.
The face renderer, perception threads and brain stay exactly the same.
"""

import time
import math
import random
import threading

from . import config
from .state import RobotState
from .face.renderer import FaceRenderer

# ---- hardware backends (swap these for Pi) ----
from .hardware.display_pygame import PygameDisplay
from .hardware.camera_opencv import OpenCVCamera
from .hardware.voice_local import LocalVoice
# On Pi later, e.g.:
#   from .hardware.display_spi import SpiDisplay as PygameDisplay
#   from .hardware.camera_picam import PiCamera as OpenCVCamera

from .perception.vision import vision_loop
from .perception.hearing import hearing_loop


def _make_brain():
    """Pick the brain from config. Swap Claude <-> your own AI here."""
    if config.BRAIN == "local":
        from .brain.local_brain import LocalBrain
        return LocalBrain()
    from .brain.claude_brain import ClaudeBrain
    return ClaudeBrain()


def _lerp(a, b, t):
    return a + (b - a) * t


def run():
    state = RobotState()
    state.load_memory()   # remember past conversations

    # --- build hardware + brain (each fails soft on its own) ---
    display = PygameDisplay(config.WIDTH, config.HEIGHT, title=f"{config.NAME} digital")
    face = FaceRenderer(config.WIDTH, config.HEIGHT)
    camera = OpenCVCamera()
    voice = LocalVoice()
    brain = _make_brain()

    # --- worker threads ---
    threading.Thread(target=vision_loop, args=(state, camera), daemon=True).start()
    threading.Thread(target=hearing_loop, args=(state, voice, brain), daemon=True).start()

    # --- main animation loop ---
    next_blink = time.time() + random.uniform(2, 5)
    blink_until = 0.0

    while state.running:
        now = time.time()

        if display.poll_quit(state):
            state.running = False
            break

        # revert emotion to neutral after 7.0 seconds of inactivity
        if state.emotion != "neutral" and not state.talking and not state.thinking and not state.listening:
            if now - state.emotion_time > 7.0:
                state.set_emotion("neutral")

        # decay excited to happy after 2.0 seconds (star eyes are temporary)
        if state.emotion == "excited" and now - state.emotion_time > 2.0:
            state.set_emotion("happy")

        # periodic blink
        if now >= next_blink:
            blink_until = now + 0.12
            next_blink = now + random.uniform(2.5, 6)
        blink = now < blink_until

        # if no face is tracked, let the eyes idle-wander
        if not state.face_seen:
            state.eye_dx = _lerp(state.eye_dx, math.sin(now * 0.6) * 0.4, 0.02)
            state.eye_dy = _lerp(state.eye_dy, math.sin(now * 0.4) * 0.2, 0.02)

        surface = display.begin_frame()
        face.draw(surface, state, now, blink)
        display.end_frame()
        display.tick(config.FPS)

    # --- shutdown ---
    voice.close()
    display.close()
