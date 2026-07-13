from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QEvent, QTimer

class AirHockeyLoadingOverlay(QWidget):
    def __init__(self, stack):
        super().__init__(stack)
        self.stack = stack
        self.is_dark = False

        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background: transparent;")

        self.dim_bg = QWidget(self.stack)
        self.dim_bg.setStyleSheet("background-color: rgba(0, 0, 0, 140);")
        self.dim_bg.setAttribute(Qt.WA_StyledBackground, True)
        self.dim_bg.hide()

        self.card = QWidget(self.stack)
        self.card.setFixedSize(260, 120)
        cv = QVBoxLayout(self.card)
        cv.setContentsMargins(20, 20, 20, 20)
        cv.setSpacing(8)

        self.icon_lbl = QLabel("🏒")
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setStyleSheet("font-size: 28px; background: transparent; border: none;")
        cv.addWidget(self.icon_lbl)

        self.text_lbl = QLabel("SWITCHING TO AIR HOCKEY")
        self.text_lbl.setAlignment(Qt.AlignCenter)
        self.text_lbl.setWordWrap(True)
        cv.addWidget(self.text_lbl)

        self.dots_lbl = QLabel("")
        self.dots_lbl.setAlignment(Qt.AlignCenter)
        cv.addWidget(self.dots_lbl)

        self.card.hide()

        self._dots_timer = QTimer(self)
        self._dots_timer.setInterval(350)
        self._dots_timer.timeout.connect(self._tick_dots)
        self._dot_count = 0

        self.stack.installEventFilter(self)
        self._reposition()
        self.apply_theme(False)
        self.hide()

    def eventFilter(self, obj, event):
        if obj is self.stack and event.type() in (QEvent.Resize, QEvent.Show):
            self._reposition()
        return False

    def _reposition(self):
        self.setGeometry(0, 0, self.stack.width(), self.stack.height())
        self.dim_bg.setGeometry(0, 0, self.stack.width(), self.stack.height())
        x = (self.stack.width() - self.card.width()) // 2
        y = (self.stack.height() - self.card.height()) // 2
        self.card.move(max(0, x), max(0, y))

    def _tick_dots(self):
        self._dot_count = (self._dot_count + 1) % 4
        self.dots_lbl.setText("." * self._dot_count)

    def show_loading(self, text: str = "SWITCHING TO AIR HOCKEY"):
        self.text_lbl.setText(text)
        self._reposition()
        self.dim_bg.show()
        self.dim_bg.raise_()
        self.card.show()
        self.card.raise_()
        self.show()
        self.raise_()
        self._dot_count = 0
        self._dots_timer.start()

    def hide_loading(self):
        self._dots_timer.stop()
        self.dim_bg.hide()
        self.card.hide()
        self.hide()

    def apply_theme(self, is_dark: bool):
        self.is_dark = is_dark
        if is_dark:
            card_bg = "#111111"; border = "#262626"; text = "#e8e8e8"; dim = "#9a9a9a"
        else:
            card_bg = "#FFFFFF"; border = "#D8CEC7"; text = "#111111"; dim = "#6F655F"

        self.card.setStyleSheet(
            f"background-color: {card_bg}; border: 1px solid {border}; border-radius: 6px;")
        self.text_lbl.setStyleSheet(
            f"font-size: 10px; font-weight: 700; letter-spacing: 1.2px; "
            f"color: {text}; background: transparent; border: none;")
        self.dots_lbl.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {dim}; background: transparent; border: none;")
