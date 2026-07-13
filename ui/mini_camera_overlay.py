import sys

from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage

_IMAGE_HEIGHT = 190


def _apply_macos_always_on_top(widget):
    try:
        import objc
        from AppKit import (
            NSWindowCollectionBehaviorCanJoinAllSpaces,
            NSWindowCollectionBehaviorFullScreenAuxiliary,
            NSStatusWindowLevel,
        )
    except ImportError:
        return
    ns_view = objc.objc_object(c_void_p=int(widget.winId()))
    ns_window = ns_view.window()
    if ns_window is None:
        return
    ns_window.setLevel_(NSStatusWindowLevel)
    ns_window.setCollectionBehavior_(
        NSWindowCollectionBehaviorCanJoinAllSpaces
        | NSWindowCollectionBehaviorFullScreenAuxiliary
    )

class MiniCameraOverlay(QWidget):
    def __init__(self, on_restore=None, parent=None):
        super().__init__(parent)
        self._on_restore = on_restore
        self._drag_offset = None
        self._press_pos = None

        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(260, _IMAGE_HEIGHT + 132)
        self.setStyleSheet("""
            background-color: #0a0a0a;
            border: 1px solid #3a3a3a;
            border-radius: 6px;
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.image_label = QLabel()
        self.image_label.setFixedHeight(_IMAGE_HEIGHT)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: none; border-radius: 6px 6px 0 0; background-color: #000000;")
        layout.addWidget(self.image_label)

        self.hint_label = QLabel("HandMouse · click to return", self)
        self.hint_label.setStyleSheet("""
            color: #E0E0E0;
            background-color: rgba(0, 0, 0, 160);
            font-size: 9px;
            padding: 2px 6px;
            border: none;
        """)
        self.hint_label.setGeometry(0, _IMAGE_HEIGHT - 20, 260, 20)

        info_panel = QWidget()
        info_panel.setStyleSheet("background-color: #141414; border-radius: 0 0 6px 6px;")
        info_layout = QGridLayout(info_panel)
        info_layout.setContentsMargins(10, 8, 10, 8)
        info_layout.setHorizontalSpacing(8)
        info_layout.setVerticalSpacing(4)
        info_layout.setColumnStretch(1, 1)

        self.mode_value = self._add_row(info_layout, 0, "MODE")
        self.status_value = self._add_row(info_layout, 1, "STATUS")
        self.gesture_value = self._add_row(info_layout, 2, "GESTURE")
        self.action_value = self._add_row(info_layout, 3, "ACTION")

        layout.addWidget(info_panel)

        hold_panel = QWidget()
        hold_panel.setStyleSheet("background-color: #141414; border-top: 1px solid #262626;")
        hold_layout = QVBoxLayout(hold_panel)
        hold_layout.setContentsMargins(10, 6, 10, 6)
        hold_layout.setSpacing(4)

        self.hold_label = QLabel("ACTION")
        self.hold_label.setStyleSheet("""
            color: #7a7a7a; font-size: 9px; font-weight: 700;
            letter-spacing: 1px; border: none; background: transparent;
        """)
        self.hold_bg = QWidget()
        self.hold_bg.setFixedHeight(3)
        self.hold_bg.setStyleSheet("background-color: #2a2a2a; border-radius: 1px;")
        self.hold_fill = QWidget(self.hold_bg)
        self.hold_fill.setGeometry(0, 0, 0, 3)
        self.hold_fill.setStyleSheet("background-color: #4da6ff; border-radius: 1px;")

        hold_layout.addWidget(self.hold_label)
        hold_layout.addWidget(self.hold_bg)

        layout.addWidget(hold_panel)

        self._position_default()

    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "darwin":
            _apply_macos_always_on_top(self)

    @staticmethod
    def _add_row(info_layout, row, key_text):
        key_lbl = QLabel(key_text)
        key_lbl.setStyleSheet("""
            color: #7a7a7a; font-size: 9px; font-weight: 600;
            letter-spacing: 1px; border: none; background: transparent;
        """)
        val_lbl = QLabel("--")
        val_lbl.setStyleSheet("""
            color: #E8E8E8; font-size: 10px; font-weight: 700;
            border: none; background: transparent;
        """)
        val_lbl.setAlignment(Qt.AlignRight)
        info_layout.addWidget(key_lbl, row, 0)
        info_layout.addWidget(val_lbl, row, 1)
        return val_lbl

    def _position_default(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        margin = 24
        self.move(geo.right() - self.width() - margin, geo.bottom() - self.height() - margin)

    def update_frame(self, image: QImage):
        pixmap = QPixmap.fromImage(image)
        self.image_label.setPixmap(
            pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        )

    def set_mode(self, text: str):
        self.mode_value.setText(text)

    def set_status(self, text: str):
        self.status_value.setText(text)

    def set_gesture(self, gesture: str, action: str):
        self.gesture_value.setText(gesture)
        self.action_value.setText(action)

    def show_hold(self, label: str, frac: float):
        self.hold_label.setText(f"● {label}")
        w = self.hold_bg.width()
        if w > 0:
            self.hold_fill.setGeometry(0, 0, int(frac * w), 3)

    def hide_hold(self):
        self.hold_label.setText("ACTION")
        self.hold_fill.setGeometry(0, 0, 0, 3)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self._drag_offset = self._press_pos - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            moved = False
            if self._press_pos is not None:
                moved = (event.globalPosition().toPoint() - self._press_pos).manhattanLength() > 6
            self._drag_offset = None
            self._press_pos = None
            if not moved and self._on_restore is not None:
                self._on_restore()
        super().mouseReleaseEvent(event)
