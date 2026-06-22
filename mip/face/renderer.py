# -*- coding: utf-8 -*-
"""Draws MIP's EMO-style face onto any pygame surface.

This module is deliberately decoupled from the window/display: it just takes a
surface to paint on. On the Pi you can render to an offscreen surface and push
it to an SPI panel -- the drawing code is unchanged.
"""

import math
import random
import pygame

from .. import config

# Emotion configuration:
# (eye_w_scale, eye_h_scale, lid_slant, eyebrow_slant, eyebrow_y_offset)
# slant: positive slants down inwards (angry), negative slants up inwards (sad)
_EMOTION_CONFIG = {
    "neutral":   (1.0, 1.0, 0.0, 0.0, 0),
    "happy":     (1.0, 0.75, 0.0, -2.0, -4),
    "sad":       (1.0, 0.9, -1.0, -8.0, 4),
    "angry":     (1.0, 0.8, 1.0, 8.0, 3),
    "surprised": (1.05, 1.25, 0.0, 0.0, -12),
    "curious":   (1.0, 1.0, 0.0, -3.0, -4),
    "sleepy":    (1.0, 0.25, 0.0, -1.0, 5),
    
    # 10 new emotions/expressions
    "crying":    (1.0, 0.85, -1.0, -8.0, 5),
    "laughing":  (1.0, 0.7, 0.0, -4.0, -6),
    "nervous":   (0.75, 0.75, 0.0, 4.0, 2),
    "upset":     (1.0, 0.8, 0.8, 6.0, 4),
    "wink":      (1.0, 1.0, 0.0, 0.0, 0),
    "love":      (1.0, 1.0, 0.0, -3.0, -5),
    "dizzy":     (1.0, 1.0, 0.0, 0.0, 0),
    "bored":     (1.0, 0.45, 0.0, 0.0, 3),
    "scared":    (0.65, 0.65, 0.0, -5.0, -8),
    "excited":   (1.1, 1.1, 0.0, -5.0, -10),
}


class FaceRenderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self._font = pygame.font.SysFont("consolas", 16)

        # Smooth transition interpolation states
        self.curr_eye_w = 70.0
        self.curr_eye_h = 90.0
        self.curr_slant = 0.0
        self.curr_eyebrow_slant = 0.0
        self.curr_eyebrow_y = 0.0

        # Jitter offsets
        self.jitter_x = 0.0
        self.jitter_y = 0.0

    def draw(self, surface, state, t, blink):
        surface.fill(config.BG)

        # 1) Calculate targets and smoothly interpolate states
        emotion = state.emotion
        cfg = _EMOTION_CONFIG.get(emotion, _EMOTION_CONFIG["neutral"])
        
        tar_w = 70.0 * cfg[0]
        tar_h = 90.0 * cfg[1]
        tar_slant = cfg[2]
        tar_eb_slant = cfg[3]
        tar_eb_y = cfg[4]

        # Handle blink override
        if blink:
            tar_h *= 0.12
            tar_slant = 0.0
            tar_eb_y += 10

        # Exponential smoothing (interpolation) for screen transitions
        self.curr_eye_w += (tar_w - self.curr_eye_w) * 0.22
        self.curr_eye_h += (tar_h - self.curr_eye_h) * 0.22
        self.curr_slant += (tar_slant - self.curr_slant) * 0.22
        self.curr_eyebrow_slant += (tar_eb_slant - self.curr_eyebrow_slant) * 0.22
        self.curr_eyebrow_y += (tar_eb_y - self.curr_eyebrow_y) * 0.22

        # 2) Emotion specific jitter (shaking/bouncing)
        self.jitter_x = 0.0
        self.jitter_y = 0.0
        if emotion == "nervous":
            self.jitter_x = random.uniform(-2, 2)
            self.jitter_y = random.uniform(-1, 1)
        elif emotion == "scared":
            self.jitter_x = random.uniform(-3, 3)
            self.jitter_y = random.uniform(-3, 3)
        elif emotion == "laughing":
            self.jitter_y = math.sin(t * 26) * 4.0
        elif emotion == "excited":
            self.jitter_y = -abs(math.sin(t * 16)) * 9.0

        cx = self.width // 2 + int(self.jitter_x)
        cy = self.height // 2 - 10 + int(self.jitter_y)

        ox = state.eye_dx * 26   # how far the eyes shift toward you
        oy = state.eye_dy * 18

        # 3) Draw face parts
        self._draw_eyes(surface, state, cx, cy, ox, oy, blink, t)
        self._draw_eyebrows(surface, state, cx, cy, ox, oy, t)
        self._draw_mouth(surface, state, cx, cy, ox, oy, t)
        self._draw_status(surface, state)

        # 4) Draw waving hand overlay
        if state.wave_time > 0:
            wave_elapsed = t - state.wave_time
            if wave_elapsed < 2.5:
                self._draw_waving_hand(surface, wave_elapsed, t)

    # ---- eyes ----
    def _draw_eyes(self, surface, state, cx, cy, ox, oy, blink, t):
        eye_gap = 95
        emotion = state.emotion

        ew = int(self.curr_eye_w)
        eh = int(self.curr_eye_h)

        # If crying, draw sliding tears under eyes
        if emotion == "crying" and not blink:
            for side in (-1, +1):
                tex = cx + side * eye_gap + ox
                tey = cy + oy + eh // 2 + 10 + int((t * 110) % 80)
                self._draw_teardrop(surface, config.EYE, tex, tey, 14, 22)

        for side in (-1, +1):
            ex = cx + side * eye_gap + ox
            ey = cy + oy
            
            # Curious offset
            if emotion == "curious" and side == -1:
                ey -= 12

            # Special eye shape: Love (hearts)
            if emotion == "love" and not blink:
                self._draw_heart(surface, config.EYE, ex, ey, ew)
                continue

            # Special eye shape: Dizzy (spirals)
            if emotion == "dizzy" and not blink:
                self._draw_spiral(surface, config.EYE, ex, ey, ew // 2, angle_offset=t * 12)
                continue

            # Special eye shape: Excited (stars)
            if emotion == "excited" and not blink:
                star_size = (ew // 2) * (1.0 + 0.15 * math.sin(t * 15))
                self._draw_star(surface, config.EYE, ex, ey, star_size, star_size * 0.45)
                continue

            # Special eye shape: Laughing / Wink (happy arcs)
            if (emotion == "laughing" or (emotion == "wink" and side == -1)) and not blink:
                rect = pygame.Rect(ex - ew // 2, ey - 15, ew, 30)
                pygame.draw.arc(surface, config.EYE, rect, 3.4, 6.0, 6)
                continue

            # Default: rounded eye rect
            rect = pygame.Rect(0, 0, ew, max(8, eh))
            rect.center = (ex, ey)
            radius = min(ew, eh) // 2 if eh > 8 else 6
            pygame.draw.rect(surface, config.EYE, rect, border_radius=radius)

            # 3D Parallax Pupil
            if eh > 20 and not blink:
                pw = int(ew * 0.4)
                ph = int(eh * 0.4)
                px = ex + int(ox * 0.25)
                py = ey + int(oy * 0.25)
                pygame.draw.ellipse(surface, (120, 215, 255), pygame.Rect(px - pw // 2, py - ph // 2, pw, ph))

            # Angry/Sad lid polygon cutoff
            if abs(self.curr_slant) > 0.02 and not blink:
                top = ey - eh // 2
                p1 = (ex - ew // 2, top)
                p2 = (ex + ew // 2, top)
                slant_amt = int((eh // 2) * abs(self.curr_slant))
                if self.curr_slant > 0:   # angry: drops toward the nose
                    p3 = (ex + side * ew // 2, top + slant_amt)
                else:                     # sad: drops toward the outside
                    p3 = (ex - side * ew // 2, top + slant_amt)
                pygame.draw.polygon(surface, config.BG, [p1, p2, p3])

    # ---- eyebrows ----
    def _draw_eyebrows(self, surface, state, cx, cy, ox, oy, t):
        emotion = state.emotion
        
        # Don't draw eyebrows if sleeping
        if emotion == "sleepy":
            return

        eye_gap = 95
        eb_w = 56
        eb_h = 7

        for side in (-1, +1):
            ex = cx + side * eye_gap + ox
            ey = cy + oy - 62 + int(self.curr_eyebrow_y)

            # Slant angle calculation: positive is angry (slants down towards nose)
            angle_rad = math.radians(-side * self.curr_eyebrow_slant)
            dx = math.cos(angle_rad) * (eb_w / 2)
            dy = math.sin(angle_rad) * (eb_w / 2)

            p1 = (ex - dx, ey - dy)
            p2 = (ex + dx, ey + dy)

            # Draw eyebrow line
            pygame.draw.line(surface, config.EYE, p1, p2, eb_h)

    # ---- mouth ----
    def _draw_mouth(self, surface, state, cx, cy, ox, oy, t):
        mx = cx + ox * 0.5
        my = cy + 90 + oy * 0.4
        emotion = state.emotion

        if state.talking:
            open_h = 8 + int(18 * abs(math.sin(t * 15)))
            pygame.draw.ellipse(
                surface, config.MOUTH,
                pygame.Rect(mx - 22, my - open_h // 2, 44, open_h)
            )
            if open_h > 12:
                # Inside hollow mouth
                pygame.draw.ellipse(
                    surface, config.BG,
                    pygame.Rect(mx - 16, my - (open_h - 6) // 2, 32, open_h - 6)
                )
        elif emotion in ("happy", "wink", "love", "laughing"):
            # Happy smiling Bezier curve
            p0 = (mx - 26, my - 6)
            p1 = (mx, my + 14)
            p2 = (mx + 26, my - 6)
            self._draw_bezier_mouth(surface, config.MOUTH, p0, p1, p2, width=5)
        elif emotion in ("sad", "upset", "crying"):
            # Sad frowning Bezier curve
            p0 = (mx - 26, my + 8)
            p1 = (mx, my - 6)
            p2 = (mx + 26, my + 8)
            self._draw_bezier_mouth(surface, config.MOUTH, p0, p1, p2, width=5)
        elif emotion == "angry":
            # Angry crooked smirk curve
            p0 = (mx - 20, my + 2)
            p1 = (mx, my - 3)
            p2 = (mx + 20, my + 4)
            self._draw_bezier_mouth(surface, config.MOUTH, p0, p1, p2, width=4)
        elif emotion == "surprised":
            pygame.draw.circle(surface, config.MOUTH, (int(mx), int(my)), 12, 4)
        elif emotion == "excited":
            # Excited open mouth
            rect = pygame.Rect(mx - 22, my - 10, 44, 24)
            pygame.draw.arc(surface, config.MOUTH, rect, math.pi, 2 * math.pi, 4)
            pygame.draw.line(surface, config.MOUTH, (mx - 22, my + 2), (mx + 22, my + 2), 4)
        elif emotion == "nervous" or emotion == "scared":
            # Squiggly zig-zag line
            points = [
                (mx - 20, my),
                (mx - 12, my - 4),
                (mx - 4, my + 4),
                (mx + 4, my - 4),
                (mx + 12, my + 4),
                (mx + 20, my)
            ]
            pygame.draw.lines(surface, config.MOUTH, False, points, 4)
        elif emotion == "dizzy":
            # Wavy lines
            points = [
                (mx - 18, my + 2),
                (mx - 9, my - 3),
                (mx, my + 3),
                (mx + 9, my - 3),
                (mx + 18, my + 2)
            ]
            pygame.draw.lines(surface, config.MOUTH, False, points, 4)
        elif emotion == "bored":
            # Bored straight/slanted line
            pygame.draw.line(surface, config.MOUTH, (mx - 15, my + 2), (mx + 15, my - 2), 4)
        elif emotion == "sleepy":
            # Yawning cycle: every 8 seconds, yawn for 3 seconds
            cycle_pos = t % 8.0
            if cycle_pos < 3.0:
                if cycle_pos < 0.8:
                    yawn_scale = cycle_pos / 0.8
                elif cycle_pos > 2.2:
                    yawn_scale = (3.0 - cycle_pos) / 0.8
                else:
                    yawn_scale = 1.0

                open_h = int(24 * yawn_scale)
                pygame.draw.ellipse(
                    surface, config.MOUTH,
                    pygame.Rect(mx - 10, my - open_h // 2, 20, open_h)
                )
                if open_h > 8:
                    pygame.draw.ellipse(
                        surface, config.BG,
                        pygame.Rect(mx - 7, my - (open_h - 4) // 2, 14, open_h - 4)
                    )
            else:
                pygame.draw.line(surface, config.MOUTH, (mx - 12, my), (mx + 12, my), 4)
        else:
            # Default straight line
            pygame.draw.line(surface, config.EYE_DIM, (mx - 18, my), (mx + 18, my), 4)

    # ---- status line ----
    def _draw_status(self, surface, state):
        if state.thinking:
            status = "...thinking..."
        elif state.talking:
            status = "talking"
        elif state.listening:
            status = "listening"
        elif not getattr(state, "conversation_active", False):
            status = f"{config.NAME} digital  -  [Asleep] Say 'MIP' or 'Hello' to wake me up"
        else:
            status = f"{config.NAME} digital  -  [Active] Talk to me... (ESC = quit)"
        surface.blit(
            self._font.render(status, True, config.TXT),
            (16, self.height - 28),
        )

    # ---- Bezier Mouth Curve helper ----
    def _draw_bezier_mouth(self, surface, color, p0, p1, p2, width=4):
        points = []
        steps = 20
        for i in range(steps + 1):
            t = i / steps
            x = (1 - t)**2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0]
            y = (1 - t)**2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1]
            points.append((x, y))
        pygame.draw.lines(surface, color, False, points, width)

    # ---- Custom Shape drawing helpers ----
    def _draw_teardrop(self, surface, color, cx, cy, w, h):
        points = [
            (cx, cy - h // 2),
            (cx + w // 2, cy + h // 6),
            (cx + w // 3, cy + h // 2),
            (cx - w // 3, cy + h // 2),
            (cx - w // 2, cy + h // 6),
        ]
        pygame.draw.polygon(surface, color, points)

    def _draw_heart(self, surface, color, cx, cy, size):
        points = []
        steps = 24
        for i in range(steps):
            theta = i * 2 * math.pi / steps
            x = 16 * (math.sin(theta) ** 3)
            y = 13 * math.cos(theta) - 5 * math.cos(2*theta) - 2 * math.cos(3*theta) - math.cos(4*theta)
            scale = size / 32
            points.append((cx + x * scale, cy - y * scale))
        pygame.draw.polygon(surface, color, points)

    def _draw_spiral(self, surface, color, cx, cy, max_r, angle_offset=0):
        points = []
        steps = 30
        for i in range(steps + 1):
            theta = (i / steps) * 4 * math.pi + angle_offset
            r = (i / steps) * max_r
            x = cx + r * math.cos(theta)
            y = cy + r * math.sin(theta)
            points.append((x, y))
        pygame.draw.lines(surface, color, False, points, 3)

    def _draw_star(self, surface, color, cx, cy, outer_r, inner_r):
        points = []
        for i in range(10):
            r = outer_r if i % 2 == 0 else inner_r
            angle = i * math.pi / 5 - math.pi / 2
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            points.append((x, y))
        pygame.draw.polygon(surface, color, points)

    # ---- Waving Hand overlay rendering ----
    def _draw_waving_hand(self, surface, elapsed, t):
        px = self.width + 30
        py = self.height - 30
        length = 180

        angle_deg = 135
        if 0.5 <= elapsed <= 2.0:
            angle_deg += math.sin(t * 16) * 15

        slide_offset = 0.0
        if elapsed < 0.5:
            # slide in
            slide_offset = (0.5 - elapsed) * 240
        elif elapsed > 2.0:
            # slide out
            slide_offset = (elapsed - 2.0) * 240

        rad = math.radians(angle_deg)
        hx = px + length * math.cos(rad) + slide_offset
        hy = py - length * math.sin(rad)

        # Draw arm line
        pygame.draw.line(surface, config.EYE_DIM, (px + slide_offset, py), (hx, hy), 12)

        # Draw palm
        pygame.draw.circle(surface, config.EYE, (int(hx), int(hy)), 18)

        # Finger offsets relative to hand center at angle=0 (pointing right)
        finger_offsets = [
            (-5, 15, 6),
            (15, 10, 5),
            (20, -2, 5),
            (15, -12, 5),
            (5, -20, 4)
        ]

        for dx, dy, frad in finger_offsets:
            # Rotate offset by hand angle
            rx = dx * math.cos(rad) - dy * math.sin(rad)
            ry = dx * math.sin(rad) + dy * math.cos(rad)
            pygame.draw.circle(surface, config.EYE, (int(hx + rx), int(hy - ry)), frad)
