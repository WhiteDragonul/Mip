# -*- coding: utf-8 -*-
"""Laptop display backend: a pygame window.

Pi port note: keep begin_frame() returning a pygame.Surface. For an SPI TFT,
subclass/replace end_frame() to push the surface's pixel buffer to the panel
(e.g. via luma.lcd / Adafruit RGB display) instead of pygame.display.flip().
"""

import pygame

from .base import Display


class PygameDisplay(Display):
    def __init__(self, width, height, title="MIP"):
        pygame.init()
        self.width = width
        self.height = height
        self._screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption(title)
        self._clock = pygame.time.Clock()
        self._quit = False

    def begin_frame(self):
        return self._screen

    def end_frame(self):
        pygame.display.flip()

    def poll_quit(self, state=None):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._quit = True
                elif state is not None:
                    if event.key == pygame.K_w:
                        state.trigger_wave()
                    elif event.key == pygame.K_1:
                        state.emotion = "neutral"
                    elif event.key == pygame.K_2:
                        state.emotion = "happy"
                    elif event.key == pygame.K_3:
                        state.emotion = "sad"
                    elif event.key == pygame.K_4:
                        state.emotion = "angry"
                    elif event.key == pygame.K_5:
                        state.emotion = "crying"
                    elif event.key == pygame.K_6:
                        state.emotion = "laughing"
                    elif event.key == pygame.K_7:
                        state.emotion = "nervous"
                    elif event.key == pygame.K_8:
                        state.emotion = "wink"
                    elif event.key == pygame.K_9:
                        state.emotion = "love"
                    elif event.key == pygame.K_0:
                        state.emotion = "dizzy"
                    elif event.key == pygame.K_b:
                        state.emotion = "bored"
                    elif event.key == pygame.K_s:
                        state.emotion = "scared"
                    elif event.key == pygame.K_e:
                        state.emotion = "excited"
                    elif event.key == pygame.K_u:
                        state.emotion = "upset"
                    elif event.key == pygame.K_c:
                        state.emotion = "curious"
            elif event.type == pygame.MOUSEBUTTONDOWN and state is not None:
                state.trigger_wave()
        return self._quit

    def tick(self, fps):
        return self._clock.tick(fps)

    def close(self):
        pygame.quit()
