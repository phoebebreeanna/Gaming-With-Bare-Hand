from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QPushButton, QHBoxLayout
)
from PySide6.QtCore import Qt, Signal

class MainMenuSetup(QWidget):

    on_lets_go = Signal()
    on_menu_toggle = Signal()

    def __init__(self, is_dark=False):
        super().__init__()
        self.is_dark = is_dark
        self.progress_labels = []
        self.progress_lines = []
        self.step_rows = []
        self.step_numbers = []
        self.step_titles = []
        self.step_details = []
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

        self.hamburger_btn = QPushButton("☰")
        self.hamburger_btn.setFixedSize(36, 42)
        self.hamburger_btn.setCursor(Qt.PointingHandCursor)
        self.hamburger_btn.clicked.connect(self.on_menu_toggle.emit)
        nav_layout.addWidget(self.hamburger_btn)

        self.nav_brand = QWidget()
        self.nav_brand.setFixedHeight(42)
        brand_layout = QHBoxLayout(self.nav_brand)
        brand_layout.setContentsMargins(14, 0, 18, 0)
        brand_layout.setSpacing(10)
        self.nav_title = QLabel("HANDMOUSE")
        self.nav_version = QLabel("v1.0")
        brand_layout.addWidget(self.nav_title)
        brand_layout.addWidget(self.nav_version)
        nav_layout.addWidget(self.nav_brand)
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

        progress_steps = [
            ("01", "GUIDE", "active"),
            ("02", "CALIBRATE", "idle"),
            ("03", "ZONE", "idle"),
        ]

        self.progress_steps_data = []

        for index, (num, label_text, state) in enumerate(progress_steps):
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

            if index < len(progress_steps) - 1:
                line = QWidget()
                line.setFixedHeight(1)
                line.setFixedWidth(28)
                self.progress_lines.append(line)
                progress_row.addWidget(line)

        progress_row.addStretch()
        progress_layout.addLayout(progress_row)
        layout.addWidget(self.progress_wrap)

        self.content = QWidget()
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(24, 20, 20, 24)
        content_layout.setSpacing(8)

        self.meta = QLabel("01 / 05 - SETUP GUIDE")
        content_layout.addWidget(self.meta)

        self.title = QLabel("Quick setup - 4 easy steps")
        content_layout.addWidget(self.title)

        self.desc = QLabel("We'll guide you through a quick setup")
        content_layout.addWidget(self.desc)

        self.steps_card = QWidget()
        self.steps_card.setFixedHeight(296)
        steps_layout = QVBoxLayout(self.steps_card)
        steps_layout.setContentsMargins(0, 0, 0, 0)
        steps_layout.setSpacing(0)

        steps = [
            (
                "Distance Check",
                "Hold your hand at arm's length until the bar turns green - confirms optimal tracking depth",
            ),
            (
                "Zone Setup",
                "Pick Small, Medium or Large tracking zone - controls cursor sensitivity across your screen",
            ),
            (
                "Camera Setup",
                "Confirm your camera input and check resolution, frame rate and permissions",
            ),
            (
                "Start Tracking",
                "Control your screen with hand gestures",
            ),
        ]

        for index, (title_text, detail_text) in enumerate(steps, start=1):
            row = QWidget()
            row.setFixedHeight(60)
            row.setProperty("has_bottom_border", index < len(steps))

            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(16, 10, 16, 8)
            row_layout.setSpacing(14)
            row_layout.setAlignment(Qt.AlignTop)

            number = QLabel(str(index))
            number.setFixedSize(22, 22)
            number.setAlignment(Qt.AlignCenter)
            self.step_numbers.append(number)
            row_layout.addWidget(number, alignment=Qt.AlignTop)

            copy = QVBoxLayout()
            copy.setContentsMargins(0, 0, 0, 0)
            copy.setSpacing(7)

            step_title = QLabel(title_text)
            self.step_titles.append(step_title)

            step_detail = QLabel(detail_text)
            self.step_details.append(step_detail)

            copy.addWidget(step_title)
            copy.addWidget(step_detail)
            row_layout.addLayout(copy, stretch=1)

            self.step_rows.append(row)
            steps_layout.addWidget(row)

        steps_layout.addStretch()

        content_layout.addSpacing(12)
        content_layout.addWidget(self.steps_card)
        content_layout.addStretch()
        layout.addWidget(self.content, stretch=1)

        self.footer = QWidget()
        self.footer.setFixedHeight(58)

        bottom = QHBoxLayout(self.footer)
        bottom.setContentsMargins(20, 0, 20, 0)

        bottom.addStretch()

        self.go_btn = QPushButton("LET'S GO")
        self.go_btn.setFixedSize(112, 34)
        self.go_btn.setCursor(Qt.PointingHandCursor)
        self.go_btn.clicked.connect(self.on_lets_go.emit)
        bottom.addWidget(self.go_btn)

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
            button_bg = "#e8e8e8"
            button_text = "#111111"
            button_hover = "#ffffff"
        else:
            page_bg = "#F4F4F4"
            panel = "#FFFFFF"
            border = "#D8CEC7"
            strong = "#111111"
            text = "#111111"
            dim = "#7A706C"
            muted = "#B8B0AB"
            button_bg = "#111111"
            button_text = "#FFFFFF"
            button_hover = "#2A2A2A"

        self.setStyleSheet(f"background-color: {page_bg};")

        self.nav_bar.setStyleSheet(f"""
            #nav_bar {{
                background-color: {page_bg};
                border-bottom: 1px solid {border};
            }}
        """)
        self.hamburger_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {strong};
                font-size: 18px;
                border: none;
                border-radius: 2px;
            }}
            QPushButton:hover {{
                background-color: {"#161616" if is_dark else "#EDE5DF"};
            }}
        """)
        self.nav_brand.setStyleSheet(f"background: transparent; border-left: 1px solid {border}; border-right: none;")
        self.nav_title.setStyleSheet(f"font-size: 11px; font-weight: 800; color: {text}; letter-spacing: 1.5px; background: transparent; border: none;")
        self.nav_version.setStyleSheet(f"font-size: 8px; color: {dim}; letter-spacing: 1px; background: transparent; border: none;")

        self.progress_wrap.setStyleSheet(f"""
            #progress_wrap {{
                background-color: {page_bg};
                border-bottom: 1px solid {border};
            }}
        """)
        self.content.setStyleSheet(f"background-color: {page_bg};")
        self.footer.setStyleSheet(f"""
            background-color: {page_bg};
            border-top: 1px solid {border};
        """)

        for num_lbl, text_lbl, state in self.progress_steps_data:
            if state == "active":
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

        self.meta.setStyleSheet(f"""
            color: {muted};
            font-size: 8px;
            letter-spacing: 1.4px;
            background: transparent;
            border: none;
        """)
        self.title.setStyleSheet(f"""
            font-size: 19px;
            font-weight: 600;
            color: {text};
            background: transparent;
            border: none;
        """)
        self.desc.setStyleSheet(f"""
            font-size: 11px;
            color: {dim};
            background: transparent;
            border: none;
        """)
        self.steps_card.setStyleSheet(f"""
            background-color: {panel};
            border: 1px solid {border};
        """)

        for row in self.step_rows:
            if row.property("has_bottom_border"):
                row.setStyleSheet(f"background: transparent; border-bottom: 1px solid {border};")
            else:
                row.setStyleSheet("background: transparent; border: none;")

        for number in self.step_numbers:
            number.setStyleSheet(f"""
                color: {text};
                border: 1px solid {strong};
                background: transparent;
                font-size: 9px;
                font-weight: 700;
            """)

        for step_title in self.step_titles:
            step_title.setStyleSheet(f"""
                color: {text};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
                background: transparent;
                border: none;
            """)

        for step_detail in self.step_details:
            step_detail.setStyleSheet(f"""
                color: {dim};
                font-size: 10px;
                background: transparent;
                border: none;
            """)

        self.go_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {button_bg};
                color: {button_text};
                border: 1px solid {button_bg};
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 1.4px;
            }}
            QPushButton:hover {{
                background-color: {button_hover};
            }}
        """)

