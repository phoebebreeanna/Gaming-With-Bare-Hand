from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal, QTimer


class AirHockeyLaunchPage(QWidget):
    on_menu_toggle = Signal()

    def __init__(self):
        super().__init__()
        self.is_dark = False
        self._proc = None
        try:
            from logic.air_hockey_launcher import is_available
            self._available = is_available()
        except Exception:
            self._available = False

        self._build()
        self.apply_theme(False)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = QWidget()
        self.header.setFixedHeight(42)
        hl = QHBoxLayout(self.header)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        self.menu_btn = QPushButton("☰")
        self.menu_btn.setFixedSize(36, 42)
        self.menu_btn.setCursor(Qt.PointingHandCursor)
        self.menu_btn.clicked.connect(self.on_menu_toggle.emit)
        hl.addWidget(self.menu_btn)

        self.brand_box = QWidget()
        self.brand_box.setFixedHeight(42)
        bl = QHBoxLayout(self.brand_box)
        bl.setContentsMargins(14, 0, 18, 0)
        bl.setSpacing(10)
        self.brand_title = QLabel("HANDMOUSE")
        self.brand_version = QLabel("v1.0")
        bl.addWidget(self.brand_title)
        bl.addWidget(self.brand_version)
        hl.addWidget(self.brand_box)
        hl.addStretch()
        root.addWidget(self.header)

        self.header_rule = QWidget()
        self.header_rule.setFixedHeight(1)
        root.addWidget(self.header_rule)

        content = QVBoxLayout()
        content.setContentsMargins(24, 24, 24, 16)
        content.setSpacing(14)
        content.addStretch()

        self.page_title = QLabel("AIR HOCKEY")
        self.page_title.setAlignment(Qt.AlignCenter)
        content.addWidget(self.page_title)

        self.icon_lbl = QLabel("🏒")
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setStyleSheet("font-size: 48px; background: transparent; border: none;")
        content.addWidget(self.icon_lbl)

        self.desc_lbl = QLabel(
            "Launch the bundled local 2-player air hockey game in its own "
            "window. Once it's open, select the AIR HOCKEY mode card in "
            "Settings and start tracking to play with gestures."
        )
        self.desc_lbl.setAlignment(Qt.AlignCenter)
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setFixedSize(360, 60)
        content.addWidget(self.desc_lbl, alignment=Qt.AlignHCenter)

        self.launch_btn = QPushButton("LAUNCH AIR HOCKEY")
        self.launch_btn.setFixedHeight(44)
        self.launch_btn.setFixedWidth(240)
        self.launch_btn.setCursor(Qt.PointingHandCursor)
        self.launch_btn.clicked.connect(self._launch)
        self.launch_btn.setEnabled(self._available)
        content.addWidget(self.launch_btn, alignment=Qt.AlignHCenter)

        self.status_lbl = QLabel(
            "" if self._available else "hockey_game/ not found in this install."
        )
        self.status_lbl.setAlignment(Qt.AlignCenter)
        content.addWidget(self.status_lbl)

        content.addStretch()
        root.addLayout(content)

    def _launch(self):
        if self._proc is not None and self._proc.poll() is None:
            return
        try:
            from logic.air_hockey_launcher import launch
            self._proc = launch()
        except Exception:
            self.status_lbl.setText("Couldn't launch the game - see logs for details.")
            return

        self.launch_btn.setEnabled(False)
        self.launch_btn.setText("RUNNING…")
        self.status_lbl.setText("Air hockey window is open. Close it to launch again.")

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(1000)
        self._poll_timer.timeout.connect(self._poll_proc)
        self._poll_timer.start()

    def _poll_proc(self):
        if self._proc is None or self._proc.poll() is not None:
            self._poll_timer.stop()
            self.launch_btn.setEnabled(True)
            self.launch_btn.setText("LAUNCH AIR HOCKEY")
            self.status_lbl.setText("")

    def apply_theme(self, is_dark: bool):
        self.is_dark = is_dark
        if is_dark:
            bg = "#0a0a0a"; border = "#262626"; text = "#e8e8e8"; muted = "#9a9a9a"
            hover = "#161616"
            btn_bg = "#e8e8e8"; btn_txt = "#111111"; btn_disabled = "#3a3a3a"
        else:
            bg = "#F4F4F4"; border = "#D8CEC7"; text = "#111111"; muted = "#6F655F"
            hover = "#EDE5DF"
            btn_bg = "#1A1A1A"; btn_txt = "#FFFFFF"; btn_disabled = "#D8CEC7"

        self.setStyleSheet(f"background-color: {bg};")
        self.header.setStyleSheet(f"background-color: {bg};")
        self.header_rule.setStyleSheet(f"background-color: {border};")
        self.menu_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {text};
                font-size: 18px; border: none; border-radius: 2px;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
        """)
        self.brand_box.setStyleSheet(
            f"background: transparent; border-left: 1px solid {border}; border-right: 1px solid {border};")
        self.brand_title.setStyleSheet(
            f"font-size: 11px; font-weight: 800; color: {text}; letter-spacing: 1.5px; background: transparent; border: none;")
        self.brand_version.setStyleSheet(
            f"font-size: 8px; color: {muted}; letter-spacing: 1px; background: transparent; border: none;")
        self.page_title.setStyleSheet(
            f"color: {text}; font-size: 16px; font-weight: 800; letter-spacing: 1.5px; background: transparent; border: none;")
        self.desc_lbl.setStyleSheet(
            f"color: {muted}; font-size: 11px; background: transparent; border: none;")
        self.status_lbl.setStyleSheet(
            f"color: {muted}; font-size: 10px; background: transparent; border: none;")
        self.launch_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_bg}; color: {btn_txt};
                font-size: 12px; font-weight: 700; letter-spacing: 1px;
                border: none; border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
            QPushButton:disabled {{ background-color: transparent; color: {btn_disabled}; border: 1px solid {btn_disabled}; }}
        """)
