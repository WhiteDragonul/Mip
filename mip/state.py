# -*- coding: utf-8 -*-
"""Shared robot state, passed between the main loop and worker threads.

Reads/writes here are simple attribute assignments on a single object. In
CPython these are atomic enough for our needs (one writer per field, the main
loop only reads), so we avoid locks to keep the hot animation path fast.
"""

import os
import json

from . import config

EMOTIONS = (
    "happy", "sad", "angry", "curious", "surprised", "sleepy", "neutral",
    "crying", "laughing", "nervous", "upset", "wink", "love", "dizzy", "bored", "scared", "excited"
)


class RobotState:
    def __init__(self):
        self.running = True

        # expression / mouth
        self.emotion = "neutral"
        import time
        self.emotion_time = time.time()
        self.talking = False        # mouth animates while True
        self.listening = False      # mic is capturing
        self.thinking = False       # waiting for Claude

        # waving state
        self.wave_time = 0.0

        # conversation active states for wake-word activation
        self.conversation_active = False
        self.last_user_interaction_time = 0.0

        # where the eyes look, in normalized -1..1 (set by vision thread)
        self.eye_dx = 0.0
        self.eye_dy = 0.0
        self.face_seen = False      # is a face currently tracked?

        # conversation history for Claude (list of {role, content})
        self.history = []

    def trigger_wave(self):
        import time
        self.wave_time = time.time()

    def set_emotion(self, emotion):
        import time
        self.emotion = emotion if emotion in EMOTIONS else "neutral"
        self.emotion_time = time.time()

    # ---- persistent memory (remembers conversation across restarts) ----
    def load_memory(self):
        try:
            if os.path.exists(config.MEMORY_FILE):
                with open(config.MEMORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self.history = data
                    print(f"[memory] Loaded {len(data)} past messages.")
        except Exception as e:
            print("[memory] could not load:", e)

    def save_memory(self):
        try:
            trimmed = self.history[-config.MEMORY_KEEP:]
            with open(config.MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(trimmed, f, ensure_ascii=False)
        except Exception as e:
            print("[memory] could not save:", e)
