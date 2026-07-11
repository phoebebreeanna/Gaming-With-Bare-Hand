from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QFrame,
                                QGraphicsOpacityEffect)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QPoint, QEvent, QRect, QTimer
from PySide6.QtGui import QColor, QPen, QPixmap, QPainter, QPainterPath


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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_dark = False
        self.setObjectName("handbotChatPanel")
        self.setFixedWidth(300)
        self.setFixedHeight(315)
        self._build()
        self.apply_theme(self.is_dark)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

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
        layout.addWidget(self.content_area, stretch=1)
        
        # --- Placeholder until Darren wires in the real chatbot ---
        self.placeholder_label = QLabel("💬 Chat coming soon!\n\nAsk me anything about gestures, setup, or HandMouse.")
        self.placeholder_label.setWordWrap(True)
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet("font-size:12px; color:#999; background:transparent; border:none;")
        self.content_layout.addWidget(self.placeholder_label, stretch=1)

    def apply_theme(self, is_dark):
        self.is_dark = is_dark
        bg = "#111111" if is_dark else "#FFFFFF"
        border = "#262626" if is_dark else "#E5E5E5"
        text = "#E8E8E8" if is_dark else "#111111"
        placeholder_color = "#777777" if is_dark else "#999999"  # add this line
        self.setStyleSheet(f"""
            QFrame#handbotChatPanel {{
                background: {bg};
                border-radius: 10px;
                border: 2px solid {border};
            }}
        """)
        self.header.setStyleSheet(f"background:transparent; border-bottom:1px solid {border};")
        self.header_title.setStyleSheet(f"font-size:14px; font-weight:600; color:{text}; background:transparent; border:none;")
        self.placeholder_label.setStyleSheet(f"font-size:12px; color:{placeholder_color}; background:transparent; border:none;")  

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

    def mouseMoveEvent(self, e):
        if self._dragging:
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
            else:
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
        if index == 0 and self.home_stack and self.home_stack.currentIndex() != 0:
            self.icon.hide()
            self._hide_chat()
            return
        self.icon.show()
        self.icon.raise_()
        self.icon.start_idle_bounce()

    def _on_icon_clicked(self):
        if self.chat_panel.isVisible():
            self._hide_chat()
        else:
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