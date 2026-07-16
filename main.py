import os
import sys

os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.ffmpeg=false;qt.multimedia.ffmpeg.*=false")

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QLineEdit, QTextEdit, QPlainTextEdit
)
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
                focused = QApplication.focusWidget()
                if isinstance(focused, (QLineEdit, QTextEdit, QPlainTextEdit)):
                    return False
                return True
        return False

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
        try:
            self.main_menu._stop_preview()
        except Exception as e:
            print(f"[Shutdown] Failed to stop camera preview: {e}")

        try:
            ctrl = self.main_menu.controller
            if ctrl is not None and ctrl.isRunning():
                ctrl.stop()
                if not ctrl.wait(4000):
                    print("[Shutdown] Gesture controller didn't stop in time - "
                          "forcing termination.")
                    ctrl.terminate()
                    ctrl.wait(1000)
        except Exception as e:
            print(f"[Shutdown] Failed to stop gesture controller: {e}")

        try:
            ah_proc = getattr(self.main_menu.air_hockey_launch_page, '_proc', None)
            if ah_proc is not None and ah_proc.poll() is None:
                ah_proc.terminate()
                try:
                    ah_proc.wait(timeout=3)
                except Exception:
                    print("[Shutdown] Air Hockey process didn't exit in time - killing it.")
                    ah_proc.kill()
        except Exception as e:
            print(f"[Shutdown] Failed to stop Air Hockey process: {e}")

        try:
            self.main_menu.shutdown()
        except Exception as e:
            print(f"[Shutdown] Cleanup step failed: {e}")

        event.accept()

def _install_global_excepthook():
    import traceback

    def _handle(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        print("[Unhandled Error]")
        traceback.print_exception(exc_type, exc_value, exc_tb)

    sys.excepthook = _handle


def _run_hockey_subprocess():
    base = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    hockey_dir = os.path.join(base, "hockey_game")
    sys.path.insert(0, hockey_dir)
    os.chdir(hockey_dir)
    import main as _hockey_main
    _hockey_main.main()


def _run_pipeline_subprocess(conf_path):
    sys.argv = [sys.argv[0], conf_path]
    from logic.gesture_pipeline import main as _pipeline_main
    _pipeline_main()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--run-hockey":
        _run_hockey_subprocess()
        sys.exit(0)

    if len(sys.argv) > 2 and sys.argv[1] == "--run-pipeline":
        _run_pipeline_subprocess(sys.argv[2])
        sys.exit(0)

    _install_global_excepthook()
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
