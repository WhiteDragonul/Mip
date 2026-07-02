# -*- coding: utf-8 -*-
"""Abstract brain interface.

The rest of MIP only talks to this. Swap the brain (Claude -> your own local
AI) by implementing this interface and selecting it in config.BRAIN -- no other
code changes. This is the seam for going fully offline / commercial.
"""

from abc import ABC, abstractmethod


class Brain(ABC):
    @abstractmethod
    def available(self) -> bool:
        """True if the brain can actually answer."""

    @abstractmethod
    def respond(self, history, state=None):
        """history: list of {role, content}. Returns (text, emotion)."""
