"""
effects/disappearing.py
Hiệu ứng biến mất / xuất hiện: người "tan" dần thành các mảng ngẫu nhiên
rồi lộ ra phần nền phía sau. Mỗi lần kích hoạt là đảo trạng thái (biến mất <-> xuất hiện).
"""

import cv2
import numpy as np

import config
from effects.base import Effect
from effects.utils import add_glow, blend_with_mask


class DisappearEffect(Effect):
    name = "disappear"
    label = "Bien mat"
    default_duration = 1.5      # Ở hiệu ứng này, "duration" là thời gian chuyển cảnh (giây)
    layer = -2                  # Vẽ đầu tiên, trước cả làm mờ/đổi nền
    needs_body = True

    EDGE_WIDTH = 0.16           # Dải chuyển tiếp rộng hơn giúp tan mềm hơn
    GLOW_COLOR = (220, 205, 165)  # Ánh sáng ấm, nhẹ (BGR)

    def __init__(self):
        super().__init__()
        self.hidden = False     # Đích đến: True = người biến mất
        self.progress = 0.0     # 0 = hiện rõ hoàn toàn, 1 = biến mất hoàn toàn
        self._noise = None      # Bản đồ "thứ tự tan" của từng điểm ảnh
        self._custom_background_path = None
        self._custom_background = None
        self._custom_background_size = None

    def trigger(self, now, hands, size):
        """Ghi đè: mỗi lần kích hoạt là đảo trạng thái, không phải chạy theo thời gian."""
        self.hidden = not self.hidden

    def is_running(self, now):
        """Hiện dấu * ở danh sách khi đang biến mất hoặc đang chuyển cảnh."""
        return self.hidden or self.progress > 0.001

    def update(self, dt, now, hands, size):
        step = dt / max(self.duration, 0.1)
        if self.hidden:
            self.progress = min(1.0, self.progress + step)
        else:
            self.progress = max(0.0, self.progress - step)

    def _get_noise(self, w, h):
        """Tạo bản đồ ngẫu nhiên dạng mảng loang, hơi ưu tiên tan từ trên xuống."""
        if self._noise is None or self._noise.shape != (h, w):
            rng = np.random.default_rng(7)   # Cố định hạt giống: mỗi lần chạy giống nhau
            blobs = rng.random((max(h // 24, 2), max(w // 24, 2))).astype(np.float32)
            blobs = cv2.resize(blobs, (w, h), interpolation=cv2.INTER_CUBIC)
            sweep = np.linspace(0, 1, h, dtype=np.float32)[:, None] * np.ones((1, w), np.float32)
            noise = 0.7 * blobs + 0.3 * sweep
            self._noise = (noise - noise.min()) / (noise.max() - noise.min())
        return self._noise

    @staticmethod
    def _person_alpha(mask):
        """Nới nhẹ viền tách người rồi feather để tránh viền người còn sót."""
        h, w = mask.shape[:2]
        radius = max(2, int(min(w, h) * 0.006))
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (radius * 2 + 1, radius * 2 + 1)
        )
        solid = (mask > 0.5).astype(np.float32)
        expanded = cv2.dilate(solid, kernel)
        # Dùng vùng chắc chắn là người để phủ viền bị bỏ sót; feather hẹp để
        # không tạo quầng xám rộng quanh silhouette.
        alpha = np.maximum(mask, expanded)
        return cv2.GaussianBlur(alpha, (0, 0), 1.2)

    def _get_custom_background(self, frame):
        """Đọc ảnh nền tùy chọn một lần rồi crop-cover theo kích thước camera."""
        path = config.DISAPPEAR_BACKGROUND_IMAGE_PATH
        if path != self._custom_background_path:
            self._custom_background_path = path
            self._custom_background = None
            self._custom_background_size = None
            if path:
                try:
                    encoded = np.fromfile(path, dtype=np.uint8)
                    self._custom_background = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
                except (OSError, ValueError, cv2.error):
                    self._custom_background = None

        if self._custom_background is None:
            return None

        h, w = frame.shape[:2]
        if self._custom_background_size != (w, h):
            source_h, source_w = self._custom_background.shape[:2]
            scale = max(w / source_w, h / source_h)
            resized_w = max(w, int(round(source_w * scale)))
            resized_h = max(h, int(round(source_h * scale)))
            resized = cv2.resize(
                self._custom_background, (resized_w, resized_h),
                interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR,
            )
            x = (resized_w - w) // 2
            y = (resized_h - h) // 2
            self._custom_background_size = (w, h)
            self._custom_background_frame = resized[y:y + h, x:x + w]
        return self._custom_background_frame

    def draw(self, frame, now):
        mask = None if self.body is None else self.body.mask
        if self.progress <= 0.001 or mask is None:
            return frame

        h, w = frame.shape[:2]
        background = self._get_custom_background(frame)
        if background is None:
            background = self.body.plate.get(frame, mask)  # Nền đã học / inpaint dự phòng
        person = self._person_alpha(mask)

        # Biến mất hoàn toàn: khỏi tính toán nặng
        if self.progress >= 0.999:
            return blend_with_mask(frame, background, 1.0 - person)

        # Điểm nào có noise nhỏ hơn progress thì đã tan (gone = 1)
        noise = self._get_noise(w, h)
        edge = self.EDGE_WIDTH
        gone = np.clip((self.progress * (1.0 + edge) - noise) / edge, 0.0, 1.0)

        keep = 1.0 - person * gone                # 1 = giữ nguyên, 0 = thay bằng nền
        out = blend_with_mask(frame, background, keep)

        # Viền sáng ở những chỗ đang tan (gone nằm giữa 0 và 1)
        glow_amt = person * 1.35 * gone * (1.0 - gone) * min(self.intensity, 1.5)
        g8 = cv2.convertScaleAbs(glow_amt, alpha=255.0)
        layer = cv2.merge([cv2.convertScaleAbs(g8, alpha=c / 255.0) for c in self.GLOW_COLOR])
        return add_glow(out, layer, sigma=6, core=False)

    def clear(self):
        """Tắt hiệu ứng thì người xuất hiện lại ngay."""
        super().clear()
        self.hidden = False
        self.progress = 0.0
