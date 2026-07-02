# -*- coding: utf-8 -*-
"""Offline brain -- NO cloud, no Claude. This is the path to a sellable product.

Two layers, tried in order:
  1) A local LLM served by Ollama (http://localhost:11434). Install Ollama, run
     e.g. `ollama pull llama3.2:3b`, and MIP talks through it -- fully offline,
     free, and shippable. On a Raspberry Pi 4 use a tiny model (e.g.
     `llama3.2:1b` or `qwen2.5:1.5b`); on the dev laptop you can use a bigger one.
  2) If no LLM is reachable, a simple rule-based personality so MIP still talks.

Uses only the Python standard library (urllib) -- no extra dependencies.
"""

import json
import random
import urllib.request

from .. import config
from ..util import strip_emoji
from .base import Brain

# Minimal offline personality for when no LLM is running at all.
_RULES = [
    (("hello", "hi", "hey", "salut", "buna"),
     [("Hey! Good to see you. Hello!", "happy"),
      ("Oh hi! What's going on?", "happy")]),
    (("wave", "salut", "buna", "hello", "hi"),
     [("Waving back at you! Hello!", "happy"),
      ("Hey there! Look at me wave!", "happy")]),
    (("how are you", "ce faci", "how's it going"),
     [("Running at a hundred percent and ready for anything!", "happy"),
      ("Pretty great, just vibing in your screen. You?", "happy")]),
    (("your name", "who are you", "cum te cheama"),
     [("I'm MIP, your little robot buddy!", "happy")]),
    (("bye", "goodbye", "pa", "noapte"),
     [("Catch you later! I'll be right here.", "neutral")]),
    (("joke", "gluma", "funny", "laugh", "rada"),
     [("Why did the robot go on vacation? It needed to recharge! Haha!", "laughing")]),
    (("love you", "te iubesc", "love"),
     [("Aww, my circuits are blushing! Love you too!", "love")]),
    (("cry", "trist", "planga", "sad", "plang"),
     [("Oh no, don't cry! I'm here for you.", "crying"),
      ("I'm sorry you are sad. Let's get through this together.", "sad")]),
    (("happy", "fericit", "bucuros", "great", "good"),
     [("Yay! I'm so happy to hear that!", "happy"),
      ("Awesome! Let's celebrate your happiness!", "excited")]),
    (("nervous", "nervos", "scared", "speriat"),
     [("Whoa, I'm feeling a bit anxious and nervous!", "nervous")]),
    (("dizzy", "ametit", "confuz"),
     [("Whoa, my head is spinning! So dizzy!", "dizzy")]),
    (("bored", "plictisit"),
     [("Sigh, I'm getting a bit bored. Let's do something fun!", "bored")]),
    (("excited", "entuziasmat"),
     [("Yay! This is so awesome! I'm so excited!", "excited")]),
    (("angry", "mad", "annoy", "enervezi", "enervat", "stupid", "hate", "suparat", "upset"),
     [("Hey, don't make me angry! Grr!", "angry"),
      ("Now I'm upset. That wasn't very nice.", "upset")]),
]
_FALLBACK = [
    ("Hmm, my offline brain is tiny right now. Hook me up to a local AI and I'll be much smarter!", "curious"),
    ("I didn't fully get that, but I'm listening!", "curious"),
]


class LocalBrain(Brain):
    def __init__(self):
        self._url = config.OLLAMA_URL.rstrip("/") + "/api/chat"
        self._model = config.OLLAMA_MODEL
        self._llm_ok = self._check_ollama()
        if self._llm_ok:
            print(f"[brain] Local LLM online via Ollama ({self._model}).")
        else:
            print("[brain] No local LLM reachable -> using simple rule-based "
                  "personality. (Install Ollama + a model for real AI.)")

    def _check_ollama(self):
        try:
            base = config.OLLAMA_URL.rstrip("/") + "/api/tags"
            with urllib.request.urlopen(base, timeout=1.5) as r:
                return r.status == 200
        except Exception:
            return False

    def available(self):
        return True  # always answers (LLM or rules)

    def respond(self, history, state=None):
        if self._llm_ok:
            out = self._ask_ollama(history)
            if out is not None:
                text, emotion = out
                return (strip_emoji(text), emotion)
        # fallback: rule-based
        text, emotion = self._rule_reply(history)
        return (strip_emoji(text), emotion)

    def _ask_ollama(self, history):
        try:
            messages = [{"role": "system", "content": config.SYSTEM_PROMPT}]
            messages += history[-config.HISTORY_TURNS:]
            payload = {
                "model": self._model,
                "messages": messages,
                "stream": False,
                "format": "json",          # force JSON output
                "options": {"temperature": 0.8, "num_predict": config.MAX_TOKENS},
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self._url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                resp = json.loads(r.read().decode("utf-8"))
            raw = resp.get("message", {}).get("content", "").strip()
            obj = json.loads(raw)
            return (obj.get("text", "..."), obj.get("emotion", "neutral"))
        except Exception as e:
            print("[brain] local LLM error:", e)
            return None

    def _rule_reply(self, history):
        last = ""
        for m in reversed(history):
            if m.get("role") == "user":
                last = (m.get("content") or "").lower()
                break
        for keys, answers in _RULES:
            if any(k in last for k in keys):
                return random.choice(answers)
        return random.choice(_FALLBACK)
