from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QFrame)

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QPoint, QEvent


popup_content ={
    "guide_intro" : {
        "body":("<b>Hi! I am Handbot</b><br><br>"
               "HandMouse is developed by FYP-26-S2-02, a team of six from SIM - University of Wollongong. <br><br>"
               "Before jumping into the application, would you like me to guide you through the first-time setup?"
        ),
        "button":[("Yes - Guide me through","guide_yes"),("Skip - I will explore myself","guide_no")],
    },

    "guide_overview" : {
        "body":("<b>Great ! Here is what we will do:</b><br><br>"
                "I will guide you through 4 quick steps:<br>"
                "01 - Read the Setup Guide<br>"
                "02 - Select your camera<br>"
                "03 - Calibrate your distance<br>"
                "04 - Choose your movement zone<br><br>"
                "I will appear at each step to guide you. Click OK to begin!"
        ),
        "button":[("OK","press ok")],
    },

    "camera" : {
        "body":("<b>Select your camera !</b><br><br>"
                "Choose your camera from the dropdown.<br><br>"
                "Check the preview looks correct - you should see yourself clearly.<br><br>"
                "Then click <b>Continue</b> to proceed to the next step."
        ),
        "button":[("OK","press ok")],
    },

    "calibration" : {
        "body":("<b>Calibrate your distance !</b><br><br>"
                "Hold your palm facing the camera at arm's length.<br><br>"
                "Move until the gauge shows <span style='color: #008000;'><b>OPTIMAL</b></span> in green,then hold for 3 seconds - I will automatically move you to the next step!"
        ),
        "button":[("OK","press ok")],
    },

    "zone" : {
        "body":("<b>Choose your movement zone !</b><br><br>"
                "Show 1,2,3 fingers to the camera to select or click your preferred option directly.<br><br>"
                "Hold for 3 seconds to auto-advance to Home dashboard. <br><br>"
                "You can always change your zone later in the settings."
        ),
        "button":[("OK","press ok")],
    }
    
}



step_for_index = {1: "guide_intro", 2: "camera", 3: "calibration", 4: "zone"}
default_card_width = 340
card_width_for_content = {"guide_intro": 340, "guide_overview": 340, "camera": 340}
card_min_height_for_content = {"guide_intro": 300, "guide_overview": 314, "zone": 314}


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
    
    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        head = QHBoxLayout()
        head.setSpacing(10)
        icon_lbl = QLabel("🤖")
        icon_lbl.setStyleSheet("font-size:20px; background:transparent; border:none;")
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
        self.setMinimumHeight(card_min_height_for_content.get(key, 0))
        self.body_lbl.setText(data["body"])
        self.body_lbl.adjustSize()

        while self.btn_row.count():
            item = self.btn_row.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        for i,(label, action_id) in enumerate(data['button']):
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("action_id", action_id)
            self._style_button(btn, action_id)
            btn.clicked.connect(lambda _, a=action_id: self.action.emit(a))
            self.btn_row.addWidget(btn)

        self.layout().invalidate()
        self.adjustSize()

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
        self.card_icon_lbl.setStyleSheet(
            f"font-size:20px; color:{text}; background:transparent; border:none;")
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

    
#draggable icon
class HandBotIcon(QLabel):
    "Floating Handbot icon that can be dragged around the screen."
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("🤖")
        self.setFixedSize(52, 52)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)
        self.apply_theme(False)

        self._dragging = False
        self._drag_offset = QPoint()
        self._moved = False
        #Breathing animation
        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(1400)
        self._anim.setEasingCurve(QEasingCurve.InOutSine)
        self._anim.setLoopCount(-1)

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
            if not self._moved:
                self.clicked.emit()
            if self.isVisible():
                self.start_idle_bounce()

    def start_idle_bounce(self):
        base = self.pos()
        self._anim.stop()
        self._anim.setStartValue(base)
        self._anim.setKeyValueAt(0.5, base + QPoint(0, -6))
        self._anim.setEndValue(base)
        self._anim.start()

    def apply_theme(self, is_dark):
        bg = "#111111" if is_dark else "#FFFFFF"
        border = "#E8E8E8" if is_dark else "#111111"
        color = "#E8E8E8" if is_dark else "#111111"
        self.setStyleSheet(f"""
            background: {bg};
            color: {color};
            border: 2px solid {border};
            border-radius: 26px;
            font-size: 22px;
        """)

class HandBotOverlay(QWidget):
    def __init__(self, stack):
        super().__init__(stack)
        self.stack = stack
        self.guide_enabled = False
        self._intro_shown = False
        self._current_key = None

        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setStyleSheet("background: transparent;")

        self.icon = HandBotIcon(self.stack)
        self.icon.hide()
        self.icon.clicked.connect(self._on_icon_clicked)

        self.card = HandBotCard(self.stack)
        self.card.hide()
        self.card.action.connect(self._on_action)

        self.stack.installEventFilter(self)
        self.stack.currentChanged.connect(self._on_step_changed)

        self._reposition()
        self.show()
        self.raise_()

    def apply_theme(self, is_dark):
        self.icon.apply_theme(is_dark)
        self.card.apply_theme(is_dark)
    
    def eventFilter(self, obj, event):
        if obj is self.stack and event.type() in (QEvent.Resize, QEvent.Show):
            self._reposition()
        return False

    def _reposition(self):
        self.setGeometry(0, 0, self.stack.width(), self.stack.height())
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

    def _on_step_changed(self, index):
        self.raise_()
        if index == 0:
            # Dashboard - HandBot stays out of the way entirely.
            self.icon.hide()
            self._hide_card()
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
        self.card.set_content(key)
        self.card.show()
        self.card.raise_()
        self._center_card()

    def _hide_card(self):
        self.card.hide()

    def _on_icon_clicked(self):
        if self.card.isVisible():
            self._hide_card()
            return

        key = self._current_key or step_for_index.get(self.stack.currentIndex())
        if key:
            self._show_card(key)

    def _on_action(self, action_id):
        if action_id == 'guide_yes':
            self.guide_enabled = True
            self._show_card('guide_overview')
        elif action_id in ('guide_skip', 'guide_no'):
            self.guide_enabled = False
            self._hide_card()
        elif action_id in ('ack', 'press ok'):
            self._current_key = step_for_index.get(self.stack.currentIndex(), self._current_key)
            self._hide_card()
