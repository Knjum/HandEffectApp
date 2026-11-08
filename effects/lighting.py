"""
effects/lighting.py
Hai hiệu ứng ánh sáng:
  - HandGlowEffect: bàn tay phát sáng, nhấp nhô theo nhịp.
  - LightRaysEffect: chớp sáng + các tia sáng xoay quanh.
"""

import math

import cv2
import numpy as np

from effects.base import Effect
from effects.utils import FINGERTIPS, palm_center, palm_size, scale_color, add_glow


class HandGlowEffect(Effect):
    name = "hand_glow"
    label = "Tay phat sang"
    default_duration = 4.0

    GLOW_COLOR = (40, 190, 255)   # Vàng cam (BGR)

    def __init__(self):
        super().__init__()
        self.hand_points = []     # Landmark các bàn tay ở khung hình hiện tại

    def update(self, dt, now, hands, size):
        self.hand_points = [h.landmarks for h in hands]

    def draw(self, frame, now):
        fade = self.fade(now)
        if fade <= 0 or not self.hand_points:
            return frame

        strength = fade * min(self.intensity, 2.0) * 0.8
        color = scale_color(self.GLOW_COLOR, strength)
        pulse = 1.0 + 0.12 * math.sin(now * 6)    # Nhấp nhô theo nhịp

        layer = np.zeros_like(frame)
        for lm in self.hand_points:
            cx, cy = palm_center(lm)
            r = int(palm_size(lm) * 0.9 * pulse)
            cv2.circle(layer, (cx, cy), r, color, -1, cv2.LINE_AA)       # Quầng sáng lòng bàn tay
            for tip in FINGERTIPS:
                cv2.circle(layer, lm[tip], int(r * 0.3), color, -1, cv2.LINE_AA)  # Đầu ngón tay
        return add_glow(frame, layer, sigma=30, core=False)

    def clear(self):
        super().clear()
        self.hand_points = []


class LightRaysEffect(Effect):
    name = "light_rays"
    label = "Tia sang"
    default_duration = 3.0

    RAY_COUNT = 14
    RAY_COLOR = (255, 235, 200)   # Trắng hơi xanh (BGR)

    def __init__(self):
        super().__init__()
        self.center = None
        self.angle = 0.0

    def on_trigger(self, now, hands, size):
        # Tia sáng tỏa ra từ bàn tay đầu tiên, không có tay thì từ giữa màn hình
        if hands:
            self.center = palm_center(hands[0].landmarks)
        else:
            self.center = (size[0] // 2, size[1] // 2)

    def update(self, dt, now, hands, size):
        self.angle += dt * 0.8
        # Tâm tia sáng bám theo tay nếu tay còn trong khung hình
        if self.is_running(now) and hands:
            self.center = palm_center(hands[0].landmarks)

    def draw(self, frame, now):
        fade = self.fade(now)
        if fade <= 0 or self.center is None:
            return frame

        h, w = frame.shape[:2]
        strength = fade * min(self.intensity, 2.0)
        cx, cy = self.center

        # Chớp sáng nhanh lúc mới kích hoạt (0.4 giây đầu)
        flash = max(0.0, 1.0 - (now - self.start_time) / 0.4)
        if flash > 0:
            v = int(70 * flash * min(self.intensity, 2.0))
            cv2.add(frame, (v, v, v, 0), dst=frame)

        # Vẽ các tia (tam giác dài, mảnh) xoay quanh tâm
        layer = np.zeros_like(frame)
        length = max(w, h)
        color = scale_color(self.RAY_COLOR, strength * 0.5)
        for i in range(self.RAY_COUNT):
            a = self.angle + i * 2 * math.pi / self.RAY_COUNT
            half = 0.05 if i % 2 == 0 else 0.03     # Tia dày và mỏng xen kẽ
            p1 = (int(cx + length * math.cos(a - half)), int(cy + length * math.sin(a - half)))
            p2 = (int(cx + length * math.cos(a + half)), int(cy + length * math.sin(a + half)))
            cv2.fillPoly(layer, [np.array([(cx, cy), p1, p2], dtype=np.int32)], color, cv2.LINE_AA)
        cv2.circle(layer, (cx, cy), 45, scale_color(self.RAY_COLOR, strength * 0.8), -1, cv2.LINE_AA)
        return add_glow(frame, layer, sigma=12)