"""
main.py
Giai đoạn 5: Webcam + bàn tay + cử chỉ + hiệu ứng + nhận diện cơ thể.
Phím tắt:
  q / ESC = thoát          1-7 = bật/tắt từng hiệu ứng
  + / -   = tăng/giảm độ mạnh hiệu ứng
  r = học lại nền (dùng khi đổi chỗ đứng, đổi ánh sáng, xê dịch camera)
  b = bật/tắt khung xương cơ thể    m = bật/tắt cửa sổ mặt nạ người
  l = ẩn/hiện bộ xương bàn tay      d = debug    n = số điểm landmark
"""

import time
import cv2
import config
from camera import Camera, CameraError
from hand_detection import HandDetector
from gesture_recognition import GestureRecognizer, GESTURE_LABELS
from effect_manager import EffectManager
from body_detection import BodyAnalyzer


def draw_text(frame, text, x, y, color=(0, 255, 0), scale=0.8):
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2)


def draw_debug(frame, recognizer):
    """Chế độ debug: hiện trạng thái 5 ngón và số đo trái tim."""
    for key, (fingers, wrist) in recognizer.debug_fingers.items():
        bits = "".join("1" if fingers[n] else "0"
                       for n in ("thumb", "index", "middle", "ring", "pinky"))
        cv2.putText(frame, f"{key}: {bits}", (wrist[0] - 40, wrist[1] + 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)
    if recognizer.debug_heart is not None:
        t, i, lift = recognizer.debug_heart
        draw_text(frame, f"Tim: cai={t:.2f} tro={i:.2f} cao={lift:.2f}",
                  10, frame.shape[0] - 15, (255, 200, 0), 0.6)


def draw_effect_hud(frame, manager, now):
    """Danh sách hiệu ứng ở góc phải: số phím, tên, ON/OFF, dấu * nếu đang chạy."""
    w = frame.shape[1]
    x, y = w - 330, 30
    for i, effect in enumerate(manager.effects):
        if not effect.enabled:
            color, state = (120, 120, 120), "OFF"
        elif effect.is_running(now):
            color, state = (0, 255, 255), "ON *"
        else:
            color, state = (0, 255, 0), "ON"
        draw_text(frame, f"[{i + 1}] {effect.label}: {state}", x, y, color, 0.6)
        y += 26
    intensity = manager.effects[0].intensity if manager.effects else 1.0
    draw_text(frame, f"Do manh (+/-): {intensity:.2f}", x, y + 4, (255, 255, 255), 0.6)


def main():
    camera = Camera()

    try:
        camera.open()
    except CameraError as e:
        print("LỖI:", e)
        input("Nhấn Enter để thoát...")
        return

    try:
        detector = HandDetector()
    except Exception as e:
        print("LỖI khởi tạo MediaPipe:", e)
        camera.close()
        input("Nhấn Enter để thoát...")
        return

    # Nhận diện cơ thể: nếu lỗi thì chương trình vẫn chạy, chỉ mất các hiệu ứng về nền
    try:
        body = BodyAnalyzer()
    except Exception as e:
        print("CẢNH BÁO: không khởi tạo được nhận diện cơ thể:", e)
        body = None

    recognizer = GestureRecognizer()
    manager = EffectManager()

    width, height = camera.get_actual_size()
    print(f"Đã mở camera. Độ phân giải thực tế: {width}x{height}")
    print("Phím: q/ESC thoát | 1-7 bật/tắt hiệu ứng | +/- độ mạnh | r học lại nền | b khung xương | m mặt nạ")
    print("MẸO: lúc mới chạy hãy bước ra khỏi khung hình 2-3 giây để chương trình học nền.")

    prev_time = time.time()
    fps = 0.0

    try:
        while True:
            frame = camera.read()

            if frame is None:
                if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                    break
                continue

            if config.MIRROR_VIEW:
                frame = cv2.flip(frame, 1)

            # 1. Nhận diện bàn tay và cử chỉ (trên ảnh GỐC, nên vẫn hoạt động khi người đã biến mất)
            hands = detector.detect(frame)
            now = time.time()
            result = recognizer.update(hands, now)
            for key, gesture in result.triggered:
                print(f"KICH HOAT: {GESTURE_LABELS.get(gesture, gesture)} ({key})")

            # 2. Nhận diện cơ thể (cũng trên ảnh gốc, trước khi áp hiệu ứng)
            if body is not None:
                body.update(frame, manager.needs_body() or body.plate.needs_learning)

            # 3. Áp hiệu ứng, rồi vẽ bộ xương lên trên cùng
            frame = manager.process(frame, hands, result, now, body)
            if config.SHOW_HAND_LANDMARKS:
                detector.draw(frame, hands)
            if body is not None and config.SHOW_POSE:
                body.draw_pose(frame)

            # 4. Thông tin trạng thái
            instant_fps = 1.0 / max(now - prev_time, 1e-6)
            fps = 0.9 * fps + 0.1 * instant_fps
            prev_time = now

            draw_text(frame, f"FPS: {fps:.1f}", 10, 30)
            if hands:
                draw_text(frame, f"So ban tay: {len(hands)}", 10, 60)
            else:
                draw_text(frame, "Khong thay ban tay", 10, 60, (0, 0, 255))
            y = 95
            for key, gesture in result.active.items():
                draw_text(frame, f"{key}: {GESTURE_LABELS.get(gesture, gesture)}",
                          10, y, (0, 255, 255))
                y += 30
            draw_effect_hud(frame, manager, now)
            if body is not None and body.mask is not None:
                draw_text(frame, f"Nen da hoc: {body.plate.coverage():.0%}",
                          10, frame.shape[0] - 45, (255, 255, 0), 0.6)
            if config.SHOW_DEBUG:
                draw_debug(frame, recognizer)

            cv2.imshow(config.WINDOW_NAME, frame)

            # Cửa sổ phụ hiện mặt nạ người (để kiểm tra tách người có tốt không)
            if config.SHOW_MASK and body is not None and body.mask is not None:
                cv2.imshow("Mask", cv2.convertScaleAbs(body.mask, alpha=255.0))

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            elif ord("1") <= key <= ord("9"):
                manager.toggle(key - ord("1"))
            elif key in (ord("+"), ord("=")):
                manager.change_intensity(config.EFFECT_INTENSITY_STEP)
            elif key == ord("-"):
                manager.change_intensity(-config.EFFECT_INTENSITY_STEP)
            elif key == ord("r") and body is not None:
                body.plate.reset()
            elif key == ord("b"):
                config.SHOW_POSE = not config.SHOW_POSE
            elif key == ord("m"):
                config.SHOW_MASK = not config.SHOW_MASK
                if not config.SHOW_MASK:
                    cv2.destroyWindow("Mask")
            elif key == ord("l"):
                config.SHOW_HAND_LANDMARKS = not config.SHOW_HAND_LANDMARKS
            elif key == ord("n"):
                config.SHOW_LANDMARK_NUMBERS = not config.SHOW_LANDMARK_NUMBERS
            elif key == ord("d"):
                config.SHOW_DEBUG = not config.SHOW_DEBUG

            if cv2.getWindowProperty(config.WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                break

    except CameraError as e:
        print("LỖI CAMERA:", e)
    except KeyboardInterrupt:
        print("Đã dừng bằng Ctrl+C.")
    finally:
        detector.close()
        if body is not None:
            body.close()
        camera.close()
        cv2.destroyAllWindows()
        print("Đã đóng chương trình.")


if __name__ == "__main__":
    main()
