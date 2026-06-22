# -*- coding: utf-8 -*-
"""Hearing loop: listen -> transcribe -> Claude -> speak.

Runs in its own thread. Uses a Voice backend (mic + speakers) and a brain.
"""

import json

from .. import config


def hearing_loop(state, voice, brain):
    if not voice.can_listen():
        return

    while state.running:
        # Check for conversation timeout (45 seconds of inactivity)
        import time
        now = time.time()
        if state.conversation_active and now - state.last_user_interaction_time > 45.0:
            state.conversation_active = False
            print("[assistant] Conversation idle -> going to sleep (waiting for wake word).")

        # Revert emotion to neutral when starting to listen
        state.set_emotion("neutral")

        # 1) listen
        state.listening = True
        text = voice.listen(config.STT_LANGUAGE)
        state.listening = False
        if not text:
            continue
        print("[you]", text)

        # Check for wake word and conversation activation (with phonetic fallbacks and greetings)
        text_lower = text.lower()
        wake_words = (
            "mip", "meep", "m.i.p.", "m i p", 
            "hello", "hi", "hey", "salut", "buna", "bună", "wave",
            "my pee", "my pet", "play me", "play mip", "hello me", "tell me"
        )
        has_wake_word = any(w in text_lower for w in wake_words)

        if not state.conversation_active:
            if not has_wake_word:
                # Ignore background room speech
                continue
            else:
                # Wake word detected! Activate conversation
                state.conversation_active = True
                state.last_user_interaction_time = time.time()
        else:
            # Conversation is active, refresh interaction timestamp
            state.last_user_interaction_time = time.time()

        # Check for wave triggers
        if any(w in text_lower for w in ("wave", "salut", "buna", "bună", "hello", "hi", "hey")):
            state.trigger_wave()

        # 2) think (Claude)
        state.set_emotion("curious")  # Attentive/thinking face
        state.history.append({"role": "user", "content": text})
        state.thinking = True
        reply, emotion = brain.respond(state.history)
        state.thinking = False
        state.history.append({
            "role": "assistant",
            "content": json.dumps({"text": reply, "emotion": emotion}),
        })
        state.save_memory()
        state.set_emotion(emotion)
        print(f"[{config.NAME}] ({emotion}) {reply}")

        # 3) speak (mouth animates dynamically inside voice.speak)
        voice.speak(reply, state)

        # Reset emotion time so the emotion persists for 7 seconds AFTER speaking ends
        import time
        state.emotion_time = time.time()
