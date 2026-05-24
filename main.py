import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PySide6.QtCore import Qt
from ui.welcome_screen import WelcomeScreen
from ui.main_menu import MainMenu


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HandMouse - Gesture Control")
        self.resize(980, 660)
        self.setMinimumSize(800, 560)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #F4F4F4;
            }
        """)

        self.stacked = QStackedWidget()
        self.setCentralWidget(self.stacked)

        self.welcome = WelcomeScreen(self._go_main)
        self.stacked.addWidget(self.welcome)

        self.main_menu = MainMenu()
        self.stacked.addWidget(self.main_menu)

        self.stacked.setCurrentIndex(0)

    def _go_main(self):
        self.stacked.setCurrentIndex(1)

    def closeEvent(self, event):
        self.main_menu._stop_preview()
        ctrl = self.main_menu.controller
        if ctrl is not None and ctrl.isRunning():
            ctrl.stop()
            ctrl.wait(4000)
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
