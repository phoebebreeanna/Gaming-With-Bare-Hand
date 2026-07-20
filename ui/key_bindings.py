from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent

_CUSTOM_SECTION_TAG = "__custom__"

_GESTURE_META = {
    'subway': [
        ('jump',  'JUMP',         'Two fingers up'),
        ('roll',  'SLIDE',        'Two fingers down'),
        ('left',  'SWIPE LEFT',   'Two fingers left'),
        ('right', 'SWIPE RIGHT',  'Two fingers right'),
        ('space', 'JUMP BOOST',   'Metal sign'),
    ],
    'racing': [
        ('accel',       'ACCELERATE',   'Right thumb up'),
        ('brake',       'BRAKE',        'Left thumb up'),
        ('steer_left',  'STEER LEFT',   'Tilt hands left'),
        ('steer_right', 'STEER RIGHT',  'Tilt hands right'),
        ('horn',        'HORN (HOLD)',   'Right index + middle fingers'),
        ('camera',      'CAMERA (TAP)', 'Left index + middle fingers'),
    ],
    'open_world': [
        ('like',           'DODGE',        'Thumbs up'),
        ('palm',           'JUMP',         'Open palm'),
        ('thumb_index',    'LEFT CLICK',   'L sign (thumb + index)',  'LMB'),
        ('little_finger',  'RIGHT CLICK',  'Pinky / small finger',    'RMB'),
        ('grabbing',       'ABILITY',      'Grabbing gesture'),
        ('ok',             'INTERACT',     'OK sign'),
        ('call',           'SKILL',       'Call sign'),
        ('dislike',        'ALT SKILL',   'Thumbs down'),
        ('holy',           'ESCAPE',      'Holy / spread hand'),
        ('grip',           'ALT',         'Grip / fist-clench'),
        ('one',            'TEAMMATE 1',  'Index finger up'),
        ('peace',          'TEAMMATE 2',  'Peace sign'),
        ('three',          'TEAMMATE 3',  'Three fingers up'),
        ('four',           'TEAMMATE 4',  'Four fingers up'),
        ('peace_inverted', 'EXTRA 1',     'Inverted peace sign'),
        ('three2',         'TAB / MAP',   'Three-three pose'),
        ('three3',         'EXTRA 2',     'Three-two pose'),
        ('two_up',          'MOVE FWD',   'Peace sign pointing up',    'W'),
        ('two_up_inverted', 'MOVE BACK',  'Peace sign pointing down',  'S'),
        ('three_gun',       'STRAFE',     'Gun pose, aim left or right', 'A / D'),
    ],
}

_MODE_LABELS = {
    'subway':     'SUBWAY',
    'racing':     'RACING',
    'open_world': 'OPEN WORLD',
}

def _qt_key_to_str(key):
    _SPECIAL = {
        Qt.Key_Up: 'up',        Qt.Key_Down: 'down',
        Qt.Key_Left: 'left',    Qt.Key_Right: 'right',
        Qt.Key_Space: 'space',  Qt.Key_Return: 'enter',
        Qt.Key_Enter: 'enter',  Qt.Key_Tab: 'tab',
        Qt.Key_Backspace: 'backspace', Qt.Key_Delete: 'delete',
        Qt.Key_Shift: 'shift',  Qt.Key_Control: 'ctrl',
        Qt.Key_Alt: 'alt',      Qt.Key_Escape: None,
    }
    if key in _SPECIAL:
        return _SPECIAL[key]
    if Qt.Key_A <= key <= Qt.Key_Z:
        return chr(key).lower()
    if Qt.Key_0 <= key <= Qt.Key_9:
        return chr(key)
    if Qt.Key_F1 <= key <= Qt.Key_F12:
        return f'f{key - Qt.Key_F1 + 1}'
    return None

class KeyBindings(QWidget):
    on_menu_toggle  = Signal()
    binding_changed = Signal(str, str, str)

    def __init__(self):
        super().__init__()
        self.is_dark     = False
        self._bindings   = {}
        self._key_btns   = {}
        self._capturing  = None
        self._custom_section_widgets = []

        self._load_bindings()
        self._init_ui()
        self.apply_theme(False)

    def _load_bindings(self):
        try:
            from logic.app_config import get_key_bindings
            for mode in ('subway', 'racing', 'open_world'):
                self._bindings[mode] = get_key_bindings(mode)
        except Exception:
            from logic.app_config import BINDINGS_DEFAULT
            self._bindings = {m: dict(v) for m, v in BINDINGS_DEFAULT.items()}

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = QWidget()
        self.header.setFixedHeight(42)
        hl = QHBoxLayout(self.header)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)
        self.menu_btn = QPushButton("☰")
        self.menu_btn.setFixedSize(36, 42)
        self.menu_btn.setCursor(Qt.PointingHandCursor)
        self.menu_btn.clicked.connect(self.on_menu_toggle.emit)
        hl.addWidget(self.menu_btn)
        self.brand_box = QWidget()
        self.brand_box.setFixedHeight(42)
        bl = QHBoxLayout(self.brand_box)
        bl.setContentsMargins(14, 0, 18, 0)
        bl.setSpacing(10)
        self.brand_title   = QLabel("HANDMOUSE")
        self.brand_version = QLabel("v1.0")
        bl.addWidget(self.brand_title)
        bl.addWidget(self.brand_version)
        hl.addWidget(self.brand_box)
        hl.addStretch()
        root.addWidget(self.header)

        self.header_rule = QWidget()
        self.header_rule.setFixedHeight(1)
        root.addWidget(self.header_rule)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scroll_content = content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(24, 16, 24, 16)
        cl.setSpacing(0)

        self.page_title = QLabel("KEY BINDINGS")
        cl.addWidget(self.page_title)
        cl.addSpacing(14)

        self._section_widgets = {}
        self._locked_keys = set()

        for mode, gestures in _GESTURE_META.items():
            mode_binds = self._bindings.get(mode, {})

            sec_row = QWidget()
            sec_row.setFixedHeight(20)
            srl = QHBoxLayout(sec_row)
            srl.setContentsMargins(0, 0, 0, 0)
            srl.setSpacing(0)
            sec_hdr = QLabel(_MODE_LABELS[mode])
            srl.addWidget(sec_hdr)
            srl.addStretch()
            reset_btn = QPushButton("RESET ALL")
            reset_btn.setFixedHeight(18)
            reset_btn.setMinimumWidth(60)
            reset_btn.setCursor(Qt.PointingHandCursor)
            reset_btn.clicked.connect(lambda _, m=mode: self._reset_mode(m))
            srl.addWidget(reset_btn)
            cl.addWidget(sec_row)
            cl.addSpacing(4)

            rows = []
            for entry in gestures:
                gesture, label, desc = entry[0], entry[1], entry[2]
                locked = len(entry) > 3

                row = QWidget()
                row.setMinimumHeight(44)
                rl = QHBoxLayout(row)
                rl.setContentsMargins(16, 4, 16, 4)
                rl.setSpacing(0)

                text_col = QVBoxLayout()
                text_col.setSpacing(2)
                name_lbl = QLabel(label)
                desc_lbl = QLabel(desc)
                desc_lbl.setWordWrap(True)
                text_col.addWidget(name_lbl)
                text_col.addWidget(desc_lbl)
                rl.addLayout(text_col, stretch=1)

                if locked:
                    key_btn = QPushButton(entry[3])
                    key_btn.setFixedHeight(26)
                    key_btn.setMinimumWidth(56)
                    key_btn.setEnabled(False)
                    self._locked_keys.add((mode, gesture))
                else:
                    key_str = mode_binds.get(gesture, '?')
                    key_btn = QPushButton(key_str.upper())
                    key_btn.setFixedHeight(26)
                    key_btn.setMinimumWidth(56)
                    key_btn.setCursor(Qt.PointingHandCursor)
                    key_btn.clicked.connect(
                        lambda _, m=mode, g=gesture: self._start_capture(m, g))

                rl.addWidget(key_btn)
                self._key_btns[(mode, gesture)] = key_btn
                cl.addWidget(row)
                rows.append((row, name_lbl, desc_lbl))

            sep = QWidget()
            sep.setFixedHeight(1)
            cl.addWidget(sep)
            cl.addSpacing(14)

            self._section_widgets[mode] = {'hdr': sec_hdr, 'rows': rows, 'sep': sep, 'reset_btn': reset_btn}

        self._custom_insert_idx = cl.count()
        cl.addStretch()
        self._content_layout = cl
        self.scroll.setWidget(content)
        root.addWidget(self.scroll, stretch=1)
        self._build_custom_sections()

    def _build_custom_sections(self):
        cl = self._content_layout
        for w in self._custom_section_widgets:
            cl.removeWidget(w)
            w.deleteLater()
        self._custom_section_widgets.clear()
        for key in list(self._section_widgets.keys()):
            if key.startswith('custom_'):
                del self._section_widgets[key]
        for key in list(self._key_btns.keys()):
            if isinstance(key, tuple) and key[0].startswith('custom_'):
                del self._key_btns[key]
        for key in list(self._bindings.keys()):
            if key.startswith('custom_'):
                del self._bindings[key]

        try:
            from logic.app_config import get_custom_modes, get_key_bindings
            custom_modes = get_custom_modes()
        except Exception:
            custom_modes = []

        if not custom_modes:
            return

        grp_lbl = QLabel("CUSTOM MODES")
        grp_lbl.setContentsMargins(6, 12, 0, 6)
        grp_lbl.setProperty(_CUSTOM_SECTION_TAG, True)
        cl.insertWidget(cl.count() - 1, grp_lbl)
        self._custom_section_widgets.append(grp_lbl)

        for mode in custom_modes:
            mode_id  = mode['id']
            mode_key = f"custom_{mode_id}"
            try:
                bindings = get_key_bindings(mode_key)
            except Exception:
                bindings = {}
            self._bindings[mode_key] = bindings

            gestures = mode.get('gestures', [])
            if not gestures:
                continue

            sec_row = QWidget()
            sec_row.setFixedHeight(20)
            srl = QHBoxLayout(sec_row)
            srl.setContentsMargins(0, 0, 0, 0)
            srl.setSpacing(0)
            sec_hdr = QLabel(mode.get('name', mode_id).upper())
            srl.addWidget(sec_hdr)
            srl.addStretch()
            reset_btn = QPushButton("RESET ALL")
            reset_btn.setFixedHeight(18)
            reset_btn.setMinimumWidth(60)
            reset_btn.setCursor(Qt.PointingHandCursor)
            reset_btn.clicked.connect(lambda _, mk=mode_key: self._reset_mode(mk))
            srl.addWidget(reset_btn)
            sec_row.setProperty(_CUSTOM_SECTION_TAG, True)
            cl.insertWidget(cl.count() - 1, sec_row)
            self._custom_section_widgets.append(sec_row)

            rows_meta = []
            for gesture in gestures:
                key_str  = bindings.get(gesture, '?')
                row = QWidget()
                row.setMinimumHeight(44)
                rl = QHBoxLayout(row)
                rl.setContentsMargins(16, 4, 16, 4)
                rl.setSpacing(0)
                text_col = QVBoxLayout()
                text_col.setSpacing(2)
                name_lbl = QLabel(gesture.replace('_', ' ').upper())
                desc_lbl = QLabel(f"Custom gesture · {mode.get('name', mode_id)}")
                desc_lbl.setWordWrap(True)
                text_col.addWidget(name_lbl)
                text_col.addWidget(desc_lbl)
                rl.addLayout(text_col, stretch=1)
                key_btn = QPushButton(key_str.upper() if key_str != '?' else '-')
                key_btn.setFixedHeight(26)
                key_btn.setMinimumWidth(56)
                key_btn.setCursor(Qt.PointingHandCursor)
                key_btn.clicked.connect(
                    lambda _, mk=mode_key, g=gesture: self._start_capture(mk, g))
                rl.addWidget(key_btn)
                self._key_btns[(mode_key, gesture)] = key_btn
                row.setProperty(_CUSTOM_SECTION_TAG, True)
                cl.insertWidget(cl.count() - 1, row)
                self._custom_section_widgets.append(row)
                rows_meta.append((row, name_lbl, desc_lbl))

            sep = QWidget()
            sep.setFixedHeight(1)
            sep.setProperty(_CUSTOM_SECTION_TAG, True)
            cl.insertWidget(cl.count() - 1, sep)
            self._custom_section_widgets.append(sep)
            spacer_w = QWidget()
            spacer_w.setFixedHeight(14)
            cl.insertWidget(cl.count() - 1, spacer_w)
            self._custom_section_widgets.append(spacer_w)

            self._section_widgets[mode_key] = {
                'hdr': sec_hdr, 'rows': rows_meta,
                'sep': sep, 'reset_btn': reset_btn,
            }

        self.apply_theme(self.is_dark)

    def refresh_custom_modes(self):
        self._build_custom_sections()

    def _reset_mode(self, mode: str):
        try:
            from logic.app_config import reset_key_bindings, BINDINGS_DEFAULT
            reset_key_bindings(mode)
            self._bindings[mode] = dict(BINDINGS_DEFAULT.get(mode, {}))
        except Exception:
            from logic.app_config import BINDINGS_DEFAULT
            self._bindings[mode] = dict(BINDINGS_DEFAULT.get(mode, {}))
        if mode.startswith('custom_'):
            for (m, gesture), btn in list(self._key_btns.items()):
                if m == mode:
                    self._bindings.setdefault(mode, {}).pop(gesture, None)
                    btn.setText('-')
        else:
            for entry in _GESTURE_META.get(mode, []):
                gesture = entry[0]
                if (mode, gesture) in self._locked_keys:
                    continue
                key_str = self._bindings[mode].get(gesture, '?')
                self._key_btns[(mode, gesture)].setText(key_str.upper())
        self.apply_theme(self.is_dark)

    def _start_capture(self, mode: str, gesture: str):
        if self._capturing:
            pm, pg = self._capturing
            old_key = self._bindings.get(pm, {}).get(pg, '?')
            self._key_btns[(pm, pg)].setText(old_key.upper())
        self._capturing = (mode, gesture)
        self._key_btns[(mode, gesture)].setText('...')
        self.grabKeyboard()

    def keyPressEvent(self, event: QKeyEvent):
        if self._capturing is None:
            super().keyPressEvent(event)
            return
        mode, gesture = self._capturing
        new_key = _qt_key_to_str(event.key())
        self._capturing = None
        self.releaseKeyboard()
        if new_key is None:
            old_key = self._bindings.get(mode, {}).get(gesture, '?')
            self._key_btns[(mode, gesture)].setText(old_key.upper())
            return
        self._bindings.setdefault(mode, {})[gesture] = new_key
        self._key_btns[(mode, gesture)].setText(new_key.upper())
        try:
            from logic.app_config import set_key_binding
            set_key_binding(mode, gesture, new_key)
        except Exception:
            pass
        self.binding_changed.emit(mode, gesture, new_key)
        self.apply_theme(self.is_dark)

    def apply_theme(self, is_dark: bool):
        self.is_dark = is_dark

        if is_dark:
            bg      = "#0a0a0a"; panel  = "#111111"; border = "#262626"
            text    = "#e8e8e8"; muted  = "#6b6b6b"; hover  = "#161616"
            dim     = "#9a9a9a"
            sec_clr = "#6b6b6b"
            btn_bg  = "#1a1a1a"; btn_txt = "#e8e8e8"
            cap_bg  = "#e8e8e8"; cap_txt = "#111111"
        else:
            bg      = "#F4F4F4"; panel  = "#FFFFFF"; border = "#D8CEC7"
            text    = "#111111"; muted  = "#B8B0AB"; hover  = "#EDE5DF"
            dim     = "#6F655F"
            sec_clr = "#9AA0A6"
            btn_bg  = "#F7F3F0"; btn_txt = "#111111"
            cap_bg  = "#1A1A1A"; cap_txt = "#FFFFFF"

        self.setStyleSheet(f"background-color: {bg};")
        self.scroll.setStyleSheet(f"""
            QScrollArea {{ background-color: {bg}; border: none; }}
            QScrollBar:vertical {{
                width: 4px;
                background: transparent;
                border: none;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {muted};
                border-radius: 2px;
                min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {dim}; }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{ background: none; }}
        """)
        self.scroll_content.setStyleSheet(f"background-color: {bg};")
        self.header.setStyleSheet(f"background-color: {bg};")
        self.header_rule.setStyleSheet(f"background-color: {border};")
        self.menu_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {text};
                font-size: 18px; border: none; border-radius: 2px;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
        """)
        self.brand_box.setStyleSheet(
            f"background: transparent; border-left: 1px solid {border}; border-right: 1px solid {border};")
        self.brand_title.setStyleSheet(
            f"font-size: 11px; font-weight: 800; color: {text}; letter-spacing: 1.5px; background: transparent; border: none;")
        self.brand_version.setStyleSheet(
            f"font-size: 8px; color: {muted}; letter-spacing: 1px; background: transparent; border: none;")
        self.page_title.setStyleSheet(
            f"color: {text}; font-size: 14px; font-weight: 800; letter-spacing: 1.5px; background: transparent; border: none;")

        normal_btn_style = f"""
            QPushButton {{
                background-color: {btn_bg}; color: {btn_txt};
                font-size: 9px; font-weight: 700; letter-spacing: 1px;
                border: 1px solid {border}; border-radius: 2px;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
        """
        capture_btn_style = f"""
            QPushButton {{
                background-color: {cap_bg}; color: {cap_txt};
                font-size: 9px; font-weight: 700; letter-spacing: 1px;
                border: 1px solid {cap_bg}; border-radius: 2px;
            }}
        """
        locked_btn_style = f"""
            QPushButton:disabled {{
                background-color: {bg}; color: {muted};
                font-size: 9px; font-weight: 700; letter-spacing: 1px;
                border: 1px solid {border}; border-radius: 2px;
            }}
        """

        reset_btn_style = f"""
            QPushButton {{
                background-color: transparent; color: {muted};
                font-size: 7px; font-weight: 700; letter-spacing: 1px;
                border: 1px solid {border}; border-radius: 2px;
            }}
            QPushButton:hover {{ background-color: {hover}; color: {text}; }}
        """

        for mode, sw in self._section_widgets.items():
            sw['hdr'].setStyleSheet(
                f"color: {sec_clr}; font-size: 8px; font-weight: 700; "
                f"letter-spacing: 1.4px; background: transparent; border: none;")
            sw['sep'].setStyleSheet(f"background-color: {border};")
            sw['reset_btn'].setStyleSheet(reset_btn_style)
            for row, name_lbl, desc_lbl in sw['rows']:
                row.setStyleSheet(
                    f"background-color: {panel}; border: 1px solid {border};")
                name_lbl.setStyleSheet(
                    f"font-size: 9px; font-weight: 700; color: {text}; "
                    f"letter-spacing: 1.5px; background: transparent; border: none;")
                desc_lbl.setStyleSheet(
                    f"font-size: 8px; color: {muted}; "
                    f"letter-spacing: 1px; background: transparent; border: none;")

        for w in self._custom_section_widgets:
            if isinstance(w, QLabel):
                w.setStyleSheet(
                    f"font-size: 8px; color: {sec_clr}; font-weight: bold; "
                    f"letter-spacing: 1.2px; background: transparent; border: none;")

        for (mode, gesture), btn in self._key_btns.items():
            if (mode, gesture) in self._locked_keys:
                btn.setStyleSheet(locked_btn_style)
            elif self._capturing and self._capturing == (mode, gesture):
                btn.setStyleSheet(capture_btn_style)
            else:
                btn.setStyleSheet(normal_btn_style)
