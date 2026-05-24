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
        self.current_mode = "General"

        self.mode_sections = {
            "General": [
                {
                    "label": "00  ·  SYSTEM CONTROLS",
                    "gestures": [
                        {"img": "assets/gestures/general/one_finger.png",   "n": "01", "name": "One Finger - Navigate",       "desc": "Point with index finger to move cursor or highlight",        "tag": "ALL MODES"},
                        {"img": "assets/gestures/general/two_finger.png",   "n": "02", "name": "Two Fingers - Confirm",        "desc": "Index + Middle fingers raised to confirm or select",         "tag": "ALL MODES"},
                        {"img": "assets/gestures/general/three_finger.png", "n": "03", "name": "Three Fingers - Switch Mode",  "desc": "Index + Middle + Ring raised to cycle between modes",        "tag": "ALL MODES"},
                        {"img": "assets/gestures/general/pause.png",        "n": "04", "name": "Pause Gesture",                "desc": "Hold open palm flat to pause the current session",           "tag": "SYSTEM"},
                        {"img": "assets/gestures/general/continue.png",     "n": "05", "name": "Continue Gesture",             "desc": "Closed fist then open to resume from paused state",          "tag": "SYSTEM"},
                        {"img": "assets/gestures/general/game_option.png",  "n": "06", "name": "Game Option",                  "desc": "Hold closed fist for 3 s to open game option menu",          "tag": "SYSTEM"},
                        {"img": "assets/gestures/general/mouse_on_game.png","n": "07", "name": "Mouse in Game",                "desc": "Enable mouse-control overlay while in a game mode",          "tag": "SYSTEM"},
                        {"img": "assets/gestures/general/exit.png",         "n": "08", "name": "Exit / Close",                 "desc": "Bring all fingers together pointing down to exit",           "tag": "SYSTEM"},
                    ],
                },
            ],
            "Mouse": [
                {
                    "label": "01  ·  MOUSE MODE",
                    "gestures": [
                        {"img": "assets/gestures/mouse/move.png",        "n": "01", "name": "Point - Move Cursor",    "desc": "Raise your index finger to move the cursor across the screen",  "tag": "ACTIVE IN MOUSE MODE"},
                        {"img": "assets/gestures/mouse/left_click.png",  "n": "02", "name": "Quick Pinch - Left Click", "desc": "Thumb + Middle pinch, held under 0.5 s",                      "tag": "QUICK ACTION"},
                        {"img": "assets/gestures/mouse/left_click.png",  "n": "03", "name": "Hold Pinch - Drag",       "desc": "Thumb + Middle pinch, held over 0.5 s",                        "tag": "HOLD 0.5S"},
                        {"img": "assets/gestures/mouse/right_click.png", "n": "04", "name": "Ring Pinch - Right Click", "desc": "Thumb + Ring finger pinch",                                   "tag": "QUICK ACTION"},
                        {"img": "assets/gestures/mouse/scroll_up.png",   "n": "05", "name": "Three Fingers - Scroll Up", "desc": "Index + Middle + Ring fingers raised",                       "tag": "ACTIVE"},
                        {"img": "assets/gestures/mouse/scroll_down.png", "n": "06", "name": "Fist - Scroll Down",        "desc": "All fingers clenched into a fist",                           "tag": "ACTIVE"},
                    ],
                },
            ],
            "Subway Surfers": [
                {
                    "label": "02  ·  SUBWAY SURFERS",
                    "gestures": [
                        {"img": "assets/gestures/subway/jump.jpg",        "n": "01", "name": "Wrist Up - Jump",         "desc": "Lean wrist upward to jump or swipe up",     "tag": "ACTIVE"},
                        {"img": "assets/gestures/subway/slide.jpg",       "n": "02", "name": "Wrist Down - Slide",       "desc": "Lean wrist downward to slide or swipe down","tag": "ACTIVE"},
                        {"img": "assets/gestures/subway/swipe_left.png",  "n": "03", "name": "Wrist Left - Swipe Left",  "desc": "Lean wrist to the left",                   "tag": "ACTIVE"},
                        {"img": "assets/gestures/subway/swipe_right.png", "n": "04", "name": "Wrist Right - Swipe Right","desc": "Lean wrist to the right",                  "tag": "ACTIVE"},
                        {"img": "assets/gestures/subway/space.png",       "n": "05", "name": "Open Hand - Space Bar",    "desc": "Open palm facing camera for space / jump", "tag": "ACTIVE"},
                    ],
                },
            ],
            "Racing": [
                {
                    "label": "03  ·  RACING",
                    "gestures": [
                        {"img": "assets/gestures/racing/accelerate.png",      "n": "01", "name": "Thumb Up - Accelerate",   "desc": "Right thumb up gesture to accelerate",      "tag": "ACTIVE"},
                        {"img": "assets/gestures/racing/brake.png",           "n": "02", "name": "Thumb Down - Brake",      "desc": "Left thumb up gesture to brake",            "tag": "ACTIVE"},
                        {"img": "assets/gestures/racing/steer_left.png",      "n": "03", "name": "Tilt Left - Steer Left",  "desc": "Tilt both hands to the left",               "tag": "ACTIVE"},
                        {"img": "assets/gestures/racing/steer_right.png",     "n": "04", "name": "Tilt Right - Steer Right","desc": "Tilt both hands to the right",              "tag": "ACTIVE"},
                        {"img": "assets/gestures/racing/steer_straight.png",  "n": "05", "name": "Level Hands - Straight",  "desc": "Both hands kept level to go straight",     "tag": "ACTIVE"},
                        {"img": "assets/gestures/racing/brake_accelerate.png","n": "06", "name": "Brake + Accelerate",      "desc": "Both thumbs up simultaneously",             "tag": "COMBO"},
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

        self.mode_tab_row = QHBoxLayout()
        self.mode_tab_row.setSpacing(4)
        self.mode_tab_btns = {}
        for mode in self.mode_sections:
            btn = QPushButton(mode.upper())
            btn.setFixedHeight(28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, m=mode: self.switch_mode(m))
            self.mode_tab_btns[mode] = btn
            self.mode_tab_row.addWidget(btn)

        header_layout.addLayout(self.mode_tab_row)
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
                card = self._make_card(g)
                self.gesture_cards.append(card)
                self.scroll_layout.addWidget(card)
                self.scroll_layout.addSpacing(8)

            self.scroll_layout.addSpacing(8)

        self.scroll_layout.addStretch()

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
        img_path = g.get("img", "")
        if img_path:
            pix = QPixmap(img_path)
            if not pix.isNull():
                img.setPixmap(pix.scaled(130, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                img.setText("NO IMAGE")
        else:
            img.setText("—")
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

    def switch_mode(self, mode):
        if mode in self.mode_sections:
            self.current_mode = mode
            self._build_content(mode)

    def apply_theme(self, is_dark: bool):
        self.is_dark = is_dark
        self._theme_ready = True

        if is_dark:
            page_bg  = "#0a0a0a"
            panel    = "#111111"
            border   = "#262626"
            text     = "#e8e8e8"
            dim      = "#9a9a9a"
            muted    = "#6b6b6b"
            active_bg   = "#e8e8e8"
            active_text = "#111111"
            tab_hover   = "#161616"
        else:
            page_bg  = "#F4F4F4"
            panel    = "#FFFFFF"
            border   = "#D8CEC7"
            text     = "#111111"
            dim      = "#6F655F"
            muted    = "#B8B0AB"
            active_bg   = "#111111"
            active_text = "#FFFFFF"
            tab_hover   = "#EDE5DF"

        self.setStyleSheet(f"background-color: {page_bg};")
        self.header.setStyleSheet(
            f"background-color: {page_bg}; border-bottom: 1px solid {border};")
        self.menu_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {text};
                font-size: 18px;
                border: none;
                border-radius: 2px;
            }}
            QPushButton:hover {{ background-color: {tab_hover}; }}
        """)
        self.title_lbl.setStyleSheet(
            f"color: {text}; font-size: 22px; font-weight: 800; background: transparent; border: none;")

        for mode, btn in self.mode_tab_btns.items():
            is_active = (mode == self.current_mode)
            if is_active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {active_bg};
                        color: {active_text};
                        border: 1px solid {active_bg};
                        font-size: 8px;
                        font-weight: 700;
                        letter-spacing: 1.3px;
                        padding: 0 10px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {dim};
                        border: 1px solid {border};
                        font-size: 8px;
                        font-weight: 700;
                        letter-spacing: 1.3px;
                        padding: 0 10px;
                    }}
                    QPushButton:hover {{ background-color: {tab_hover}; color: {text}; }}
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
        self.footer.setStyleSheet(
            f"background-color: {page_bg}; border-top: 1px solid {border};")

        for lbl in self.section_labels:
            lbl.setStyleSheet(
                f"color: {muted}; font-size: 8px; letter-spacing: 1.4px; background: transparent; border: none;")

        for line in self.section_lines:
            line.setStyleSheet(f"background-color: {border};")

        for card in self.gesture_cards:
            card.setStyleSheet(
                f"background-color: {panel}; border: 1px solid {border};")

        for img in self.image_placeholders:
            img.setStyleSheet(
                f"color: {muted}; font-size: 8px; letter-spacing: 1.2px;"
                f" border-right: 1px solid {border}; background: transparent;")

        for lbl in self.num_labels:
            lbl.setStyleSheet(
                f"color: {muted}; font-size: 8px; letter-spacing: 1.2px; background: transparent; border: none;")

        for lbl in self.name_labels:
            lbl.setStyleSheet(
                f"color: {text}; font-size: 13px; font-weight: 700; background: transparent; border: none;")

        for lbl in self.desc_labels:
            lbl.setStyleSheet(
                f"color: {dim}; font-size: 10px; background: transparent; border: none;")

        for lbl in self.tag_labels:
            lbl.setStyleSheet(
                f"color: {dim}; font-size: 8px; letter-spacing: 1.2px;"
                f" background: transparent; border: 1px solid {border}; padding: 0 6px;")

