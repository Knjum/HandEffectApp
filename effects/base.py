"""
effects/base.py
Lớp cha (khuôn mẫu) cho mọi hiệu ứng.
Mỗi hiệu ứng con chỉ cần viết lại 3 hàm: on_trigger, update, draw.
"""

import config


class Effect:
    name = "base"               # Tên nội bộ, dùng trong GESTURE_EFFECTS
    label = "Base"              # Tên hiển thị (không dấu)
    default_duration = 4.0      # Hiệu ứng chạy bao nhiêu giây sau khi kích hoạt
    layer = 0                   # Thứ tự vẽ: số nhỏ vẽ trước (hiệu ứng nền dùng số âm)
    needs_body = False          # True nếu hiệu ứng cần mặt nạ tách người khỏi nền

    def __init__(self):
        self.enabled = True                              # Công tắc bật/tắt
        self.intensity = config.EFFECT_DEFAULT_INTENSITY  # Độ mạnh
        self.duration = self.default_duration            # Thời gian chạy (giây)
        self.start_time = 0.0
        self.end_time = 0.0
        self.body = None        # BodyAnalyzer (có .mask và .plate), do EffectManager gán mỗi khung

    # ----- Các hàm dùng chung -----
    def is_running(self, now):
        """Hiệu ứng đang trong thời gian chạy không?"""
        return now < self.end_time

    def trigger(self, now, hands, size):
        """Được gọi khi cử chỉ kích hoạt. Kích hoạt lại thì tính lại thời gian."""
        self.start_time = now
        self.end_time = now + self.duration
        self.on_trigger(now, hands, size)

    def fade(self, now):
        """
        Hệ số 0.0 - 1.0: hiện dần lúc đầu (0.3 giây) và mờ dần lúc cuối (0.6 giây).
        """
        if not self.is_running(now):
            return 0.0
        fade_in = (now - self.start_time) / 0.3
        fade_out = (self.end_time - now) / 0.6
        return max(0.0, min(fade_in, fade_out, 1.0))

    # ----- Các hàm hiệu ứng con viết lại -----
    def on_trigger(self, now, hands, size):
        pass

    def update(self, dt, now, hands, size):
        pass

    def draw(self, frame, now):
        return frame

    def clear(self):
        """Xóa sạch mọi thứ đang hiển thị (gọi khi người dùng tắt hiệu ứng)."""
        self.end_time = 0.0