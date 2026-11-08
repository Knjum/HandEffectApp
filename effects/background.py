"""
effects/background.py
Hai hiệu ứng thay đổi nền:
  - BackgroundBlurEffect:    làm mờ nền, giữ người nét.
  - BackgroundReplaceEffect: thay nền bằng ảnh của bạn hoặc nền màu chuyển động.
"""

import os

import cv2
import numpy as np

import config
from effects.base import Effect
from effects.utils import blend_with_mask


class BackgroundBlurEffect(Effect):
    name = "bg_blur"
    label = "Lam mo nen"
    default_duration = 8.0
    layer = -1                  # Vẽ trước các hiệu ứng ánh sáng, hạt, trái tim
    needs_body = True

    def draw(self, frame, now):
        fade = self.fade(now)
        mask = None if self.body is None else self.body.mask
        if fade <= 0 or mask is None:
            return frame        # Chưa có mặt nạ người thì bỏ qua, không báo lỗi

        h, w = frame.shape[:2]
        # Làm mờ trên ảnh thu nhỏ 1/4 cho nhanh, rồi phóng lại
        small = cv2.resize(frame, (max(w // 4, 1), max(h // 4, 1)),
                           interpolation=cv2.INTER_AREA)
        small = cv2.GaussianBlur(small, (0, 0), 2.0 + 2.0 * self.intensity)
        blurred = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)

        # fade: lúc mới bật nền mờ dần, lúc tắt nền rõ dần
        keep = 1.0 - (1.0 - mask) * fade
        return blend_with_mask(frame, blurred, keep)


class BackgroundReplaceEffect(Effect):
    name = "bg_replace"
    label = "Doi nen"
    default_duration = 8.0
    layer = -1
    needs_body = True

    def __init__(self):
        super().__init__()
        self._bg = None
        self._is_image = False

    def _make_background(self, w, h):
        """Tạo nền mới: dùng ảnh của bạn nếu có, không thì sinh nền màu chuyển động."""
        path = config.BACKGROUND_IMAGE_PATH
        if os.path.exists(path):
            img = cv2.imread(path)
            if img is not None:
                self._is_image = True
                return cv2.resize(img, (w, h))

        self._is_image = False
        # Dải màu tuần hoàn theo chiều ngang (để cuộn vòng liền mạch), tối dần xuống dưới
        x = np.linspace(0, 2 * np.pi, w, endpoint=False, dtype=np.float32)
        row = np.stack([128 + 127 * np.sin(x + p) for p in (0.0, 2.1, 4.2)], axis=1)
        shade = np.linspace(1.0, 0.5, h, dtype=np.float32)[:, None, None]
        return (row[None, :, :] * shade).astype(np.uint8)

    def draw(self, frame, now):
        fade = self.fade(now)
        mask = None if self.body is None else self.body.mask
        if fade <= 0 or mask is None:
            return frame

        h, w = frame.shape[:2]
        if self._bg is None or self._bg.shape[:2] != (h, w):
            self._bg = self._make_background(w, h)

        bg = self._bg
        if not self._is_image:
            bg = np.roll(bg, -(int(now * 80) % w), axis=1)   # Cuộn nền cho chuyển động

        keep = 1.0 - (1.0 - mask) * fade
        return blend_with_mask(frame, bg, keep)