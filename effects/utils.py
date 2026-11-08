"""
effects/utils.py
Các hàm tiện ích dùng chung cho nhiều hiệu ứng.
"""

import cv2
from gesture_recognition import palm_size  # noqa: F401  (để các hiệu ứng import từ đây cho gọn)

# Số thứ tự 5 đầu ngón tay trong 21 điểm landmark
FINGERTIPS = (4, 8, 12, 16, 20)


def palm_center(lm):
    """Tâm lòng bàn tay = trung bình cổ tay và 4 gốc ngón (điểm 0, 5, 9, 13, 17)."""
    pts = [lm[i] for i in (0, 5, 9, 13, 17)]
    return (sum(p[0] for p in pts) // 5, sum(p[1] for p in pts) // 5)


def scale_color(color, factor):
    """Làm màu tối đi theo hệ số (0-1+). Màu càng tối thì ánh sáng cộng thêm càng yếu."""
    return tuple(int(max(0, min(255, c * factor))) for c in color)


def add_glow(frame, layer, sigma=12, core=True):
    """
    Cộng 'lớp ánh sáng' vào ảnh theo kiểu phát sáng.
    layer: ảnh đen cùng kích thước, chỉ vẽ những thứ muốn phát sáng bằng màu sáng.
    Cách làm: làm mờ layer (tạo quầng sáng) rồi CỘNG vào ảnh gốc.
    Làm mờ trên ảnh thu nhỏ 1/4 cho nhanh, rồi phóng lại.
    """
    h, w = layer.shape[:2]
    small = cv2.resize(layer, (max(w // 4, 1), max(h // 4, 1)), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), max(sigma / 4, 0.5))
    glow = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
    cv2.add(frame, glow, dst=frame)
    if core:
        cv2.add(frame, layer, dst=frame)  # Cộng thêm lõi sắc nét
    return frame



def blend8(fg, bg, mask8):
    """
    Trộn ảnh fg (tiền cảnh) lên bg (hậu cảnh) theo mặt nạ mask8 (ảnh xám uint8, 0-255).
    Điểm có mặt nạ = 255 lấy từ fg, = 0 lấy từ bg, ở giữa thì trộn mịn.
    """
    m3 = cv2.merge([mask8, mask8, mask8])
    a = cv2.multiply(fg, m3, scale=1.0 / 255.0)
    b = cv2.multiply(bg, cv2.bitwise_not(m3), scale=1.0 / 255.0)
    return cv2.add(a, b)


def blend_with_mask(fg, bg, mask):
    """Giống blend8 nhưng mặt nạ là số thực 0.0 - 1.0 (float32)."""
    return blend8(fg, bg, cv2.convertScaleAbs(mask, alpha=255.0))