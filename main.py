import os
import sys
import time

os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.ffmpeg=false;qt.multimedia.ffmpeg.*=false")


def _log_lifecycle(event: str):
    try:
        log_dir = os.path.join(os.path.expanduser('~'), '.handmouse')
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, 'lifecycle.log'), 'a', encoding='utf-8') as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} pid={os.getpid()} {event}\n")
    except OSError:
        pass

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
        _log_lifecycle("closeEvent entered")
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

        _log_lifecycle("closeEvent accepting")
        event.accept()

def _check_mac_accessibility_permission():
    if sys.platform != 'darwin':
        return
    try:
        from ApplicationServices import AXIsProcessTrustedWithOptions
        trusted = AXIsProcessTrustedWithOptions({"AXTrustedCheckOptionPrompt": False})
    except Exception:
        _log_lifecycle("accessibility check unavailable (pyobjc missing)")
        return
    _log_lifecycle(f"accessibility trusted={trusted}")
    if not trusted:
        import subprocess
        from PySide6.QtWidgets import QMessageBox
        box = QMessageBox()
        box.setWindowTitle("Accessibility Permission Needed")
        box.setIcon(QMessageBox.Warning)
        box.setText(
            "HandMouse needs Accessibility permission to send keyboard/mouse "
            "input for gestures (mouse, subway, racing, custom modes).\n\n"
            "1. Click \"Open System Settings\" below.\n"
            "2. Turn HandMouse ON in the Accessibility list (if it's already "
            "listed but greyed out, remove it first with the − button, then "
            "re-add it and check it).\n"
            "3. Come back here and click \"Done\"."
        )
        open_btn = box.addButton("Open System Settings", QMessageBox.ActionRole)
        done_btn = box.addButton("Done", QMessageBox.AcceptRole)
        box.setDefaultButton(done_btn)
        while True:
            box.exec()
            if box.clickedButton() is open_btn:
                subprocess.run([
                    'open',
                    'x-apple.systempreferences:com.apple.preference.security'
                    '?Privacy_Accessibility',
                ])
                continue
            break


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


def _acquire_single_instance_lock():
    lock_dir = os.path.join(os.path.expanduser('~'), '.handmouse')
    os.makedirs(lock_dir, exist_ok=True)
    lock_path = os.path.join(lock_dir, 'handmouse.lock')
    fh = open(lock_path, 'w')
    try:
        if sys.platform == 'win32':
            import msvcrt
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        return None
    return fh


if __name__ == "__main__":
    if '-c' in sys.argv:
        exec(sys.argv[sys.argv.index('-c') + 1])
        sys.exit(0)

    if len(sys.argv) >= 2 and sys.argv[1] == '--multiprocessing-fork':
        from multiprocessing.spawn import spawn_main
        _mp_kwds = {}
        for _arg in sys.argv[2:]:
            _name, _value = _arg.split('=')
            _mp_kwds[_name] = None if _value == 'None' else int(_value)
        spawn_main(**_mp_kwds)
        sys.exit(0)

    _log_lifecycle(f"process started argv={sys.argv!r} frozen={getattr(sys, 'frozen', False)}")

    if len(sys.argv) > 1 and sys.argv[1] == "--run-hockey":
        _run_hockey_subprocess()
        sys.exit(0)

    if len(sys.argv) > 2 and sys.argv[1] == "--run-pipeline":
        _run_pipeline_subprocess(sys.argv[2])
        sys.exit(0)

    if getattr(sys, 'frozen', False):
        _single_instance_lock = _acquire_single_instance_lock()
        if _single_instance_lock is None:
            _log_lifecycle("single-instance lock denied - exiting")
            sys.exit(0)
        _log_lifecycle("single-instance lock acquired")

    _install_global_excepthook()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    _check_mac_accessibility_permission()
    window = MainWindow()
    blocker = _GestureKeyBlocker(window)
    app.installEventFilter(blocker)
    window.show()
    exit_code = app.exec()
    _log_lifecycle(f"app.exec() returned exit_code={exit_code}")

    import atexit
    atexit._run_exitfuncs()
    _log_lifecycle("about to os._exit()")
    os._exit(exit_code)
