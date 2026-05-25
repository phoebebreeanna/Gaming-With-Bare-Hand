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
                        {"img": "assets/gestures/general/one_finger.png",        "n": "01", "name": "One Finger - Choose Option",      "desc": "Raise index finger to navigate and select an option in a zone",                              "tag": "ALL MODES"},
                        {"img": "assets/gestures/general/two_finger.png",        "n": "02", "name": "Two Fingers - Choose Option",      "desc": "Raise index and middle fingers to confirm or choose an option in a zone",                   "tag": "ALL MODES"},
                        {"img": "assets/gestures/general/three_finger.png",      "n": "03", "name": "Three Fingers - Choose Option",    "desc": "Raise index, middle and ring fingers to choose an option in a zone",                        "tag": "ALL MODES"},
                        {"img": "assets/gestures/general/pause.png",             "n": "04", "name": "Pause",                            "desc": "Open both hands with palms facing the camera to pause the current session",                  "tag": "SYSTEM"},
                        {"img": "assets/gestures/general/continue.png",          "n": "05", "name": "Continue",                         "desc": "Show peace sign with both hands simultaneously to resume from paused state",                 "tag": "SYSTEM"},
                        {"img": "assets/gestures/general/game_option_one.png",   "n": "06", "name": "Game Option 1 - Mouse Mode",       "desc": "One hand fist + other hand 1 finger raised, hold for 5 s to switch to Mouse mode",          "tag": "GAME OPTION"},
                        {"img": "assets/gestures/general/game_option_two.png",   "n": "07", "name": "Game Option 2 - Subway Mode",      "desc": "One hand fist + other hand 2 fingers raised, hold for 5 s to switch to Subway mode",        "tag": "GAME OPTION"},
                        {"img": "assets/gestures/general/game_option_three.png", "n": "08", "name": "Game Option 3 - Racing Mode",      "desc": "One hand fist + other hand 3 fingers raised, hold for 5 s to switch to Racing mode",        "tag": "GAME OPTION"},
                        {"img": "assets/gestures/general/game_option_four.png",  "n": "09", "name": "Game Option 4 - Open World",      "desc": "One hand fist + other hand 4 fingers raised, hold for 5 s to switch to Open World mode",    "tag": "GAME OPTION"},
                        {"img": "assets/gestures/general/mouse_in_game.png",     "n": "10", "name": "Mouse in Game",                    "desc": "One hand devil horn + other hand index finger raised to navigate with mouse in game",       "tag": "SYSTEM"},
                        {"img": "assets/gestures/general/exit.png",              "n": "11", "name": "Exit / Close",                     "desc": "Close both hands into fists simultaneously to exit the application",                        "tag": "SYSTEM"},
                    ],
                },
            ],
            "Mouse": [
                {
                    "label": "01  ·  MOUSE MODE",
                    "gestures": [
                        {"img": "assets/gestures/mouse/move.png",        "n": "01", "name": "Point - Move Cursor",      "desc": "Raise your index finger to move the cursor across the screen",  "tag": "ACTIVE IN MOUSE MODE"},
                        {"img": "assets/gestures/mouse/left_click.png",  "n": "02", "name": "OK Sign - Left Click",    "desc": "Thumb + Index finger pinch (OK sign), held under 0.5 s",       "tag": "QUICK ACTION"},
                        {"img": "assets/gestures/mouse/left_click.png",  "n": "03", "name": "OK Sign Hold - Drag",     "desc": "Thumb + Index finger pinch (OK sign), held over 0.5 s",        "tag": "HOLD 0.5S"},
                        {"img": "assets/gestures/mouse/right_click.png", "n": "04", "name": "Middle Pinch - Right Click", "desc": "Thumb + Middle finger pinch",                                "tag": "QUICK ACTION"},
                        {"img": "assets/gestures/mouse/scroll_up.png",   "n": "05", "name": "Three Fingers - Scroll Up","desc": "Index + Middle + Ring fingers raised",                          "tag": "ACTIVE"},
                        {"img": "assets/gestures/mouse/scroll_down.png", "n": "06", "name": "Fist - Scroll Down",       "desc": "All fingers clenched into a fist",                              "tag": "ACTIVE"},
                    ],
                },
            ],
            "Subway Surfers": [
                {
                    "label": "02  ·  SUBWAY SURFERS",
                    "gestures": [
                        {"img": "assets/gestures/subway/jump.jpg",        "n": "01", "name": "Two Fingers Up - Jump",        "desc": "Raise index and middle fingers pointing upward to jump",              "tag": "ACTIVE"},
                        {"img": "assets/gestures/subway/slide.jpg",       "n": "02", "name": "Two Fingers Down - Slide",     "desc": "Point index and middle fingers downward to slide",                    "tag": "ACTIVE"},
                        {"img": "assets/gestures/subway/swipe_left.png",  "n": "03", "name": "Two Fingers Left - Swipe Left","desc": "Point index and middle fingers to the left to swipe left",            "tag": "ACTIVE"},
                        {"img": "assets/gestures/subway/swipe_right.png", "n": "04", "name": "Two Fingers Right - Swipe Right","desc": "Point index and middle fingers to the right to swipe right",        "tag": "ACTIVE"},
                        {"img": "assets/gestures/subway/space.png",       "n": "05", "name": "Metal Sign - Space Bar",      "desc": "Raise index and pinky fingers (devil horn / metal sign) to activate space", "tag": "ACTIVE"},
                    ],
                },
            ],
            "Open World": [
                {
                    "label": "04  ·  OPEN WORLD",
                    "gestures": [
                        {"img": "assets/gestures/open_world/two_up.png",     "n": "01", "name": "Two Up - Move Forward",      "desc": "Peace sign pointing up (V sign upward) to move forward (W key)",                                    "tag": "MOVEMENT"},
                        {"img": "assets/gestures/open_world/two_up_inv.png", "n": "02", "name": "Two Up Inv - Move Backward", "desc": "Peace sign pointing downward to move backward (S key)",                                             "tag": "MOVEMENT"},
                        {"img": "assets/gestures/open_world/three_gun.png",  "n": "03", "name": "Three Gun - Strafe",         "desc": "Gun-hand gesture, aim left for A key or right for D key",                                          "tag": "MOVEMENT"},
                        {"img": "assets/gestures/open_world/like.png",       "n": "04", "name": "Thumbs Up - Dodge",          "desc": "Thumb up to dodge or dash (Shift key)",                                                             "tag": "ACTION"},
                        {"img": "assets/gestures/open_world/palm.png",       "n": "05", "name": "Open Palm - Jump",           "desc": "Open palm facing camera to jump (Space key)",                                                       "tag": "ACTION"},
                        {"img": "assets/gestures/open_world/thumb_index.png","n": "06", "name": "Thumb Index - Ability",      "desc": "L-sign (thumb + index extended) to use main ability (E key)",                                       "tag": "ACTION"},
                        {"img": "assets/gestures/open_world/ok.png",         "n": "07", "name": "OK Sign - Interact",         "desc": "OK sign (thumb + index pinch) to interact (F key)",                                                 "tag": "ACTION"},
                        {"img": "assets/gestures/open_world/call.png",       "n": "08", "name": "Call - Skill",               "desc": "Call sign to trigger skill (R key)",                                                                "tag": "ACTION"},
                        {"img": "assets/gestures/open_world/dislike.png",    "n": "09", "name": "Thumbs Down - Alt Skill",    "desc": "Thumb down to trigger alternate skill (Q key)",                                                     "tag": "ACTION"},
                        {"img": "assets/gestures/open_world/grip.png",       "n": "10", "name": "Grip - Alt",                 "desc": "Gripping gesture for alt action (Alt key)",                                                         "tag": "ACTION"},
                        {"img": "assets/gestures/open_world/one.png",        "n": "11", "name": "One - Teammate 1",           "desc": "Index finger raised to select teammate 1 (1 key)",                                                  "tag": "TEAM"},
                        {"img": "assets/gestures/open_world/peace.png",      "n": "12", "name": "Peace - Teammate 2",         "desc": "Peace sign to select teammate 2 (2 key)",                                                           "tag": "TEAM"},
                        {"img": "assets/gestures/open_world/three.png",      "n": "13", "name": "Three - Teammate 3",         "desc": "Three fingers raised to select teammate 3 (3 key)",                                                 "tag": "TEAM"},
                        {"img": "assets/gestures/open_world/four.png",       "n": "14", "name": "Four - Teammate 4",          "desc": "Four fingers raised to select teammate 4 (4 key)",                                                  "tag": "TEAM"},
                        {"img": "assets/gestures/open_world/holy.png",       "n": "15", "name": "Holy - Escape",              "desc": "Holy / spread hand gesture to open menu or escape (Esc key)",                                       "tag": "SYSTEM"},
                        {"img": "assets/gestures/open_world/peace_inv.png",  "n": "16", "name": "Peace Inv - Extra",          "desc": "Inverted peace sign for extra action (T key)",                                                      "tag": "EXTRA"},
                        {"img": "assets/gestures/open_world/three_three.png","n": "17", "name": "Three-Three - Tab",          "desc": "Three-three finger pose for map / tab (Tab key)",                                                   "tag": "EXTRA"},
                        {"img": "assets/gestures/open_world/three_two.png",  "n": "18", "name": "Three-Two - Extra",          "desc": "Three-two finger pose for extra action (G key)",                                                    "tag": "EXTRA"},
                    ],
                },
            ],
            "Racing": [
                {
                    "label": "03  ·  RACING",
                    "gestures": [
                        {"img": "assets/gestures/racing/accelerate.png",      "n": "01", "name": "Right Thumb Up - Accelerate",    "desc": "Right hand thumb up to accelerate",                                                       "tag": "ACTIVE"},
                        {"img": "assets/gestures/racing/brake.png",           "n": "02", "name": "Left Thumb Up - Brake",          "desc": "Left hand thumb up to brake",                                                             "tag": "ACTIVE"},
                        {"img": "assets/gestures/racing/steer_left.png",      "n": "03", "name": "Tilt Left - Steer Left",         "desc": "Tilt both hands to the left to steer left",                                               "tag": "ACTIVE"},
                        {"img": "assets/gestures/racing/steer_right.png",     "n": "04", "name": "Tilt Right - Steer Right",       "desc": "Tilt both hands to the right to steer right",                                             "tag": "ACTIVE"},
                        {"img": "assets/gestures/racing/steer_straight.png",  "n": "05", "name": "Level Hands - Straight",         "desc": "Both hands kept level to go straight",                                                    "tag": "ACTIVE"},
                        {"img": "assets/gestures/racing/brake_accelerate.png","n": "06", "name": "Brake + Accelerate",             "desc": "Both thumbs up simultaneously",                                                           "tag": "COMBO"},
                        {"img": "assets/gestures/racing/camera.png",          "n": "07", "name": "Camera - Change Angle",          "desc": "Left hand index and middle fingers pointing forward to change the in-game camera angle",  "tag": "RACING"},
                        {"img": "assets/gestures/racing/horn.png",            "n": "08", "name": "Horn",                           "desc": "Right hand index and middle fingers pointing forward to sound the horn",                  "tag": "RACING"},
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
            img.setText("-")
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
