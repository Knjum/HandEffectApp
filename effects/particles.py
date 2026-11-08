"""
effects/particles.py
Hiệu ứng hạt lấp lánh: các hạt sáng bắn ra từ đầu ngón tay, bay lên và mờ dần.
"""

import math
import random
from dataclasses import dataclass

import cv2

from effects.base import Effect
from effects.utils import FINGERTIPS, palm_center, scale_color, add_glow

# Màu hạt (BGR): vàng kim, trắng, xanh dương nhạt, xanh ngọc
PALETTE = [(60, 200, 255), (255, 255, 255), (255, 180, 80), (150, 255, 200)]

MAX_PARTICLES = 400


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    size: float
    color: tuple
    age: float = 0.0


class ParticleEffect(Effect):
    name = "particles"
    label = "Hat lap lanh"
    default_duration = 4.0

    def __init__(self):
        super().__init__()
        self.particles = []
        self.spawn_acc = 0.0

    def _spawn(self, x, y, speed):
        if len(self.particles) >= MAX_PARTICLES:
            return
        angle = random.uniform(0, 2 * math.pi)
        v = random.uniform(speed * 0.3, speed)
        self.particles.append(Particle(
            x=x, y=y,
            vx=math.cos(angle) * v,
            vy=math.sin(angle) * v,
            life=random.uniform(0.8, 1.8),
            size=random.uniform(2, 6),
            color=random.choice(PALETTE),
        ))

    def on_trigger(self, now, hands, size):
        # Bắn tung một loạt hạt từ lòng bàn tay
        for hand in hands:
            cx, cy = palm_center(hand.landmarks)
            for _ in range(int(60 * self.intensity)):
                self._spawn(cx, cy, 350)

    def update(self, dt, now, hands, size):
        # Đang chạy thì liên tục phát hạt từ các đầu ngón tay
        if self.is_running(now) and hands:
            self.spawn_acc += 60 * self.intensity * dt
            while self.spawn_acc >= 1:
                self.spawn_acc -= 1
                hand = random.choice(hands)
                tip = hand.landmarks[random.choice(FINGERTIPS)]
                self._spawn(tip[0], tip[1], 120)

        damping = 0.4 ** dt        # Ma sát: hạt chậm dần
        alive = []
        for p in self.particles:
            p.age += dt
            p.vx *= damping
            p.vy = p.vy * damping - 25 * dt   # Thêm chút lực nổi lên trên
            p.x += p.vx * dt
            p.y += p.vy * dt
            if p.age < p.life:
                alive.append(p)
        self.particles = alive

    def draw(self, frame, now):
        if not self.particles:
            return frame

        layer = frame.copy()
        layer[:] = 0   # Lớp đen, chỉ vẽ hạt sáng lên
        for p in self.particles:
            f = 1.0 - p.age / p.life            # 1 -> 0: hạt mờ dần và nhỏ dần
            radius = max(1, int(p.size * f))
            cv2.circle(layer, (int(p.x), int(p.y)), radius,
                       scale_color(p.color, f), -1, cv2.LINE_AA)
        return add_glow(frame, layer, sigma=10)

    def clear(self):
        super().clear()
        self.particles = []