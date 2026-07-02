#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIP - a digital desktop pet (EMO-style companion robot).

Run:
    python main.py

Press ESC or close the window to quit.
If the camera / microphone / API key is missing, MIP still starts
(it just runs without that feature).

See README.md for setup and the Raspberry Pi porting guide.
"""

from mip.app import run

if __name__ == "__main__":
    run()
