from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, Signal


class MainMenuCalibration(QWidget):

    on_continue = Signal()
    on_back = Signal()
    on_menu_toggle = Signal()

    def __init__(self, is_dark=False):
        super().__init__()
        self.is_dark = is_dark
        self.init_ui()
        self.apply_theme(self.is_dark)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        #Top nav bar with hamburger + brand
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

        #Progress / stepper bar
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
            ("✓", "GUIDE", "done"),
            ("02", "CALIBRATE", "active"),
            ("03", "ZONE", "idle"),
            ("04", "CAMERA", "idle"),
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

        self.meta = QLabel("02 / 04 - CALIBRATION")
        content_layout.addWidget(self.meta)

        self.title = QLabel("Set hand distance")
        content_layout.addWidget(self.title)

        self.desc = QLabel("Hold your dominant hand in front of camera, palm forward. Move until indicator reads OPTIMAL.")
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

        self.distance_panel = QWidget()
        distance_layout = QVBoxLayout(self.distance_panel)
        distance_layout.setContentsMargins(0, 0, 0, 0)
        distance_layout.setSpacing(0)
        self.distance_header = QWidget()
        self.distance_header.setFixedHeight(40)
        distance_header_layout = QHBoxLayout(self.distance_header)
        distance_header_layout.setContentsMargins(12, 0, 12, 0)
        self.distance_title = QLabel("B   DISTANCE")
        distance_header_layout.addWidget(self.distance_title)
        distance_layout.addWidget(self.distance_header)
        self.distance_header_line = QWidget()
        self.distance_header_line.setFixedHeight(1)
        distance_layout.addWidget(self.distance_header_line)

        distance_body = QWidget()
        distance_body_layout = QVBoxLayout(distance_body)
        distance_body_layout.setContentsMargins(12, 10, 12, 12)
        distance_body_layout.setSpacing(8)
        self.distance_bar = QWidget()
        self.distance_bar.setFixedHeight(66)
        gauge_layout = QHBoxLayout(self.distance_bar)
        gauge_layout.setContentsMargins(0, 0, 0, 0)
        gauge_layout.setSpacing(0)
        self.gauge_cells = []
        for cell_index in range(4):
            cell = QWidget()
            self.gauge_cells.append(cell)
            gauge_layout.addWidget(cell)
        self.optimal_lbl = QLabel("OPTIMAL")
        self.optimal_lbl.setAlignment(Qt.AlignCenter)
        self.optimal_lbl.setParent(self.distance_bar)
        self.optimal_lbl.setGeometry(82, 6, 58, 12)
        self.marker_lbl = QLabel("|")
        self.marker_lbl.setAlignment(Qt.AlignCenter)
        self.marker_lbl.setParent(self.distance_bar)
        self.marker_lbl.setGeometry(104, 18, 18, 42)
        self.distance_value = QLabel("39.4cm")
        self.distance_value.setAlignment(Qt.AlignCenter)
        self.distance_axis = QLabel("20cm                                      80cm")
        self.distance_badge = QLabel("* Optimal range")
        distance_body_layout.addWidget(self.distance_bar)
        distance_body_layout.addWidget(self.distance_value)
        distance_body_layout.addWidget(self.distance_axis)
        distance_body_layout.addWidget(self.distance_badge)
        distance_layout.addWidget(distance_body)
        right_col.addWidget(self.distance_panel)

        self.telemetry_panel = QWidget()
        telemetry_layout = QVBoxLayout(self.telemetry_panel)
        telemetry_layout.setContentsMargins(0, 0, 0, 0)
        telemetry_layout.setSpacing(0)
        self.telemetry_header = QWidget()
        self.telemetry_header.setFixedHeight(40)
        telemetry_header_layout = QHBoxLayout(self.telemetry_header)
        telemetry_header_layout.setContentsMargins(12, 0, 12, 0)
        self.telemetry_title = QLabel("C   TELEMETRY")
        telemetry_header_layout.addWidget(self.telemetry_title)
        telemetry_layout.addWidget(self.telemetry_header)
        self.telemetry_header_line = QWidget()
        self.telemetry_header_line.setFixedHeight(1)
        telemetry_layout.addWidget(self.telemetry_header_line)
        telemetry_body = QWidget()
        telemetry_body_layout = QVBoxLayout(telemetry_body)
        telemetry_body_layout.setContentsMargins(12, 12, 12, 12)
        telemetry_body_layout.setSpacing(12)
        self.lighting_lbl = QLabel("LIGHTING                                      GOOD")
        self.background_lbl = QLabel("BACKGROUND                                 CLEAR")
        telemetry_body_layout.addWidget(self.lighting_lbl)
        telemetry_body_layout.addWidget(self.background_lbl)
        telemetry_layout.addWidget(telemetry_body)
        right_col.addWidget(self.telemetry_panel)
        right_col.addStretch()

        self.distance_panel.setFixedWidth(225)
        self.telemetry_panel.setFixedWidth(225)
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
        self.back_btn.clicked.connect(self.on_back.emit)
        footer_layout.addWidget(self.back_btn)

        footer_layout.addStretch()

        self.continue_btn = QPushButton("CONTINUE")
        self.continue_btn.setFixedSize(120, 34)
        self.continue_btn.setCursor(Qt.PointingHandCursor)
        self.continue_btn.clicked.connect(self.on_continue.emit)
        footer_layout.addWidget(self.continue_btn)

        layout.addWidget(self.footer)

    def apply_theme(self, is_dark):
        self.is_dark = is_dark

        if is_dark:
            page_bg = "#0a0a0a"
            panel = "#111111"
            panel2 = "#161616"
            border = "#262626"
            strong = "#3a3a3a"
            text = "#e8e8e8"
            dim = "#9a9a9a"
            muted = "#6b6b6b"
            camera_bg = "#111111"
            primary_bg = "#e8e8e8"
            primary_text = "#111111"
            success = "#00d084"
        else:
            page_bg = "#F4F4F4"
            panel = "#FFFFFF"
            panel2 = "#F4F4F4"
            border = "#D8CEC7"
            strong = "#111111"
            text = "#111111"
            dim = "#7A706C"
            muted = "#B8B0AB"
            camera_bg = "#FFFFFF"
            primary_bg = "#111111"
            primary_text = "#FFFFFF"
            success = "#00A36C"

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
        self.progress_rule.setStyleSheet(f"""
            background-color: {border};
        """)
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
            font-size: 11px;
            font-weight: 800;
            color: {text};
            letter-spacing: 1.5px;
            background: transparent;
            border: none;
        """)
        self.brand_version.setStyleSheet(f"""
            font-size: 8px;
            color: {muted};
            letter-spacing: 1px;
            background: transparent;
            border: none;
        """)

        for num_lbl, text_lbl, state in self.progress_steps_data:
            if state == "done":
                num_lbl.setStyleSheet(f"""
                    background-color: transparent;
                    border: 1px solid {border};
                    color: {dim};
                    font-size: 8px;
                    font-weight: 700;
                """)
                text_lbl.setStyleSheet(f"""
                    color: {dim};
                    font-size: 8px;
                    font-weight: 700;
                    letter-spacing: 1.5px;
                    background: transparent;
                    border: none;
                """)
            elif state == "active":
                num_lbl.setStyleSheet(f"""
                    background-color: {panel};
                    border: 1px solid {strong};
                    color: {strong};
                    font-size: 8px;
                    font-weight: 700;
                """)
                text_lbl.setStyleSheet(f"""
                    color: {text};
                    font-size: 8px;
                    font-weight: 700;
                    letter-spacing: 1.5px;
                    background: transparent;
                    border: none;
                """)
            else:
                num_lbl.setStyleSheet(f"""
                    background-color: transparent;
                    border: 1px solid {border};
                    color: {muted};
                    font-size: 8px;
                    font-weight: 700;
                """)
                text_lbl.setStyleSheet(f"""
                    color: {muted};
                    font-size: 8px;
                    letter-spacing: 1.5px;
                    background: transparent;
                    border: none;
                """)

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
            background-color: {camera_bg};
            color: {muted};
            font-size: 10px;
            letter-spacing: 2px;
            border: 1px solid {border};
        """)

        for side_panel in [self.distance_panel, self.telemetry_panel]:
            side_panel.setStyleSheet(f"background-color: {panel}; border: 1px solid {border};")

        for header in [self.distance_header, self.telemetry_header]:
            header.setStyleSheet(f"background-color: {panel2}; border: none;")

        for line in [self.distance_header_line, self.telemetry_header_line]:
            line.setStyleSheet(f"background-color: {border}; border: none;")

        for label in [self.distance_title, self.telemetry_title]:
            label.setStyleSheet(f"color: {text}; font-size: 9px; font-weight: 700; letter-spacing: 1.4px; border: none;")

        self.distance_bar.setStyleSheet(f"""
            background-color: {panel2};
            border: 1px solid {border};
        """)
        for index, cell in enumerate(self.gauge_cells):
            cell.setStyleSheet(f"""
                background-color: {panel};
                border-right: {'1px solid ' + border if index < len(self.gauge_cells) - 1 else 'none'};
            """)
        self.optimal_lbl.setStyleSheet(f"color: {dim}; font-size: 7px; letter-spacing: 1.2px; border: none;")
        self.marker_lbl.setStyleSheet(f"color: {text}; font-size: 20px; border: none;")
        self.distance_value.setStyleSheet(f"color: {dim}; font-size: 8px; border: none;")
        self.distance_axis.setStyleSheet(f"color: {muted}; font-size: 7px; border: none;")
        self.distance_badge.setStyleSheet(f"color: {success}; font-size: 8px; font-weight: 700; border: 1px solid {success}; padding: 4px 8px;")
        self.lighting_lbl.setStyleSheet(f"color: {success}; font-size: 9px; letter-spacing: 1px; border: none;")
        self.background_lbl.setStyleSheet(f"color: {success}; font-size: 9px; letter-spacing: 1px; border: none;")

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

    def set_frame(self, pixmap):
        self.camera_label.setPixmap(
            pixmap.scaled(
                self.camera_label.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
        )
