from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QPushButton, QHBoxLayout, QComboBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap

class MainMenuCamera(QWidget):
    on_camera_continue = Signal()
    on_camera_back = Signal()
    on_menu_toggle = Signal()
    on_camera_select = Signal(int)

    def __init__(self, is_dark=False):
        super().__init__()
        self.is_dark = is_dark
        self._last_pixmap = None
        self.init_ui()
        self.apply_theme(self.is_dark)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.nav_bar = QWidget()
        self.nav_bar.setObjectName("nav_bar")
        self.nav_bar.setFixedHeight(42)
        nav_layout = QHBoxLayout(self.nav_bar)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)
        self.menu_toggle_btn = QPushButton("☰")
        self.menu_toggle_btn.setFixedSize(36, 42)
        self.menu_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.menu_toggle_btn.clicked.connect(self.on_menu_toggle.emit)
        nav_layout.addWidget(self.menu_toggle_btn)
        self.brand_box = QWidget()
        self.brand_box.setFixedHeight(42)
        brand_layout = QHBoxLayout(self.brand_box)
        brand_layout.setContentsMargins(14, 0, 18, 0)
        brand_layout.setSpacing(10)
        self.brand_title = QLabel("HANDMOUSE")
        self.brand_version = QLabel("v1.0")
        brand_layout.addWidget(self.brand_title)
        brand_layout.addWidget(self.brand_version)
        nav_layout.addWidget(self.brand_box)
        nav_layout.addStretch()
        layout.addWidget(self.nav_bar)

        self.progress_wrap = QWidget()
        self.progress_wrap.setObjectName("progress_wrap")
        self.progress_wrap.setFixedHeight(44)
        progress_layout = QVBoxLayout(self.progress_wrap)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(0)
        progress_layout.setAlignment(Qt.AlignVCenter)
        progress_row = QHBoxLayout()
        progress_row.setContentsMargins(18, 0, 18, 0)
        progress_row.setSpacing(8)
        progress_row.setAlignment(Qt.AlignVCenter)

        self.progress_steps_data = []
        self.progress_lines = []
        for index, (num, label_text, state) in enumerate([
            ("✓",  "GUIDE",     "done"),
            ("02", "CAMERA",    "active"),
            ("03", "CALIBRATE", "idle"),
            ("04", "ZONE",      "idle"),
        ]):
            step_widget = QWidget()
            step_h = QHBoxLayout(step_widget)
            step_h.setContentsMargins(0, 0, 0, 0)
            step_h.setSpacing(6)
            step_h.setAlignment(Qt.AlignVCenter)
            num_lbl = QLabel(num)
            num_lbl.setFixedSize(20, 20)
            num_lbl.setAlignment(Qt.AlignCenter)
            text_lbl = QLabel(label_text)
            step_h.addWidget(num_lbl)
            step_h.addWidget(text_lbl)
            self.progress_steps_data.append((num_lbl, text_lbl, state))
            progress_row.addWidget(step_widget)
            if index < 3:
                line = QWidget()
                line.setFixedSize(28, 1)
                self.progress_lines.append(line)
                progress_row.addWidget(line)

        progress_row.addStretch()
        progress_layout.addLayout(progress_row)
        layout.addWidget(self.progress_wrap)

        self.progress_rule = QWidget()
        self.progress_rule.setFixedHeight(1)
        layout.addWidget(self.progress_rule)

        self.content = QWidget()
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(24, 20, 20, 12)
        content_layout.setSpacing(8)

        self.meta = QLabel("02 / 04 - CAMERA SETUP")
        content_layout.addWidget(self.meta)

        self.title = QLabel("Select Your Camera")
        content_layout.addWidget(self.title)

        self.desc = QLabel("Choose your camera input and verify the preview below.")
        content_layout.addWidget(self.desc)

        content_layout.addSpacing(12)

        cam_row = QHBoxLayout()
        cam_row.setSpacing(10)
        self.cam_label = QLabel("CAMERA INPUT")
        self.cam_combo = QComboBox()
        self.cam_combo.setFixedHeight(30)
        self.cam_combo.setMinimumWidth(190)
        self.cam_combo.currentIndexChanged.connect(self._on_combo_changed)
        cam_row.addWidget(self.cam_label)
        cam_row.addWidget(self.cam_combo)
        cam_row.addStretch()
        content_layout.addLayout(cam_row)

        content_layout.addSpacing(8)

        self.camera_panel = QWidget()
        camera_layout = QVBoxLayout(self.camera_panel)
        camera_layout.setContentsMargins(0, 0, 0, 0)
        camera_layout.setSpacing(0)

        self.camera_header = QWidget()
        self.camera_header.setFixedHeight(40)
        camera_header_layout = QHBoxLayout(self.camera_header)
        camera_header_layout.setContentsMargins(12, 0, 12, 0)
        self.camera_title_lbl = QLabel("A   CAMERA PREVIEW")
        self.camera_status_lbl = QLabel("LIVE")
        camera_header_layout.addWidget(self.camera_title_lbl)
        camera_header_layout.addStretch()
        camera_header_layout.addWidget(self.camera_status_lbl)
        camera_layout.addWidget(self.camera_header)

        self.camera_header_line = QWidget()
        self.camera_header_line.setFixedHeight(1)
        camera_layout.addWidget(self.camera_header_line)

        self.camera_body = QWidget()
        camera_body_layout = QVBoxLayout(self.camera_body)
        camera_body_layout.setContentsMargins(8, 8, 8, 8)
        camera_body_layout.setSpacing(0)
        self.camera_preview = QLabel("CAMERA PREVIEW")
        self.camera_preview.setAlignment(Qt.AlignCenter)
        self.camera_preview.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        camera_body_layout.addWidget(self.camera_preview, stretch=1)
        camera_layout.addWidget(self.camera_body, stretch=1)

        content_layout.addWidget(self.camera_panel, stretch=1)
        layout.addWidget(self.content, stretch=1)

        self.footer = QWidget()
        self.footer.setFixedHeight(58)
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(20, 0, 20, 0)
        self.back_btn = QPushButton("BACK")
        self.back_btn.setFixedHeight(34)
        self.back_btn.setMinimumWidth(76)
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.on_camera_back.emit)
        footer_layout.addWidget(self.back_btn)
        footer_layout.addStretch()
        self.continue_btn = QPushButton("CONTINUE")
        self.continue_btn.setFixedHeight(34)
        self.continue_btn.setMinimumWidth(96)
        self.continue_btn.setCursor(Qt.PointingHandCursor)
        self.continue_btn.clicked.connect(self.on_camera_continue.emit)
        footer_layout.addWidget(self.continue_btn)
        layout.addWidget(self.footer)

    def populate_cameras(self, cameras: list):
        self.cam_combo.blockSignals(True)
        self.cam_combo.clear()
        if not cameras:
            self.cam_combo.addItem("No camera found", -1)
        else:
            for idx in cameras:
                self.cam_combo.addItem(
                    f"Camera {idx}" + (" (Default)" if idx == 0 else ""), idx)
        self.cam_combo.blockSignals(False)

    def get_selected_camera(self) -> int:
        d = self.cam_combo.itemData(self.cam_combo.currentIndex())
        return d if d is not None and d >= 0 else 0

    def set_camera_index(self, cam_idx: int):
        self.cam_combo.blockSignals(True)
        for i in range(self.cam_combo.count()):
            if self.cam_combo.itemData(i) == cam_idx:
                self.cam_combo.setCurrentIndex(i)
                break
        self.cam_combo.blockSignals(False)

    def _on_combo_changed(self, combo_idx: int):
        d = self.cam_combo.itemData(combo_idx)
        if d is not None and d >= 0:
            self._last_pixmap = None
            self.camera_preview.setPixmap(QPixmap())
            self.camera_preview.setText("CAMERA PREVIEW")
            self.on_camera_select.emit(d)

    def set_frame(self, pixmap: QPixmap):
        self._last_pixmap = pixmap
        size = self.camera_preview.size()
        if size.width() > 0 and size.height() > 0:
            self.camera_preview.setText("")
            self.camera_preview.setPixmap(
                pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._last_pixmap:
            self.set_frame(self._last_pixmap)

    def apply_theme(self, is_dark):
        self.is_dark = is_dark

        if is_dark:
            page_bg      = "#0a0a0a"
            panel        = "#111111"
            panel2       = "#161616"
            border       = "#262626"
            strong       = "#3a3a3a"
            text         = "#e8e8e8"
            dim          = "#9a9a9a"
            muted        = "#6b6b6b"
            primary_bg   = "#e8e8e8"
            primary_text = "#111111"
        else:
            page_bg      = "#F4F4F4"
            panel        = "#FFFFFF"
            panel2       = "#F4F4F4"
            border       = "#D8CEC7"
            strong       = "#111111"
            text         = "#111111"
            dim          = "#7A706C"
            muted        = "#B8B0AB"
            primary_bg   = "#111111"
            primary_text = "#FFFFFF"

        self.setStyleSheet(f"background-color: {page_bg};")
        self.nav_bar.setStyleSheet(f"""
            #nav_bar {{
                background-color: {page_bg};
                border-bottom: 1px solid {border};
            }}
        """)
        self.progress_wrap.setStyleSheet(f"""
            #progress_wrap {{
                background-color: {page_bg};
                border-bottom: 1px solid {border};
            }}
        """)
        self.progress_rule.setStyleSheet(f"background-color: {border};")
        self.content.setStyleSheet(f"background-color: {page_bg};")
        self.footer.setStyleSheet(f"background-color: {page_bg}; border-top: 1px solid {border};")

        self.menu_toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {text};
                font-size: 18px;
                font-weight: 800;
                border: none;
                border-radius: 2px;
            }}
            QPushButton:hover {{ background-color: {panel}; }}
        """)
        self.brand_box.setStyleSheet(
            f"background: transparent; border-left: 1px solid {border}; border-right: 1px solid {border};")
        self.brand_title.setStyleSheet(
            f"font-size: 11px; font-weight: 800; color: {text}; letter-spacing: 1.5px; background: transparent; border: none;")
        self.brand_version.setStyleSheet(
            f"font-size: 8px; color: {muted}; letter-spacing: 1px; background: transparent; border: none;")

        for num_lbl, text_lbl, state in self.progress_steps_data:
            if state == "done":
                num_lbl.setStyleSheet(f"background-color: transparent; border: 1px solid {border}; color: {dim}; font-size: 8px; font-weight: 700;")
                text_lbl.setStyleSheet(f"color: {dim}; font-size: 8px; font-weight: 700; letter-spacing: 1.5px; background: transparent; border: none;")
            elif state == "active":
                num_lbl.setStyleSheet(f"background-color: {panel}; border: 1px solid {strong}; color: {strong}; font-size: 8px; font-weight: 700;")
                text_lbl.setStyleSheet(f"color: {text}; font-size: 8px; font-weight: 700; letter-spacing: 1.5px; background: transparent; border: none;")
            else:
                num_lbl.setStyleSheet(f"background-color: transparent; border: 1px solid {border}; color: {muted}; font-size: 8px; font-weight: 700;")
                text_lbl.setStyleSheet(f"color: {muted}; font-size: 8px; letter-spacing: 1.5px; background: transparent; border: none;")

        for line in self.progress_lines:
            line.setStyleSheet(f"background-color: {border};")

        self.meta.setStyleSheet(f"color: {muted}; font-size: 8px; letter-spacing: 1.4px; border: none;")
        self.title.setStyleSheet(f"color: {text}; font-size: 19px; font-weight: 600; border: none;")
        self.desc.setStyleSheet(f"color: {dim}; font-size: 11px; border: none;")
        self.cam_label.setStyleSheet(
            f"color: {muted}; font-size: 8px; font-weight: 700; letter-spacing: 1.4px; background: transparent; border: none;")
        self.cam_combo.setStyleSheet(f"""
            QComboBox {{
                background: {panel}; color: {text};
                border: 1px solid {border};
                border-radius: 2px; padding: 4px 8px; font-size: 10px;
                letter-spacing: 1px;
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox::down-arrow {{
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {dim};
                width: 0; height: 0; margin-right: 6px;
            }}
            QComboBox QAbstractItemView {{
                background: {panel}; color: {text};
                border: 1px solid {border};
                selection-background-color: {panel2};
                selection-color: {text}; outline: none;
            }}
        """)

        self.camera_panel.setStyleSheet(f"background-color: {panel}; border: 1px solid {border};")
        self.camera_header.setStyleSheet(f"background-color: {panel2}; border: none;")
        self.camera_header_line.setStyleSheet(f"background-color: {border}; border: none;")
        self.camera_title_lbl.setStyleSheet(
            f"color: {text}; font-size: 9px; font-weight: 700; letter-spacing: 1.4px; border: none;")
        self.camera_status_lbl.setStyleSheet(
            f"color: {dim}; font-size: 8px; letter-spacing: 1.2px; border: none;")
        self.camera_body.setStyleSheet(f"background-color: {panel}; border: none;")
        self.camera_preview.setStyleSheet(f"""
            background-color: transparent;
            color: {muted};
            font-size: 10px;
            letter-spacing: 2px;
            border: none;
        """)

        self.back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {dim};
                border: 1px solid {border};
                font-size: 8px;
                font-weight: 700;
                letter-spacing: 1.4px;
            }}
            QPushButton:hover {{ background-color: {panel}; }}
        """)
        self.continue_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {primary_bg};
                color: {primary_text};
                border: 1px solid {primary_bg};
                font-size: 8px;
                font-weight: 700;
                letter-spacing: 1.4px;
            }}
            QPushButton:hover {{ background-color: {strong}; }}
        """)
