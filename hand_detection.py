"""
hand_detection.py
Module nhận diện bàn tay bằng MediaPipe.
Đầu vào: một khung hình (ảnh BGR của OpenCV).
Đầu ra: danh sách HandInfo, mỗi phần tử là thông tin của một bàn tay.
"""

from dataclasses import dataclass, field
import cv2
import mediapipe as mp
import config


@dataclass
class HandInfo:
    """Gói thông tin của MỘT bàn tay, để các module sau dễ dùng."""
    label: str                    # "Left" hoặc "Right"
    score: float                  # Độ tin cậy (0.0 - 1.0)
    landmarks: list = field(default_factory=list)  # 21 điểm (x, y) theo pixel
    raw: object = None            # Dữ liệu gốc của MediaPipe (dùng để vẽ)


class HandDetector:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_styles = mp.solutions.drawing_styles

        # Tạo bộ nhận diện. static_image_mode=False nghĩa là video:
        # MediaPipe sẽ "bám theo" tay giữa các khung hình -> nhanh hơn.
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=config.MAX_HANDS,
            model_complexity=config.HAND_MODEL_COMPLEXITY,
            min_detection_confidence=config.HAND_DETECTION_CONFIDENCE,
            min_tracking_confidence=config.HAND_TRACKING_CONFIDENCE,
        )

    def detect(self, frame):
        """
        Tìm bàn tay trong khung hình.
        Trả về: danh sách HandInfo (rỗng nếu không thấy tay nào).
        """
        height, width = frame.shape[:2]
        # MediaPipe cần ảnh RGB, còn OpenCV dùng BGR -> phải đổi màu
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Đánh dấu chỉ-đọc giúp MediaPipe xử lý nhanh hơn một chút
        rgb.flags.writeable = False
        results = self.hands.process(rgb)

        hands_found = []
        # Không thấy tay -> multi_hand_landmarks là None -> trả danh sách rỗng
        if not results.multi_hand_landmarks:
            return hands_found

        for hand_lms, handedness in zip(results.multi_hand_landmarks,
                                        results.multi_handedness):
            # MediaPipe trả tọa độ dạng 0.0-1.0 (tỉ lệ), ta đổi sang pixel
            points = [
                (int(lm.x * width), int(lm.y * height))
                for lm in hand_lms.landmark
            ]
            info = HandInfo(
                label=handedness.classification[0].label,
                score=handedness.classification[0].score,
                landmarks=points,
                raw=hand_lms,
            )
            hands_found.append(info)

        return hands_found

    def draw(self, frame, hands):
        """Vẽ 21 điểm landmark và các đường nối lên khung hình."""
        for hand in hands:
            self.mp_draw.draw_landmarks(
                frame,
                hand.raw,
                self.mp_hands.HAND_CONNECTIONS,
                self.mp_styles.get_default_hand_landmarks_style(),
                self.mp_styles.get_default_hand_connections_style(),
            )

            # Tùy chọn: ghi số thứ tự 0-20 lên từng điểm (để học cho dễ)
            if config.SHOW_LANDMARK_NUMBERS:
                for i, (x, y) in enumerate(hand.landmarks):
                    cv2.putText(frame, str(i), (x + 4, y - 4),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                                (255, 255, 0), 1)

            # Ghi nhãn tay ngay cạnh cổ tay (điểm số 0)
            wrist_x, wrist_y = hand.landmarks[0]
            text = f"{hand.label} {hand.score:.0%}"
            cv2.putText(frame, text, (wrist_x - 30, wrist_y + 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    def close(self):
        """Giải phóng tài nguyên của MediaPipe."""
        self.hands.close()
