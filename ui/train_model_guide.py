from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap

import os
import sys
_BASE = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


class TrainModelGuide(QWidget):

    on_menu_toggle = Signal()
    on_done        = Signal()

    def __init__(self):
        super().__init__()
        self.is_dark = False
        self.steps = [
            {
                "title": "Collect Gesture Samples",
                "image": None,
                "items": [
                    "Select your game mode tab at the top: Mouse, Subway, or Racing.",
                    "Under Pipeline Steps, click Collect Data, then Add More to record samples with your camera.",
                    "Aim for around 50 samples per gesture - the Gesture Data panel on the left tracks your progress per gesture.",
                    "Turn on Mirror Aug if your gestures don't rely on left/right direction - it doubles your data automatically.",
                ],
            },
            {
                "title": "Preprocess Your Data",
                "image": None,
                "items": [
                    "Once you have enough samples, click Re-run next to Preprocess.",
                    "This step requires collected data to be available first.",
                    "Preprocessing prepares your raw samples for training.",
                ],
            },
            {
                "title": "Train the Model",
                "image": None,
                "items": [
                    "Click Re-run next to Train Model once preprocessing is complete.",
                    "The training progress bar at the bottom shows completion (e.g. 150 / 150).",
                    "This step requires your data to be preprocessed first.",
                ],
            },
            {
                "title": "Review Your Samples",
                "image": None,
                "items": [
                    "Once training completes, Review Samples becomes Ready.",
                    "Each sample shows the True Label vs Predicted result, plus a confidence flag like LOW CONF.",
                    "Click Keep to confirm a sample, or Remove to mark it for exclusion and retraining.",
                    "Click Done once you've reviewed all samples.",
                ],
            },
            {
                "title": "Use Your Custom Model",
                "image": None,
                "items": [
                    "Go to Settings (04) from the sidebar.",
                    "Toggle Default to Custom for your chosen game mode.",
                    "Your trained gestures are now active immediately.",
                ],
            },
        ]
        self.step_nav_items = []
        self.step_nav_lines = []
        self.step_cards = []
        self.step_card_headers = []
        self.step_numbers = []
        self.step_titles = []
        self.step_images = []
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

        self.title_tmg = QLabel("Train Model Guide")
        header_layout.addWidget(self.title_tmg)
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
        card.setMinimumHeight(160)
        self.step_cards.append(card)
        hl = QHBoxLayout(card)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        img = QLabel()
        img.setFixedSize(160, 160)
        img.setAlignment(Qt.AlignCenter)
        img_path = step.get("image")
        if img_path:
            pix = QPixmap(os.path.join(_BASE, img_path))
            if not pix.isNull():
                img.setPixmap(pix.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                img.setText("NO IMAGE")
        else:
            img.setText("IMAGE")
        self.step_images.append(img)
        hl.addWidget(img)
        
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(18, 14, 18, 14)
        cl.setSpacing(6)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        number = QLabel(str(step_index))
        number.setAlignment(Qt.AlignCenter)
        number.setFixedSize(24, 24)
        self.step_numbers.append(number)
        header_row.addWidget(number)

        title = QLabel(step["title"])
        self.step_titles.append(title)
        header_row.addWidget(title)
        header_row.addStretch()
        cl.addLayout(header_row)
        
        items = step["items"]
        for i, item_text in enumerate(items):
            row = QHBoxLayout()
            row.setSpacing(10)

            num_lbl = QLabel(f"{i + 1:02d}")
            num_lbl.setFixedWidth(18)
            num_lbl.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            self.step_item_nums.append(num_lbl)
            row.addWidget(num_lbl)

            text_lbl = QLabel(item_text)
            text_lbl.setWordWrap(True)
            self.step_item_texts.append(text_lbl)
            row.addWidget(text_lbl, stretch=1)

            cl.addLayout(row)
        
        cl.addStretch()
        hl.addWidget(content, stretch=1)

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
            image_bg = "#161616"
        else:
            page_bg = "#F4F4F4"
            panel = "#FFFFFF"
            border = "#D8CEC7"
            strong = "#111111"
            text = "#111111"
            dim = "#6F655F"
            muted = "#B8B0AB"
            image_bg = "#F0EBE7"

        self.setStyleSheet(f"background-color: {page_bg};")
        self.header.setStyleSheet(f"background-color: {page_bg}; border-bottom: 1px solid {border};")
        self.stepper.setStyleSheet(f"background-color: {page_bg}; border-bottom: 1px solid {border};")
        self.footer.setStyleSheet(f"background-color: {page_bg}; border-top: 1px solid {border};")

        self.menu_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {text};
                font-size: 18px; border: none; border-radius: 2px;
            }}
            QPushButton:hover {{ background-color: {"#161616" if is_dark else "#EDE5DF"}; }}
        """)
        self.title_tmg.setStyleSheet(f"color: {text}; font-size: 22px; font-weight: 800; background: transparent; border: none;")
        self.step_indicator.setStyleSheet(f"color: {dim}; border: 1px solid {border}; font-size: 8px; font-weight: 700; letter-spacing: 1.5px; background: transparent;")

        current = self.step_stack.currentIndex()
        for index, step_box in enumerate(self.step_nav_items):
            if index < current:
                step_box.setText("✓")
                step_box.setStyleSheet(f"background-color: transparent; color: {text}; border: 1px solid {strong}; font-size: 9px; font-weight: 700;")
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

        for number in self.step_numbers:
            number.setStyleSheet(f"color: {text}; border: 1px solid {strong}; background: transparent; font-size: 9px; font-weight: 700;")

        for title in self.step_titles:
            title.setStyleSheet(f"color: {text}; font-size: 12px; font-weight: 700; background: transparent; border: none;")

        for img in self.step_images:
            img.setStyleSheet(
                f"color: {muted}; font-size: 9px; letter-spacing: 1.5px;"
                f" border-right: 1px solid {border}; background: transparent;")

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
                background-color: transparent; color: {text};
                border: 1px solid {border};
                font-size: 9px; font-weight: 700; letter-spacing: 1.4px;
            }}
            QPushButton:hover {{ background-color: {btn_hover}; }}
            QPushButton:pressed {{ background-color: {btn_hover}; }}
            QPushButton:disabled {{ color: {muted}; border-color: {muted}; background-color: transparent; }}
        """
        self.prev_btn.setStyleSheet(btn_style)
        self.next_btn.setStyleSheet(btn_style)

        if hasattr(self, "handbot_icon"):
            self.handbot_icon.apply_theme(is_dark)