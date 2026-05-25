import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QComboBox,
)
from PySide6.QtCore import Qt, Signal

_LOGIC_DIR  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logic")
_CUSTOM_DIR = os.path.join(_LOGIC_DIR, "data", "custom")

_CUSTOM_FILES = {
    'mouse':  ('mouse_gesture_model_best.pt',  'mouse_label_encoder.pkl'),
    'subway': ('subway_gesture_model_best.pt', 'subway_label_encoder.pkl'),
    'racing': ('racing_gesture_model_best.pt', 'racing_label_encoder.pkl'),
}

class GameMode(QWidget):
    on_menu_toggle        = Signal()
    game_mode_changed     = Signal(str)
    camera_changed        = Signal(int)
    cursor_point_changed  = Signal(str)
    mouse_in_game_changed = Signal(bool)
    model_source_changed  = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.is_dark       = False
        self.selected_mode = 'mouse'
        self.mouse_enabled = False
        self._camera_index = 0
        self._cursor_point = 'tip'
        self._mode_sources = {k: 'default' for k in ('mouse', 'subway', 'racing')}
        self._source_btns  = {}
        self._mode_cards   = {}
        self._camera_combo = None
        self._cursor_btns  = {}

        self._load_state()
        self._init_ui()
        self.apply_theme(False)

    def _load_state(self):
        try:
            from logic.app_config import get_game_mode, get_mouse_enabled, get_model_source, get_camera_index, get_cursor_point
            self.selected_mode = get_game_mode()
            self.mouse_enabled = get_mouse_enabled()
            self._camera_index = get_camera_index()
            self._cursor_point = get_cursor_point()
            for m in ('mouse', 'subway', 'racing'):
                self._mode_sources[m] = get_model_source(m)
        except Exception:
            self._camera_index = 0

    def _custom_exists(self, mode: str) -> bool:
        if mode not in _CUSTOM_FILES:
            return False
        w, e = _CUSTOM_FILES[mode]
        return (os.path.exists(os.path.join(_CUSTOM_DIR, w)) and
                os.path.exists(os.path.join(_CUSTOM_DIR, e)))

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

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(24, 16, 24, 16)
        cl.setSpacing(14)

        self.page_title = QLabel("SETTINGS")
        cl.addWidget(self.page_title)

        self.mouse_panel = QWidget()
        self.mouse_panel.setFixedHeight(52)
        mp = QHBoxLayout(self.mouse_panel)
        mp.setContentsMargins(16, 0, 16, 0)
        mp.setSpacing(0)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self.mouse_hdr_lbl = QLabel("MOUSE MODE")
        self.mouse_sub_lbl = QLabel("Enable cursor control when not in a game mode")
        text_col.addWidget(self.mouse_hdr_lbl)
        text_col.addWidget(self.mouse_sub_lbl)
        mp.addLayout(text_col, stretch=1)

        self.mouse_toggle_btn = QPushButton("ON" if self.mouse_enabled else "OFF")
        self.mouse_toggle_btn.setFixedSize(52, 26)
        self.mouse_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.mouse_toggle_btn.clicked.connect(self._toggle_mouse)
        mp.addWidget(self.mouse_toggle_btn)
        cl.addWidget(self.mouse_panel)

        self.div1 = QWidget()
        self.div1.setFixedHeight(1)
        cl.addWidget(self.div1)

        self.cursor_panel = QWidget()
        self.cursor_panel.setFixedHeight(52)
        crp = QHBoxLayout(self.cursor_panel)
        crp.setContentsMargins(16, 0, 16, 0)
        crp.setSpacing(0)

        cursor_text_col = QVBoxLayout()
        cursor_text_col.setSpacing(2)
        self.cursor_hdr_lbl = QLabel("CURSOR TRACKING POINT")
        self.cursor_sub_lbl = QLabel("Landmark used to position the cursor on screen")
        cursor_text_col.addWidget(self.cursor_hdr_lbl)
        cursor_text_col.addWidget(self.cursor_sub_lbl)
        crp.addLayout(cursor_text_col, stretch=1)

        cursor_row = QHBoxLayout()
        cursor_row.setSpacing(4)
        tip_btn = QPushButton("TIP")
        tip_btn.setFixedSize(52, 26)
        tip_btn.setCursor(Qt.PointingHandCursor)
        tip_btn.clicked.connect(lambda: self._set_cursor_point('tip'))
        knuckle_btn = QPushButton("KNUCKLE")
        knuckle_btn.setFixedSize(72, 26)
        knuckle_btn.setCursor(Qt.PointingHandCursor)
        knuckle_btn.clicked.connect(lambda: self._set_cursor_point('knuckle'))
        cursor_row.addWidget(tip_btn)
        cursor_row.addWidget(knuckle_btn)
        crp.addLayout(cursor_row)
        self._cursor_btns = {'tip': tip_btn, 'knuckle': knuckle_btn}
        cl.addWidget(self.cursor_panel)

        self.div1b = QWidget()
        self.div1b.setFixedHeight(1)
        cl.addWidget(self.div1b)

        self.camera_panel = QWidget()
        self.camera_panel.setFixedHeight(52)
        cp = QHBoxLayout(self.camera_panel)
        cp.setContentsMargins(16, 0, 16, 0)
        cp.setSpacing(0)

        cam_text_col = QVBoxLayout()
        cam_text_col.setSpacing(2)
        self.camera_hdr_lbl = QLabel("CAMERA INPUT")
        self.camera_sub_lbl = QLabel("Select which camera to use for hand tracking")
        cam_text_col.addWidget(self.camera_hdr_lbl)
        cam_text_col.addWidget(self.camera_sub_lbl)
        cp.addLayout(cam_text_col, stretch=1)

        self._camera_combo = QComboBox()
        self._camera_combo.setFixedSize(140, 26)
        self._camera_combo.currentIndexChanged.connect(self._on_camera_combo_changed)
        cp.addWidget(self._camera_combo)
        cl.addWidget(self.camera_panel)
        self._populate_cameras()

        self.div2 = QWidget()
        self.div2.setFixedHeight(1)
        cl.addWidget(self.div2)

        self.mode_section_hdr = QLabel("GAME MODE")
        cl.addWidget(self.mode_section_hdr)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(12)

        modes = [
            ("🖱", "MOUSE",      "mouse"),
            ("🚇", "SUBWAY",     "subway"),
            ("🏎", "RACING",     "racing"),
            ("🌍", "OPEN WORLD", "open_world"),
        ]

        for icon, label, key in modes:
            card_col = QVBoxLayout()
            card_col.setSpacing(6)

            card = QPushButton()
            card.setFixedSize(150, 96)
            card.setCheckable(True)
            card.setCursor(Qt.PointingHandCursor)
            card.clicked.connect(lambda _, k=key: self.select_mode(k))

            card_inner = QVBoxLayout(card)
            card_inner.setAlignment(Qt.AlignCenter)
            card_inner.setSpacing(6)
            card_inner.setContentsMargins(8, 8, 8, 8)

            icon_lbl = QLabel(icon)
            icon_lbl.setAlignment(Qt.AlignCenter)
            icon_lbl.setStyleSheet("font-size: 26px; background: transparent; border: none;")

            name_lbl = QLabel(label)
            name_lbl.setAlignment(Qt.AlignCenter)

            card_inner.addWidget(icon_lbl)
            card_inner.addWidget(name_lbl)

            self._mode_cards[key] = {'card': card, 'name': name_lbl}
            card_col.addWidget(card)

            src_row = QHBoxLayout()
            src_row.setSpacing(4)
            src_row.setContentsMargins(0, 0, 0, 0)

            def_btn = QPushButton("DEFAULT")
            def_btn.setFixedHeight(22)
            def_btn.setCursor(Qt.PointingHandCursor)
            def_btn.clicked.connect(lambda _, k=key: self._set_model_source(k, 'default'))

            custom_btn = QPushButton("CUSTOM")
            custom_btn.setFixedHeight(22)
            custom_btn.setCursor(Qt.PointingHandCursor)
            custom_btn.clicked.connect(lambda _, k=key: self._set_model_source(k, 'custom'))
            custom_btn.setEnabled(self._custom_exists(key))

            src_row.addWidget(def_btn)
            src_row.addWidget(custom_btn)

            self._source_btns[key] = {'default': def_btn, 'custom': custom_btn}

            card_col.addLayout(src_row)

            mode_row.addLayout(card_col)

        mode_row.addStretch()
        cl.addLayout(mode_row)
        cl.addStretch()

        root.addWidget(content, stretch=1)

    def select_mode(self, key: str):
        self.selected_mode = key
        try:
            from logic.app_config import set_game_mode
            set_game_mode(key)
        except Exception:
            pass
        self.apply_theme(self.is_dark)
        self.game_mode_changed.emit(key)

    def set_selected_mode(self, key: str):
        if key == self.selected_mode:
            return
        self.selected_mode = key
        try:
            from logic.app_config import set_game_mode
            set_game_mode(key)
        except Exception:
            pass
        self.apply_theme(self.is_dark)

    def refresh_custom_availability(self):
        for key, btns in self._source_btns.items():
            exists = self._custom_exists(key)
            btns['custom'].setEnabled(exists)
            if not exists and self._mode_sources.get(key) == 'custom':
                self._mode_sources[key] = 'default'
                try:
                    from logic.app_config import set_model_source
                    set_model_source(key, 'default')
                except Exception:
                    pass
        self.apply_theme(self.is_dark)

    def _toggle_mouse(self):
        self.mouse_enabled = not self.mouse_enabled
        self.mouse_toggle_btn.setText("ON" if self.mouse_enabled else "OFF")
        try:
            from logic.app_config import set_mouse_enabled
            set_mouse_enabled(self.mouse_enabled)
        except Exception:
            pass
        self.mouse_in_game_changed.emit(self.mouse_enabled)
        self.apply_theme(self.is_dark)

    def _set_cursor_point(self, point: str):
        self._cursor_point = point
        try:
            from logic.app_config import set_cursor_point
            set_cursor_point(point)
        except Exception:
            pass
        self.cursor_point_changed.emit(point)
        self.apply_theme(self.is_dark)

    def _set_model_source(self, mode: str, source: str):
        if source == 'custom' and not self._custom_exists(mode):
            return
        self._mode_sources[mode] = source
        try:
            from logic.app_config import set_model_source
            set_model_source(mode, source)
        except Exception:
            pass
        self.model_source_changed.emit(mode, source)
        self.apply_theme(self.is_dark)

    def _populate_cameras(self):
        if self._camera_combo is None:
            return
        try:
            from logic.hand_controller import list_cameras
            cameras = list_cameras()
        except Exception:
            cameras = []
        self._camera_combo.blockSignals(True)
        self._camera_combo.clear()
        if not cameras:
            self._camera_combo.addItem("No camera found", -1)
        else:
            for idx in cameras:
                self._camera_combo.addItem(
                    f"Camera {idx}" + (" (Default)" if idx == 0 else ""), idx)
            for i in range(self._camera_combo.count()):
                if self._camera_combo.itemData(i) == self._camera_index:
                    self._camera_combo.setCurrentIndex(i)
                    break
        self._camera_combo.blockSignals(False)

    def _on_camera_combo_changed(self, combo_idx: int):
        if self._camera_combo is None:
            return
        d = self._camera_combo.itemData(combo_idx)
        if d is not None and d >= 0:
            self._camera_index = d
            try:
                from logic.app_config import set_camera_index
                set_camera_index(d)
            except Exception:
                pass
            self.camera_changed.emit(d)

    def set_camera_index(self, idx: int):
        self._camera_index = idx
        if self._camera_combo is None:
            return
        self._camera_combo.blockSignals(True)
        for i in range(self._camera_combo.count()):
            if self._camera_combo.itemData(i) == idx:
                self._camera_combo.setCurrentIndex(i)
                break
        self._camera_combo.blockSignals(False)

    def apply_theme(self, is_dark: bool):
        self.is_dark = is_dark

        if is_dark:
            bg             = "#0a0a0a"; panel  = "#111111"; border = "#262626"
            text           = "#e8e8e8"; dim    = "#9a9a9a"; muted  = "#6b6b6b"
            hover          = "#161616"
            sel_bg         = "#e8e8e8"; sel_border = "#e8e8e8"; sel_txt = "#111111"
            unsel_bg       = "#111111"; unsel_txt  = "#9a9a9a"
            src_active_bg  = "#e8e8e8"; src_active_txt = "#111111"
            tog_on_bg      = "#e8e8e8"; tog_on_txt    = "#111111"
            tog_off_bg     = "#111111"; tog_off_txt   = "#9a9a9a"
        else:
            bg             = "#F4F4F4"; panel  = "#FFFFFF"; border = "#D8CEC7"
            text           = "#111111"; dim    = "#6F655F"; muted  = "#B8B0AB"
            hover          = "#EDE5DF"
            sel_bg         = "#1A1A1A"; sel_border = "#1A1A1A"; sel_txt = "#FFFFFF"
            unsel_bg       = "#FFFFFF"; unsel_txt  = "#6F655F"
            src_active_bg  = "#111111"; src_active_txt = "#FFFFFF"
            tog_on_bg      = "#1A1A1A"; tog_on_txt    = "#FFFFFF"
            tog_off_bg     = "#F7F3F0"; tog_off_txt   = "#8B817B"

        self.setStyleSheet(f"background-color: {bg};")

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

        self.mouse_panel.setStyleSheet(
            f"background-color: {panel}; border: 1px solid {border};")
        self.mouse_hdr_lbl.setStyleSheet(
            f"font-size: 9px; font-weight: 700; color: {text}; letter-spacing: 1.5px; background: transparent; border: none;")
        self.mouse_sub_lbl.setStyleSheet(
            f"font-size: 8px; color: {muted}; letter-spacing: 1px; background: transparent; border: none;")
        if self.mouse_enabled:
            self.mouse_toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {tog_on_bg}; color: {tog_on_txt};
                    font-size: 8px; font-weight: 700; letter-spacing: 1px;
                    border: 1px solid {tog_on_bg}; border-radius: 2px;
                }}
            """)
        else:
            self.mouse_toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {tog_off_bg}; color: {tog_off_txt};
                    font-size: 8px; font-weight: 700; letter-spacing: 1px;
                    border: 1px solid {border}; border-radius: 2px;
                }}
                QPushButton:hover {{ background-color: {hover}; }}
            """)

        self.div1.setStyleSheet(f"background-color: {border};")

        self.cursor_panel.setStyleSheet(
            f"background-color: {panel}; border: 1px solid {border};")
        self.cursor_hdr_lbl.setStyleSheet(
            f"font-size: 9px; font-weight: 700; color: {text}; letter-spacing: 1.5px; background: transparent; border: none;")
        self.cursor_sub_lbl.setStyleSheet(
            f"font-size: 8px; color: {muted}; letter-spacing: 1px; background: transparent; border: none;")
        for pt, btn in self._cursor_btns.items():
            if pt == self._cursor_point:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {tog_on_bg}; color: {tog_on_txt};
                        font-size: 8px; font-weight: 700; letter-spacing: 1px;
                        border: 1px solid {tog_on_bg}; border-radius: 2px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {tog_off_bg}; color: {tog_off_txt};
                        font-size: 8px; font-weight: 700; letter-spacing: 1px;
                        border: 1px solid {border}; border-radius: 2px;
                    }}
                    QPushButton:hover {{ background-color: {hover}; color: {text}; }}
                """)
        self.div1b.setStyleSheet(f"background-color: {border};")

        self.div2.setStyleSheet(f"background-color: {border};")

        self.camera_panel.setStyleSheet(
            f"background-color: {panel}; border: 1px solid {border};")
        self.camera_hdr_lbl.setStyleSheet(
            f"font-size: 9px; font-weight: 700; color: {text}; letter-spacing: 1.5px; background: transparent; border: none;")
        self.camera_sub_lbl.setStyleSheet(
            f"font-size: 8px; color: {muted}; letter-spacing: 1px; background: transparent; border: none;")
        if self._camera_combo:
            self._camera_combo.setStyleSheet(f"""
                QComboBox {{
                    background: {panel}; color: {text};
                    border: 1px solid {border};
                    border-radius: 2px; padding: 2px 6px; font-size: 9px;
                    letter-spacing: 1px;
                }}
                QComboBox::drop-down {{ border: none; width: 16px; }}
                QComboBox::down-arrow {{
                    border-left: 3px solid transparent;
                    border-right: 3px solid transparent;
                    border-top: 4px solid {dim};
                    width: 0; height: 0; margin-right: 5px;
                }}
                QComboBox QAbstractItemView {{
                    background: {panel}; color: {text};
                    border: 1px solid {border};
                    selection-background-color: {"#161616" if is_dark else "#EDE5DF"};
                    selection-color: {text}; outline: none;
                }}
            """)

        self.mode_section_hdr.setStyleSheet(
            f"color: {muted}; font-size: 8px; font-weight: 700; letter-spacing: 1.4px; background: transparent; border: none;")

        for key, widgets in self._mode_cards.items():
            card     = widgets['card']
            name_lbl = widgets['name']
            selected = (key == self.selected_mode)

            if selected:
                card.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {sel_bg};
                        border: 2px solid {sel_border};
                        border-radius: 4px;
                    }}
                """)
                name_lbl.setStyleSheet(
                    f"color: {sel_txt}; font-size: 9px; font-weight: 700; letter-spacing: 1.2px; background: transparent; border: none;")
            else:
                card.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {unsel_bg};
                        border: 1px solid {border};
                        border-radius: 4px;
                    }}
                    QPushButton:hover {{
                        background-color: {hover};
                        border: 1px solid {border};
                    }}
                """)
                name_lbl.setStyleSheet(
                    f"color: {unsel_txt}; font-size: 9px; font-weight: 700; letter-spacing: 1.2px; background: transparent; border: none;")

        for key, btns in self._source_btns.items():
            cur_src = self._mode_sources.get(key, 'default')
            for src, btn in btns.items():
                is_active = (src == cur_src) and (src == 'default' or self._custom_exists(key))
                if is_active:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {src_active_bg}; color: {src_active_txt};
                            font-size: 7px; font-weight: 700; letter-spacing: 1px;
                            border: 1px solid {src_active_bg}; border-radius: 2px;
                        }}
                    """)
                else:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: transparent; color: {dim};
                            font-size: 7px; font-weight: 700; letter-spacing: 1px;
                            border: 1px solid {border}; border-radius: 2px;
                        }}
                        QPushButton:hover {{ background-color: {hover}; color: {text}; }}
                        QPushButton:disabled {{ color: {border}; border-color: {border}; }}
                    """)
