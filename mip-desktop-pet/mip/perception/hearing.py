# -*- coding: utf-8 -*-
"""Hearing loop: listen -> transcribe -> brain -> speak.

Runs in its own thread. Uses a Voice backend (mic + speakers) and a brain.

It also gives MIP a life of its own: on quiet beats (when nothing was heard) it
may say something spontaneous -- a compliment, an "I love you", a random
thought, or a little teasing. That chatter is injected HERE, between listens,
on purpose: speaking and listening share one thread, so MIP never talks over
you and never hears its own voice.
"""

import json
import time
import random

from .. import config


# spoken phrases that should wake MIP up / keep a chat going
_WAKE_WORDS = (
    "mip", "meep", "m.i.p.", "m i p",
    "hello", "hi", "hey", "salut", "buna", "bună", "wave",
    "my pee", "my pet", "play me", "play mip", "hello me", "tell me",
)
_WAVE_WORDS = ("wave", "salut", "buna", "bună", "hello", "hi", "hey")


def _say(state, voice, text, emotion, record=True):
    """Speak one line: set the face, print, speak, persist. Shared by replies
    and spontaneous remarks so behavior stays identical."""
    state.set_emotion(emotion)
    if record:
        state.history.append({
            "role": "assistant",
            "content": json.dumps({"text": text, "emotion": emotion}),
        })
        state.save_memory()
    print(f"[{config.NAME}] ({emotion}) {text}")
    voice.speak(text, state)
    state.emotion_time = time.time()   # hold the emotion ~7s after speaking


def hearing_loop(state, voice, brain):
    if not voice.can_listen():
        return

    last_spontaneous = 0.0   # last unprompted remark (in an active chat)
    last_seen_greet = 0.0    # last "oh, I see you!" greeting
    was_seen = False         # face visible on the previous beat

    while state.running:
        now = time.time()

        # active chat falls asleep after a quiet stretch
        if state.conversation_active and \
                now - state.last_user_interaction_time > config.CONVERSATION_TIMEOUT_SEC:
            state.conversation_active = False
            print("[assistant] Conversation idle -> sleeping (waiting for wake word).")

        # neutral face while we open our ears
        state.set_emotion("neutral")

        # 1) listen (bilingual: tries every language in config.STT_LANGUAGES)
        state.listening = True
        text = voice.listen(config.STT_LANGUAGES)
        state.listening = False

        if not text:
            # Nothing heard -> maybe MIP says something on its own.
            last_spontaneous, last_seen_greet, was_seen = _idle_behavior(
                state, voice, brain, now, last_spontaneous, last_seen_greet, was_seen)
            continue

        print("[you]", text)
        text_lower = text.lower()

        # wake-word gating: ignore room chatter until MIP is addressed
        has_wake_word = any(w in text_lower for w in _WAKE_WORDS)
        if not state.conversation_active:
            if not has_wake_word:
                continue
            state.conversation_active = True
        state.last_user_interaction_time = time.time()

        if any(w in text_lower for w in _WAVE_WORDS):
            state.trigger_wave()

        # 2) think
        state.set_emotion("curious")  # attentive face
        state.history.append({"role": "user", "content": text})
        state.thinking = True
        reply, emotion = brain.respond(state.history, state)
        state.thinking = False

        # 3) speak (records to history + memory inside _say)
        _say(state, voice, reply, emotion)
        was_seen = state.face_seen


def _idle_behavior(state, voice, brain, now, last_spontaneous, last_seen_greet, was_seen):
    """On a quiet beat decide whether MIP pipes up on its own.

    Two triggers, both opt-in via config:
      * in an active chat -> a spontaneous remark (compliment / love / teasing)
      * it just spotted your face after a while -> a glad-to-see-you greeting
    Returns the updated (last_spontaneous, last_seen_greet, was_seen).
    """
    if not config.IDLE_CHATTER:
        return last_spontaneous, last_seen_greet, state.face_seen

    # don't talk over ourselves / while busy
    if state.talking or state.thinking:
        return last_spontaneous, last_seen_greet, state.face_seen

    # noticed your face after not seeing it -> greet
    if state.face_seen and not was_seen and \
            now - last_seen_greet > config.SEEN_GREET_GAP_SEC and \
            random.random() < config.SEEN_GREET_CHANCE and \
            hasattr(brain, "greeting_when_seen"):
        text, emotion = brain.greeting_when_seen(state)
        _say(state, voice, text, emotion)
        return now, now, state.face_seen

    # in an active chat, fill a quiet moment with a spontaneous remark
    if state.conversation_active and \
            now - last_spontaneous > config.IDLE_MIN_GAP_SEC and \
            random.random() < config.SPONTANEOUS_CHANCE and \
            hasattr(brain, "spontaneous"):
        text, emotion = brain.spontaneous(state)
        _say(state, voice, text, emotion)
        state.last_user_interaction_time = time.time()  # keep the chat awake
        return now, last_seen_greet, state.face_seen

    return last_spontaneous, last_seen_greet, state.face_seen
