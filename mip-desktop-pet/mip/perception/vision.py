# -*- coding: utf-8 -*-
"""Vision loop: ask the camera where the face is, steer the eyes there.

Runs in its own thread. Works with any Camera backend (base.Camera).
"""

import time


def vision_loop(state, camera):
    if not camera.available():
        return
    while state.running:
        center = camera.detect_face()
        if center is not None:
            nx, ny = center
            # map image position (0..1) to eye offset (-1..1), with gain & clamp
            tx = max(-1.0, min(1.0, (nx - 0.5) * 2.2))
            ty = max(-1.0, min(1.0, (ny - 0.5) * 2.2))
            # smooth move toward the target
            state.eye_dx += (tx - state.eye_dx) * 0.35
            state.eye_dy += (ty - state.eye_dy) * 0.35
            state.face_seen = True
        else:
            state.face_seen = False
        time.sleep(0.04)
    camera.close()
