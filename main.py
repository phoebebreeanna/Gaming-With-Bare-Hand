import os
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PySide6.QtCore import Qt, QObject, QEvent
from ui.welcome_screen import WelcomeScreen
from ui.main_menu import MainMenu

class _GestureKeyBlocker(QObject):
    def __init__(self, window: 'MainWindow'):
        super().__init__()
        self._window = window

    def eventFilter(self, obj, event):
        t = event.type()
        if t in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            ctrl = self._window.main_menu.controller
            if ctrl is not None and ctrl.isRunning():
                kb = getattr(self._window.main_menu, 'key_bindings_widget', None)
                if kb is not None and getattr(kb, '_capturing', None):
                    return False
                return True
        return False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HandMouse - Gesture Control")
        self.resize(980, 660)
        self.setMinimumSize(800, 560)

        self.setAttribute(Qt.WA_ShowWithoutActivating)

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
        ah_proc = getattr(self.main_menu.air_hockey_launch_page, '_proc', None)
        if ah_proc is not None and ah_proc.poll() is None:
            ah_proc.terminate()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    blocker = _GestureKeyBlocker(window)
    app.installEventFilter(blocker)
    window.show()
    exit_code = app.exec()

    import atexit
    atexit._run_exitfuncs()
    os._exit(exit_code)
