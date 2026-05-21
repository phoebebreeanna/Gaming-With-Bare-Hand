from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap


class GestureGuide(QWidget):

    on_menu_toggle = Signal()

    def __init__(self):
        super().__init__()
        self.is_dark = False
        self.current_mode = "Mouse"

        self.mode_sections = {
            "Mouse": [
                {
                    "label": "01  ·  MOUSE MODE",
                    "gestures": [
                        {"n": "01", "name": "Point - Move Cursor", "desc": "Raise your index finger to move the cursor across the screen", "tag": "ACTIVE IN MOUSE MODE"},
                        {"n": "02", "name": "Quick Pinch - Left Click", "desc": "Thumb + Middle pinch, held under 0.5s", "tag": "QUICK ACTION"},
                        {"n": "03", "name": "Hold Pinch - Drag", "desc": "Thumb + Middle pinch, held over 0.5s", "tag": "HOLD 0.5S"},
                        {"n": "04", "name": "Ring Pinch - Right Click", "desc": "Thumb + Ring finger pinch", "tag": "QUICK ACTION"},
                        {"img": "pic/three_finger.png", "n": "05", "name": "Three Fingers - Scroll Up", "desc": "Index + Middle + Ring fingers raised up", "tag": "ACTIVE"},
                        {"n": "06", "name": "Fist - Scroll Down", "desc": "All fingers clenched into a fist", "tag": "ACTIVE"},
                    ],
                },
            ],
            "Subway Surfers": [
                {
                    "label": "02  ·  SUBWAY SURFERS",
                    "gestures": [
                        {"n": "01", "name": "Wrist Up - Jump", "desc": "Lean wrist upward to jump or swipe up", "tag": "ACTIVE"},
                        {"n": "02", "name": "Wrist Down - Slide", "desc": "Lean wrist downward to slide or swipe down", "tag": "ACTIVE"},
                        {"n": "03", "name": "Wrist Left - Swipe Left", "desc": "Lean wrist to the left", "tag": "ACTIVE"},
                        {"n": "04", "name": "Wrist Right - Swipe Right", "desc": "Lean wrist to the right", "tag": "ACTIVE"},
                        {"n": "05", "name": "Open Hand - Space Bar", "desc": "Open palm facing camera for space bar / jump", "tag": "ACTIVE"},
                        {"n": "06", "name": "Fist - Idle", "desc": "Relaxed or closed hand", "tag": "NEUTRAL"},
                    ],
                },
            ],
            "Racing": [
                {
                    "label": "03  ·  RACING",
                    "gestures": [
                        {"n": "01", "name": "Thumb Up - Accelerate", "desc": "Right thumb up gesture to accelerate", "tag": "ACTIVE"},
                        {"n": "02", "name": "Thumb Down - Brake", "desc": "Left thumb up gesture to brake", "tag": "ACTIVE"},
                        {"n": "03", "name": "Tilt Left - Steer Left", "desc": "Tilt both hands to the left", "tag": "ACTIVE"},
                        {"n": "04", "name": "Tilt Right - Steer Right", "desc": "Tilt both hands to the right", "tag": "ACTIVE"},
                        {"n": "05", "name": "Level Hands - Go Straight", "desc": "Both hands kept level", "tag": "ACTIVE"},
                    ],
                },
            ],
        }

        self.section_labels = []
        self.section_lines = []
        self.gesture_cards = []
        self.image_placeholders = []
        self.num_labels = []
        self.name_labels = []
        self.desc_labels = []
        self.tag_labels = []

        self.init_ui()
        self.apply_theme(self.is_dark)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = QWidget()
        self.header.setFixedHeight(58)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(24, 0, 14, 0)
        header_layout.setSpacing(14)

        self.menu_btn = QPushButton("☰")
        self.menu_btn.setFixedSize(36, 42)
        self.menu_btn.setCursor(Qt.PointingHandCursor)
        self.menu_btn.clicked.connect(self.on_menu_toggle.emit)
        header_layout.addWidget(self.menu_btn)

        self.title_lbl = QLabel("Gesture Guide")
        header_layout.addWidget(self.title_lbl)
        header_layout.addStretch()

        self.mode_badge = QPushButton("MOUSE MODE")
        self.mode_badge.setFixedHeight(28)
        self.mode_badge.setCursor(Qt.PointingHandCursor)
        self.mode_badge.clicked.connect(self._cycle_mode)
        header_layout.addWidget(self.mode_badge)

        layout.addWidget(self.header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(24, 16, 24, 16)
        self.scroll_layout.setSpacing(0)
        self.scroll.setWidget(self.scroll_content)

        layout.addWidget(self.scroll, stretch=1)

        self.footer = QWidget()
        self.footer.setFixedHeight(58)
        layout.addWidget(self.footer)

        self._build_content(self.current_mode)

    def _build_content(self, mode):
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.section_labels.clear()
        self.section_lines.clear()
        self.gesture_cards.clear()
        self.image_placeholders.clear()
        self.num_labels.clear()
        self.name_labels.clear()
        self.desc_labels.clear()
        self.tag_labels.clear()

        total = 0
        for section in self.mode_sections[mode]:
            lbl = QLabel(section["label"])
            self.section_labels.append(lbl)
            self.scroll_layout.addWidget(lbl)

            line = QWidget()
            line.setFixedHeight(1)
            self.section_lines.append(line)
            self.scroll_layout.addWidget(line)
            self.scroll_layout.addSpacing(8)

            for g in section["gestures"]:
                total += 1
                card = self._make_card(g)
                self.gesture_cards.append(card)
                self.scroll_layout.addWidget(card)
                self.scroll_layout.addSpacing(8)

            self.scroll_layout.addSpacing(8)

        self.scroll_layout.addStretch()

        if mode == "Subway Surfers":
            self.mode_badge.setText("SUBWAY MODE")
        else:
            self.mode_badge.setText(f"{mode.upper()} MODE")

        if hasattr(self, "_theme_ready"):
            self.apply_theme(self.is_dark)

    def _make_card(self, g):
        card = QWidget()
        card.setFixedHeight(100)
        hl = QHBoxLayout(card)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        img = QLabel()
        img.setFixedSize(130, 100)
        img.setAlignment(Qt.AlignCenter)
        if g.get("img"):
            pix = QPixmap(g["img"]).scaled(
                130, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            img.setPixmap(pix)
        else:
            img.setText("IMAGE")
        self.image_placeholders.append(img)
        hl.addWidget(img)

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(18, 10, 18, 10)
        cl.setSpacing(3)

        num_lbl = QLabel(f"GESTURE  ·  {g['n']}")
        self.num_labels.append(num_lbl)
        cl.addWidget(num_lbl)

        name_lbl = QLabel(g["name"])
        self.name_labels.append(name_lbl)
        cl.addWidget(name_lbl)

        desc_lbl = QLabel(g["desc"])
        desc_lbl.setWordWrap(True)
        self.desc_labels.append(desc_lbl)
        cl.addWidget(desc_lbl)

        cl.addSpacing(4)

        tag_lbl = QLabel(f"●  {g['tag']}")
        tag_lbl.setFixedHeight(20)
        self.tag_labels.append(tag_lbl)
        tag_row = QHBoxLayout()
        tag_row.setContentsMargins(0, 0, 0, 0)
        tag_row.setSpacing(0)
        tag_row.addWidget(tag_lbl)
        tag_row.addStretch()
        cl.addLayout(tag_row)

        hl.addWidget(content, stretch=1)
        return card

    def _cycle_mode(self):
        modes = list(self.mode_sections.keys())
        idx = modes.index(self.current_mode)
        self.switch_mode(modes[(idx + 1) % len(modes)])

    def switch_mode(self, mode):
        if mode in self.mode_sections:
            self.current_mode = mode
            self._build_content(mode)

    def apply_theme(self, is_dark: bool):
        self.is_dark = is_dark
        self._theme_ready = True

        if is_dark:
            page_bg = "#0a0a0a"
            panel  = "#111111"
            border = "#262626"
            text   = "#e8e8e8"
            dim    = "#9a9a9a"
            muted  = "#6b6b6b"
        else:
            page_bg = "#F4F4F4"
            panel  = "#FFFFFF"
            border = "#D8CEC7"
            text   = "#111111"
            dim    = "#6F655F"
            muted  = "#B8B0AB"

        self.setStyleSheet(f"background-color: {page_bg};")
        self.header.setStyleSheet(f"background-color: {page_bg}; border-bottom: 1px solid {border};")
        self.menu_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {text};
                font-size: 18px;
                border: none;
                border-radius: 2px;
            }}
            QPushButton:hover {{ background-color: {"#161616" if is_dark else "#EDE5DF"}; }}
        """)
        self.title_lbl.setStyleSheet(f"color: {text}; font-size: 22px; font-weight: 800; background: transparent; border: none;")
        self.mode_badge.setStyleSheet(f"""
            QPushButton {{
                color: {dim};
                border: 1px solid {border};
                font-size: 8px;
                font-weight: 700;
                letter-spacing: 1.5px;
                background: transparent;
                padding: 0 8px;
            }}
            QPushButton:hover {{ background-color: {"#161616" if is_dark else "#EDE5DF"}; }}
        """)

        self.scroll.setStyleSheet(f"""
            QScrollArea {{ background-color: {page_bg}; border: none; }}
            QScrollBar:vertical {{
                width: 4px;
                background: transparent;
                border: none;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {muted};
                border-radius: 2px;
                min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {dim}; }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{ background: none; }}
        """)
        self.scroll_content.setStyleSheet(f"background-color: {page_bg};")

        self.footer.setStyleSheet(f"background-color: {page_bg}; border-top: 1px solid {border};")

        for lbl in self.section_labels:
            lbl.setStyleSheet(f"color: {muted}; font-size: 8px; letter-spacing: 1.4px; background: transparent; border: none;")

        for line in self.section_lines:
            line.setStyleSheet(f"background-color: {border};")

        for card in self.gesture_cards:
            card.setStyleSheet(f"background-color: {panel}; border: 1px solid {border};")

        for img in self.image_placeholders:
            img.setStyleSheet(f"color: {muted}; font-size: 8px; letter-spacing: 1.2px; border: 1px dashed {border}; background: transparent; margin: 12px;")

        for lbl in self.num_labels:
            lbl.setStyleSheet(f"color: {muted}; font-size: 8px; letter-spacing: 1.2px; background: transparent; border: none;")

        for lbl in self.name_labels:
            lbl.setStyleSheet(f"color: {text}; font-size: 13px; font-weight: 700; background: transparent; border: none;")

        for lbl in self.desc_labels:
            lbl.setStyleSheet(f"color: {dim}; font-size: 10px; background: transparent; border: none;")

        for lbl in self.tag_labels:
            lbl.setStyleSheet(f"color: {dim}; font-size: 8px; letter-spacing: 1.2px; background: transparent; border: 1px solid {border}; padding: 0 6px;")
