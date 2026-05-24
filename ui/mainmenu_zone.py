from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QPushButton, QHBoxLayout, QSizePolicy, QProgressBar
)
from PySide6.QtCore import Qt, Signal

class MainMenuZone(QWidget):
    on_zone_continue = Signal()
    on_zone_back = Signal()
    on_menu_toggle = Signal()

    def __init__(self, is_dark=False):
        super().__init__()
        self.is_dark = is_dark
        self.selected_zone = 'medium'
        self._pending_zone = None
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
        _progress_steps = [
            ("✓",  "GUIDE",     "done"),
            ("✓",  "CAMERA",    "done"),
            ("✓",  "CALIBRATE", "done"),
            ("04", "ZONE",      "active"),
        ]
        for index, (num, label_text, state) in enumerate(_progress_steps):
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
            if index < len(_progress_steps) - 1:
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

        self.meta = QLabel("04 / 04 - ZONE")
        content_layout.addWidget(self.meta)
        self.title = QLabel("Zone Setup")
        content_layout.addWidget(self.title)
        self.desc = QLabel("Select the control zone size for hand tracking.")
        content_layout.addWidget(self.desc)

        panel_row = QHBoxLayout()
        panel_row.setSpacing(14)

        self.camera_panel = QWidget()
        camera_layout = QVBoxLayout(self.camera_panel)
        camera_layout.setContentsMargins(0, 0, 0, 0)
        camera_layout.setSpacing(0)

        self.camera_header = QWidget()
        self.camera_header.setFixedHeight(40)
        camera_header_layout = QHBoxLayout(self.camera_header)
        camera_header_layout.setContentsMargins(12, 0, 12, 0)
        self.camera_title = QLabel("A   CAMERA FEED")
        self.tracking_lbl = QLabel("REC - TRACKING")
        camera_header_layout.addWidget(self.camera_title)
        camera_header_layout.addStretch()
        camera_header_layout.addWidget(self.tracking_lbl)
        camera_layout.addWidget(self.camera_header)

        self.camera_header_line = QWidget()
        self.camera_header_line.setFixedHeight(1)
        camera_layout.addWidget(self.camera_header_line)

        self.camera_body = QWidget()
        camera_body_layout = QVBoxLayout(self.camera_body)
        camera_body_layout.setContentsMargins(8, 8, 8, 8)
        camera_body_layout.setSpacing(0)
        self.camera_label = QLabel("LIVE CAMERA FEED")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        camera_body_layout.addWidget(self.camera_label, stretch=1)
        camera_layout.addWidget(self.camera_body, stretch=1)
        panel_row.addWidget(self.camera_panel, stretch=1)

        right_col = QVBoxLayout()
        right_col.setSpacing(10)
        right_col.setContentsMargins(0, 0, 0, 0)

        self.zone_panel = QWidget()
        zone_layout = QVBoxLayout(self.zone_panel)
        zone_layout.setContentsMargins(0, 0, 0, 0)
        zone_layout.setSpacing(0)

        self.zone_header = QWidget()
        self.zone_header.setFixedHeight(40)
        zone_header_layout = QHBoxLayout(self.zone_header)
        zone_header_layout.setContentsMargins(12, 0, 12, 0)
        self.zone_title = QLabel("B   ZONE SIZE")
        zone_header_layout.addWidget(self.zone_title)
        zone_layout.addWidget(self.zone_header)

        self.zone_header_line = QWidget()
        self.zone_header_line.setFixedHeight(1)
        zone_layout.addWidget(self.zone_header_line)

        zone_body = QWidget()
        zone_body_layout = QVBoxLayout(zone_body)
        zone_body_layout.setContentsMargins(12, 12, 12, 12)
        zone_body_layout.setSpacing(6)

        self.zone_buttons = {}
        zone_options = [
            ('small',  'SMALL',  '1 finger - precise area'),
            ('medium', 'MEDIUM', '2 fingers - balanced'),
            ('large',  'LARGE',  '3 fingers - wide area'),
        ]
        for name, label, hint in zone_options:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setText(f"{label}\n{hint}")
            btn.setFixedHeight(48)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, n=name: self._select_zone(n))
            self.zone_buttons[name] = btn
            zone_body_layout.addWidget(btn)

        zone_body_layout.addSpacing(6)

        self.gesture_hint = QLabel("OR HOLD FINGERS IN VIEW")
        zone_body_layout.addWidget(self.gesture_hint)

        self.gesture_progress_label = QLabel("DETECTING...")
        zone_body_layout.addWidget(self.gesture_progress_label)

        self.gesture_progress = QProgressBar()
        self.gesture_progress.setRange(0, 100)
        self.gesture_progress.setValue(0)
        self.gesture_progress.setFixedHeight(5)
        self.gesture_progress.setTextVisible(False)
        zone_body_layout.addWidget(self.gesture_progress)

        zone_body_layout.addStretch()
        zone_layout.addWidget(zone_body)
        right_col.addWidget(self.zone_panel)
        right_col.addStretch()

        self.zone_panel.setFixedWidth(225)
        panel_row.addLayout(right_col, stretch=0)
        content_layout.addLayout(panel_row, stretch=1)
        layout.addWidget(self.content, stretch=1)

        self.footer = QWidget()
        self.footer.setFixedHeight(58)
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(20, 0, 20, 0)
        self.back_btn = QPushButton("BACK")
        self.back_btn.setFixedSize(92, 34)
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.on_zone_back.emit)
        footer_layout.addWidget(self.back_btn)
        footer_layout.addStretch()
        self.continue_btn = QPushButton("START TRACKING")
        self.continue_btn.setFixedSize(140, 34)
        self.continue_btn.setCursor(Qt.PointingHandCursor)
        self.continue_btn.clicked.connect(self.on_zone_continue.emit)
        footer_layout.addWidget(self.continue_btn)
        layout.addWidget(self.footer)

    def _select_zone(self, name):
        self.selected_zone = name
        self._pending_zone = None
        for zone_name, btn in self.zone_buttons.items():
            btn.setChecked(zone_name == name)
        self._restyle_zone_buttons()

    def _restyle_zone_buttons(self):
        if self.is_dark:
            normal_bg     = "#111111"
            normal_border = "#262626"
            normal_text   = "#9a9a9a"
            sel_bg        = "#1a2a1a"
            sel_border    = "#00d084"
            sel_text      = "#00d084"
            pend_bg       = "#2a2010"
            pend_border   = "#d08400"
            pend_text     = "#d08400"
            hover_bg      = "#161616"
        else:
            normal_bg     = "#FFFFFF"
            normal_border = "#D8CEC7"
            normal_text   = "#7A706C"
            sel_bg        = "#F0FFF8"
            sel_border    = "#00A36C"
            sel_text      = "#00A36C"
            pend_bg       = "#FFFBEE"
            pend_border   = "#B86A00"
            pend_text     = "#B86A00"
            hover_bg      = "#F4F4F4"

        for name, btn in self.zone_buttons.items():
            is_selected = btn.isChecked()
            is_pending  = (name == self._pending_zone) and not is_selected
            if is_selected:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {sel_bg};
                        color: {sel_text};
                        border: 1px solid {sel_border};
                        font-size: 9px;
                        font-weight: 700;
                        letter-spacing: 1.2px;
                        text-align: left;
                        padding: 8px 12px;
                    }}
                """)
            elif is_pending:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {pend_bg};
                        color: {pend_text};
                        border: 1px solid {pend_border};
                        font-size: 9px;
                        font-weight: 700;
                        letter-spacing: 1.2px;
                        text-align: left;
                        padding: 8px 12px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {normal_bg};
                        color: {normal_text};
                        border: 1px solid {normal_border};
                        font-size: 9px;
                        letter-spacing: 1.2px;
                        text-align: left;
                        padding: 8px 12px;
                    }}
                    QPushButton:hover {{ background-color: {hover_bg}; }}
                """)

    def set_frame(self, pixmap):
        self.camera_label.setPixmap(
            pixmap.scaled(
                self.camera_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )

    def set_zone_progress(self, pending_zone, frac: float):
        if pending_zone is None or frac <= 0:
            self._pending_zone = None
            self.gesture_progress.setValue(0)
            self.gesture_progress_label.setText("DETECTING...")
        else:
            self._pending_zone = pending_zone
            self.gesture_progress.setValue(int(frac * 100))
            self.gesture_progress_label.setText(
                f"HOLD - {pending_zone.upper()} ({int(frac * 100)}%)"
            )
        self._restyle_zone_buttons()

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
            camera_bg    = "#111111"
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
            camera_bg    = "#FFFFFF"
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
        self.brand_box.setStyleSheet(f"background: transparent; border-left: 1px solid {border}; border-right: 1px solid {border};")
        self.brand_title.setStyleSheet(f"""
            font-size: 11px; font-weight: 800; color: {text};
            letter-spacing: 1.5px; background: transparent; border: none;
        """)
        self.brand_version.setStyleSheet(f"""
            font-size: 8px; color: {muted};
            letter-spacing: 1px; background: transparent; border: none;
        """)

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

        self.camera_panel.setStyleSheet(f"background-color: {camera_bg}; border: 1px solid {border};")
        self.camera_header.setStyleSheet(f"background-color: {panel2}; border: none;")
        self.camera_header_line.setStyleSheet(f"background-color: {border}; border: none;")
        self.camera_title.setStyleSheet(f"color: {text}; font-size: 9px; font-weight: 700; letter-spacing: 1.4px; border: none;")
        self.tracking_lbl.setStyleSheet(f"color: {dim}; font-size: 8px; letter-spacing: 1.2px; border: none;")
        self.camera_body.setStyleSheet(f"background-color: {camera_bg}; border: none;")
        self.camera_label.setStyleSheet(f"""
            background-color: #000000;
            color: {muted};
            font-size: 10px;
            letter-spacing: 2px;
            border: 1px solid {border};
        """)

        self.zone_panel.setStyleSheet(f"background-color: {panel}; border: 1px solid {border};")
        self.zone_header.setStyleSheet(f"background-color: {panel2}; border: none;")
        self.zone_header_line.setStyleSheet(f"background-color: {border}; border: none;")
        self.zone_title.setStyleSheet(f"color: {text}; font-size: 9px; font-weight: 700; letter-spacing: 1.4px; border: none;")

        self.gesture_hint.setStyleSheet(f"color: {muted}; font-size: 7px; letter-spacing: 1.2px; border: none;")
        self.gesture_progress_label.setStyleSheet(f"color: {dim}; font-size: 7px; letter-spacing: 1.2px; border: none;")
        success = "#00d084" if is_dark else "#00A36C"
        self.gesture_progress.setStyleSheet(f"""
            QProgressBar {{ background-color: {border}; border: none; }}
            QProgressBar::chunk {{ background-color: {success}; }}
        """)

        self._restyle_zone_buttons()

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

