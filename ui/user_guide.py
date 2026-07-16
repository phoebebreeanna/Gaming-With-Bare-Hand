from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget
)
from PySide6.QtCore import Qt, Signal

class UserGuide(QWidget):

    on_menu_toggle = Signal()
    on_done        = Signal()

    def __init__(self):
        super().__init__()
        self.is_dark = False
        self.steps = [
            {
                "title": "Welcome",
                "items": [
                    "HandMouse launches with a 3-second welcome screen - it navigates automatically.",
                    "First-time users are taken through a quick setup wizard (camera, calibration, zone).",
                    "Returning users land directly on the Home dashboard.",
                    "Use the sidebar at any time to switch between pages.",
                ],
            },
            {
                "title": "First-Time Setup",
                "items": [
                    "Camera Setup: select your camera and confirm the live preview looks correct.",
                    "Distance Calibration: hold your hand at roughly arm's length until the progress bar completes.",
                    "Zone Setup: hold 1, 2, or 3 fingers to choose Small, Medium, or Large movement zone.",
                    "Once all steps are complete, setup is saved and the Home dashboard appears automatically.",
                ],
            },
            {
                "title": "Choose a Game Mode",
                "items": [
                    "Open Settings (05) from the sidebar.",
                    "Choose Mouse, Subway Surfers, Racing, or Open World mode.",
                    "For each mode, toggle Default or Custom model source - Custom activates once you have trained your own model via Train Model (06).",
                    "Switching Default ↔ Custom takes effect immediately, even while the controller is running.",
                ],
            },
            {
                "title": "Customize Controls",
                "items": [
                    "Open Key Bindings (07) from the sidebar.",
                    "Click any key button to remap a gesture - press the desired key to confirm, or Escape to cancel.",
                    "Locked gestures (greyed out) use fixed directional logic and cannot be rebound to a single key.",
                    "Use the Reset All button at the top of each section to restore that mode's defaults instantly.",
                ],
            },
            {
                "title": "Start the Controller",
                "items": [
                    "Go to Home (01) from the sidebar.",
                    "Check the distance alert in the camera feed: OPTIMAL / TOO FAR / TOO CLOSE.",
                    "Click Start and wait for the status card to show Running.",
                    "Keep your hand clearly inside the camera frame while playing.",
                ],
            },
            {
                "title": "Using Gestures",
                "items": [
                    "Open Gesture Guide (03) from the sidebar to see all gestures for any mode.",
                    "Show both open palms to pause the controller at any time.",
                    "Show peace signs with both hands simultaneously to resume from the paused state.",
                    "Hold both fists (two hands) to exit the controller completely.",
                    "Switch game modes by holding one fist and N fingers on the other hand for 3 seconds.",
                ],
            },
            {
                "title": "Best Performance",
                "items": [
                    "Avoid strong backlight or a busy background behind your hand.",
                    "Keep fingers clearly separated - spread them out for better detection accuracy.",
                    "Use the distance alert on the Home page to stay at the optimal depth.",
                    "Train a Custom model for your own gestures via Train Model (06) in the sidebar.",
                ],
            },
        ]
        self.step_nav_items = []
        self.step_nav_lines = []
        self.step_cards = []
        self.step_card_headers = []
        self.step_numbers = []
        self.step_titles = []
        self.step_item_nums = []
        self.step_item_texts = []
        self.step_item_rows = []
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

        self.title_ug = QLabel("User Guide")
        header_layout.addWidget(self.title_ug)
        header_layout.addStretch()

        self.step_indicator = QLabel()
        self.step_indicator.setAlignment(Qt.AlignCenter)
        self.step_indicator.setFixedSize(98, 28)
        header_layout.addWidget(self.step_indicator)
        layout.addWidget(self.header)

        self.stepper = QWidget()
        self.stepper.setFixedHeight(42)
        stepper_layout = QHBoxLayout(self.stepper)
        stepper_layout.setContentsMargins(24, 0, 24, 0)
        stepper_layout.setSpacing(10)

        for index, step in enumerate(self.steps):
            step_box = QLabel(str(index + 1))
            step_box.setAlignment(Qt.AlignCenter)
            step_box.setFixedSize(28, 28)
            self.step_nav_items.append(step_box)
            stepper_layout.addWidget(step_box)

            if index < len(self.steps) - 1:
                line = QWidget()
                line.setFixedSize(18, 1)
                self.step_nav_lines.append(line)
                stepper_layout.addWidget(line)

        self.current_step_name = QLabel("")
        stepper_layout.addWidget(self.current_step_name)
        stepper_layout.addStretch()
        layout.addWidget(self.stepper)

        self.step_stack = QStackedWidget()
        for step_index, step in enumerate(self.steps, start=1):
            self.step_stack.addWidget(self.create_step_page(step_index, step))
        layout.addWidget(self.step_stack, stretch=1)

        self.footer = QWidget()
        self.footer.setFixedHeight(58)
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(24, 0, 24, 0)
        footer_layout.setSpacing(12)

        self.prev_btn = QPushButton("Previous")
        self.prev_btn.setFixedHeight(34)
        self.prev_btn.setMinimumWidth(90)
        self.prev_btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.clicked.connect(self.go_previous)
        footer_layout.addWidget(self.prev_btn)
        footer_layout.addStretch()

        self.next_btn = QPushButton("Next")
        self.next_btn.setFixedHeight(34)
        self.next_btn.setMinimumWidth(90)
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.clicked.connect(self.go_next)
        footer_layout.addWidget(self.next_btn)

        layout.addWidget(self.footer)

        self.update_navigation(0)

    def create_step_page(self, step_index, step):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(24, 24, 24, 24)
        page_layout.setSpacing(0)

        card = QWidget()
        self.step_cards.append(card)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        card_header = QWidget()
        card_header.setFixedHeight(48)
        self.step_card_headers.append(card_header)
        header_layout = QHBoxLayout(card_header)
        header_layout.setContentsMargins(18, 0, 18, 0)
        header_layout.setSpacing(14)

        number = QLabel(str(step_index))
        number.setAlignment(Qt.AlignCenter)
        number.setFixedSize(24, 24)
        self.step_numbers.append(number)
        header_layout.addWidget(number)

        title = QLabel(step["title"])
        self.step_titles.append(title)
        header_layout.addWidget(title)
        header_layout.addStretch()

        card_layout.addWidget(card_header)

        items = step["items"]
        for i, item_text in enumerate(items):
            row = QWidget()
            row.setFixedHeight(42)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(18, 0, 18, 0)
            row_layout.setSpacing(14)
            row_layout.setAlignment(Qt.AlignVCenter)

            num_lbl = QLabel(f"{i + 1:02d}")
            num_lbl.setFixedWidth(18)
            num_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.step_item_nums.append(num_lbl)
            row_layout.addWidget(num_lbl)

            text_lbl = QLabel(item_text)
            text_lbl.setWordWrap(True)
            self.step_item_texts.append(text_lbl)
            row_layout.addWidget(text_lbl, stretch=1)

            row.setProperty("has_bottom_border", i < len(items) - 1)
            self.step_item_rows.append(row)
            card_layout.addWidget(row)

        page_layout.addWidget(card)
        page_layout.addStretch()
        return page

    def go_next(self):
        current = self.step_stack.currentIndex()
        if current < len(self.steps) - 1:
            self.step_stack.setCurrentIndex(current + 1)
            self.update_navigation(current + 1)
        else:
            self.on_done.emit()

    def go_previous(self):
        current = self.step_stack.currentIndex()
        if current > 0:
            self.step_stack.setCurrentIndex(current - 1)
            self.update_navigation(current - 1)

    def update_navigation(self, index):
        total = len(self.steps)
        self.step_indicator.setText(f"STEP {index + 1} / {total}")
        self.current_step_name.setText(self.steps[index]["title"].upper())
        self.prev_btn.setEnabled(index > 0)
        self.next_btn.setEnabled(True)
        self.next_btn.setText("Done" if index == total - 1 else "Next")
        if hasattr(self, "_theme_ready"):
            self.apply_theme(self.is_dark)

    def apply_theme(self, is_dark: bool):
        self.is_dark = is_dark
        self._theme_ready = True

        if is_dark:
            page_bg = "#0a0a0a"
            panel = "#111111"
            border = "#262626"
            strong = "#3a3a3a"
            text = "#e8e8e8"
            dim = "#9a9a9a"
            muted = "#6b6b6b"
            button_bg = strong
            button_text = text
        else:
            page_bg = "#F4F4F4"
            panel = "#FFFFFF"
            border = "#D8CEC7"
            strong = "#111111"
            text = "#111111"
            dim = "#6F655F"
            muted = "#B8B0AB"
            button_bg = strong
            button_text = text

        self.setStyleSheet(f"background-color: {page_bg};")
        self.header.setStyleSheet(f"background-color: {page_bg}; border-bottom: 1px solid {border};")
        self.stepper.setStyleSheet(f"background-color: {page_bg}; border-bottom: 1px solid {border};")
        self.footer.setStyleSheet(f"background-color: {page_bg}; border-top: 1px solid {border};")

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
        self.title_ug.setStyleSheet(f"color: {text}; font-size: 22px; font-weight: 800; background: transparent; border: none;")
        self.step_indicator.setStyleSheet(f"color: {dim}; border: 1px solid {border}; font-size: 8px; font-weight: 700; letter-spacing: 1.5px; background: transparent;")

        current = self.step_stack.currentIndex()
        for index, step_box in enumerate(self.step_nav_items):
            if index < current:
                step_box.setText("✓")
                step_box.setStyleSheet(f"background-color: transparent; color: {button_text}; border: 1px solid {button_bg}; font-size: 9px; font-weight: 700;")
            elif index == current:
                step_box.setText(str(index + 1))
                step_box.setStyleSheet(f"background-color: transparent; color: {text}; border: 1px solid {strong}; font-size: 9px; font-weight: 700;")
            else:
                step_box.setText(str(index + 1))
                step_box.setStyleSheet(f"background-color: transparent; color: {muted}; border: 1px solid {border}; font-size: 9px;")

        for line in self.step_nav_lines:
            line.setStyleSheet(f"background-color: {border};")

        self.current_step_name.setStyleSheet(f"color: {muted}; font-size: 8px; letter-spacing: 1.4px; background: transparent; border: none;")

        for card in self.step_cards:
            card.setStyleSheet(f"background-color: {panel}; border: 1px solid {border};")

        for card_header in self.step_card_headers:
            card_header.setStyleSheet(f"background: transparent; border-bottom: 1px solid {border};")

        for number in self.step_numbers:
            number.setStyleSheet(f"color: {text}; border: 1px solid {strong}; background: transparent; font-size: 9px; font-weight: 700;")

        for title in self.step_titles:
            title.setStyleSheet(f"color: {text}; font-size: 12px; font-weight: 700; background: transparent; border: none;")

        for num_lbl in self.step_item_nums:
            num_lbl.setStyleSheet(f"color: {muted}; font-size: 9px; background: transparent; border: none;")

        for text_lbl in self.step_item_texts:
            text_lbl.setStyleSheet(f"color: {dim}; font-size: 11px; background: transparent; border: none;")

        for row in self.step_item_rows:
            if row.property("has_bottom_border"):
                row.setStyleSheet(f"background: transparent; border-bottom: 1px solid {border};")
            else:
                row.setStyleSheet("background: transparent; border: none;")

        btn_hover = "#161616" if is_dark else "#EDE5DF"
        btn_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {text};
                border: 1px solid {border};
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 1.4px;
            }}
            QPushButton:hover {{ background-color: {btn_hover}; }}
            QPushButton:pressed {{ background-color: {btn_hover}; }}
            QPushButton:disabled {{ color: {muted}; border-color: {muted}; background-color: transparent; }}
        """
        self.prev_btn.setStyleSheet(btn_style)
        self.next_btn.setStyleSheet(btn_style)
