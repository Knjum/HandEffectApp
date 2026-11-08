"""
test_vcam.py
Kiểm tra camera ảo hoạt động chưa: gửi màu đổi liên tục trong 30 giây.
Chạy: python test_vcam.py
"""

import time
import numpy as np
import pyvirtualcam

W, H = 1280, 720

with pyvirtualcam.Camera(width=W, height=H, fps=30,
                         fmt=pyvirtualcam.PixelFormat.BGR) as cam:
    print("Camera ảo đang chạy:", cam.device)
    print("Hãy mở Zoom/Discord/Messenger và chọn camera này. Chạy 30 giây...")
    frame = np.zeros((H, W, 3), np.uint8)
    start = time.time()
    while time.time() - start < 30:
        t = time.time() - start
        # Màu BGR đổi dần theo thời gian
        frame[:] = (int(127 + 127 * np.sin(t)),
                    int(127 + 127 * np.sin(t + 2)),
                    int(127 + 127 * np.sin(t + 4)))
        cam.send(frame)
        cam.sleep_until_next_frame()
print("Xong.")