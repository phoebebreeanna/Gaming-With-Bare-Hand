import html
import threading

from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QFrame,
                                QGraphicsOpacityEffect, QTextEdit, QLineEdit, QDialog,
                                QProgressBar, QApplication)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QPoint, QEvent, QRect, QTimer
from PySide6.QtGui import QColor, QPen, QPixmap, QPainter, QPainterPath

from logic import app_config
from logic.chatbot_worker import ChatbotQueryThread, ModelDownloadThread


def _markdown_to_html(text: str) -> str:
    try:
        import markdown
        return markdown.markdown(text, extensions=["nl2br", "sane_lists"])
    except Exception:
        return f"<p>{html.escape(text).replace(chr(10), '<br>')}</p>"


class _CardDialog(QDialog):
    """Frameless, rounded-corner dialog card matching the app's flat style."""

    def __init__(self, parent=None, is_dark=False, width=340):
        super().__init__(parent)
        self.is_dark = is_dark
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedWidth(width)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame()
        self.card.setObjectName("cardDialog")
        outer.addWidget(self.card)

        self.body = QVBoxLayout(self.card)
        self.body.setContentsMargins(24, 22, 24, 22)
        self.body.setSpacing(12)

    def _palette(self):
        return dict(
            card_bg="#111111" if self.is_dark else "#FFFFFF",
            border="#262626" if self.is_dark else "#E5E5E5",
            text="#E8E8E8" if self.is_dark else "#111111",
            muted="#9A9A9A" if self.is_dark else "#6B6B6B",
            input_bg="#1A1A1A" if self.is_dark else "#F1F1F1",
            primary_bg="#E8E8E8" if self.is_dark else "#000000",
            primary_text="#0A0A0A" if self.is_dark else "#FFFFFF",
        )

    def _style_card(self):
        p = self._palette()
        self.card.setStyleSheet(f"""
            QFrame#cardDialog {{
                background: {p['card_bg']};
                border-radius: 14px;
                border: 1px solid {p['border']};
            }}
        """)
        return p


class ModelDownloadPromptDialog(_CardDialog):
    """Asks the user to confirm the one-time chatbot model download."""

    def __init__(self, parent=None, is_dark=False):
        super().__init__(parent, is_dark)

        title = QLabel("Download Chatbot Model")
        title.setAlignment(Qt.AlignCenter)
        self.body.addWidget(title)

        subtitle = QLabel(
            "HandBot needs to download its AI model (about 2 GB) the first "
            "time it's used. This only happens once."
        )
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignCenter)
        self.body.addWidget(subtitle)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.not_now_btn = QPushButton("Not Now")
        self.not_now_btn.setCursor(Qt.PointingHandCursor)
        self.not_now_btn.setFixedHeight(34)
        self.not_now_btn.clicked.connect(self.reject)
        self.download_btn = QPushButton("Download")
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.setFixedHeight(34)
        self.download_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.not_now_btn)
        btn_row.addWidget(self.download_btn)
        self.body.addLayout(btn_row)

        p = self._style_card()
        title.setStyleSheet(f"font-size:15px; font-weight:700; color:{p['text']}; background:transparent; border:none;")
        subtitle.setStyleSheet(f"font-size:12px; color:{p['muted']}; background:transparent; border:none;")
        self.not_now_btn.setStyleSheet(f"""
            QPushButton {{
                background: {p['card_bg']}; color: {p['text']};
                border: 1px solid {p['border']}; border-radius: 8px;
                font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {p['input_bg']}; }}
        """)
        self.download_btn.setStyleSheet(f"""
            QPushButton {{
                background: {p['primary_bg']}; color: {p['primary_text']};
                border: none; border-radius: 8px;
                font-size: 12px; font-weight: 700;
            }}
        """)


class ModelDownloadDialog(_CardDialog):
    """Progress card shown while the chatbot's GGUF model downloads."""

    def __init__(self, parent=None, is_dark=False):
        super().__init__(parent, is_dark)

        title = QLabel("Setting Up Chatbot")
        title.setAlignment(Qt.AlignCenter)
        self.body.addWidget(title)

        self.status_lbl = QLabel("Starting download…")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setAlignment(Qt.AlignCenter)
        self.body.addWidget(self.status_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(10)
        self.body.addWidget(self.progress_bar)

        self.pct_lbl = QLabel("0%")
        self.pct_lbl.setAlignment(Qt.AlignCenter)
        self.body.addWidget(self.pct_lbl)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.setFixedHeight(34)
        self.cancel_btn.clicked.connect(self._on_cancel)
        self.body.addWidget(self.cancel_btn)

        p = self._style_card()
        title.setStyleSheet(f"font-size:15px; font-weight:700; color:{p['text']}; background:transparent; border:none;")
        self.status_lbl.setStyleSheet(f"font-size:12px; color:{p['muted']}; background:transparent; border:none;")
        self.pct_lbl.setStyleSheet(f"font-size:11px; font-weight:600; color:{p['muted']}; background:transparent; border:none;")
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {p['input_bg']};
                border: none;
                border-radius: 5px;
            }}
            QProgressBar::chunk {{
                background-color: {p['primary_bg']};
                border-radius: 5px;
            }}
        """)
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {p['card_bg']}; color: {p['text']};
                border: 1px solid {p['border']}; border-radius: 8px;
                font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {p['input_bg']}; }}
        """)

        self._cancelling = False
        self._cancel_event = threading.Event()
        self._thread = ModelDownloadThread(self._cancel_event, self)
        self._thread.progress.connect(self._on_progress)
        self._thread.finished_ok.connect(self.accept)
        self._thread.failed.connect(self._on_failed)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.start()

    def _on_progress(self, downloaded: int, total: int):
        mb_done = downloaded / (1024 * 1024)
        self.status_lbl.setText("Downloading the chatbot's AI model…")
        if total:
            pct = min(int(downloaded * 100 / total), 100)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(pct)
            mb_total = total / (1024 * 1024)
            self.pct_lbl.setText(f"{pct}%  ·  {mb_done:.0f} MB / {mb_total:.0f} MB")
        else:
            self.progress_bar.setRange(0, 0)
            self.pct_lbl.setText(f"{mb_done:.0f} MB downloaded")

    def _on_cancel(self):
        if self._cancelling:
            return
        self._cancelling = True
        self._cancel_event.set()
        self.cancel_btn.setEnabled(False)
        self.status_lbl.setText("Cancelling…")

    def _on_failed(self, message: str):
        self.status_lbl.setText(message)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.pct_lbl.setText("")
        self.cancel_btn.setText("Close")

    def _on_thread_finished(self):
        if self._cancelling:
            QDialog.reject(self)

    def closeEvent(self, event):
        if self._thread.isRunning():
            self._cancelling = True
            self._cancel_event.set()
            self.cancel_btn.setEnabled(False)
            self.status_lbl.setText("Cancelling…")
            event.ignore()
            return
        super().closeEvent(event)


def ensure_model_ready(parent: QWidget, is_dark: bool = False) -> bool:
    """Returns True if the chatbot model is ready to use, prompting the user
    to download it first if it isn't."""
    from logic.chatbot import rag_service

    if rag_service.is_primary_model_ready():
        return True

    prompt = ModelDownloadPromptDialog(parent, is_dark=is_dark)
    if prompt.exec() != QDialog.Accepted:
        return False

    dialog = ModelDownloadDialog(parent, is_dark=is_dark)
    return dialog.exec() == QDialog.Accepted


# --- HandBot image assets ---
HANDBOT_EXPLAINING = "assets/handbot/handbot_explaining.png"
HANDBOT_NEUTRAL = "assets/handbot/handbot_neutral_icon.png"
HANDBOT_CELEBRATING = "assets/handbot/handbot_celebrating.png"  


def make_circular_pixmap(source_pixmap: QPixmap, diameter: int, bg_color: str, border_color: str, padding_ratio: float = 0.78) -> QPixmap:
    """Returns a circularly-clipped pixmap with a solid background circle
    (so it matches the app's light/dark theme) and padding around the character."""
    result = QPixmap(diameter, diameter)
    result.fill(Qt.transparent)

    painter = QPainter(result)
    painter.setRenderHint(QPainter.Antialiasing)

    path = QPainterPath()
    path.addEllipse(0, 0, diameter, diameter)
    painter.setClipPath(path)

    painter.setBrush(QColor(bg_color))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(0, 0, diameter, diameter)

    inner_size = int(diameter * padding_ratio)
    scaled = source_pixmap.scaled(inner_size, inner_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    offset_x = (diameter - scaled.width()) // 2
    offset_y = (diameter - scaled.height()) // 2
    painter.drawPixmap(offset_x, offset_y, scaled)

    painter.setClipping(False)
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(QColor(border_color), 1))
    painter.drawEllipse(0, 0, diameter - 1, diameter - 1)

    painter.end()
    return result


popup_content = {
    "guide_intro": {
        "body": ("<b>Hi! I am Handbot</b><br><br>"
                 "I am your friendly guide to help you get started with HandMouse.<br><br>"
                 "HandMouse is developed by <b>FYP-26-S2-02</b>, a team of six from SIM - University of Wollongong. <br><br>"
                 "Before jumping into the application, would you like me to guide you through the first-time setup?"
                 ),
        "button": [("Yes - Guide me through", "guide_yes"), ("Skip - I will explore myself", "guide_no")],
    },

    "guide_overview": {
        "body": ("<b>Great ! Here is what we will do:</b><br><br>"
                 "I will guide you through 4 quick steps:<br>"
                 "01 - Read the Setup Guide<br>"
                 "02 - Select your camera<br>"
                 "03 - Calibrate your distance<br>"
                 "04 - Choose your movement zone<br><br>"
                 "I will appear at each step to guide you. Click OK to begin!"
                 ),
        "button": [("OK", "press ok")],
    },

    "camera": {
        "body": ("<b>Select your camera !</b><br><br>"
                 "Choose your camera from the dropdown.<br><br>"
                 "Check the preview looks correct - you should see yourself clearly.<br><br>"
                 "Then click <b>Continue</b> to proceed to the next step."
                 ),
        "button": [("OK", "press ok")],
    },

    "calibration": {
        "body": ("<b>Calibrate your distance !</b><br><br>"
                 "Hold your palm facing the camera at arm's length.<br><br>"
                 "Move until the gauge shows <span style='color: #008000;'><b>OPTIMAL</b></span> in green,then hold for 3 seconds - I will automatically move you to the next step!"
                 ),
        "button": [("OK", "press ok")],
    },

    "zone": {
        "body": ("<b>Choose your movement zone !</b><br><br>"
                 "Show 1,2,3 fingers to the camera to select or click your preferred option directly.<br><br>"
                 "Hold for 3 seconds to auto-advance to Home dashboard. <br><br>"
                 "You can always change your zone later in the settings."
                 ),
        "button": [("OK", "press ok")],
    }
}

step_for_index = {1: "guide_intro", 2: "camera", 3: "calibration", 4: "zone"}
default_card_width = 340
card_width_for_content = {"guide_intro": 340, "guide_overview": 340, "camera": 340}


class HandBotCard(QFrame):
    """The white popup card with HandBot's message and buttons."""
    action = Signal(str)
    action_signal = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_dark = False
        self.setObjectName("handbotCard")
        self.setFixedWidth(default_card_width)
        self._build()
        self.apply_theme(self.is_dark)

        # --- Pop-in animation setup ---
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        head = QHBoxLayout()
        head.setSpacing(10)

        # --- CHANGED: real HandBot image instead of emoji ---
        icon_lbl = QLabel()
        icon_lbl.setStyleSheet("background:transparent; border:none;")
        pixmap = QPixmap(HANDBOT_EXPLAINING)
        icon_lbl.setPixmap(pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        head.addWidget(icon_lbl)
        self.card_icon_lbl = icon_lbl

        title_lbl = QLabel("HandBot")
        title_lbl.setStyleSheet(
            "font-size:16px; font-weight:700; color:#111; "
            "background:transparent; border:none;")
        head.addWidget(title_lbl)
        self.title_lbl = title_lbl
        head.addStretch()
        layout.addLayout(head)

        self.body_box = QFrame()
        self.body_box.setObjectName("handbotBodyBox")
        body_layout = QVBoxLayout(self.body_box)
        body_layout.setContentsMargins(10, 10, 10, 10)

        self.body_lbl = QLabel("")
        self.body_lbl.setTextFormat(Qt.RichText)
        self.body_lbl.setWordWrap(True)
        body_layout.addWidget(self.body_lbl)
        layout.addWidget(self.body_box)

        self.btn_row = QVBoxLayout()
        self.btn_row.setSpacing(10)
        layout.addLayout(self.btn_row)

    def set_content(self, key):
        data = popup_content.get(key)
        self.setFixedWidth(card_width_for_content.get(key, default_card_width))
        self.setMinimumHeight(340 if key == "guide_overview" else 0)
        self.body_lbl.setFixedWidth(self.width() - 64)
        self.body_lbl.setText(data["body"])
        self.body_lbl.adjustSize()

        while self.btn_row.count():
            item = self.btn_row.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        for i, (label, action_id) in enumerate(data['button']):
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("action_id", action_id)
            self._style_button(btn, action_id)
            btn.clicked.connect(lambda _, a=action_id: self.action.emit(a))
            self.btn_row.addWidget(btn)

        self.layout().invalidate()
        self.layout().activate()
        self.adjustSize()

    def play_pop_in(self):
        """Scale + fade entrance animation. Call this right after the
        card is positioned and shown."""
        final_geometry = self.geometry()
        start_geometry = QRect(
            final_geometry.center().x() - int(final_geometry.width() * 0.4),
            final_geometry.center().y() - int(final_geometry.height() * 0.4),
            int(final_geometry.width() * 0.8),
            int(final_geometry.height() * 0.8),
        )
        self.setGeometry(start_geometry)
        self.opacity_effect.setOpacity(0.0)

        self.scale_anim = QPropertyAnimation(self, b"geometry")
        self.scale_anim.setDuration(300)
        self.scale_anim.setStartValue(start_geometry)
        self.scale_anim.setEndValue(final_geometry)
        self.scale_anim.setEasingCurve(QEasingCurve.OutCubic)

        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(300)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)

        self.scale_anim.start()
        self.fade_anim.start()

    def apply_theme(self, is_dark):
        self.is_dark = is_dark

        card_bg = "#111111" if is_dark else "#FFFFFF"
        body_bg = "#1A1A1A" if is_dark else "#EEEEEE"
        border = "#262626" if is_dark else "#E5E5E5"
        text = "#E8E8E8" if is_dark else "#111111"

        self.setStyleSheet(f"""
            QFrame#handbotCard {{
                background: {card_bg};
                border-radius: 4px;
                border: 1px solid {border};
            }}
        """)
        self.body_box.setStyleSheet(f"""
            QFrame#handbotBodyBox {{
                background: {body_bg};
                border: none;
                border-radius: 4px;
            }}
        """)
        self.body_lbl.setStyleSheet(
            f"font-size:12px; color:{text}; background:transparent; border:none;")
        self.title_lbl.setStyleSheet(
            f"font-size:16px; font-weight:700; color:{text}; background:transparent; border:none;")

        for i in range(self.btn_row.count()):
            widget = self.btn_row.itemAt(i).widget()
            if widget:
                self._style_button(widget, widget.property("action_id"))

    def _style_button(self, btn, action_id):
        if self.is_dark:
            primary_bg = "#E8E8E8"
            primary_text = "#0A0A0A"
            primary_hover = "#FFFFFF"
            primary_pressed = "#CFCFCF"
            secondary_bg = "#111111"
            secondary_text = "#E8E8E8"
            secondary_border = "#3A3A3A"
            secondary_hover = "#1A1A1A"
            secondary_pressed = "#262626"
        else:
            primary_bg = "#000000"
            primary_text = "#FFFFFF"
            primary_hover = "#222222"
            primary_pressed = "#444444"
            secondary_bg = "#FFFFFF"
            secondary_text = "#111111"
            secondary_border = "#D8D8D8"
            secondary_hover = "#F3F3F3"
            secondary_pressed = "#E6E6E6"

        if action_id in ("guide_no", "guide_skip"):
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {secondary_bg};
                    color: {secondary_text};
                    border: 1px solid {secondary_border};
                    border-radius: 4px;
                    padding: 10px 18px;
                    font-size: 12px;
                }}
                QPushButton:hover {{ background: {secondary_hover}; }}
                QPushButton:pressed {{ background: {secondary_pressed}; }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {primary_bg};
                    color: {primary_text};
                    border: none;
                    border-radius: 4px;
                    padding: 10px 18px;
                    font-size: 12px;
                }}
                QPushButton:hover {{ background: {primary_hover}; }}
                QPushButton:pressed {{ background: {primary_pressed}; }}
            """)

class HandBotChatPanel(QFrame):
    ### The floating chat panel that appears when the HandBot icon is clicked on the Home dashboard.
    closed = Signal()

    MIN_WIDTH = 300
    MAX_WIDTH = 420
    MIN_HEIGHT = 315
    MAX_HEIGHT = 620

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_dark = False
        self.setObjectName("handbotChatPanel")
        self.setFixedWidth(self.MIN_WIDTH)
        self.setFixedHeight(self.MIN_HEIGHT)
        self._build()
        self.apply_theme(self.is_dark)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

    def resize_to_fit(self, available_width: int, available_height: int):
        target_w = int(available_width * 0.34)
        target_h = int(available_height * 0.62)
        width = max(self.MIN_WIDTH, min(target_w, self.MAX_WIDTH, available_width - 24))
        height = max(self.MIN_HEIGHT, min(target_h, self.MAX_HEIGHT, available_height - 24))
        self.setFixedSize(width, height)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(50)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 12, 0)

        self.header_title = QLabel("HandBot")
        self.header_title.setStyleSheet("font-size:14px; font-weight:600; background:transparent; border:none;")
        header_layout.addWidget(self.header_title)
        header_layout.addStretch()

        close_btn = QPushButton("✗")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton{background:transparent; border:none; font-size:18px;} QPushButton:hover{color:#999;}")
        close_btn.clicked.connect(self.closed.emit)
        header_layout.addWidget(close_btn)
        layout.addWidget(header)
        self.header = header

        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(12, 12, 12, 12)
        self.content_layout.setSpacing(8)
        layout.addWidget(self.content_area, stretch=1)

        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setPlaceholderText("Ask me anything about gestures, setup, or HandMouse.")
        self.transcript.document().setDefaultStyleSheet(
            "p, ul, ol { margin: 0; padding: 0; }"
            "li { margin: 0 0 2px 18px; }"
            ".sender { margin: 0 0 2px 0; }"
            ".spacer { margin: 0; line-height: 14px; }"
        )
        self.content_layout.addWidget(self.transcript, stretch=1)

        self.typing_lbl = QLabel("")
        self.typing_lbl.hide()
        self.content_layout.addWidget(self.typing_lbl)

        self._typing_timer = QTimer(self)
        self._typing_timer.setInterval(400)
        self._typing_timer.timeout.connect(self._tick_typing)
        self._typing_frame = 0

        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Type a message…")
        self.input_box.returnPressed.connect(self._on_send)
        input_row.addWidget(self.input_box, stretch=1)

        self.send_btn = QPushButton("Send")
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self._on_send)
        input_row.addWidget(self.send_btn)

        self.content_layout.addLayout(input_row)

        self._query_thread = None
        self._messages = []

    def _append_line(self, sender: str, text: str, is_markdown: bool = False):
        body = _markdown_to_html(text) if is_markdown else html.escape(text)
        self._messages.append((sender, body))
        self._render_transcript()

    def _render_transcript(self):
        blocks = []
        for sender, body in self._messages:
            blocks.append(
                f'<p class="sender"><b>{sender}:</b></p>'
                f'{body}'
                f'<p class="spacer">&nbsp;</p>'
            )
        self.transcript.setHtml("".join(blocks))
        scrollbar = self.transcript.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_send(self):
        question = self.input_box.text().strip()
        if not question or self._query_thread is not None:
            return

        self._append_line("You", question)
        self.input_box.clear()

        if not app_config.get_chatbot_enabled():
            self._append_line("HandBot", "Chatbot is disabled - enable it in Settings.")
            return

        self.input_box.setEnabled(False)
        self.send_btn.setEnabled(False)
        self._show_typing()

        self._query_thread = ChatbotQueryThread(question, self)
        self._query_thread.answer_ready.connect(self._on_answer_ready)
        self._query_thread.answer_failed.connect(self._on_answer_failed)
        self._query_thread.finished.connect(self._on_query_finished)
        self._query_thread.start()

    def _show_typing(self):
        self._typing_frame = 0
        self.typing_lbl.setText("HandBot is thinking")
        self.typing_lbl.show()
        self._typing_timer.start()

    def _tick_typing(self):
        self._typing_frame = (self._typing_frame + 1) % 4
        self.typing_lbl.setText("HandBot is thinking" + "." * self._typing_frame)

    def _hide_typing(self):
        self._typing_timer.stop()
        self.typing_lbl.hide()

    def _on_answer_ready(self, answer: str):
        self._hide_typing()
        self._append_line("HandBot", answer, is_markdown=True)

    def _on_answer_failed(self, message: str):
        self._hide_typing()
        self._append_line("HandBot", message)

    def _on_query_finished(self):
        self._hide_typing()
        self.input_box.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.input_box.setFocus()
        self._query_thread = None

    def apply_theme(self, is_dark):
        self.is_dark = is_dark
        bg = "#111111" if is_dark else "#FFFFFF"
        border = "#262626" if is_dark else "#E5E5E5"
        text = "#E8E8E8" if is_dark else "#111111"
        input_bg = "#1A1A1A" if is_dark else "#F4F4F4"
        self.setStyleSheet(f"""
            QFrame#handbotChatPanel {{
                background: {bg};
                border-radius: 10px;
                border: 2px solid {border};
            }}
        """)
        self.header.setStyleSheet(f"background:transparent; border-bottom:1px solid {border};")
        self.header_title.setStyleSheet(f"font-size:14px; font-weight:600; color:{text}; background:transparent; border:none;")
        muted = "#8A8A8A" if is_dark else "#777777"
        self.typing_lbl.setStyleSheet(
            f"font-size:11px; font-style:italic; color:{muted}; background:transparent; border:none;")
        scroll_track = "#1A1A1A" if is_dark else "#F4F4F4"
        scroll_handle = "#3A3A3A" if is_dark else "#C9C9C9"
        scroll_handle_hover = "#555555" if is_dark else "#AFAFAF"
        self.transcript.setStyleSheet(f"""
            QTextEdit {{
                background: {input_bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 6px;
                font-size: 12px;
                padding: 6px;
            }}
            QScrollBar:vertical {{
                width: 4px;
                background: {scroll_track};
                border: none;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {scroll_handle};
                border-radius: 2px;
                min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {scroll_handle_hover}; }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{ background: none; }}
        """)
        self.input_box.setStyleSheet(f"""
            QLineEdit {{
                background: {input_bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 6px;
                font-size: 12px;
                padding: 6px;
            }}
        """)
        primary_bg = "#E8E8E8" if is_dark else "#000000"
        primary_text = "#0A0A0A" if is_dark else "#FFFFFF"
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {primary_bg};
                color: {primary_text};
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
            }}
        """)

    def play_pop_in(self):
        final_geometry = self.geometry()
        start_geometry = QRect(
            final_geometry.center().x() - int(final_geometry.width() * 0.4),
            final_geometry.center().y() - int(final_geometry.height() * 0.4),
            int(final_geometry.width() * 0.8),
            int(final_geometry.height() * 0.8),
        )
        self.setGeometry(start_geometry)
        self.opacity_effect.setOpacity(0.0)

        self.scale_anim = QPropertyAnimation(self, b"geometry")
        self.scale_anim.setDuration(300)
        self.scale_anim.setStartValue(start_geometry)
        self.scale_anim.setEndValue(final_geometry)
        self.scale_anim.setEasingCurve(QEasingCurve.OutCubic)

        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(300)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)

        self.scale_anim.start()
        self.fade_anim.start()

#draggable icon 
class HandBotIcon(QLabel):
    """Floating HandBot icon that can be dragged around the screen."""
    clicked = Signal()
    position_reset = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(52, 52)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)
        self.setScaledContents(False)
        self.setStyleSheet("background: transparent; border: none;")
        self.apply_theme(False)

        self._dragging = False
        self._drag_offset = QPoint()
        self._press_pos = QPoint()
        self._moved = False
        self._bounce_paused = False
        self._ignore_next_release = False

        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(1400)
        self._anim.setEasingCurve(QEasingCurve.InOutSine)
        self._anim.setLoopCount(-1)

        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.setInterval(200)
        self._click_timer.timeout.connect(self.clicked.emit)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._anim.stop()
            self._dragging = True
            self._moved = False
            self._drag_offset = e.pos()
            self._press_pos = e.pos()

    def mouseMoveEvent(self, e):
        if self._dragging:
            if not self._moved:
                delta = e.pos() - self._press_pos
                if delta.manhattanLength() < QApplication.startDragDistance():
                    return
                self._moved = True
            new_pos = self.mapToParent(e.pos() - self._drag_offset)
            parent = self.parentWidget()
            if parent:
                new_pos.setX(max(0, min(new_pos.x(), parent.width() - self.width())))
                new_pos.setY(max(0, min(new_pos.y(), parent.height() - self.height())))
            self.move(new_pos)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._dragging = False
            if self._ignore_next_release:
                self._ignore_next_release = False
            elif not self._moved:
                self._click_timer.start()
            if self.isVisible() and not self._bounce_paused:
                self.start_idle_bounce()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._click_timer.stop()
            self._ignore_next_release = True
            self.reset_position()
            e.accept()

    def reset_position(self):
        parent = self.parentWidget()
        if not parent:
            return
        self._anim.stop()
        self._dragging = False
        self._moved = False
        self.move(parent.width() - self.width() - 1, 110)
        self.position_reset.emit()
        if self.isVisible() and not self._bounce_paused:
            self.start_idle_bounce()

    def start_idle_bounce(self):
        if self._bounce_paused:
            return
        base = self.pos()
        self._anim.stop()
        self._anim.setStartValue(base)
        self._anim.setKeyValueAt(0.5, base + QPoint(0, -6))
        self._anim.setEndValue(base)
        self._anim.start()
        
    def play_celebrate(self, duration_ms=1200):
        bg_color = "#111111" if self.is_dark else "#FFFFFF"
        border = "#E8E8E8" if self.is_dark else "#D8CEC7"
        source = QPixmap(HANDBOT_CELEBRATING)
        circular = make_circular_pixmap(source, self.width(), bg_color, border)
        self.setPixmap(circular)

        self._anim.stop()
        base = self.pos()
        self._anim.setStartValue(base)
        self._anim.setKeyValueAt(0.3, base + QPoint(0, -10))
        self._anim.setEndValue(base)
        self._anim.setLoopCount(1)  
        self._anim.start()

        QTimer.singleShot(duration_ms, self._end_celebrate)

    def _end_celebrate(self):
        self.apply_theme(self.is_dark)  
        self._anim.setLoopCount(-1)  
        if not self._bounce_paused:
            self.start_idle_bounce()

    def apply_theme(self, is_dark):
        self.is_dark = is_dark
        bg_color = "#111111" if is_dark else "#FFFFFF"
        border = "#E8E8E8" if is_dark else "#D8CEC7"
        source = QPixmap(HANDBOT_NEUTRAL)
        circular = make_circular_pixmap(source, self.width(), bg_color, border)
        self.setPixmap(circular)
        
        


class HandBotOverlay(QWidget):
    def __init__(self, stack):
        super().__init__(stack)
        self.stack = stack
        self.guide_enabled = False
        self._intro_shown = False
        self._current_key = None
        self.is_dark = False

        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setStyleSheet("background: transparent;")

        self.dim_bg = QWidget(self.stack)
        self.dim_bg.setStyleSheet("background-color: rgba(0, 0, 0, 60);")
        self.dim_bg.setAttribute(Qt.WA_StyledBackground, True)
        self.dim_bg.hide()

        self.icon = HandBotIcon(self.stack)
        self.icon.hide()
        self.icon.clicked.connect(self._on_icon_clicked)
        self.icon.position_reset.connect(self._on_icon_position_reset)

        self.card = HandBotCard(self.stack)
        self.card.hide()
        self.card.action.connect(self._on_action)

        self.chat_panel = HandBotChatPanel(self.stack)
        self.chat_panel.hide()
        self.chat_panel.closed.connect(self._hide_chat)

        self.stack.installEventFilter(self)
        self.stack.currentChanged.connect(self._on_step_changed)
        self._on_step_changed(self.stack.currentIndex())

        self._reposition()
        self.show()
        self.raise_()
        
        self.celebrate_toast = HandBotCelebrateToast(self.stack)
        self.celebrate_toast.hide()

    def apply_theme(self, is_dark):
        self.is_dark = is_dark
        self.icon.apply_theme(is_dark)
        self.card.apply_theme(is_dark)
        self.chat_panel.apply_theme(is_dark)
        self.celebrate_toast.apply_theme(is_dark)

    def eventFilter(self, obj, event):
        if obj is self.stack and event.type() in (QEvent.Resize, QEvent.Show):
            self._reposition()
        return False

    def _reposition(self):
        self.setGeometry(0, 0, self.stack.width(), self.stack.height())
        self.dim_bg.setGeometry(0, 0, self.stack.width(), self.stack.height())  # NEW
        if not self.icon._dragging and not self.icon._moved:
            self.icon._anim.stop()
            self.icon.move(self.width() - self.icon.width() - 1, 110)
            if self.icon.isVisible():
                self.icon.start_idle_bounce()
        self._center_card()

    def _center_card(self):
        if self.card.isVisible():
            self.card.adjustSize()
            x = (self.width() - self.card.width()) // 2
            y = (self.height() - self.card.height()) // 2
            self.card.move(x, y)

    def _on_step_changed(self, index): #icon appears on the home dashboard 
        self.raise_()
        if index == 0:
            self.dim_bg.hide()
            self._hide_card()
            self._hide_chat()
            self.icon.hide()
            return

        key = step_for_index.get(index)

        if key == 'guide_intro' and not self._intro_shown:
            self._intro_shown = True
            self.dim_bg.show()
            self.dim_bg.raise_()
            self.icon.hide()  # icon stays hidden until Skip/Yes dismisses the intro
            self._show_card('guide_intro')
            return

        self.icon.show()
        self.icon.raise_()
        self.icon.start_idle_bounce()
        key = step_for_index.get(index)
        if key is None:
            return

        if key == 'guide_intro' and not self._intro_shown:
            self._intro_shown = True
            self._show_card('guide_intro')
        elif key != 'guide_intro' and self.guide_enabled:
            self._show_card(key)
        else:
            self._current_key = key
            self._hide_card()

    def _show_card(self, key):
        self._current_key = key
        self.icon._bounce_paused = True
        self.icon._anim.stop()
        self.card.set_content(key)
        self.card.show()
        self.card.raise_()
        self._center_card()
        self.card.play_pop_in()  # --- CHANGED: animate every card appearance ---

    def _hide_card(self):
        self.card.hide()
        self.icon._bounce_paused = False
        if self.icon.isVisible():
            self.icon.start_idle_bounce()

    def _on_icon_clicked(self):
        if self.stack.currentIndex() == 0:
            if self.chat_panel.isVisible():
                self._hide_chat()
            elif ensure_model_ready(self, self.is_dark):
                self._show_chat()
            return

        if self.card.isVisible():
            self._hide_card()
            return

        key = self._current_key or step_for_index.get(self.stack.currentIndex())
        if key:
            self._show_card(key)

    def _show_chat(self):
        self.icon._bounce_paused = True
        self.icon._anim.stop()
        self.chat_panel.show()
        self.chat_panel.raise_()
        self._position_chat()
        self.chat_panel.play_pop_in()

    def _position_chat(self):
        gap = 12
        self.chat_panel.resize_to_fit(self.width(), self.height())
        x = self.icon.x() - self.chat_panel.width() - gap
        if x < gap:
            x = self.icon.x() + self.icon.width() + gap
        x = max(gap, min(x, self.width() - self.chat_panel.width() - gap))
        y = self.icon.y()
        y = max(gap, min(y, self.height() - self.chat_panel.height() - gap))
        self.chat_panel.move(x, y)

    def _on_icon_position_reset(self):
        if self.chat_panel.isVisible():
            self._position_chat()

    def _hide_chat(self):
        self.chat_panel.hide()
        self.icon._bounce_paused = False
        if self.icon.isVisible():
            self.icon.start_idle_bounce()

    def _on_action(self, action_id):
        if action_id == 'guide_yes':
            self.guide_enabled = True
            self.dim_bg.hide()  # NEW: dim goes away once intro is dismissed
            self.icon.show()
            self.icon.raise_()
            self.icon.start_idle_bounce()
            self._show_card('guide_overview')
        elif action_id in ('guide_skip', 'guide_no'):
            self.guide_enabled = False
            self._skip_with_fly_animation()
        elif action_id in ('ack', 'press ok'):
            self._current_key = step_for_index.get(self.stack.currentIndex(), self._current_key)
            self._hide_card()

    def _skip_with_fly_animation(self):
        target_rect = QRect(
            self.icon.x(), self.icon.y(), self.icon.width(), self.icon.height()
        )
        start_rect = self.card.geometry()

        # NEW: fade the dim out at the same time as the shrink
        self.dim_fade = QPropertyAnimation(self.dim_bg, b"windowOpacity")
        self.dim_opacity_effect = QGraphicsOpacityEffect(self.dim_bg)
        self.dim_bg.setGraphicsEffect(self.dim_opacity_effect)
        self.dim_opacity_effect.setOpacity(1.0)
        self.dim_fade = QPropertyAnimation(self.dim_opacity_effect, b"opacity")
        self.dim_fade.setDuration(500)
        self.dim_fade.setStartValue(1.0)
        self.dim_fade.setEndValue(0.0)
        self.dim_fade.finished.connect(self.dim_bg.hide)
        self.dim_fade.start()

        self.icon.show()  # NEW: reveal the icon just as the card starts flying toward it
        self.icon.raise_()

        self.fly_anim = QPropertyAnimation(self.card, b"geometry")
        self.fly_anim.setDuration(500)
        self.fly_anim.setStartValue(start_rect)
        self.fly_anim.setEndValue(target_rect)
        self.fly_anim.setEasingCurve(QEasingCurve.InBack)
        self.fly_anim.finished.connect(self._on_skip_fly_finished)
        self.fly_anim.start()

    def _on_skip_fly_finished(self):
        self._hide_card()
        # Restore card to its normal size for next time it's shown
        self.card.setGeometry(self.card.x(), self.card.y(), default_card_width, self.card.minimumHeight())
        self.icon.start_idle_bounce()
        
    def play_celebration(self, message="Optimal! Great job!", on_finished=None):
        self.celebrate_toast.message_label.setText(message)
        center_x = self.stack.width() // 2
        center_y = self.stack.height() // 2
        self.celebrate_toast.play(center_x, center_y, hold_ms=900, on_finished=on_finished)
        self.icon.play_celebrate()  # keep the icon animation too, as a bonus


class HandBotPagesOverlay(QWidget):
    def __init__(self, pages_stack, home_stack=None):
        super().__init__(pages_stack)
        self.pages_stack = pages_stack
        self.home_stack = home_stack
        self._chatbot_enabled = app_config.get_chatbot_enabled()
        self.is_dark = False
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setStyleSheet("background: transparent;")

        self.icon = HandBotIcon(self.pages_stack)
        self.icon.hide()
        self.icon.clicked.connect(self._on_icon_clicked)
        self.icon.position_reset.connect(self._on_icon_position_reset)

        self.chat_panel = HandBotChatPanel(self.pages_stack)
        self.chat_panel.hide()
        self.chat_panel.closed.connect(self._hide_chat)

        self.pages_stack.installEventFilter(self)
        self.pages_stack.currentChanged.connect(self._on_page_changed)
        if self.home_stack:
            self.home_stack.currentChanged.connect(lambda _: self._on_page_changed(self.pages_stack.currentIndex()))
        self._on_page_changed(self.pages_stack.currentIndex())

        self._reposition()
        self.show()
        self.raise_()

    def apply_theme(self, is_dark):
        self.is_dark = is_dark
        self.icon.apply_theme(is_dark)
        self.chat_panel.apply_theme(is_dark)

    def eventFilter(self, obj, event):
        if obj is self.pages_stack and event.type() in (QEvent.Resize, QEvent.Show):
            self._reposition()
        return False

    def _reposition(self):
        self.setGeometry(0, 0, self.pages_stack.width(), self.pages_stack.height())
        if not self.icon._dragging and not self.icon._moved:
            self.icon._anim.stop()
            self.icon.move(self.width() - self.icon.width() - 1, 110)
            if self.icon.isVisible():
                self.icon.start_idle_bounce()
        if self.chat_panel.isVisible():
            self._position_chat()

    def _position_chat(self):
        gap = 12
        self.chat_panel.resize_to_fit(self.width(), self.height())
        x = self.icon.x() - self.chat_panel.width() - gap
        if x < gap:
            x = self.icon.x() + self.icon.width() + gap
        x = max(gap, min(x, self.width() - self.chat_panel.width() - gap))
        y = self.icon.y()
        y = max(gap, min(y, self.height() - self.chat_panel.height() - gap))
        self.chat_panel.move(x, y)

    def _on_icon_position_reset(self):
        if self.chat_panel.isVisible():
            self._position_chat()

    def _on_page_changed(self, index):
        self.raise_()
        self._hide_chat()
        if not self._chatbot_enabled:
            self.icon.hide()
            return
        if index == 0 and self.home_stack and self.home_stack.currentIndex() != 0:
            self.icon.hide()
            return
        self.icon.show()
        self.icon.raise_()
        self.icon.start_idle_bounce()

    def set_chatbot_enabled(self, enabled: bool):
        self._chatbot_enabled = enabled
        self._on_page_changed(self.pages_stack.currentIndex())

    def _on_icon_clicked(self):
        if not self._chatbot_enabled:
            return
        if self.chat_panel.isVisible():
            self._hide_chat()
        elif ensure_model_ready(self, self.is_dark):
            self._show_chat()

    def _show_chat(self):
        self.icon._bounce_paused = True
        self.icon._anim.stop()
        self.chat_panel.show()
        self.chat_panel.raise_()
        self._position_chat()
        self.chat_panel.play_pop_in()

    def _hide_chat(self):
        self.chat_panel.hide()
        self.icon._bounce_paused = False
        if self.icon.isVisible():
            self.icon.start_idle_bounce()

class HandBotCelebrateToast(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("celebrateToast")
        self.setFixedSize(300, 240)  # bigger, was 240x180
        self._build()
        self.apply_theme(False)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0.0)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignCenter)

        self.avatar_label = QLabel()
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setStyleSheet("background:transparent; border:none;")
        pixmap = QPixmap(HANDBOT_CELEBRATING)
        self.avatar_label.setPixmap(pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))  # bigger, was 80x80
        layout.addWidget(self.avatar_label)

        self.message_label = QLabel("Optimal! Great job!")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet("font-size:16px; font-weight:700; background:transparent; border:none;")  # bigger, was 14px
        layout.addWidget(self.message_label)

    def apply_theme(self, is_dark):
        bg = "#111111" if is_dark else "#FFFFFF"
        border = "#262626" if is_dark else "#E5E5E5"
        text = "#E8E8E8" if is_dark else "#111111"
        self.setStyleSheet(f"""
            QFrame#celebrateToast {{
                background: {bg};
                border-radius: 16px;
                border: 1px solid {border};
            }}
        """)
        self.message_label.setStyleSheet(f"font-size:16px; font-weight:700; color:{text}; background:transparent; border:none;")

    def play(self, center_x, center_y, hold_ms=1600, on_finished=None):
        """Pop in with a bounce, jump twice, hold, then fade out."""
        final_rect = QRect(
            center_x - self.width() // 2, center_y - self.height() // 2,
            self.width(), self.height()
        )
        start_rect = QRect(
            final_rect.center().x() - int(final_rect.width() * 0.3),
            final_rect.center().y() - int(final_rect.height() * 0.3),
            int(final_rect.width() * 0.6), int(final_rect.height() * 0.6)
        )

        self.setGeometry(start_rect)
        self.opacity_effect.setOpacity(0.0)
        self.show()
        self.raise_()

        self.pop_scale = QPropertyAnimation(self, b"geometry")
        self.pop_scale.setDuration(450)  # slower pop-in, was 250
        self.pop_scale.setStartValue(start_rect)
        self.pop_scale.setEndValue(final_rect)
        self.pop_scale.setEasingCurve(QEasingCurve.OutBack)

        self.pop_fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.pop_fade_in.setDuration(300)  # was 200
        self.pop_fade_in.setStartValue(0.0)
        self.pop_fade_in.setEndValue(1.0)

        self.pop_scale.start()
        self.pop_fade_in.start()

        # Jump animation once settled - two noticeable hops
        def _start_jump():
            self.jump_anim = QPropertyAnimation(self, b"geometry")
            self.jump_anim.setDuration(700)
            self.jump_anim.setStartValue(final_rect)
            jump_up = QRect(final_rect.x(), final_rect.y() - 18, final_rect.width(), final_rect.height())
            self.jump_anim.setKeyValueAt(0.25, jump_up)
            self.jump_anim.setKeyValueAt(0.5, final_rect)
            self.jump_anim.setKeyValueAt(0.75, jump_up)
            self.jump_anim.setKeyValueAt(1.0, final_rect)
            self.jump_anim.setEasingCurve(QEasingCurve.OutQuad)
            self.jump_anim.start()

        QTimer.singleShot(450, _start_jump)  # starts right as pop-in finishes

        def _start_fade_out():
            self.fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
            self.fade_out.setDuration(400)  # was 300
            self.fade_out.setStartValue(1.0)
            self.fade_out.setEndValue(0.0)
            self.fade_out.finished.connect(self.hide)
            if on_finished:
                self.fade_out.finished.connect(on_finished)
            self.fade_out.start()

        QTimer.singleShot(hold_ms, _start_fade_out)