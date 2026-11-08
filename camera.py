"""
camera.py
Module quản lý webcam: mở camera, đọc khung hình, xử lý lỗi, đóng camera.
"""

import cv2
import config


class CameraError(Exception):
    """Lỗi riêng cho camera, để main.py bắt và báo cho người dùng dễ hiểu."""
    pass


class Camera:
    def __init__(self, index=config.CAMERA_INDEX,
                 width=config.FRAME_WIDTH,
                 height=config.FRAME_HEIGHT,
                 fps=config.TARGET_FPS):
        self.index = index
        self.width = width
        self.height = height
        self.fps = fps
        self.cap = None                # Đối tượng VideoCapture của OpenCV
        self.fail_count = 0            # Đếm số lần đọc lỗi liên tiếp

    def open(self):
        """Mở webcam. Nếu không mở được thì báo lỗi CameraError."""
        # CAP_DSHOW giúp mở camera nhanh hơn và ổn định hơn trên Windows
        self.cap = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)

        if not self.cap.isOpened():
            # Thử lại bằng cách mở mặc định (cho macOS/Linux)
            self.cap = cv2.VideoCapture(self.index)

        if not self.cap.isOpened():
            self.cap = None
            raise CameraError(
                f"Không mở được camera số {self.index}.\n"
                "Hãy kiểm tra: (1) webcam đã cắm chưa, "
                "(2) có app nào khác đang dùng camera không (Zoom, Messenger...), "
                "(3) thử đổi CAMERA_INDEX trong config.py thành 1."
            )

        # Yêu cầu độ phân giải và FPS (camera có thể không hỗ trợ đúng như yêu cầu)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        # Giữ bộ đệm nhỏ để hình luôn mới nhất, giảm độ trễ
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.fail_count = 0

    def read(self):
        """
        Đọc một khung hình.
        Trả về: ảnh (numpy array) nếu thành công, None nếu lần này đọc lỗi.
        Nếu lỗi quá nhiều lần liên tiếp -> báo CameraError (camera bị ngắt).
        """
        if self.cap is None:
            raise CameraError("Camera chưa được mở. Hãy gọi open() trước.")

        success, frame = self.cap.read()

        if not success or frame is None:
            self.fail_count += 1
            if self.fail_count >= config.MAX_READ_FAILURES:
                raise CameraError(
                    "Mất kết nối với camera (có thể bị rút cáp hoặc app khác chiếm dụng)."
                )
            return None

        self.fail_count = 0  # Đọc được rồi thì reset bộ đếm lỗi
        return frame

    def get_actual_size(self):
        """Lấy độ phân giải thực tế mà camera đang dùng."""
        if self.cap is None:
            return (0, 0)
        w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return (w, h)

    def close(self):
        """Giải phóng camera để app khác có thể dùng."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None