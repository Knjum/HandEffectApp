"""Thiết lập chung của chương trình.

Muốn thay đổi camera, độ phân giải... chỉ cần sửa ở file này.
"""

import os
import sys


def resource_path(relative_path):
    """Find a resource beside a PyInstaller/Nuitka bundle or source file."""
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    elif "__compiled__" in globals():
        base_path = __compiled__.containing_dir
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# --- Thiết lập camera ---
CAMERA_INDEX = 0        # 0 = webcam mặc định. Nếu có nhiều camera, thử 1, 2...
FRAME_WIDTH = 1280      # Chiều rộng khung hình
FRAME_HEIGHT = 720      # Chiều cao khung hình
TARGET_FPS = 30         # Số khung hình mỗi giây mong muốn

# --- Thiết lập hiển thị ---
WINDOW_NAME = "Hand Effect App"
MIRROR_VIEW = True      # True = lật ngược ảnh như soi gương (tự nhiên hơn khi dùng)

# --- Thiết lập xử lý lỗi ---
MAX_READ_FAILURES = 30  # Số lần đọc khung hình lỗi liên tiếp trước khi coi là camera bị ngắt

# --- Thiết lập nhận diện bàn tay ---
MAX_HANDS = 2                   # Số bàn tay tối đa cần nhận diện
HAND_MODEL_COMPLEXITY = 0       # 0 = nhẹ và nhanh, 1 = chính xác hơn nhưng chậm hơn
HAND_DETECTION_CONFIDENCE = 0.6 # Ngưỡng tin cậy để phát hiện tay (0.0 - 1.0)
HAND_TRACKING_CONFIDENCE = 0.5  # Ngưỡng tin cậy để bám theo tay (0.0 - 1.0)
SHOW_LANDMARK_NUMBERS = False   # True = hiện số thứ tự 0-20 trên từng điểm (để học)


# --- Thiết lập nhận diện cử chỉ ---
FINGER_EXTEND_RATIO = 1.15      # Ngón được coi là DUỖI khi đầu ngón xa cổ tay hơn khớp giữa x lần này
THUMB_EXTEND_RATIO = 0.6        # Ngón cái duỗi khi đầu ngón cách gốc ngón trỏ >= tỉ lệ này x kích thước lòng bàn tay
THUMBS_UP_LIFT_RATIO = 0.3      # Đầu ngón cái phải cao hơn gốc ngón trỏ ít nhất tỉ lệ này x kích thước lòng bàn tay
HEART_DISTANCE_RATIO = 0.8      # Hai đầu ngón cái (và hai đầu ngón trỏ) phải gần nhau trong ngưỡng này (tính theo lòng bàn tay)

# --- Chống kích hoạt nhầm ---
GESTURE_ENTER_FRAMES = 5        # Số khung hình liên tiếp để XÁC NHẬN một cử chỉ
GESTURE_EXIT_FRAMES = 8         # Số khung hình liên tiếp để coi cử chỉ đã KẾT THÚC
GESTURE_COOLDOWN = 1.0          # Giây chờ trước khi cùng một cử chỉ được kích hoạt lại

# --- Hiển thị ---
SHOW_DEBUG = False              # True = hiện trạng thái 5 ngón để chỉnh ngưỡng
BANNER_SECONDS = 1.5            # Thời gian hiện chữ "KICH HOAT" giữa màn hình


# --- Thiết lập hiệu ứng ---
EFFECT_DEFAULT_INTENSITY = 1.0  # Độ mạnh mặc định (1.0 = bình thường)
EFFECT_MIN_INTENSITY = 0.25
EFFECT_MAX_INTENSITY = 3.0
EFFECT_INTENSITY_STEP = 0.25    # Mỗi lần bấm + hoặc - thì đổi bấy nhiêu
SHOW_HAND_LANDMARKS = True      # False = ẩn bộ xương bàn tay, chỉ thấy hiệu ứng

# Bảng gắn cử chỉ -> hiệu ứng. Sửa ở đây để đổi cách kích hoạt.
# Tên cử chỉ lấy từ gesture_recognition.py, tên hiệu ứng lấy từ thuộc tính `name` của từng hiệu ứng.
GESTURE_EFFECTS = {
   "HEART":     ["hearts", "particles"],
    "THUMBS_UP": ["hearts"],
    "PEACE":     ["particles"],
    "OPEN_PALM": ["hand_glow"],
    "FIST":      ["light_rays"],
    "ROCK":      ["bg_blur"],
    "THREE":     ["bg_replace"],
    "POINTING":  ["disappear"],
}


# --- Giai đoạn 5: Nhận diện cơ thể ---
SEGMENTATION_MODEL = 0           # 0 = model chung (nhanh), 1 = model phong cảnh
SEGMENTATION_SCALE = 0.5         # Thu nhỏ ảnh trước khi tách người (nhỏ hơn = nhanh hơn, kém nét hơn)
SEGMENTATION_EVERY_N_FRAMES = 1  # 1 = tách người mọi khung; 2 = cách 1 khung (nhanh hơn, hơi trễ)
MASK_SMOOTHING = 0.4             # 0 = không làm mượt; càng cao viền càng ổn định nhưng càng trễ
PLATE_UPDATE_EVERY = 3           # Cứ N lần tách người thì cập nhật "ảnh nền sạch" một lần
BACKGROUND_IMAGE_PATH = resource_path(os.path.join("assets", "background.jpg"))  # Ảnh nền tùy chọn cho hiệu ứng Đổi nền
DISAPPEAR_BACKGROUND_IMAGE_PATH = ""  # Ảnh tùy chọn lấp vùng người khi dùng hiệu ứng tàng hình
BACKGROUND_LEARNING_MODE = "auto"  # "manual" = khóa nền; "auto" = tự học vùng nền ổn định
SHOW_POSE = False                # True = vẽ khung xương cơ thể (phím b)
SHOW_MASK = False                # True = mở cửa sổ phụ hiện mặt nạ người (phím m), để kiểm tra


# --- Giai đoạn 6: Giao diện (tên tiếng Việt có dấu để hiển thị) ---
EFFECT_LABELS_VI = {
    "hearts":     "Trái tim bay",
    "particles":  "Hạt lấp lánh",
    "hand_glow":  "Tay phát sáng",
    "light_rays": "Tia sáng",
    "bg_blur":    "Làm mờ nền",
    "bg_replace": "Đổi nền",
    "disappear":  "Biến mất / Xuất hiện",
}

GESTURE_LABELS_VI = {
    "THUMBS_UP": "Giơ ngón cái",
    "PEACE":     "Chữ V",
    "OPEN_PALM": "Bàn tay mở",
    "FIST":      "Nắm tay",
    "POINTING":  "Chỉ tay",
    "ROCK":      "Rock on",
    "THREE":     "Giơ 3 ngón",
    "HEART":     "Trái tim hai tay",
}


# --- Giai đoạn 7: Camera ảo ---
VCAM_MIRROR = False    # False = gửi ảnh KHÔNG lật gương (chữ/biển hiệu phía sau bạn không bị ngược khi người khác xem)
VCAM_FPS = 30          # FPS khai báo cho camera ảo
