"""
main.py
Giai đoạn 6: chạy ứng dụng với giao diện PySide6.
(Bản dùng cửa sổ OpenCV cũ được giữ trong main_opencv.py)
"""

import sys
from PySide6.QtWidgets import QApplication
from interface.gui import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()