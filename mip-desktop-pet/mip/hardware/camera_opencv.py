# -*- coding: utf-8 -*-
"""Laptop camera backend: OpenCV webcam + Haar-cascade face detection.

Pi port note: implement camera_picam.py with the same detect_face() contract
using picamera2. You can also map the returned (nx, ny) onto pan/tilt servos.
"""

import time

try:
    import cv2
except Exception:
    cv2 = None

from .base import Camera


class OpenCVCamera(Camera):
    def __init__(self, index=0, min_face=80):
        self._cap = None
        self._cascade = None
        self._ok = False
        if cv2 is None:
            print("[camera] OpenCV not installed -> eyes will wander on their own.")
            return
        try:
            self._cap = cv2.VideoCapture(index)
            if not self._cap.isOpened():
                print("[camera] No camera found -> eyes will wander on their own.")
                return
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self._cascade = cv2.CascadeClassifier(cascade_path)
            self._min_face = min_face
            self._ok = True
            print("[camera] Ready. Watching you :)")
        except Exception as e:
            print("[camera] Init failed:", e)
            self._ok = False

    def available(self):
        return self._ok

    def detect_face(self):
        if not self._ok:
            return None
        ok, frame = self._cap.read()
        if not ok:
            time.sleep(0.05)
            return None
        frame = cv2.flip(frame, 1)  # mirror, so moving right moves eyes right
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self._cascade.detectMultiScale(
            gray, 1.2, 5, minSize=(self._min_face, self._min_face)
        )
        if len(faces) == 0:
            return None
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        nx = (x + w / 2) / frame.shape[1]
        ny = (y + h / 2) / frame.shape[0]
        return (nx, ny)

    def close(self):
        if self._cap is not None:
            self._cap.release()
