# -*- coding: utf-8 -*-
"""Abstract hardware interfaces.

Everything above the hardware layer (perception, face renderer, app loop) talks
ONLY to these interfaces. To run on the Raspberry Pi you implement new classes
with the same methods (e.g. an SPI display, the Pi camera, USB audio) and plug
them into app.py -- no other code changes.
"""

from abc import ABC, abstractmethod


class Display(ABC):
    """A surface MIP draws its face onto, plus a frame/event pump.

    Laptop: a pygame window (display_pygame.py).
    Pi:     an SPI TFT (future display_spi.py) -- draw the face to an offscreen
            pygame.Surface, then blit the buffer to the panel each frame.
    """

    width: int
    height: int

    @abstractmethod
    def begin_frame(self):
        """Return a drawable surface for this frame (cleared/ready)."""

    @abstractmethod
    def end_frame(self):
        """Present the frame to the screen."""

    @abstractmethod
    def poll_quit(self, state=None) -> bool:
        """Return True if the user asked to quit (window closed / ESC)."""

    @abstractmethod
    def tick(self, fps: int):
        """Cap the frame rate. Returns elapsed ms (optional)."""

    @abstractmethod
    def close(self):
        ...


class Camera(ABC):
    """Source of frames + face detection.

    Laptop: OpenCV webcam (camera_opencv.py).
    Pi:     picamera2 (future camera_picam.py), optionally driving pan/tilt.
    """

    @abstractmethod
    def available(self) -> bool:
        ...

    @abstractmethod
    def detect_face(self):
        """Grab one frame and return the largest face center as (nx, ny) in
        normalized 0..1 image coords, or None if no face / no camera."""

    @abstractmethod
    def close(self):
        ...


class Voice(ABC):
    """Microphone (speech-to-text) + speakers (text-to-speech).

    Laptop & Pi (USB audio) use the same local backend (voice_local.py).
    """

    @abstractmethod
    def can_listen(self) -> bool:
        ...

    @abstractmethod
    def can_speak(self) -> bool:
        ...

    @abstractmethod
    def listen(self, language: str):
        """Block until a phrase is heard; return transcribed text or None."""

    @abstractmethod
    def speak(self, text: str, state=None):
        """Block while speaking the text aloud."""

    @abstractmethod
    def close(self):
        ...
