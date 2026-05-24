from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
)
from PySide6.QtCore import Qt, QTimer

class WelcomeScreen(QWidget):
    def __init__(self, on_get_started):
        super().__init__()
        self.on_get_started = on_get_started
        self.countdown = 5
        self._total = self.countdown
        self.init_ui()

    def init_ui(self):
        self.setAutoFillBackground(True)
        self.setStyleSheet("WelcomeScreen { background-color: #F4F4F4; }")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addStretch()

        center = QVBoxLayout()
        center.setAlignment(Qt.AlignCenter)
        center.setSpacing(0)

        title = QLabel("HANDMOUSE")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 52px; font-weight: 800; color: #111111; letter-spacing: 8px; background: transparent; border: none;")
        center.addWidget(title)

        center.addSpacing(10)

        subtitle = QLabel("GESTURE CONTROL · V1.0")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 9px; color: #9A9A9A; letter-spacing: 3px; background: transparent; border: none;")
        center.addWidget(subtitle)

        center.addSpacing(32)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(280)
        self.progress_bar.setFixedHeight(2)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #D8D8D8; border: none; border-radius: 1px; }
            QProgressBar::chunk { background-color: #111111; border-radius: 1px; }
        """)
        progress_row = QHBoxLayout()
        progress_row.addStretch()
        progress_row.addWidget(self.progress_bar)
        progress_row.addStretch()
        center.addLayout(progress_row)

        center.addSpacing(10)

        self.countdown_label = QLabel(f"STARTING IN {self.countdown}")
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.setStyleSheet("font-size: 8px; color: #C8896A; letter-spacing: 2px; background: transparent; border: none;")
        center.addWidget(self.countdown_label)

        outer.addLayout(center)
        outer.addStretch()

        footer_wrap = QWidget()
        footer_wrap.setFixedHeight(36)
        footer_wrap.setStyleSheet("background: transparent; border-top: 1px solid #D8D8D8;")
        footer_inner = QHBoxLayout(footer_wrap)
        footer_inner.setContentsMargins(0, 0, 0, 0)
        footer = QLabel("GESTURE CONTROL · v1.0 ·")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("font-size: 7px; color: #B8B0AB; letter-spacing: 2px; background: transparent; border: none;")
        footer_inner.addWidget(footer)
        outer.addWidget(footer_wrap)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_countdown)
        self.timer.start(1000)

    def update_countdown(self):
        self.countdown -= 1
        self.progress_bar.setValue(int((self._total - self.countdown) / self._total * 100))
        self.countdown_label.setText(f"STARTING IN {self.countdown}")
        if self.countdown <= 0:
            self.timer.stop()
            self.on_get_main()

    def on_get_main(self):
        self.timer.stop()
        self.on_get_started()

