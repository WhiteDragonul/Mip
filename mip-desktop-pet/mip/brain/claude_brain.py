# -*- coding: utf-8 -*-
"""Claude brain: sends conversation to the Anthropic API, returns (text, emotion).

If the SDK or API key is missing, ClaudeBrain.available() is False and the app
still runs -- MIP just says it has no brain yet.
"""

import os
import re
import json

try:
    import anthropic
except Exception:
    anthropic = None

from .. import config
from ..util import strip_emoji
from .base import Brain


class ClaudeBrain(Brain):
    def __init__(self):
        self._client = None
        if anthropic is None:
            print("[brain] anthropic SDK not installed -> running without a brain.")
            return
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("[brain] ANTHROPIC_API_KEY not set -> running without a brain.")
            return
        try:
            self._client = anthropic.Anthropic()
            print(f"[brain] Claude online ({config.MODEL}).")
        except Exception as e:
            print("[brain] could not start client:", e)
            self._client = None

    def available(self):
        return self._client is not None

    def _tools(self):
        if config.WEB_SEARCH:
            return [{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": config.WEB_SEARCH_MAX_USES,
            }]
        return []

    @staticmethod
    def _extract_text(resp):
        """Join all text blocks (web search adds tool blocks we ignore)."""
        parts = []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)
        return "".join(parts).strip()

    def respond(self, history, state=None):
        """history: list of {role, content}. Returns (text, emotion)."""
        if not self.available():
            return ("I don't have a brain yet -- set ANTHROPIC_API_KEY!", "sad")
        raw = ""
        try:
            kwargs = dict(
                model=config.MODEL,
                max_tokens=config.MAX_TOKENS,
                system=config.SYSTEM_PROMPT,
                messages=history[-config.HISTORY_TURNS:],
            )
            tools = self._tools()
            if tools:
                kwargs["tools"] = tools

            resp = self._client.messages.create(**kwargs)
            raw = self._extract_text(resp)
            raw = raw.replace("```json", "").replace("```", "").strip()

            text, emotion = self._parse(raw)
            return (strip_emoji(text), emotion)
        except Exception as e:
            print("[brain] error:", e)
            return ("Hmm, I didn't catch that. Say it again?", "curious")

    @staticmethod
    def _parse(raw):
        """Parse the {text, emotion} JSON, tolerating extra prose around it."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # try to find a JSON object embedded in the text
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(0))
                except json.JSONDecodeError:
                    return (raw or "Hmm?", "curious")
            else:
                return (raw or "Hmm?", "curious")
        return (data.get("text", "..."), data.get("emotion", "neutral"))
