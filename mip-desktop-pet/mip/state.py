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

        # conversation history (list of {role, content})
        self.history = []

        # learning & custom brain variables (100% offline learning)
        self.facts_user = {}
        self.facts_world = {}
        self.learned_responses = []
        self.interactions_count = 0

        # --- growth / companion brain ---
        # when MIP was first switched on (its own "birth"); used to compute how
        # long it has known you and how grown-up it is.
        self.born_at = time.time()
        # last calendar year MIP already sang "happy birthday", so it only sings
        # once per birthday, not on every sentence.
        self.last_birthday_year = 0

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
                    self.facts_user = {}
                    self.facts_world = {}
                    self.learned_responses = []
                    self.interactions_count = 0
                    print(f"[memory] Loaded legacy list memory with {len(data)} past messages.")
                elif isinstance(data, dict):
                    self.history = data.get("history", [])
                    self.facts_user = data.get("facts_user", {})
                    self.facts_world = data.get("facts_world", {})
                    self.learned_responses = data.get("learned_responses", [])
                    self.interactions_count = data.get("interactions_count", 0)
                    self.born_at = data.get("born_at", self.born_at)
                    self.last_birthday_year = data.get("last_birthday_year", 0)
                    print(f"[memory] Loaded rich memory: {len(self.history)} messages, "
                          f"{len(self.facts_user)} user facts, {len(self.facts_world)} world facts, "
                          f"{len(self.learned_responses)} taught responses, interactions: {self.interactions_count}")
        except Exception as e:
            print("[memory] could not load:", e)

    def save_memory(self):
        try:
            trimmed_history = self.history[-config.MEMORY_KEEP:]
            data = {
                "history": trimmed_history,
                "facts_user": self.facts_user,
                "facts_world": self.facts_world,
                "learned_responses": self.learned_responses,
                "interactions_count": self.interactions_count,
                "born_at": self.born_at,
                "last_birthday_year": self.last_birthday_year,
            }
            with open(config.MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("[memory] could not save:", e)
