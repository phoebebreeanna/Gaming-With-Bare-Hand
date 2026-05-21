from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QPushButton, QHBoxLayout
)
from PySide6.QtCore import Qt, Signal

class MainMenuCamera(QWidget):
    on_camera_continue = Signal()
    on_camera_back = Signal()
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
            ("✓", "CALIBRATE", "done"),
            ("✓", "ZONE", "done"),
            ("04", "CAMERA", "active"),
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

        #Content area
        self.content = QWidget()
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(24, 20, 20, 12)
        content_layout.setSpacing(8)

        self.meta = QLabel("04 / 04 - CAMERA")
        content_layout.addWidget(self.meta)

        self.title = QLabel("Camera Setup")
        content_layout.addWidget(self.title)

        self.desc = QLabel("Content coming soon.")
        content_layout.addWidget(self.desc)

        content_layout.addStretch()
        layout.addWidget(self.content, stretch=1)

        self.footer = QWidget()
        self.footer.setFixedHeight(58)
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(20, 0, 20, 0)

        self.back_btn = QPushButton("BACK")
        self.back_btn.setFixedSize(92, 34)
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.on_camera_back.emit)
        footer_layout.addWidget(self.back_btn)

        footer_layout.addStretch()

        self.continue_btn = QPushButton("START TRACKING")
        self.continue_btn.setFixedSize(120, 34)
        self.continue_btn.setCursor(Qt.PointingHandCursor)
        self.continue_btn.clicked.connect(self.on_camera_continue.emit)
        footer_layout.addWidget(self.continue_btn)

        layout.addWidget(self.footer)

    def apply_theme(self, is_dark):
        self.is_dark = is_dark

        if is_dark:
            page_bg = "#0a0a0a"
            panel = "#111111"
            border = "#262626"
            strong = "#3a3a3a"
            text = "#e8e8e8"
            dim = "#9a9a9a"
            muted = "#6b6b6b"
            primary_bg = "#e8e8e8"
            primary_text = "#111111"
        else:
            page_bg = "#F4F4F4"
            panel = "#FFFFFF"
            border = "#D8CEC7"
            strong = "#111111"
            text = "#111111"
            dim = "#7A706C"
            muted = "#B8B0AB"
            primary_bg = "#111111"
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