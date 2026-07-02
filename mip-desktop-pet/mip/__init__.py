"""MIP - a modular desktop pet (EMO-style) that ports cleanly to Raspberry Pi.

Architecture (so you can swap laptop hardware for Pi hardware later):

    mip/
      config.py            global settings + personality
      state.py             RobotState: shared, thread-safe-ish state
      app.py               wires backends together + runs main loop

      hardware/            HARDWARE ABSTRACTION LAYER (swap these on Pi)
        base.py            abstract interfaces: Display, Camera, Voice
        display_pygame.py  laptop window      -> later: display_spi.py
        camera_opencv.py   laptop webcam      -> later: camera_picam.py
        voice_local.py     laptop mic + speakers (USB audio works as-is)

      face/
        renderer.py        pure face drawing (knows nothing about pygame window)

      perception/
        vision.py          face-tracking loop (uses a Camera backend)
        hearing.py         listen->transcribe loop (uses a Voice backend)

      brain/
        custom_brain.py    MIP's own brain (default): 100% offline, grows up,
                           remembers you, has a personality -- no API at all
        local_brain.py     optional local LLM via Ollama (offline)
        claude_brain.py    optional Claude API: text -> {text, emotion}

To port to Pi: implement new hardware/*.py backends against hardware/base.py
and pick them in app.py. Everything above the hardware layer stays the same.
"""

__all__ = ["__version__"]
__version__ = "0.1.0"
