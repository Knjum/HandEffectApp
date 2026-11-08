"""
effects/heart.py
Hiệu ứng trái tim bay lên: trái tim nổi từ đáy màn hình và từ quanh bàn tay.
"""

import math
import random
from dataclasses import dataclass

import cv2
import numpy as np

from effects.base import Effect
from effects.utils import palm_center, palm_size

# --- Tạo sẵn hình trái tim (công thức toán học), dùng lại cho mọi trái tim ---
_t = np.linspace(0, 2 * np.pi, 40)
_x = 16 * np.sin(_t) ** 3
_y = -(13 * np.cos(_t) - 5 * np.cos(2 * _t) - 2 * np.cos(3 * _t) - np.cos(4 * _t))
HEART_SHAPE = np.stack([_x, _y], axis=1) / 17.0   # Chuẩn hóa về khoảng -1..1

# Các màu hồng/đỏ (BGR)
HEART_COLORS = [(180, 105, 255), (147, 20, 255), (90, 90, 255), (203, 192, 255), (120, 60, 230)]

MAX_HEARTS = 120


@dataclass
class Heart:
    x: float
    y: float
    size: float         # Nửa chiều rộng của trái tim (pixel)
    vy: float           # Vận tốc bay lên (pixel/giây, âm = đi lên)
    sway_amp: float     # Biên độ lắc ngang
    sway_speed: float
    phase: float
    life: float         # Tuổi thọ (giây)
    color: tuple
    age: float = 0.0


class HeartEffect(Effect):
    name = "hearts"
    label = "Trai tim bay"
    default_duration = 5.0

    def __init__(self):
        super().__init__()
        self.hearts = []
        self.spawn_acc = 0.0   # Bộ tích lũy để sinh trái tim đều theo thời gian

    def _spawn(self, x, y):
        if len(self.hearts) >= MAX_HEARTS:
            return
        self.hearts.append(Heart(
            x=x, y=y,
            size=random.uniform(14, 38),
            vy=-random.uniform(60, 160),
            sway_amp=random.uniform(20, 60),
            sway_speed=random.uniform(1.5, 3.5),
            phase=random.uniform(0, 6.28),
            life=random.uniform(2.5, 4.5),
            color=random.choice(HEART_COLORS),
        ))

    def on_trigger(self, now, hands, size):
        # Bắn một loạt trái tim ngay từ lòng bàn tay lúc kích hoạt
        for hand in hands:
            cx, cy = palm_center(hand.landmarks)
            spread = palm_size(hand.landmarks)
            for _ in range(int(10 * self.intensity)):
                self._spawn(cx + random.uniform(-spread, spread),
                            cy + random.uniform(-spread, spread * 0.5))

    def update(self, dt, now, hands, size):
        w, h = size

        # Đang trong thời gian chạy thì sinh thêm trái tim
        if self.is_running(now):
            self.spawn_acc += 12 * self.intensity * dt
            while self.spawn_acc >= 1:
                self.spawn_acc -= 1
                if hands and random.random() < 0.5:
                    # Nửa số trái tim sinh quanh một bàn tay
                    hand = random.choice(hands)
                    cx, cy = palm_center(hand.landmarks)
                    r = palm_size(hand.landmarks) * 1.5
                    self._spawn(cx + random.uniform(-r, r), cy + random.uniform(-r, r))
                else:
                    # Nửa còn lại nổi lên từ đáy màn hình
                    self._spawn(random.uniform(0, w), h + 30)

        # Di chuyển và xóa trái tim đã hết tuổi hoặc bay khỏi màn hình
        alive = []
        for heart in self.hearts:
            heart.age += dt
            heart.y += heart.vy * dt
            heart.x += math.sin(heart.age * heart.sway_speed + heart.phase) * heart.sway_amp * dt
            if heart.age < heart.life and heart.y > -heart.size * 2:
                alive.append(heart)
        self.hearts = alive

    def draw(self, frame, now):
        if not self.hearts:
            return frame

        overlay = frame.copy()
        for heart in self.hearts:
            # Phóng to dần lúc mới sinh, nhỏ dần lúc sắp biến mất
            grow = min(1.0, heart.age / 0.3)
            shrink = min(1.0, (heart.life - heart.age) / 0.8)
            s = heart.size * grow * shrink
            if s < 2:
                continue
            pts = (HEART_SHAPE * s + (heart.x, heart.y)).astype(np.int32)
            cv2.fillPoly(overlay, [pts], heart.color, cv2.LINE_AA)
            # Điểm sáng nhỏ để trái tim trông bóng hơn
            cv2.circle(overlay, (int(heart.x - s * 0.4), int(heart.y - s * 0.3)),
                       max(1, int(s * 0.15)), (255, 255, 255), -1, cv2.LINE_AA)

        # Trộn overlay vào ảnh gốc để trái tim hơi trong suốt
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, dst=frame)
        return frame

    def clear(self):
        super().clear()
        self.hearts = []