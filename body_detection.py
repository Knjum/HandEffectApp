"""
body_detection.py
Nhận diện cơ thể:
  - Selfie Segmentation: tách người khỏi nền -> mặt nạ (mask) float32, 0.0 = nền, 1.0 = người.
  - BackgroundPlate: tự học "ảnh nền sạch" (căn phòng khi không có người).
  - Pose (tùy chọn): khung xương cơ thể, bật bằng phím b.
"""

import cv2
import numpy as np
import mediapipe as mp

import config
from effects.utils import blend8


class BackgroundPlate:
    """
    Lưu nền sạch theo chế độ thủ công hoặc tự động.

    Manual chỉ thay plate sau khi đã gom đủ nhiều frame không có người.
    Auto chỉ cập nhật pixel ngoài mask và đứng yên đủ lâu.
    """

    CAPTURE_FRAMES = 15
    CAPTURE_MAX_ATTEMPTS = 300
    AUTO_STABLE_FRAMES = 8
    AUTO_MOTION_THRESHOLD = 10

    def __init__(self):
        self.plate = None       # Ảnh nền đã học
        self.known = None       # Mặt nạ uint8: 255 = điểm này đã từng thấy nền
        self._fallback = None   # Ảnh tạm dùng cho vùng chưa học được
        self._fallback_count = 0
        self.mode = getattr(config, "BACKGROUND_LEARNING_MODE", "auto")
        self.capture_active = False
        self.capture_progress = 0.0
        self._capture_frames = []
        self._capture_attempts = 0
        self._capture_message = ""
        self._notice = None
        self._previous_colour = None
        self._stable_count = None
        self._manual_ready = False

    def reset(self):
        self.plate = None
        self.known = None
        self._fallback = None
        self._fallback_count = 0
        self.capture_active = False
        self.capture_progress = 0.0
        self._capture_frames.clear()
        self._capture_attempts = 0
        self._capture_message = ""
        self._previous_colour = None
        self._stable_count = None
        self._manual_ready = False

    def set_mode(self, mode):
        if mode not in ("manual", "auto") or mode == self.mode:
            return
        self.mode = mode
        self.capture_active = False
        self.capture_progress = 0.0
        self._capture_frames.clear()
        self._capture_attempts = 0
        self._capture_message = ""
        self._previous_colour = None
        self._stable_count = None
        self._notice = None
        # Manual phải được capture rõ ràng sau khi chuyển từ Auto.
        if mode == "manual":
            self._manual_ready = False

    def begin_capture(self):
        if self.mode != "manual":
            return False
        self.capture_active = True
        self.capture_progress = 0.0
        self._capture_frames.clear()
        self._capture_attempts = 0
        self._capture_message = "Hãy ra khỏi khung hình để chụp nền sạch."
        self._notice = None
        return True

    @property
    def needs_learning(self):
        return self.mode == "auto" or self.capture_active

    @property
    def auto_update(self):
        return self.mode == "auto"

    @property
    def ready(self):
        if self.mode == "manual":
            return self._manual_ready
        # Auto intentionally leaves the eroded image border unknown.
        return self.coverage() >= 0.90

    @property
    def status(self):
        if self.capture_active:
            return "LEARNING"
        if self.mode == "manual":
            return "READY" if self._manual_ready else "NOT LEARNED"
        return "READY" if self.ready else "LEARNING"

    @property
    def progress(self):
        if self.mode == "manual":
            return self.capture_progress if self.capture_active else (1.0 if self._manual_ready else 0.0)
        return min(1.0, self.coverage() / 0.90)

    @property
    def message(self):
        if self.capture_active:
            return self._capture_message
        if self.mode == "manual" and not self._manual_ready:
            return "Chọn HỌC NỀN và ra khỏi khung hình trước khi dùng tàng hình."
        if self.mode == "manual" and self._manual_ready:
            return "Nền thủ công đã khóa; nhấn HỌC LẠI NỀN sau khi đổi cảnh hoặc ánh sáng."
        if self.mode == "auto" and not self.ready:
            return "Đang học các vùng nền đứng yên; hãy di chuyển để lộ nền bị che."
        return ""

    def pop_notice(self):
        notice, self._notice = self._notice, None
        return notice

    def coverage(self):
        """Tỉ lệ (0-1) điểm ảnh đã học được nền."""
        if self.known is None:
            return 0.0
        return cv2.countNonZero(self.known) / self.known.size

    def update(self, frame, mask):
        if mask.shape[:2] != frame.shape[:2]:
            return
        if self.mode == "manual":
            if self.capture_active:
                self._capture_clean_frame(frame, mask)
            return

        self._update_auto(frame, mask)

    def _ensure_buffers(self, frame):
        if self.plate is None or self.plate.shape != frame.shape:
            self.plate = np.zeros_like(frame)
            self.known = np.zeros(frame.shape[:2], dtype=np.uint8)
            self._stable_count = np.zeros(frame.shape[:2], dtype=np.uint8)
            self._previous_colour = None
            self._fallback = None

    def _safe_background_mask(self, mask):
        # Mask là float 0..1. Lùi khỏi silhouette để không học nhầm tóc/áo.
        free = (mask < 0.08).astype(np.uint8) * 255
        return cv2.erode(
            free, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))
        )

    def _capture_clean_frame(self, frame, mask):
        self._capture_attempts += 1
        person_fraction = float(np.mean(mask > 0.12))
        if person_fraction <= 0.005:
            self._capture_frames.append(frame.copy())
            self.capture_progress = min(1.0, len(self._capture_frames) / self.CAPTURE_FRAMES)
            self._capture_message = (
                f"Đang thu khung nền sạch: {len(self._capture_frames)}/{self.CAPTURE_FRAMES}."
            )
        else:
            self._capture_message = "Phát hiện người trong hình; hãy ra khỏi khung hình."

        if len(self._capture_frames) >= self.CAPTURE_FRAMES:
            # Median bỏ các vật/chuyển động chỉ xuất hiện trong một phần mẫu.
            samples = np.stack(self._capture_frames, axis=0)
            self.plate = np.partition(
                samples, self.CAPTURE_FRAMES // 2, axis=0
            )[self.CAPTURE_FRAMES // 2].copy()
            self.known = np.full(frame.shape[:2], 255, dtype=np.uint8)
            self._manual_ready = True
            self.capture_active = False
            self.capture_progress = 1.0
            self._capture_frames.clear()
            self._previous_colour = None
            self._stable_count = None
            self._fallback = None
            self._capture_message = "Đã học và khóa nền thủ công."
        elif self._capture_attempts >= self.CAPTURE_MAX_ATTEMPTS:
            self.capture_active = False
            self._capture_frames.clear()
            self.capture_progress = 0.0
            self._capture_message = "Học nền thất bại; hãy kiểm tra camera rồi thử lại."
            self._notice = self._capture_message

    def _update_auto(self, frame, mask):
        self._ensure_buffers(frame)
        free = self._safe_background_mask(mask) > 0

        colour = cv2.GaussianBlur(frame, (3, 3), 0)
        if self._previous_colour is None:
            stable = free
        else:
            delta = np.max(cv2.absdiff(colour, self._previous_colour), axis=2)
            stable = free & (delta < self.AUTO_MOTION_THRESHOLD)
        self._previous_colour = colour

        self._stable_count[~stable] = 0
        self._stable_count[stable] = np.minimum(
            self._stable_count[stable].astype(np.uint16) + 1,
            self.AUTO_STABLE_FRAMES,
        ).astype(np.uint8)
        safe = (self._stable_count >= self.AUTO_STABLE_FRAMES).astype(np.uint8) * 255

        # Chỉ thay nền bằng pixel nền không chuyển động qua nhiều lần quan sát.
        self.plate = blend8(frame, self.plate, safe)
        self.known = cv2.bitwise_or(self.known, safe)

    def _make_fallback(self, frame, mask):
        """Ước lượng phần nền bị che bằng inpaint trên ảnh thu nhỏ 1/4."""
        h, w = frame.shape[:2]
        # 1/4 giữ nhiều chi tiết nền hơn 1/8, trong khi inpaint vẫn nhẹ.
        sw, sh = max(w // 4, 1), max(h // 4, 1)
        small = cv2.resize(frame, (sw, sh), interpolation=cv2.INTER_AREA)
        m8 = cv2.resize((mask > 0.08).astype(np.uint8) * 255, (sw, sh),
                        interpolation=cv2.INTER_NEAREST)
        m8 = cv2.dilate(m8, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
        filled = cv2.inpaint(small, m8, 4, cv2.INPAINT_TELEA)
        return cv2.resize(filled, (w, h), interpolation=cv2.INTER_LINEAR)

    def get(self, frame, mask):
        """Trả về ảnh nền để lấp chỗ người. Vùng chưa học được thì dùng ảnh tô mờ tạm."""
        if mask.shape[:2] != frame.shape[:2]:
            return frame
        if self.plate is None or self.plate.shape != frame.shape:
            return self._make_fallback(frame, mask)

        person8 = (mask > 0.08).astype(np.uint8) * 255
        hole = cv2.bitwise_and(person8, cv2.bitwise_not(self.known))
        if cv2.countNonZero(hole) == 0:
            return self.plate           # Nền sau lưng người đã học đủ

        # Còn vùng chưa học: dùng ảnh tạm (cập nhật 4 khung một lần cho nhẹ)
        self._fallback_count += 1
        if self._fallback is None or self._fallback.shape != frame.shape \
                or self._fallback_count % 4 == 0:
            self._fallback = self._make_fallback(frame, mask)
        return blend8(self.plate, self._fallback, self.known)

    def can_hide(self, mask):
        if (mask is None or self.known is None
                or mask.shape[:2] != self.known.shape):
            return False
        if self.mode == "manual":
            return self._manual_ready
        person = mask > 0.35
        if not np.any(person):
            return False
        return float(np.mean(self.known[person] > 0)) >= 0.95


class BodyAnalyzer:
    def __init__(self):
        self.segmenter = mp.solutions.selfie_segmentation.SelfieSegmentation(
            model_selection=config.SEGMENTATION_MODEL
        )
        self.mp_pose = mp.solutions.pose
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_styles = mp.solutions.drawing_styles
        self.pose = None            # Chỉ tạo khi bật khung xương
        self.pose_landmarks = None

        self.mask = None            # float32, cùng kích thước khung hình (None = chưa có)
        self.plate = BackgroundPlate()
        self._frame_count = 0
        self._seg_runs = 0

    def update(self, frame, need_mask):
        """Gọi mỗi khung hình với ảnh GỐC (trước khi áp hiệu ứng)."""
        if need_mask:
            self._frame_count += 1
            if self.mask is None or self._frame_count % config.SEGMENTATION_EVERY_N_FRAMES == 0:
                self._segment(frame)
        else:
            self.mask = None        # Không hiệu ứng nào cần -> bỏ qua để tiết kiệm CPU

        if config.SHOW_POSE:
            self._detect_pose(frame)
        else:
            self.pose_landmarks = None

    def _segment(self, frame):
        h, w = frame.shape[:2]
        s = config.SEGMENTATION_SCALE
        small = cv2.resize(frame, (max(int(w * s), 1), max(int(h * s), 1)),
                           interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        result = self.segmenter.process(rgb)
        if result.segmentation_mask is None:
            return

        # Làm "cứng" mặt nạ (đẩy giá trị về gần 0 hoặc 1), làm mịn viền, phóng về cỡ gốc
        m = np.clip((result.segmentation_mask - 0.35) / 0.3, 0.0, 1.0).astype(np.float32)
        m = cv2.GaussianBlur(m, (0, 0), 2)
        m = cv2.resize(m, (w, h), interpolation=cv2.INTER_LINEAR)

        # Trộn với mặt nạ khung trước để viền không nhấp nháy
        a = config.MASK_SMOOTHING
        if a > 0 and self.mask is not None and self.mask.shape == m.shape:
            m = cv2.addWeighted(m, 1.0 - a, self.mask, a, 0)
        self.mask = m

        self._seg_runs += 1
        if self.plate.capture_active or (self._seg_runs - 1) % config.PLATE_UPDATE_EVERY == 0:
            self.plate.update(frame, self.mask)

    def _detect_pose(self, frame):
        if self.pose is None:
            self.pose = self.mp_pose.Pose(
                static_image_mode=False,
                model_complexity=0,         # 0 = nhẹ nhất
                smooth_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
        small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        self.pose_landmarks = self.pose.process(rgb).pose_landmarks   # None nếu không thấy người

    def draw_pose(self, frame):
        """Vẽ khung xương cơ thể (33 điểm) lên ảnh."""
        if self.pose_landmarks is not None:
            self.mp_draw.draw_landmarks(
                frame, self.pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                self.mp_styles.get_default_pose_landmarks_style(),
            )

    def close(self):
        self.segmenter.close()
        if self.pose is not None:
            self.pose.close()
