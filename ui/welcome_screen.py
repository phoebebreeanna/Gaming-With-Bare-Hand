from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
)
from PySide6.QtCore import Qt, QTimer

class WelcomeScreen(QWidget):
    def __init__(self, on_get_started):
        super().__init__()
        self.on_get_started = on_get_started
        self.init_ui()

    def init_ui(self):
        self.setAutoFillBackground(True)
        self.setStyleSheet("""
            WelcomeScreen {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2D1B69,
                    stop:1 #9B6FBE
                );
            }
            WelcomeScreen QLabel {
                background: transparent;
                color: white;
            }
        """)

        layout= QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        #logo (we can replace this with an actual image later)
        logo = QLabel("Logo")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("font-size: 80px; font-weight: bold; color: white")
        layout.addWidget(logo)

        #Welcome message
        welcome_message= QLabel ("Welcome to our application!")
        welcome_message.setAlignment(Qt.AlignCenter)
        welcome_message.setStyleSheet("font-size: 24px; font-weight: bold; color: white")
        layout.addWidget(welcome_message)

        layout.addSpacing(40)

        #Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(400)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255,255,255,0.2);
                border-radius: 5px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #6B35C7;
                border-radius: 5px;
            }
        """)

        progress_row = QHBoxLayout()
        progress_row.addStretch()
        progress_row.addWidget(self.progress_bar)
        progress_row.addStretch()
        layout.addLayout(progress_row)

        #Countdown label
        self.countdown_label = QLabel("Starting in 5s...")
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.setStyleSheet("font-size: 14px; color: #CCCCCC; background: transparent;")
        layout.addWidget(self.countdown_label)

        layout.addSpacing(20)

        #Countdown 5 seconds and jump to main menu
        self.countdown = 1 # Testing with 1 seconds for faster transition, change to 10 for prototype demo
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_countdown)
        self.timer.start(1000)  # Update every second

    def update_countdown(self):
        self.countdown -= 1

        #Update progress bar
        progress = int((5 - self.countdown) / 5 * 100)
        self.progress_bar.setValue(progress)

        #Update countdown label
        self.countdown_label.setText(f"Starting in {self.countdown}s...")

        if self.countdown <= 0:
            self.timer.stop()
            self.on_get_main()

    def on_get_main(self):
        self.timer.stop()  #Stop the timer if it's still running
        self.on_get_started()
