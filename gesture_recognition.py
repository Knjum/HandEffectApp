"""
gesture_recognition.py
Nhận diện cử chỉ tay từ 21 điểm landmark, kèm bộ ổn định chống kích hoạt nhầm.

Muốn thêm cử chỉ mới: viết một hàm is_xxx(fingers, lm) rồi thêm vào danh sách
SINGLE_HAND_GESTURES ở dưới (xem phần "CỬ CHỈ TÙY CHỈNH").
"""

import math
import time
from dataclasses import dataclass, field
import config


# ----------------------------------------------------------------------
# 1. HÀM TIỆN ÍCH
# ----------------------------------------------------------------------
def dist(a, b):
    """Khoảng cách giữa hai điểm (x, y)."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def palm_size(lm):
    """
    Kích hoạt "thước đo" của bàn tay: khoảng cách từ cổ tay (0) đến gốc ngón giữa (9).
    Dùng thước này để các ngưỡng không phụ thuộc việc tay gần hay xa camera.
    """
    return max(dist(lm[0], lm[9]), 1.0)


# Mỗi ngón: (số điểm đầu ngón, số điểm khớp giữa PIP)
FINGER_JOINTS = {
    "index":  (8, 6),
    "middle": (12, 10),
    "ring":   (16, 14),
    "pinky":  (20, 18),
}


def get_finger_states(lm):
    """
    Trả về dict cho biết từng ngón đang DUỖI (True) hay GẬP (False).
    Cách làm: ngón duỗi thì đầu ngón xa cổ tay hơn khớp giữa.
    Cách này không phụ thuộc hướng bàn tay (úp, ngửa, nghiêng đều được).
    """
    wrist = lm[0]
    states = {}

    for name, (tip, pip) in FINGER_JOINTS.items():
        states[name] = dist(lm[tip], wrist) > dist(lm[pip], wrist) * config.FINGER_EXTEND_RATIO

    # Ngón cái cử động khác 4 ngón còn lại nên xét riêng:
    # duỗi khi đầu ngón (4) xa gốc ngón út (17) hơn khớp (3),
    # và đầu ngón đủ xa gốc ngón trỏ (5).
    palm = palm_size(lm)
    states["thumb"] = (
        dist(lm[4], lm[17]) > dist(lm[3], lm[17])
        and dist(lm[4], lm[5]) > config.THUMB_EXTEND_RATIO * palm
    )
    return states


# ----------------------------------------------------------------------
# 2. LUẬT CHO CỬ CHỈ MỘT TAY
# Mỗi hàm nhận (fingers, lm) và trả về True/False.
# ----------------------------------------------------------------------
def four_folded(f):
    """4 ngón (trỏ, giữa, áp út, út) đều gập."""
    return not (f["index"] or f["middle"] or f["ring"] or f["pinky"])


def is_thumbs_up(f, lm):
    """Giơ ngón cái: cái duỗi, 4 ngón kia gập, đầu ngón cái hướng LÊN."""
    if not (f["thumb"] and four_folded(f)):
        return False
    lift = config.THUMBS_UP_LIFT_RATIO * palm_size(lm)
    # Trong ảnh, y nhỏ hơn nghĩa là ở cao hơn
    return lm[4][1] < lm[5][1] - lift


def is_peace(f, lm):
    """Chữ V: trỏ và giữa duỗi, áp út và út gập."""
    return f["index"] and f["middle"] and not f["ring"] and not f["pinky"]


def is_open_palm(f, lm):
    """Bàn tay mở: 4 ngón đều duỗi (ngón cái thế nào cũng được)."""
    return f["index"] and f["middle"] and f["ring"] and f["pinky"]


def is_fist(f, lm):
    """Nắm tay: cả 4 ngón gập (kiểm tra sau ngón cái giơ lên nên không bị nhầm)."""
    return four_folded(f)


# --- CỬ CHỈ TÙY CHỈNH (ví dụ để bạn học cách thêm) ---
def is_pointing(f, lm):
    """Chỉ tay: chỉ ngón trỏ duỗi."""
    return f["index"] and not f["middle"] and not f["ring"] and not f["pinky"]


def is_rock(f, lm):
    """Rock on: ngón trỏ và ngón út duỗi, giữa và áp út gập."""
    return f["index"] and f["pinky"] and not f["middle"] and not f["ring"]

def is_three(f, lm):
    """Giơ 3 ngón: trỏ, giữa, áp út duỗi; út gập."""
    return f["index"] and f["middle"] and f["ring"] and not f["pinky"]


# Danh sách cử chỉ một tay. THỨ TỰ = ĐỘ ƯU TIÊN: cái nào khớp trước thì được chọn.
# (Ngón cái giơ lên phải đứng trước nắm tay vì cả hai đều có 4 ngón gập.)
SINGLE_HAND_GESTURES = [
    ("THUMBS_UP", is_thumbs_up),
    ("PEACE", is_peace),
    ("OPEN_PALM", is_open_palm),
    ("FIST", is_fist),
    ("POINTING", is_pointing),
    ("ROCK", is_rock),
     ("THREE", is_three),
]


# ----------------------------------------------------------------------
# 3. LUẬT CHO CỬ CHỈ HAI TAY: TRÁI TIM
# ----------------------------------------------------------------------
def heart_metrics(lm_a, lm_b):
    """
    Tính 3 con số mô tả "độ giống trái tim" của hai tay (đều tính theo kích thước lòng bàn tay):
      - thumb_ratio: khoảng cách giữa hai đầu ngón cái (càng nhỏ càng chạm nhau)
      - index_ratio: khoảng cách giữa hai đầu ngón trỏ (càng nhỏ càng chạm nhau)
      - lift_ratio:  hai đầu ngón trỏ cao hơn hai đầu ngón cái bao nhiêu (phải > 0)
    """
    palm = (palm_size(lm_a) + palm_size(lm_b)) / 2
    thumb_ratio = dist(lm_a[4], lm_b[4]) / palm
    index_ratio = dist(lm_a[8], lm_b[8]) / palm
    idx_y = (lm_a[8][1] + lm_b[8][1]) / 2
    thumb_y = (lm_a[4][1] + lm_b[4][1]) / 2
    lift_ratio = (thumb_y - idx_y) / palm   # dương = ngón trỏ ở trên ngón cái
    return thumb_ratio, index_ratio, lift_ratio


def is_heart(lm_a, lm_b):
    """Trái tim hai tay: đầu ngón cái chạm nhau ở dưới, đầu ngón trỏ chạm nhau ở trên."""
    thumb_ratio, index_ratio, lift_ratio = heart_metrics(lm_a, lm_b)
    limit = config.HEART_DISTANCE_RATIO
    return thumb_ratio < limit and index_ratio < limit and lift_ratio > 0.2


# Tên hiển thị (không dấu vì cv2.putText không vẽ được tiếng Việt có dấu)
GESTURE_LABELS = {
    "THUMBS_UP": "Gio ngon cai",
    "PEACE": "Chu V",
    "OPEN_PALM": "Ban tay mo",
    "FIST": "Nam tay",
    "POINTING": "Chi tay",
    "ROCK": "Rock on",
    "HEART": "Trai tim 2 tay",
    "THREE": "Gio 3 ngon",
}


# ----------------------------------------------------------------------
# 4. BỘ ỔN ĐỊNH - CHỐNG KÍCH HOẠT NHẦM
# ----------------------------------------------------------------------
class GestureStabilizer:
    """
    Nhận cử chỉ "thô" của từng khung hình, trả về cử chỉ "chính thức".
    - Cần ENTER_FRAMES khung liên tiếp để chuyển sang cử chỉ mới.
    - Cần EXIT_FRAMES khung liên tiếp (không có cử chỉ) để kết thúc.
    - Có cooldown để cùng cử chỉ không kích hoạt dồn dập.
    """

    def __init__(self):
        self.active = None          # Cử chỉ chính thức hiện tại
        self.candidate = None       # Cử chỉ đang "thử thách"
        self.count = 0              # Số khung liên tiếp thấy candidate
        self.last_trigger = {}      # Thời điểm kích hoạt gần nhất của mỗi cử chỉ

    def update(self, raw, now):
        """
        raw: tên cử chỉ thô của khung này (hoặc None).
        Trả về (cử chỉ chính thức, có vừa kích hoạt không).
        """
        # Cử chỉ thô trùng với cử chỉ chính thức: mọi thứ ổn, xóa bộ đếm thử thách
        if raw == self.active:
            self.candidate = None
            self.count = 0
            return self.active, False

        # Cử chỉ thô khác: đếm xem nó có liên tục không
        if raw == self.candidate:
            self.count += 1
        else:
            self.candidate = raw
            self.count = 1

        # Mất cử chỉ (raw=None) cần nhiều khung hơn để kết luận -> chống nhấp nháy
        needed = config.GESTURE_ENTER_FRAMES if raw is not None else config.GESTURE_EXIT_FRAMES

        if self.count < needed:
            return self.active, False

        # Đủ điều kiện: chuyển sang cử chỉ mới
        self.active = raw
        self.candidate = None
        self.count = 0

        triggered = False
        if raw is not None:
            last = self.last_trigger.get(raw, float("-inf"))
            if now - last >= config.GESTURE_COOLDOWN:
                triggered = True
                self.last_trigger[raw] = now
        return self.active, triggered


# ----------------------------------------------------------------------
# 5. BỘ NHẬN DIỆN CHÍNH
# ----------------------------------------------------------------------
@dataclass
class GestureResult:
    active: dict = field(default_factory=dict)      # {"Left": "PEACE", "Right": "FIST"} hoặc {"Both": "HEART"}
    triggered: list = field(default_factory=list)   # [("Right", "FIST")] - các cử chỉ VỪA kích hoạt


class GestureRecognizer:
    def __init__(self):
        self.stabilizers = {}       # Mỗi "vị trí" (Left/Right/Both) có một bộ ổn định riêng
        self.debug_fingers = {}     # Dữ liệu để hiển thị chế độ debug
        self.debug_heart = None

    @staticmethod
    def _assign_keys(hands):
        """Gán nhãn Left/Right cho từng tay. Nếu MediaPipe gán trùng nhãn thì đổi nhãn tay thứ hai."""
        keyed = {}
        for hand in hands[:2]:
            key = hand.label
            if key in keyed:
                key = "Left" if key == "Right" else "Right"
            keyed[key] = hand
        return keyed

    def _detect_raw(self, keyed):
        """Tìm cử chỉ thô của khung hình hiện tại."""
        raw = {}
        self.debug_fingers = {}
        self.debug_heart = None

        # Hai tay: kiểm tra trái tim trước (ưu tiên cao nhất)
        if len(keyed) == 2:
            a, b = keyed["Left"].landmarks, keyed["Right"].landmarks
            self.debug_heart = heart_metrics(a, b)
            if is_heart(a, b):
                return {"Both": "HEART"}

        # Từng tay riêng lẻ
        for key, hand in keyed.items():
            fingers = get_finger_states(hand.landmarks)
            self.debug_fingers[key] = (fingers, hand.landmarks[0])
            for name, rule in SINGLE_HAND_GESTURES:
                if rule(fingers, hand.landmarks):
                    raw[key] = name
                    break
        return raw

    def update(self, hands, now=None):
        """Gọi mỗi khung hình. Trả về GestureResult."""
        if now is None:
            now = time.time()

        keyed = self._assign_keys(hands)
        raw = self._detect_raw(keyed)

        result = GestureResult()
        # Phải cập nhật cả những vị trí không còn tay (raw=None) để chúng kết thúc đúng lúc
        for key in set(self.stabilizers) | set(raw):
            stabilizer = self.stabilizers.setdefault(key, GestureStabilizer())
            active, triggered = stabilizer.update(raw.get(key), now)
            if active is not None:
                result.active[key] = active
            if triggered:
                result.triggered.append((key, active))
        return result