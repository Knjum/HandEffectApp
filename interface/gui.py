"""
interface/gui.py
Cửa sổ chính: xem trước camera, bật/tắt camera, danh sách hiệu ứng,
trạng thái cử chỉ, thanh trượt độ mạnh / thời gian, nút thoát.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QGroupBox, QSlider, QCheckBox,
    QMessageBox, QScrollArea, QSizePolicy, QFileDialog, QButtonGroup,
    QRadioButton, QProgressBar,
)

import config
from effects import ALL_EFFECTS
from interface.worker import VideoWorker

HAND_KEY_VI = {"Left": "Tay trái", "Right": "Tay phải", "Both": "Hai tay"}

STYLE = """
QMainWindow, QWidget { background: #1e1f26; color: #e6e6e6; font-size: 13px; }
QLabel#preview { background: #000; border-radius: 8px; color: #8a8a99; font-size: 16px; }
QGroupBox { border: 1px solid #3a3c4a; border-radius: 8px; margin-top: 10px; padding: 12px 8px 8px 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #9fb4ff; }
QPushButton { background: #2f3242; border: 1px solid #44475a; border-radius: 6px; padding: 8px; }
QPushButton:hover { background: #3a3e54; }
QPushButton:disabled { color: #777; }
QPushButton#camera_on { background: #1f7a3f; border-color: #2fa85a; font-weight: bold; }
QPushButton#camera_off { background: #8a2a2a; border-color: #b84545; font-weight: bold; }
QPushButton#exit_btn { background: #4a2a2a; }
QListWidget { background: #14151b; border: 1px solid #3a3c4a; border-radius: 6px; }
QListWidget::item { padding: 5px; }
QListWidget::item:selected { background: #34407a; }
QSlider::groove:horizontal { height: 6px; background: #3a3c4a; border-radius: 3px; }
QSlider::handle:horizontal { background: #9fb4ff; width: 16px; margin: -5px 0; border-radius: 8px; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hand Effect App - Hiệu ứng camera")
        self.resize(1240, 760)

        self.worker = None            # Luồng xử lý video (None = camera đang tắt)
        self._close_when_worker_stops = False
        self.selected = None          # Tên nội bộ của hiệu ứng đang được chọn
        self._last_running = set()

        # Trạng thái của từng hiệu ứng, giao diện là nơi "giữ" các giá trị này
        self.state = {
            cls.name: {
                "enabled": True,
                "intensity": config.EFFECT_DEFAULT_INTENSITY,
                "duration": cls.default_duration,
            }
            for cls in ALL_EFFECTS
        }
        self.options = {
            "MIRROR_VIEW": config.MIRROR_VIEW,
            "SHOW_HAND_LANDMARKS": config.SHOW_HAND_LANDMARKS,
            "SHOW_POSE": config.SHOW_POSE,
            "VCAM_MIRROR": config.VCAM_MIRROR,
            "DISAPPEAR_BACKGROUND_IMAGE_PATH": config.DISAPPEAR_BACKGROUND_IMAGE_PATH,
            "BACKGROUND_LEARNING_MODE": config.BACKGROUND_LEARNING_MODE,
        }
        self._background_status_data = {
            "background_mode": config.BACKGROUND_LEARNING_MODE,
            "background_status": "NOT LEARNED" if config.BACKGROUND_LEARNING_MODE == "manual" else "LEARNING",
            "background_progress": 0.0,
            "background_auto_update": config.BACKGROUND_LEARNING_MODE == "auto",
            "background_ready": False,
            "background_capturing": False,
            "background_message": "",
        }

        self._build_ui()
        self.setStyleSheet(STYLE)

    # ==================================================================
    # DỰNG GIAO DIỆN
    # ==================================================================
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        # ---------- Bên trái: màn hình xem trước ----------
        left = QVBoxLayout()
        self.preview = QLabel('Camera đang tắt\nBấm "Bật camera" để bắt đầu')
        self.preview.setObjectName("preview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(640, 360)
        # Ignored: ảnh lớn đến mấy cũng không làm cửa sổ phình ra
        self.preview.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        left.addWidget(self.preview, 1)

        self.info_label = QLabel("FPS: --")
        left.addWidget(self.info_label)
        root.addLayout(left, 1)

        # ---------- Bên phải: bảng điều khiển (có thanh cuộn cho màn hình nhỏ) ----------
        panel = QWidget()
        right = QVBoxLayout(panel)

        self.camera_btn = QPushButton("▶  Bật camera")
        self.camera_btn.setObjectName("camera_on")
        self.camera_btn.setMinimumHeight(42)
        self.camera_btn.clicked.connect(self.toggle_camera)
        right.addWidget(self.camera_btn)

        # -- Trạng thái nhận diện --
        box = QGroupBox("Trạng thái nhận diện")
        lay = QVBoxLayout(box)
        self.hand_label = QLabel("Số bàn tay: 0")
        self.gesture_label = QLabel("Chưa có cử chỉ")
        self.gesture_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffd866;")
        self.gesture_label.setWordWrap(True)
        lay.addWidget(self.hand_label)
        lay.addWidget(self.gesture_label)
        right.addWidget(box)

        # -- Danh sách hiệu ứng --
        box = QGroupBox("Hiệu ứng (tích để bật/tắt)")
        lay = QVBoxLayout(box)
        self.effect_list = QListWidget()
        self.effect_list.setMaximumHeight(210)
        for cls in ALL_EFFECTS:
            item = QListWidgetItem(self._effect_label(cls.name))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, cls.name)      # Cất tên nội bộ vào item
            item.setToolTip("Kích hoạt bằng: " + self._gesture_text(cls.name))
            self.effect_list.addItem(item)
        lay.addWidget(self.effect_list)
        hint = QLabel("● = đang chạy")
        hint.setStyleSheet("color: #8a8a99;")
        lay.addWidget(hint)
        right.addWidget(box)

        # -- Điều chỉnh hiệu ứng đang chọn --
        box = QGroupBox("Điều chỉnh hiệu ứng đang chọn")
        lay = QVBoxLayout(box)
        self.sel_name_label = QLabel("")
        self.sel_name_label.setStyleSheet("font-weight: bold; color: #9fb4ff;")
        self.sel_gesture_label = QLabel("")
        self.sel_gesture_label.setWordWrap(True)

        self.intensity_text = QLabel("")
        self.intensity_slider = QSlider(Qt.Orientation.Horizontal)
        self.intensity_slider.setRange(int(config.EFFECT_MIN_INTENSITY * 100),
                                       int(config.EFFECT_MAX_INTENSITY * 100))
        self.intensity_slider.setSingleStep(5)
        self.intensity_slider.setPageStep(25)
        self.intensity_slider.valueChanged.connect(self.on_intensity_changed)

        self.duration_title = QLabel("Thời gian chạy")
        self.duration_text = QLabel("")
        self.duration_slider = QSlider(Qt.Orientation.Horizontal)
        self.duration_slider.setRange(5, 150)            # 0.5 đến 15 giây (chia 10)
        self.duration_slider.setPageStep(10)
        self.duration_slider.valueChanged.connect(self.on_duration_changed)

        self.test_btn = QPushButton("✨  Kích hoạt thử")
        self.test_btn.clicked.connect(self.on_test_clicked)

        for w in (self.sel_name_label, self.sel_gesture_label, self.intensity_text,
                  self.intensity_slider, self.duration_title, self.duration_text,
                  self.duration_slider, self.test_btn):
            lay.addWidget(w)
        right.addWidget(box)

        # -- Tùy chọn --
        box = QGroupBox("Tùy chọn")
        lay = QVBoxLayout(box)
        for text, attr in (("Lật gương", "MIRROR_VIEW"),
                           ("Hiện bộ xương bàn tay", "SHOW_HAND_LANDMARKS"),
                           ("Hiện khung xương cơ thể", "SHOW_POSE")):
            cb = QCheckBox(text)
            cb.setChecked(self.options[attr])
            cb.toggled.connect(lambda checked, a=attr: self.on_option_toggled(a, checked))
            lay.addWidget(cb)
        right.addWidget(box)

        # -- Chế độ học nền --
        box = QGroupBox("BACKGROUND LEARNING MODE (CHẾ ĐỘ HỌC NỀN)")
        lay = QVBoxLayout(box)
        self.background_mode_group = QButtonGroup(self)
        self.manual_mode_radio = QRadioButton("MANUAL MODE — Học nền thủ công")
        self.auto_mode_radio = QRadioButton("AUTO MODE — Học nền tự động")
        self.background_mode_group.addButton(self.manual_mode_radio)
        self.background_mode_group.addButton(self.auto_mode_radio)
        mode = self.options["BACKGROUND_LEARNING_MODE"]
        self.manual_mode_radio.setChecked(mode == "manual")
        self.auto_mode_radio.setChecked(mode != "manual")
        self.manual_mode_radio.toggled.connect(
            lambda checked: checked and self.set_background_mode("manual"))
        self.auto_mode_radio.toggled.connect(
            lambda checked: checked and self.set_background_mode("auto"))
        lay.addWidget(self.manual_mode_radio)
        lay.addWidget(self.auto_mode_radio)

        self.background_status_label = QLabel("Background: LEARNING")
        self.auto_update_label = QLabel("Auto Update: ON")
        self.background_progress = QProgressBar()
        self.background_progress.setRange(0, 100)
        self.background_progress.setValue(0)
        self.background_message_label = QLabel("")
        self.background_message_label.setWordWrap(True)
        self.background_message_label.setStyleSheet("color: #8a8a99;")
        lay.addWidget(self.background_status_label)
        lay.addWidget(self.auto_update_label)
        lay.addWidget(self.background_progress)
        lay.addWidget(self.background_message_label)

        self.capture_background_btn = QPushButton("CAPTURE BACKGROUND / HỌC NỀN")
        self.capture_background_btn.clicked.connect(self.capture_background)
        self.recapture_background_btn = QPushButton("RECAPTURE BACKGROUND / HỌC LẠI NỀN")
        self.recapture_background_btn.clicked.connect(self.capture_background)
        self.reset_auto_background_btn = QPushButton("RESET AUTO BACKGROUND")
        self.reset_auto_background_btn.clicked.connect(self.reset_auto_background)
        lay.addWidget(self.capture_background_btn)
        lay.addWidget(self.recapture_background_btn)
        lay.addWidget(self.reset_auto_background_btn)
        right.addWidget(box)
        self._update_background_controls()

        # -- Ảnh lấp vùng người khi tàng hình --
        box = QGroupBox("Ảnh nền khi tàng hình")
        lay = QVBoxLayout(box)
        self.disappear_bg_label = QLabel("")
        self.disappear_bg_label.setWordWrap(True)
        bg_hint = QLabel("Ảnh sẽ lấp vùng người khi biến mất; ảnh chụp cùng góc camera thường ghép tự nhiên hơn.")
        bg_hint.setWordWrap(True)
        bg_hint.setStyleSheet("color: #8a8a99;")
        choose_bg_btn = QPushButton("🖼  Chọn ảnh nền...")
        choose_bg_btn.clicked.connect(self.choose_disappear_background)
        clear_bg_btn = QPushButton("Dùng nền camera đã học")
        clear_bg_btn.clicked.connect(self.clear_disappear_background)
        lay.addWidget(self.disappear_bg_label)
        lay.addWidget(bg_hint)
        lay.addWidget(choose_bg_btn)
        lay.addWidget(clear_bg_btn)
        right.addWidget(box)
        self._refresh_disappear_background_label()

                # -- Camera ảo (OBS) --
        box = QGroupBox("Camera ảo (OBS)")
        lay = QVBoxLayout(box)
        self.vcam_check = QCheckBox("Xuất hình ra camera ảo")
        self.vcam_check.toggled.connect(self.on_vcam_toggled)
        self.vcam_mirror_check = QCheckBox("Lật gương hình gửi đi")
        self.vcam_mirror_check.setToolTip(
            "Thường nên TẮT: người bên kia sẽ thấy chữ không bị ngược")
        self.vcam_mirror_check.setChecked(self.options["VCAM_MIRROR"])
        self.vcam_mirror_check.toggled.connect(
            lambda checked: self.on_option_toggled("VCAM_MIRROR", checked))
        self.vcam_status = QLabel("")
        self.vcam_status.setWordWrap(True)
        vcam_hint = QLabel('Trong Messenger / Discord / Zoom, hãy chọn camera '
                           '"OBS Virtual Camera".')
        vcam_hint.setWordWrap(True)
        vcam_hint.setStyleSheet("color: #8a8a99;")
        for w in (self.vcam_check, self.vcam_mirror_check, self.vcam_status, vcam_hint):
            lay.addWidget(w)
        right.addWidget(box)
        self._set_vcam_status("Đang tắt", "#8a8a99")

        right.addStretch(1)

        right.addStretch(1)

        exit_btn = QPushButton("Thoát chương trình")
        exit_btn.setObjectName("exit_btn")
        exit_btn.clicked.connect(self.close)
        right.addWidget(exit_btn)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setFixedWidth(390)
        scroll.setWidget(panel)
        root.addWidget(scroll)

        # Nối sự kiện danh sách SAU khi mọi widget đã tạo xong
        self.effect_list.itemChanged.connect(self.on_item_changed)
        self.effect_list.currentRowChanged.connect(self.on_select_effect)
        self.effect_list.setCurrentRow(0)

    # ==================================================================
    # HÀM PHỤ
    # ==================================================================
    @staticmethod
    def _effect_label(name, running=False):
        label = config.EFFECT_LABELS_VI.get(name, name)
        return label + ("   ●" if running else "")

    @staticmethod
    def _gesture_text(name):
        """Liệt kê các cử chỉ kích hoạt hiệu ứng này, lấy từ bảng GESTURE_EFFECTS."""
        gestures = [config.GESTURE_LABELS_VI.get(g, g)
                    for g, effects in config.GESTURE_EFFECTS.items() if name in effects]
        return ", ".join(gestures) if gestures else "(chưa gắn cử chỉ nào)"

    def send(self, *command):
        """Gửi lệnh sang luồng video (bỏ qua nếu camera đang tắt)."""
        if self.worker is not None:
            self.worker.send(*command)

    # ==================================================================
    # SỰ KIỆN: DANH SÁCH VÀ THANH TRƯỢT
    # ==================================================================
    def on_item_changed(self, item):
        """Người dùng tích/bỏ tích một hiệu ứng."""
        name = item.data(Qt.ItemDataRole.UserRole)
        enabled = item.checkState() == Qt.CheckState.Checked
        self.state[name]["enabled"] = enabled
        self.send("effect", name, "enabled", enabled)

    def on_select_effect(self, row):
        """Người dùng bấm chọn một dòng: cập nhật các thanh trượt theo hiệu ứng đó."""
        item = self.effect_list.item(row)
        if item is None:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        self.selected = name
        s = self.state[name]

        self.sel_name_label.setText(config.EFFECT_LABELS_VI.get(name, name))
        self.sel_gesture_label.setText("Kích hoạt bằng: " + self._gesture_text(name))
        self.duration_title.setText("Thời gian chuyển cảnh" if name == "disappear"
                                    else "Thời gian chạy")

        # blockSignals: đặt giá trị mà không làm thanh trượt phát lệnh ngược lại
        for slider, value in ((self.intensity_slider, round(s["intensity"] * 100)),
                              (self.duration_slider, round(s["duration"] * 10))):
            slider.blockSignals(True)
            slider.setValue(int(value))
            slider.blockSignals(False)
        self.intensity_text.setText(f"Độ mạnh: {s['intensity']:.2f}")
        self.duration_text.setText(f"{s['duration']:.1f} giây")

    def on_intensity_changed(self, value):
        if self.selected is None:
            return
        v = value / 100.0
        self.state[self.selected]["intensity"] = v
        self.intensity_text.setText(f"Độ mạnh: {v:.2f}")
        self.send("effect", self.selected, "intensity", v)

    def on_duration_changed(self, value):
        if self.selected is None:
            return
        v = value / 10.0
        self.state[self.selected]["duration"] = v
        self.duration_text.setText(f"{v:.1f} giây")
        self.send("effect", self.selected, "duration", v)

    def on_test_clicked(self):
        if self.worker is None:
            QMessageBox.information(self, "Chưa bật camera", "Hãy bật camera trước khi kích hoạt thử.")
            return
        if self.selected is not None:
            self.send("trigger", self.selected)

    def set_background_mode(self, mode):
        target = self.manual_mode_radio if mode == "manual" else self.auto_mode_radio
        if not target.isChecked():
            self.manual_mode_radio.blockSignals(True)
            self.auto_mode_radio.blockSignals(True)
            target.setChecked(True)
            self.manual_mode_radio.blockSignals(False)
            self.auto_mode_radio.blockSignals(False)
        self.options["BACKGROUND_LEARNING_MODE"] = mode
        config.BACKGROUND_LEARNING_MODE = mode
        self._background_status_data.update({
            "background_mode": mode,
            "background_status": "NOT LEARNED" if mode == "manual" else "LEARNING",
            "background_progress": 0.0,
            "background_auto_update": mode == "auto",
            "background_ready": False,
            "background_capturing": False,
            "background_message": "",
        })
        self._update_background_controls()
        self.send("background_mode", mode)

    def capture_background(self):
        if self.worker is None:
            QMessageBox.information(self, "Chưa bật camera", "Hãy bật camera trước khi học nền.")
            return
        if self.options["BACKGROUND_LEARNING_MODE"] != "manual":
            QMessageBox.information(self, "Auto Mode đang bật", "Hãy chuyển sang MANUAL MODE để chụp nền thủ công.")
            return
        self._background_status_data.update({
            "background_status": "LEARNING",
            "background_progress": 0.0,
            "background_capturing": True,
            "background_message": "Hãy ra khỏi khung hình để chụp nền sạch.",
        })
        self._update_background_controls()
        self.send("capture_background")

    def reset_auto_background(self):
        if self.worker is None:
            return
        if self.options["BACKGROUND_LEARNING_MODE"] != "auto":
            return
        self._background_status_data.update({
            "background_status": "LEARNING",
            "background_progress": 0.0,
            "background_ready": False,
            "background_message": "Auto đang học lại nền từ các vùng tĩnh.",
        })
        self._update_background_controls()
        self.send("reset_plate")

    def _update_background_controls(self, status=None):
        if status:
            self._background_status_data.update(status)
        state = self._background_status_data
        mode = state.get("background_mode") or self.options["BACKGROUND_LEARNING_MODE"]
        status_text = state.get("background_status", "NOT LEARNED")
        self.background_status_label.setText(f"Background: {status_text}")
        self.auto_update_label.setText(
            "Auto Update: ON" if state.get("background_auto_update") else "Auto Update: OFF"
        )
        progress = max(0, min(100, int(round(state.get("background_progress", 0.0) * 100))))
        self.background_progress.setValue(progress)
        self.background_message_label.setText(state.get("background_message", ""))

        has_worker = self.worker is not None
        capturing = state.get("background_capturing", False)
        ready = state.get("background_ready", False)
        manual_available = has_worker and mode == "manual" and status_text != "UNAVAILABLE"
        self.capture_background_btn.setEnabled(manual_available and not ready and not capturing)
        self.recapture_background_btn.setEnabled(manual_available and ready and not capturing)
        self.reset_auto_background_btn.setEnabled(has_worker and mode == "auto")

    def _refresh_disappear_background_label(self):
        path = self.options["DISAPPEAR_BACKGROUND_IMAGE_PATH"]
        if path:
            name = path.replace("\\", "/").rsplit("/", 1)[-1]
            self.disappear_bg_label.setText(f"Ảnh đang chọn: {name}")
            self.disappear_bg_label.setToolTip(path)
        else:
            self.disappear_bg_label.setText("Đang dùng nền camera đã học")
            self.disappear_bg_label.setToolTip("")

    def choose_disappear_background(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn ảnh nền để lấp vùng người khi tàng hình",
            "",
            "Ảnh (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if not path:
            return
        if QPixmap(path).isNull():
            QMessageBox.warning(self, "Ảnh nền", "Không đọc được ảnh đã chọn.")
            return

        self.options["DISAPPEAR_BACKGROUND_IMAGE_PATH"] = path
        self._refresh_disappear_background_label()
        self.send("config", "DISAPPEAR_BACKGROUND_IMAGE_PATH", path)

    def clear_disappear_background(self):
        self.options["DISAPPEAR_BACKGROUND_IMAGE_PATH"] = ""
        self._refresh_disappear_background_label()
        self.send("config", "DISAPPEAR_BACKGROUND_IMAGE_PATH", "")

    def on_option_toggled(self, attr, checked):
        self.options[attr] = checked
        self.send("config", attr, checked)

    # ==================================================================
    # CAMERA ẢO
    # ==================================================================
    def _set_vcam_status(self, text, color):
        self.vcam_status.setText(text)
        self.vcam_status.setStyleSheet(f"color: {color}; font-weight: bold;")

    def on_vcam_toggled(self, checked):
        """Người dùng tích/bỏ tích 'Xuất hình ra camera ảo'."""
        if self.worker is None:
            if checked:
                self._set_vcam_status("Sẽ xuất khi bạn bật camera", "#ffd866")
            else:
                self._set_vcam_status("Đang tắt", "#8a8a99")
        elif checked:
            self._set_vcam_status("Đang kết nối...", "#ffd866")
        self.send("vcam", checked)

    def on_vcam_state(self, active, message):
        """Nhận kết quả mở/đóng camera ảo từ luồng video."""
        if active:
            self._set_vcam_status(f"● Đang xuất ra: {message}", "#4cd964")
        elif message:
            # Có lỗi: bỏ tích mà không phát lại lệnh, rồi báo người dùng.
            self.vcam_check.blockSignals(True)
            self.vcam_check.setChecked(False)
            self.vcam_check.blockSignals(False)
            self._set_vcam_status("Lỗi, xem hộp thoại thông báo", "#ff6b6b")
            QMessageBox.warning(self, "Camera ảo", message)
        else:
            self._set_vcam_status("Đang tắt", "#8a8a99")

    # ==================================================================
    # BẬT / TẮT CAMERA
    # ==================================================================
    def toggle_camera(self):
        if self.worker is None:
            self.start_camera()
        else:
            self.stop_camera()

    def start_camera(self):
        worker = VideoWorker()
        worker.frame_ready.connect(self.on_frame)
        worker.status_changed.connect(self.on_status)
        worker.error.connect(self.on_error)
        worker.warning.connect(self.on_warning)
        worker.vcam_state.connect(self.on_vcam_state)
        worker.finished.connect(lambda w=worker: self._on_worker_finished(w))
        self.worker = worker

        # Gửi toàn bộ thiết lập hiện tại cho luồng mới TRƯỚC khi nó chạy
        for name, s in self.state.items():
            for key, value in s.items():
                worker.send("effect", name, key, value)
        for attr, value in self.options.items():
            worker.send("config", attr, value)
        if self.vcam_check.isChecked():
            worker.send("vcam", True)
            self._set_vcam_status("Đang kết nối...", "#ffd866")

        worker.start()
        self._set_camera_button(on=True)
        self.preview.setText("Đang mở camera...")

    def stop_camera(self):
        worker = self.worker
        if worker is None:
            return True
        worker.stop()
        if worker.wait(3000):
            # Signal finished sẽ cập nhật giao diện. Tránh dọn đồng bộ ở đây
            # vì các signal trạng thái cuối từ worker có thể còn đang chờ xử lý.
            return True

        # Không bỏ tham chiếu tới QThread còn đang chạy. Chờ signal finished
        # xử lý phần dọn dẹp khi luồng dừng thật sự.
        self.camera_btn.setEnabled(False)
        self.preview.setText("Đang dừng camera...")
        return False

    def _on_worker_finished(self, worker):
        """Luồng đã dừng (do người dùng tắt, hoặc do lỗi). Có thể được gọi 2 lần nên phải an toàn."""
        if self.worker is not worker:
            return
        worker.wait(1000)
        self.worker = None
        self._last_running = set()
        self._refresh_running_marks(set())
        self._set_camera_button(on=False)
        self.camera_btn.setEnabled(True)
        self.preview.clear()
        self.preview.setText('Camera đang tắt\nBấm "Bật camera" để bắt đầu')
        self.info_label.setText("FPS: --")
        self.hand_label.setText("Số bàn tay: 0")
        self.gesture_label.setText("Chưa có cử chỉ")

        if self.vcam_check.isChecked():
            self._set_vcam_status("Sẽ xuất khi bạn bật camera", "#ffd866")
        else:
            self._set_vcam_status("Đang tắt", "#8a8a99")

        mode = self.options["BACKGROUND_LEARNING_MODE"]
        self._background_status_data.update({
            "background_mode": mode,
            "background_status": "NOT LEARNED" if mode == "manual" else "LEARNING",
            "background_progress": 0.0,
            "background_auto_update": mode == "auto",
            "background_ready": False,
            "background_capturing": False,
            "background_message": "",
        })
        self._update_background_controls()

        if self._close_when_worker_stops:
            self._close_when_worker_stops = False
            self.close()

    def _set_camera_button(self, on):
        self.camera_btn.setText("■  Tắt camera" if on else "▶  Bật camera")
        self.camera_btn.setObjectName("camera_off" if on else "camera_on")
        # Báo Qt áp dụng lại stylesheet vì objectName đổi
        self.camera_btn.style().unpolish(self.camera_btn)
        self.camera_btn.style().polish(self.camera_btn)

    # ==================================================================
    # NHẬN DỮ LIỆU TỪ LUỒNG VIDEO
    # ==================================================================
    def on_frame(self, image):
        pix = QPixmap.fromImage(image).scaled(
            self.preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self.preview.setPixmap(pix)
        if self.worker is not None:
            self.worker.display_done()         # Báo luồng nền: đã vẽ xong, gửi khung tiếp được

    def on_status(self, st):
        self._update_background_controls(st)
        text = f"FPS: {st['fps']:.1f}"
        if st["coverage"] is not None:
            text += f"     |     Nền đã học: {st['coverage']:.0%}"
        self.info_label.setText(text)

        self.hand_label.setText(f"Số bàn tay: {st['hands']}")
        if st["gestures"]:
            lines = [f"{HAND_KEY_VI.get(k, k)}: {config.GESTURE_LABELS_VI.get(g, g)}"
                     for k, g in st["gestures"].items()]
            self.gesture_label.setText("\n".join(lines))
        else:
            self.gesture_label.setText("Chưa có cử chỉ")

        running = set(st["running"])
        if running != self._last_running:      # Chỉ cập nhật khi có thay đổi, tránh chớp
            self._last_running = running
            self._refresh_running_marks(running)

    def _refresh_running_marks(self, running):
        """Thêm dấu ● sau tên các hiệu ứng đang chạy."""
        self.effect_list.blockSignals(True)    # Đổi chữ không được tính là "người dùng tích chọn"
        for i in range(self.effect_list.count()):
            item = self.effect_list.item(i)
            name = item.data(Qt.ItemDataRole.UserRole)
            item.setText(self._effect_label(name, name in running))
        self.effect_list.blockSignals(False)

    def on_error(self, message):
        QMessageBox.critical(self, "Lỗi", message)

    def on_warning(self, message):
        QMessageBox.warning(self, "Cảnh báo", message)

    # ==================================================================
    # ĐÓNG CỬA SỔ
    # ==================================================================
    def closeEvent(self, event):
        worker = self.worker
        if worker is not None:
            worker.stop()
            if not worker.wait(3000):
                self._close_when_worker_stops = True
                self.camera_btn.setEnabled(False)
                self.preview.setText("Đang dừng camera...")
                event.ignore()
                return
            self._close_when_worker_stops = False
        event.accept()
