import os
import sys

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QSizePolicy, QComboBox, QScrollArea, QLineEdit,
)
from PySide6.QtCore import Qt, Signal, QTimer

if getattr(sys, 'frozen', False):
    _CUSTOM_DIR = os.path.join(os.path.expanduser('~'), '.handmouse', 'data', 'custom')
else:
    _LOGIC_DIR  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logic")
    _CUSTOM_DIR = os.path.join(_LOGIC_DIR, "data", "custom")

_CUSTOM_FILES = {
    'mouse':  ('mouse_gesture_model_best.pt',  'mouse_label_encoder.pkl'),
    'subway': ('subway_gesture_model_best.pt', 'subway_label_encoder.pkl'),
}

MODE_SWITCH_LOCK_DEFAULTS = {
    'mouse':      False,
    'subway':     False,
    'racing':     True,
    'open_world': True,
    'air_hockey': True,
}
MODE_SWITCH_LOCK_LABELS = (
    ('mouse', 'MOUSE'), ('subway', 'SUBWAY'), ('racing', 'RACING'),
    ('open_world', 'OPEN WORLD'), ('air_hockey', 'AIR HOCKEY'),
)

CONTROL_GESTURE_DEFAULTS = {
    'mouse':      True,
    'subway':     False,
    'racing':     False,
    'open_world': False,
    'custom':     False,
    'air_hockey': False,
}
CONTROL_GESTURE_LABELS = (
    ('mouse', 'MOUSE'), ('subway', 'SUBWAY'), ('racing', 'RACING'),
    ('open_world', 'OPEN WORLD'), ('custom', 'CUSTOM'), ('air_hockey', 'AIR HOCKEY'),
)

def _custom_game_mode_model_exists(mode_id: str) -> bool:
    mode_dir = os.path.join(_CUSTOM_DIR, mode_id)
    return (os.path.exists(os.path.join(mode_dir, 'gesture_model_best.pt')) and
            os.path.exists(os.path.join(mode_dir, 'label_encoder.pkl')))

class GameMode(QWidget):
    on_menu_toggle        = Signal()
    game_mode_changed     = Signal(str)
    camera_changed        = Signal(int)
    cursor_point_changed  = Signal(str)
    mouse_in_game_changed = Signal(bool)
    model_source_changed  = Signal(str, str)
    zone_changed          = Signal(str)
    mouse_side_changed    = Signal(str)
    perf_stats_changed    = Signal(bool)
    custom_mode_selected  = Signal(str, str)
    chatbot_enabled_changed = Signal(bool)
    chatbot_backend_changed = Signal(str)
    mini_overlay_enabled_changed = Signal(bool)
    custom_meta_gestures_changed = Signal(bool)
    mode_switch_lock_changed     = Signal(str, bool)
    control_gestures_changed     = Signal(str, bool)

    def __init__(self):
        super().__init__()
        self.is_dark       = False
        self.selected_mode = 'mouse'
        self.mouse_enabled = False
        self._camera_index = 0
        self._cursor_point = 'knuckle'
        self._zone         = 'large'
        self._mouse_side   = 'right'
        self._mode_sources = {k: 'default' for k in ('mouse', 'subway')}
        self._source_btns    = {}
        self._mode_cards     = {}
        self._camera_combo   = None
        self._camera_scan_btn = None
        self._cursor_btns    = {}
        self._zone_btns      = {}
        self._side_btns      = {}
        self._backend_btns   = {}
        self._openai_api_key = ''
        self._show_perf_stats = True
        self._chatbot_enabled = True
        self._chatbot_backend = 'local'
        self._mini_overlay_enabled = True
        self._custom_meta_gestures_enabled = True
        self._custom_mode_combo   = None
        self._selected_custom_id  = ''
        self._mode_switch_locks   = dict(MODE_SWITCH_LOCK_DEFAULTS)
        self._mode_lock_btns      = {}
        self._control_gestures    = dict(CONTROL_GESTURE_DEFAULTS)
        self._control_gesture_btns = {}

        self._load_state()
        self._init_ui()
        self.apply_theme(False)

    def _load_state(self):
        try:
            from logic.app_config import (
                get_game_mode, get_mouse_enabled, get_model_source, get_camera_index,
                get_cursor_point, get_saved_zone, get_mouse_side, get_show_perf_stats,
                get_selected_custom_mode_id,
                get_chatbot_enabled, get_mini_overlay_enabled, get_chatbot_backend,
                get_custom_meta_gestures_enabled, get_openai_api_key,
                get_mode_switch_locked, get_control_gestures_enabled,
            )
            self.selected_mode      = get_game_mode()
            self.mouse_enabled      = get_mouse_enabled()
            self._camera_index      = get_camera_index()
            self._cursor_point      = get_cursor_point()
            self._zone              = get_saved_zone()
            self._mouse_side        = get_mouse_side()
            self._show_perf_stats   = get_show_perf_stats()
            self._chatbot_enabled   = get_chatbot_enabled()
            self._chatbot_backend   = get_chatbot_backend()
            self._openai_api_key    = get_openai_api_key()
            self._mini_overlay_enabled = get_mini_overlay_enabled()
            self._custom_meta_gestures_enabled = get_custom_meta_gestures_enabled()
            self._selected_custom_id = get_selected_custom_mode_id()
            for m in ('mouse', 'subway'):
                self._mode_sources[m] = get_model_source(m)
            for m in MODE_SWITCH_LOCK_DEFAULTS:
                self._mode_switch_locks[m] = get_mode_switch_locked(m)
            for m in CONTROL_GESTURE_DEFAULTS:
                self._control_gestures[m] = get_control_gestures_enabled(m)
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
        self.mouse_panel.setMinimumHeight(52)
        mp = QHBoxLayout(self.mouse_panel)
        mp.setContentsMargins(16, 0, 16, 0)
        mp.setSpacing(0)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self.mouse_hdr_lbl = QLabel("MOUSE MODE")
        self.mouse_sub_lbl = QLabel("Enable cursor control when not in a game mode")
        self.mouse_sub_lbl.setWordWrap(True)
        text_col.addWidget(self.mouse_hdr_lbl)
        text_col.addWidget(self.mouse_sub_lbl)
        mp.addLayout(text_col, stretch=1)

        self.mouse_toggle_btn = QPushButton("ON" if self.mouse_enabled else "OFF")
        self.mouse_toggle_btn.setFixedHeight(26)
        self.mouse_toggle_btn.setMinimumWidth(46)
        self.mouse_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.mouse_toggle_btn.clicked.connect(self._toggle_mouse)
        mp.addWidget(self.mouse_toggle_btn)
        cl.addWidget(self.mouse_panel)

        self.div1 = QWidget()
        self.div1.setFixedHeight(1)
        cl.addWidget(self.div1)

        self.cursor_panel = QWidget()
        self.cursor_panel.setMinimumHeight(52)
        crp = QHBoxLayout(self.cursor_panel)
        crp.setContentsMargins(16, 0, 16, 0)
        crp.setSpacing(0)

        cursor_text_col = QVBoxLayout()
        cursor_text_col.setSpacing(2)
        self.cursor_hdr_lbl = QLabel("CURSOR TRACKING POINT")
        self.cursor_sub_lbl = QLabel("Landmark used to position the cursor on screen")
        self.cursor_sub_lbl.setWordWrap(True)
        cursor_text_col.addWidget(self.cursor_hdr_lbl)
        cursor_text_col.addWidget(self.cursor_sub_lbl)
        crp.addLayout(cursor_text_col, stretch=1)

        cursor_row = QHBoxLayout()
        cursor_row.setSpacing(4)
        tip_btn = QPushButton("TIP")
        tip_btn.setFixedHeight(26)
        tip_btn.setMinimumWidth(46)
        tip_btn.setCursor(Qt.PointingHandCursor)
        tip_btn.clicked.connect(lambda: self._set_cursor_point('tip'))
        knuckle_btn = QPushButton("KNUCKLE")
        knuckle_btn.setFixedHeight(26)
        knuckle_btn.setMinimumWidth(64)
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

        self.zone_panel = QWidget()
        self.zone_panel.setMinimumHeight(52)
        zp = QHBoxLayout(self.zone_panel)
        zp.setContentsMargins(16, 0, 16, 0)
        zp.setSpacing(0)

        zone_text_col = QVBoxLayout()
        zone_text_col.setSpacing(2)
        self.zone_hdr_lbl = QLabel("ZONE SIZE")
        self.zone_sub_lbl = QLabel("Control zone for cursor tracking area")
        self.zone_sub_lbl.setWordWrap(True)
        zone_text_col.addWidget(self.zone_hdr_lbl)
        zone_text_col.addWidget(self.zone_sub_lbl)
        zp.addLayout(zone_text_col, stretch=1)

        zone_row = QHBoxLayout()
        zone_row.setSpacing(4)
        for z in ('small', 'medium', 'large'):
            btn = QPushButton(z.upper())
            btn.setFixedHeight(26)
            btn.setMinimumWidth(50)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, z=z: self._set_zone_setting(z))
            zone_row.addWidget(btn)
            self._zone_btns[z] = btn
        zp.addLayout(zone_row)
        cl.addWidget(self.zone_panel)

        self.div1c = QWidget()
        self.div1c.setFixedHeight(1)
        cl.addWidget(self.div1c)

        self.side_panel = QWidget()
        self.side_panel.setMinimumHeight(52)
        sp = QHBoxLayout(self.side_panel)
        sp.setContentsMargins(16, 0, 16, 0)
        sp.setSpacing(0)

        side_text_col = QVBoxLayout()
        side_text_col.setSpacing(2)
        self.side_hdr_lbl = QLabel("GAME MOUSE SIDE")
        self.side_sub_lbl = QLabel("Which screen half to use when devil horn is active")
        self.side_sub_lbl.setWordWrap(True)
        side_text_col.addWidget(self.side_hdr_lbl)
        side_text_col.addWidget(self.side_sub_lbl)
        sp.addLayout(side_text_col, stretch=1)

        side_row = QHBoxLayout()
        side_row.setSpacing(4)
        for s in ('left', 'right'):
            btn = QPushButton(s.upper())
            btn.setFixedHeight(26)
            btn.setMinimumWidth(46)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, s=s: self._set_mouse_side(s))
            side_row.addWidget(btn)
            self._side_btns[s] = btn
        sp.addLayout(side_row)
        cl.addWidget(self.side_panel)

        self.div1d = QWidget()
        self.div1d.setFixedHeight(1)
        cl.addWidget(self.div1d)

        self.camera_panel = QWidget()
        self.camera_panel.setMinimumHeight(52)
        cp = QHBoxLayout(self.camera_panel)
        cp.setContentsMargins(16, 0, 16, 0)
        cp.setSpacing(0)

        cam_text_col = QVBoxLayout()
        cam_text_col.setSpacing(2)
        self.camera_hdr_lbl = QLabel("CAMERA INPUT")
        self.camera_sub_lbl = QLabel("Select which camera to use for hand tracking")
        self.camera_sub_lbl.setWordWrap(True)
        cam_text_col.addWidget(self.camera_hdr_lbl)
        cam_text_col.addWidget(self.camera_sub_lbl)
        cp.addLayout(cam_text_col, stretch=1)

        self._camera_combo = QComboBox()
        self._camera_combo.setFixedHeight(26)
        self._camera_combo.setMinimumWidth(100)
        self._camera_combo.currentIndexChanged.connect(self._on_camera_combo_changed)
        cp.addWidget(self._camera_combo)

        self._camera_scan_btn = QPushButton("Scan")
        self._camera_scan_btn.setFixedHeight(26)
        self._camera_scan_btn.setMinimumWidth(56)
        self._camera_scan_btn.setCursor(Qt.PointingHandCursor)
        self._camera_scan_btn.clicked.connect(self._scan_cameras)
        cp.addSpacing(6)
        cp.addWidget(self._camera_scan_btn)

        cl.addWidget(self.camera_panel)
        self._populate_cameras(scan=False)

        self.div1e = QWidget()
        self.div1e.setFixedHeight(1)
        cl.addWidget(self.div1e)

        self.perf_panel = QWidget()
        self.perf_panel.setMinimumHeight(52)
        pfp = QHBoxLayout(self.perf_panel)
        pfp.setContentsMargins(16, 0, 16, 0)
        pfp.setSpacing(0)

        perf_text_col = QVBoxLayout()
        perf_text_col.setSpacing(2)
        self.perf_hdr_lbl = QLabel("PERFORMANCE DISPLAY")
        self.perf_sub_lbl = QLabel("Show FPS and latency in the home screen footer")
        self.perf_sub_lbl.setWordWrap(True)
        perf_text_col.addWidget(self.perf_hdr_lbl)
        perf_text_col.addWidget(self.perf_sub_lbl)
        pfp.addLayout(perf_text_col, stretch=1)

        self.perf_toggle_btn = QPushButton("ON" if self._show_perf_stats else "OFF")
        self.perf_toggle_btn.setFixedHeight(26)
        self.perf_toggle_btn.setMinimumWidth(46)
        self.perf_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.perf_toggle_btn.clicked.connect(self._toggle_perf_stats)
        pfp.addWidget(self.perf_toggle_btn)
        cl.addWidget(self.perf_panel)

        self.div1f = QWidget()
        self.div1f.setFixedHeight(1)
        cl.addWidget(self.div1f)

        self.chatbot_section_hdr = QLabel("CHATBOT")
        cl.addWidget(self.chatbot_section_hdr)

        self.chatbot_panel = QWidget()
        self.chatbot_panel.setMinimumHeight(52)
        cbp = QHBoxLayout(self.chatbot_panel)
        cbp.setContentsMargins(16, 0, 16, 0)
        cbp.setSpacing(0)

        chatbot_text_col = QVBoxLayout()
        chatbot_text_col.setSpacing(2)
        self.chatbot_hdr_lbl = QLabel("ENABLE CHATBOT")
        self.chatbot_sub_lbl = QLabel("Ask HandBot questions from the chat panel")
        self.chatbot_sub_lbl.setWordWrap(True)
        chatbot_text_col.addWidget(self.chatbot_hdr_lbl)
        chatbot_text_col.addWidget(self.chatbot_sub_lbl)
        cbp.addLayout(chatbot_text_col, stretch=1)

        self.chatbot_toggle_btn = QPushButton("ON" if self._chatbot_enabled else "OFF")
        self.chatbot_toggle_btn.setFixedHeight(26)
        self.chatbot_toggle_btn.setMinimumWidth(46)
        self.chatbot_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.chatbot_toggle_btn.clicked.connect(self._toggle_chatbot_enabled)
        cbp.addWidget(self.chatbot_toggle_btn)
        cl.addWidget(self.chatbot_panel)

        self.div1g = QWidget()
        self.div1g.setFixedHeight(1)
        cl.addWidget(self.div1g)

        self.backend_panel = QWidget()
        self.backend_panel.setMinimumHeight(52)
        bkp = QHBoxLayout(self.backend_panel)
        bkp.setContentsMargins(16, 0, 16, 0)
        bkp.setSpacing(0)

        backend_text_col = QVBoxLayout()
        backend_text_col.setSpacing(2)
        self.backend_hdr_lbl = QLabel("AI BACKEND")
        self.backend_sub_lbl = QLabel(
            "LOCAL runs fully offline. CHATGPT uses the OpenAI API - add your "
            "API key below."
        )
        self.backend_sub_lbl.setWordWrap(True)
        backend_text_col.addWidget(self.backend_hdr_lbl)
        backend_text_col.addWidget(self.backend_sub_lbl)
        bkp.addLayout(backend_text_col, stretch=1)

        backend_row = QHBoxLayout()
        backend_row.setSpacing(4)
        self._backend_btns = {}
        for b, label in (("local", "LOCAL"), ("openai", "CHATGPT")):
            btn = QPushButton(label)
            btn.setFixedHeight(26)
            btn.setMinimumWidth(64)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, b=b: self._set_chatbot_backend(b))
            backend_row.addWidget(btn)
            self._backend_btns[b] = btn
        bkp.addLayout(backend_row)
        cl.addWidget(self.backend_panel)

        self.apikey_panel = QWidget()
        self.apikey_panel.setMinimumHeight(76)
        akp = QVBoxLayout(self.apikey_panel)
        akp.setContentsMargins(16, 10, 16, 10)
        akp.setSpacing(6)

        self.apikey_hdr_lbl = QLabel("OPENAI API KEY")
        akp.addWidget(self.apikey_hdr_lbl)

        self.apikey_sub_lbl = QLabel(
            "Stored locally on this device - no .env file needed"
        )
        self.apikey_sub_lbl.setWordWrap(True)
        akp.addWidget(self.apikey_sub_lbl)

        apikey_row = QHBoxLayout()
        apikey_row.setSpacing(6)

        self.apikey_input = QLineEdit()
        self.apikey_input.setEchoMode(QLineEdit.Password)
        self.apikey_input.setPlaceholderText("sk-...")
        self.apikey_input.setText(self._openai_api_key)
        self.apikey_input.setFixedHeight(28)
        self.apikey_input.textEdited.connect(self._on_apikey_edited)
        apikey_row.addWidget(self.apikey_input, stretch=1)

        self.apikey_show_btn = QPushButton("SHOW")
        self.apikey_show_btn.setFixedHeight(28)
        self.apikey_show_btn.setMinimumWidth(56)
        self.apikey_show_btn.setCursor(Qt.PointingHandCursor)
        self.apikey_show_btn.setCheckable(True)
        self.apikey_show_btn.clicked.connect(self._toggle_apikey_visibility)
        apikey_row.addWidget(self.apikey_show_btn)

        self.apikey_save_btn = QPushButton("SAVE")
        self.apikey_save_btn.setFixedHeight(28)
        self.apikey_save_btn.setMinimumWidth(64)
        self.apikey_save_btn.setCursor(Qt.PointingHandCursor)
        self.apikey_save_btn.clicked.connect(self._save_openai_api_key)
        apikey_row.addWidget(self.apikey_save_btn)

        akp.addLayout(apikey_row)

        self.apikey_status_lbl = QLabel("")
        self.apikey_status_lbl.setVisible(False)
        akp.addWidget(self.apikey_status_lbl)

        cl.addWidget(self.apikey_panel)

        self.div1h = QWidget()
        self.div1h.setFixedHeight(1)
        cl.addWidget(self.div1h)

        self.overlay_panel = QWidget()
        self.overlay_panel.setMinimumHeight(52)
        ovp = QHBoxLayout(self.overlay_panel)
        ovp.setContentsMargins(16, 0, 16, 0)
        ovp.setSpacing(0)

        overlay_text_col = QVBoxLayout()
        overlay_text_col.setSpacing(2)
        self.overlay_hdr_lbl = QLabel("STATUS OVERLAY")
        self.overlay_sub_lbl = QLabel("Show a small status panel when you switch to another app")
        self.overlay_sub_lbl.setWordWrap(True)
        overlay_text_col.addWidget(self.overlay_hdr_lbl)
        overlay_text_col.addWidget(self.overlay_sub_lbl)
        ovp.addLayout(overlay_text_col, stretch=1)

        self.overlay_toggle_btn = QPushButton("ON" if self._mini_overlay_enabled else "OFF")
        self.overlay_toggle_btn.setFixedHeight(26)
        self.overlay_toggle_btn.setMinimumWidth(46)
        self.overlay_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.overlay_toggle_btn.clicked.connect(self._toggle_mini_overlay_enabled)
        ovp.addWidget(self.overlay_toggle_btn)
        cl.addWidget(self.overlay_panel)

        self.div2 = QWidget()
        self.div2.setFixedHeight(1)
        cl.addWidget(self.div2)

        self.mode_section_hdr = QLabel("GAME MODE")
        cl.addWidget(self.mode_section_hdr)

        MODE_GRID_COLS = 3

        mode_grid_widget = QWidget()
        mode_grid = QGridLayout(mode_grid_widget)
        mode_grid.setHorizontalSpacing(12)
        mode_grid.setVerticalSpacing(12)
        mode_grid.setContentsMargins(0, 0, 0, 0)
        for _c in range(MODE_GRID_COLS):
            mode_grid.setColumnStretch(_c, 1)

        modes = [
            ("🖱", "MOUSE",      "mouse"),
            ("🚇", "SUBWAY",     "subway"),
            ("🏎", "RACING",     "racing"),
            ("🌍", "OPEN WORLD", "open_world"),
            ("🏒", "AIR HOCKEY", "air_hockey"),
        ]

        for idx, (icon, label, key) in enumerate(modes):
            card_col = QVBoxLayout()
            card_col.setSpacing(6)

            card = QPushButton()
            card.setMinimumSize(100, 80)
            card.setFixedHeight(96)
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
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

            if key in ('mouse', 'subway'):
                src_row = QHBoxLayout()
                src_row.setSpacing(4)
                src_row.setContentsMargins(0, 0, 0, 0)

                def_btn = QPushButton("DEFAULT")
                def_btn.setFixedHeight(22)
                def_btn.setMinimumWidth(56)
                def_btn.setCursor(Qt.PointingHandCursor)
                def_btn.clicked.connect(lambda _, k=key: self._set_model_source(k, 'default'))

                custom_btn = QPushButton("CUSTOM")
                custom_btn.setFixedHeight(22)
                custom_btn.setMinimumWidth(52)
                custom_btn.setCursor(Qt.PointingHandCursor)
                custom_btn.clicked.connect(lambda _, k=key: self._set_model_source(k, 'custom'))
                custom_btn.setEnabled(self._custom_exists(key))

                src_row.addWidget(def_btn)
                src_row.addWidget(custom_btn)

                self._source_btns[key] = {'default': def_btn, 'custom': custom_btn}

                card_col.addLayout(src_row)
            else:
                ah_spacer = QWidget()
                ah_spacer.setFixedHeight(22)
                card_col.addWidget(ah_spacer)

            row, col = divmod(idx, MODE_GRID_COLS)
            mode_grid.addLayout(card_col, row, col)

        custom_card_col = QVBoxLayout()
        custom_card_col.setSpacing(6)

        custom_card = QPushButton()
        custom_card.setMinimumSize(100, 80)
        custom_card.setFixedHeight(96)
        custom_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        custom_card.setCheckable(True)
        custom_card.setCursor(Qt.PointingHandCursor)
        custom_card.clicked.connect(lambda: self.select_mode('custom'))

        cc_inner = QVBoxLayout(custom_card)
        cc_inner.setAlignment(Qt.AlignCenter)
        cc_inner.setSpacing(6)
        cc_inner.setContentsMargins(8, 8, 8, 8)

        cc_icon_lbl = QLabel("🎮")
        cc_icon_lbl.setAlignment(Qt.AlignCenter)
        cc_icon_lbl.setStyleSheet("font-size: 26px; background: transparent; border: none;")
        cc_name_lbl = QLabel("CUSTOM")
        cc_name_lbl.setAlignment(Qt.AlignCenter)
        cc_inner.addWidget(cc_icon_lbl)
        cc_inner.addWidget(cc_name_lbl)

        self._mode_cards['custom'] = {'card': custom_card, 'name': cc_name_lbl}
        custom_card_col.addWidget(custom_card)

        cc_spacer = QWidget()
        cc_spacer.setFixedHeight(22)
        custom_card_col.addWidget(cc_spacer)

        custom_row, custom_col = divmod(len(modes), MODE_GRID_COLS)
        mode_grid.addLayout(custom_card_col, custom_row, custom_col)

        cl.addWidget(mode_grid_widget)

        self.div1i = QWidget()
        self.div1i.setFixedHeight(1)
        cl.addWidget(self.div1i)

        self._custom_mode_panel = QWidget()
        self._custom_mode_panel.setMinimumHeight(52)
        cmp_l = QHBoxLayout(self._custom_mode_panel)
        cmp_l.setContentsMargins(16, 0, 16, 0)
        cmp_l.setSpacing(0)

        cmp_text = QVBoxLayout()
        cmp_text.setSpacing(2)
        self._cmp_hdr_lbl = QLabel("CUSTOM GAME MODE")
        self._cmp_sub_lbl = QLabel("Choose which trained custom mode to use")
        self._cmp_sub_lbl.setWordWrap(True)
        cmp_text.addWidget(self._cmp_hdr_lbl)
        cmp_text.addWidget(self._cmp_sub_lbl)
        cmp_l.addLayout(cmp_text, stretch=1)

        self._custom_mode_combo = QComboBox()
        self._custom_mode_combo.setFixedHeight(26)
        self._custom_mode_combo.setMinimumWidth(120)
        self._custom_mode_combo.currentIndexChanged.connect(self._on_custom_mode_combo_changed)
        cmp_l.addWidget(self._custom_mode_combo)

        cl.addWidget(self._custom_mode_panel)
        self._populate_custom_mode_combo()

        self.div1j = QWidget()
        self.div1j.setFixedHeight(1)
        cl.addWidget(self.div1j)

        self.meta_gestures_panel = QWidget()
        self.meta_gestures_panel.setMinimumHeight(52)
        mgp = QHBoxLayout(self.meta_gestures_panel)
        mgp.setContentsMargins(16, 0, 16, 0)
        mgp.setSpacing(0)

        meta_gestures_text_col = QVBoxLayout()
        meta_gestures_text_col.setSpacing(2)
        self.meta_gestures_hdr_lbl = QLabel("ALLOW META GESTURES IN CUSTOM MODE")
        self.meta_gestures_sub_lbl = QLabel(
            "Devil horn mouse overlay and game-option mode switching while in Custom Mode")
        self.meta_gestures_sub_lbl.setWordWrap(True)
        meta_gestures_text_col.addWidget(self.meta_gestures_hdr_lbl)
        meta_gestures_text_col.addWidget(self.meta_gestures_sub_lbl)
        mgp.addLayout(meta_gestures_text_col, stretch=1)

        self.meta_gestures_toggle_btn = QPushButton(
            "ON" if self._custom_meta_gestures_enabled else "OFF")
        self.meta_gestures_toggle_btn.setFixedHeight(26)
        self.meta_gestures_toggle_btn.setMinimumWidth(46)
        self.meta_gestures_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.meta_gestures_toggle_btn.clicked.connect(self._toggle_custom_meta_gestures_enabled)
        mgp.addWidget(self.meta_gestures_toggle_btn)
        cl.addWidget(self.meta_gestures_panel)

        self.div1k = QWidget()
        self.div1k.setFixedHeight(1)
        cl.addWidget(self.div1k)

        self.mode_lock_panel = QWidget()
        mlp = QVBoxLayout(self.mode_lock_panel)
        mlp.setContentsMargins(16, 10, 16, 10)
        mlp.setSpacing(6)

        mode_lock_text_col = QVBoxLayout()
        mode_lock_text_col.setSpacing(2)
        self.mode_lock_hdr_lbl = QLabel("LOCK GESTURE MODE SWITCHING")
        self.mode_lock_sub_lbl = QLabel(
            "When ON for a mode, the hand-gesture shortcut can't switch out of it while it's active")
        self.mode_lock_sub_lbl.setWordWrap(True)
        mode_lock_text_col.addWidget(self.mode_lock_hdr_lbl)
        mode_lock_text_col.addWidget(self.mode_lock_sub_lbl)
        mlp.addLayout(mode_lock_text_col)

        mode_lock_row = QHBoxLayout()
        mode_lock_row.setSpacing(6)
        self._mode_lock_name_lbls = []
        for mode_id, mode_label in MODE_SWITCH_LOCK_LABELS:
            col = QVBoxLayout()
            col.setSpacing(2)
            name_lbl = QLabel(mode_label)
            name_lbl.setAlignment(Qt.AlignCenter)
            self._mode_lock_name_lbls.append(name_lbl)
            btn = QPushButton()
            btn.setFixedHeight(24)
            btn.setMinimumWidth(64)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, m=mode_id: self._toggle_mode_switch_lock(m))
            self._mode_lock_btns[mode_id] = btn
            col.addWidget(name_lbl)
            col.addWidget(btn)
            mode_lock_row.addLayout(col)
        mlp.addLayout(mode_lock_row)
        cl.addWidget(self.mode_lock_panel)
        self._refresh_mode_lock_buttons()

        self.div1l = QWidget()
        self.div1l.setFixedHeight(1)
        cl.addWidget(self.div1l)

        self.control_gesture_panel = QWidget()
        cgp = QVBoxLayout(self.control_gesture_panel)
        cgp.setContentsMargins(16, 10, 16, 10)
        cgp.setSpacing(6)

        control_gesture_text_col = QVBoxLayout()
        control_gesture_text_col.setSpacing(2)
        self.control_gesture_hdr_lbl = QLabel("PAUSE / CLOSE HAND GESTURES")
        self.control_gesture_sub_lbl = QLabel(
            "Both palms open = pause, both fists held = close app, for that mode")
        self.control_gesture_sub_lbl.setWordWrap(True)
        control_gesture_text_col.addWidget(self.control_gesture_hdr_lbl)
        control_gesture_text_col.addWidget(self.control_gesture_sub_lbl)
        cgp.addLayout(control_gesture_text_col)

        control_gesture_row = QHBoxLayout()
        control_gesture_row.setSpacing(6)
        self._control_gesture_name_lbls = []
        for mode_id, mode_label in CONTROL_GESTURE_LABELS:
            col = QVBoxLayout()
            col.setSpacing(2)
            name_lbl = QLabel(mode_label)
            name_lbl.setAlignment(Qt.AlignCenter)
            self._control_gesture_name_lbls.append(name_lbl)
            btn = QPushButton()
            btn.setFixedHeight(24)
            btn.setMinimumWidth(64)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, m=mode_id: self._toggle_control_gesture(m))
            self._control_gesture_btns[mode_id] = btn
            col.addWidget(name_lbl)
            col.addWidget(btn)
            control_gesture_row.addLayout(col)
        cgp.addLayout(control_gesture_row)
        cl.addWidget(self.control_gesture_panel)
        self._refresh_control_gesture_buttons()

        cl.addStretch()

        self._settings_scroll = QScrollArea()
        self._settings_scroll.setWidgetResizable(True)
        self._settings_scroll.setFrameShape(QScrollArea.NoFrame)
        self._settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._settings_scroll.setWidget(content)
        root.addWidget(self._settings_scroll, stretch=1)

    def _populate_custom_mode_combo(self):
        if self._custom_mode_combo is None:
            return
        self._custom_mode_combo.blockSignals(True)
        self._custom_mode_combo.clear()
        try:
            from logic.app_config import get_custom_modes
            modes = [m for m in get_custom_modes() if _custom_game_mode_model_exists(m['id'])]
        except Exception:
            modes = []
        if not modes:
            self._custom_mode_combo.addItem("No trained custom modes yet", "")
            self._custom_mode_combo.setEnabled(False)
        else:
            self._custom_mode_combo.setEnabled(True)
            for m in modes:
                self._custom_mode_combo.addItem(m['name'], m['id'])
            for i in range(self._custom_mode_combo.count()):
                if self._custom_mode_combo.itemData(i) == self._selected_custom_id:
                    self._custom_mode_combo.setCurrentIndex(i)
                    break
        if hasattr(self, '_custom_mode_panel'):
            self._custom_mode_panel.setEnabled(bool(modes))
        self._custom_mode_combo.blockSignals(False)

    def _on_custom_mode_combo_changed(self, idx: int):
        if self._custom_mode_combo is None:
            return
        mode_id = self._custom_mode_combo.itemData(idx)
        if mode_id and mode_id != self._selected_custom_id:
            self._selected_custom_id = mode_id
            try:
                from logic.app_config import set_selected_custom_mode_id
                set_selected_custom_mode_id(mode_id)
            except Exception:
                pass
            self.apply_theme(self.is_dark)
            self.custom_mode_selected.emit(mode_id, 'custom')

    def refresh_custom_modes(self):
        self._populate_custom_mode_combo()
        self.apply_theme(self.is_dark)

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
                self.model_source_changed.emit(key, 'default')
        try:
            from logic.app_config import get_selected_custom_mode_id
            self._selected_custom_id = get_selected_custom_mode_id()
        except Exception:
            pass
        self._populate_custom_mode_combo()
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

    def _set_zone_setting(self, zone: str):
        self._zone = zone
        try:
            from logic.app_config import set_zone
            set_zone(zone)
        except Exception:
            pass
        self.zone_changed.emit(zone)
        self.apply_theme(self.is_dark)

    def _set_mouse_side(self, side: str):
        self._mouse_side = side
        try:
            from logic.app_config import set_mouse_side
            set_mouse_side(side)
        except Exception:
            pass
        self.mouse_side_changed.emit(side)
        self.apply_theme(self.is_dark)

    def _toggle_perf_stats(self):
        self._show_perf_stats = not self._show_perf_stats
        self.perf_toggle_btn.setText("ON" if self._show_perf_stats else "OFF")
        try:
            from logic.app_config import set_show_perf_stats
            set_show_perf_stats(self._show_perf_stats)
        except Exception:
            pass
        self.perf_stats_changed.emit(self._show_perf_stats)
        self.apply_theme(self.is_dark)

    def _toggle_chatbot_enabled(self):
        self._chatbot_enabled = not self._chatbot_enabled
        self.chatbot_toggle_btn.setText("ON" if self._chatbot_enabled else "OFF")
        try:
            from logic.app_config import set_chatbot_enabled
            set_chatbot_enabled(self._chatbot_enabled)
        except Exception:
            pass

        self.chatbot_enabled_changed.emit(self._chatbot_enabled)
        self.apply_theme(self.is_dark)

    def _set_chatbot_backend(self, backend: str):
        if backend == self._chatbot_backend:
            return
        self._chatbot_backend = backend
        try:
            from logic.app_config import set_chatbot_backend
            set_chatbot_backend(self._chatbot_backend)
        except Exception:
            pass

        self.chatbot_backend_changed.emit(self._chatbot_backend)
        self.apply_theme(self.is_dark)

    def _toggle_apikey_visibility(self):
        if self.apikey_show_btn.isChecked():
            self.apikey_input.setEchoMode(QLineEdit.Normal)
            self.apikey_show_btn.setText("HIDE")
        else:
            self.apikey_input.setEchoMode(QLineEdit.Password)
            self.apikey_show_btn.setText("SHOW")

    def _save_openai_api_key(self):
        key = self.apikey_input.text().strip()
        self._openai_api_key = key
        try:
            from logic.app_config import set_openai_api_key
            set_openai_api_key(key)
        except Exception:
            pass
        try:
            import threading
            from logic.chatbot.rag_service import reset_engine
            threading.Thread(target=reset_engine, args=("openai",), daemon=True).start()
        except Exception:
            pass

        self.apikey_status_lbl.setText(
            "Key saved - cleared" if not key else "Key saved"
        )
        self.apikey_status_lbl.setVisible(True)
        self._flash_apikey_saved()
        QTimer.singleShot(2200, lambda: self.apikey_status_lbl.setVisible(False))

    def _on_apikey_edited(self, _text):
        self.apikey_status_lbl.setVisible(False)

    def _flash_apikey_saved(self):
        saved_bg = "#2E7D32"
        original = self.apikey_save_btn.styleSheet()
        self.apikey_save_btn.setText("SAVED ✓")
        self.apikey_save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {saved_bg}; color: #FFFFFF;
                font-size: 8px; font-weight: 700; letter-spacing: 1px;
                border: 1px solid {saved_bg}; border-radius: 2px;
            }}
        """)
        QTimer.singleShot(1200, lambda: self._restore_apikey_save_btn(original))

    def _restore_apikey_save_btn(self, original_style: str):
        self.apikey_save_btn.setText("SAVE")
        self.apikey_save_btn.setStyleSheet(original_style)

    def _toggle_mini_overlay_enabled(self):
        self._mini_overlay_enabled = not self._mini_overlay_enabled
        self.overlay_toggle_btn.setText("ON" if self._mini_overlay_enabled else "OFF")
        try:
            from logic.app_config import set_mini_overlay_enabled
            set_mini_overlay_enabled(self._mini_overlay_enabled)
        except Exception:
            pass

        self.mini_overlay_enabled_changed.emit(self._mini_overlay_enabled)
        self.apply_theme(self.is_dark)

    def _toggle_custom_meta_gestures_enabled(self):
        self._custom_meta_gestures_enabled = not self._custom_meta_gestures_enabled
        self.meta_gestures_toggle_btn.setText("ON" if self._custom_meta_gestures_enabled else "OFF")
        try:
            from logic.app_config import set_custom_meta_gestures_enabled
            set_custom_meta_gestures_enabled(self._custom_meta_gestures_enabled)
        except Exception:
            pass

        self.custom_meta_gestures_changed.emit(self._custom_meta_gestures_enabled)
        self.apply_theme(self.is_dark)

    def _toggle_mode_switch_lock(self, mode_id: str):
        locked = not self._mode_switch_locks.get(mode_id, MODE_SWITCH_LOCK_DEFAULTS.get(mode_id, False))
        self._mode_switch_locks[mode_id] = locked
        try:
            from logic.app_config import set_mode_switch_locked
            set_mode_switch_locked(mode_id, locked)
        except Exception:
            pass
        self._refresh_mode_lock_buttons()
        self.mode_switch_lock_changed.emit(mode_id, locked)
        self.apply_theme(self.is_dark)

    def _refresh_mode_lock_buttons(self):
        for mode_id, btn in self._mode_lock_btns.items():
            locked = self._mode_switch_locks.get(mode_id, MODE_SWITCH_LOCK_DEFAULTS.get(mode_id, False))
            btn.setText("LOCKED" if locked else "OPEN")

    def _toggle_control_gesture(self, mode_id: str):
        enabled = not self._control_gestures.get(mode_id, CONTROL_GESTURE_DEFAULTS.get(mode_id, False))
        self._control_gestures[mode_id] = enabled
        try:
            from logic.app_config import set_control_gestures_enabled
            set_control_gestures_enabled(mode_id, enabled)
        except Exception:
            pass
        self._refresh_control_gesture_buttons()
        self.control_gestures_changed.emit(mode_id, enabled)
        self.apply_theme(self.is_dark)

    def _refresh_control_gesture_buttons(self):
        for mode_id, btn in self._control_gesture_btns.items():
            enabled = self._control_gestures.get(mode_id, CONTROL_GESTURE_DEFAULTS.get(mode_id, False))
            btn.setText("ON" if enabled else "OFF")

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

    def _populate_cameras(self, scan=True):
        if self._camera_combo is None:
            return
        cameras = []
        if scan:
            try:
                from logic.hand_controller import list_cameras
                cameras = list_cameras()
            except Exception:
                cameras = []
            try:
                from logic.app_config import set_cached_cameras
                set_cached_cameras(cameras)
            except Exception:
                pass
        else:
            try:
                from logic.app_config import get_cached_cameras
                cameras = get_cached_cameras()
            except Exception:
                cameras = []
            if self._camera_index not in cameras:
                cameras = sorted(set(cameras) | {self._camera_index})

        self._camera_combo.blockSignals(True)
        self._camera_combo.clear()
        if not cameras:
            self._camera_combo.addItem("Press Scan to detect cameras", -1)
        else:
            for idx in cameras:
                self._camera_combo.addItem(
                    f"Camera {idx}" + (" (Default)" if idx == 0 else ""), idx)
            for i in range(self._camera_combo.count()):
                if self._camera_combo.itemData(i) == self._camera_index:
                    self._camera_combo.setCurrentIndex(i)
                    break
        self._camera_combo.blockSignals(False)

    def _scan_cameras(self):
        if self._camera_scan_btn is not None:
            self._camera_scan_btn.setEnabled(False)
            self._camera_scan_btn.setText("Scanning...")
        try:
            self._populate_cameras(scan=True)
        finally:
            if self._camera_scan_btn is not None:
                self._camera_scan_btn.setEnabled(True)
                self._camera_scan_btn.setText("Scan")

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

    def set_zone(self, zone: str):
        if self._zone == zone:
            return
        self._zone = zone
        self.apply_theme(self.is_dark)

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

        self._settings_scroll.setStyleSheet(f"""
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
        self._settings_scroll.viewport().setStyleSheet(f"background-color: {bg}; border: none;")

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

        self.zone_panel.setStyleSheet(
            f"background-color: {panel}; border: 1px solid {border};")
        self.zone_hdr_lbl.setStyleSheet(
            f"font-size: 9px; font-weight: 700; color: {text}; letter-spacing: 1.5px; background: transparent; border: none;")
        self.zone_sub_lbl.setStyleSheet(
            f"font-size: 8px; color: {muted}; letter-spacing: 1px; background: transparent; border: none;")
        for z, btn in self._zone_btns.items():
            if z == self._zone:
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
        self.div1c.setStyleSheet(f"background-color: {border};")

        self.side_panel.setStyleSheet(
            f"background-color: {panel}; border: 1px solid {border};")
        self.side_hdr_lbl.setStyleSheet(
            f"font-size: 9px; font-weight: 700; color: {text}; letter-spacing: 1.5px; background: transparent; border: none;")
        self.side_sub_lbl.setStyleSheet(
            f"font-size: 8px; color: {muted}; letter-spacing: 1px; background: transparent; border: none;")
        for s, btn in self._side_btns.items():
            if s == self._mouse_side:
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
        self.div1d.setStyleSheet(f"background-color: {border};")

        self.div1e.setStyleSheet(f"background-color: {border};")

        self.perf_panel.setStyleSheet(
            f"background-color: {panel}; border: 1px solid {border};")
        self.perf_hdr_lbl.setStyleSheet(
            f"font-size: 9px; font-weight: 700; color: {text}; letter-spacing: 1.5px; background: transparent; border: none;")
        self.perf_sub_lbl.setStyleSheet(
            f"font-size: 8px; color: {muted}; letter-spacing: 1px; background: transparent; border: none;")
        if self._show_perf_stats:
            self.perf_toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {tog_on_bg}; color: {tog_on_txt};
                    font-size: 8px; font-weight: 700; letter-spacing: 1px;
                    border: 1px solid {tog_on_bg}; border-radius: 2px;
                }}
            """)
        else:
            self.perf_toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {tog_off_bg}; color: {tog_off_txt};
                    font-size: 8px; font-weight: 700; letter-spacing: 1px;
                    border: 1px solid {border}; border-radius: 2px;
                }}
                QPushButton:hover {{ background-color: {hover}; }}
            """)

        self.div1f.setStyleSheet(f"background-color: {border};")

        self.chatbot_section_hdr.setStyleSheet(
            f"color: {text}; font-size: 12px; font-weight: 800; letter-spacing: 1.5px; background: transparent; border: none;")

        self.chatbot_panel.setStyleSheet(
            f"background-color: {panel}; border: 1px solid {border};")
        self.chatbot_hdr_lbl.setStyleSheet(
            f"font-size: 9px; font-weight: 700; color: {text}; letter-spacing: 1.5px; background: transparent; border: none;")
        self.chatbot_sub_lbl.setStyleSheet(
            f"font-size: 8px; color: {muted}; letter-spacing: 1px; background: transparent; border: none;")
        if self._chatbot_enabled:
            self.chatbot_toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {tog_on_bg}; color: {tog_on_txt};
                    font-size: 8px; font-weight: 700; letter-spacing: 1px;
                    border: 1px solid {tog_on_bg}; border-radius: 2px;
                }}
            """)
        else:
            self.chatbot_toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {tog_off_bg}; color: {tog_off_txt};
                    font-size: 8px; font-weight: 700; letter-spacing: 1px;
                    border: 1px solid {border}; border-radius: 2px;
                }}
                QPushButton:hover {{ background-color: {hover}; }}
            """)

        self.backend_panel.setStyleSheet(
            f"background-color: {panel}; border: 1px solid {border};")
        self.backend_hdr_lbl.setStyleSheet(
            f"font-size: 9px; font-weight: 700; color: {text}; letter-spacing: 1.5px; background: transparent; border: none;")
        self.backend_sub_lbl.setStyleSheet(
            f"font-size: 8px; color: {muted}; letter-spacing: 1px; background: transparent; border: none;")
        for b, btn in self._backend_btns.items():
            if b == self._chatbot_backend:
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

        self.apikey_panel.setStyleSheet(
            f"background-color: {panel}; border: 1px solid {border};")
        self.apikey_hdr_lbl.setStyleSheet(
            f"font-size: 9px; font-weight: 700; color: {text}; letter-spacing: 1.5px; background: transparent; border: none;")
        self.apikey_sub_lbl.setStyleSheet(
            f"font-size: 8px; color: {muted}; letter-spacing: 1px; background: transparent; border: none;")
        self.apikey_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {bg}; color: {text};
                border: 1px solid {border}; border-radius: 2px;
                padding: 0 6px; font-size: 10px;
            }}
            QLineEdit:focus {{ border-color: {tog_on_bg}; }}
        """)
        for btn in (self.apikey_show_btn, self.apikey_save_btn):
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {tog_off_bg}; color: {tog_off_txt};
                    font-size: 8px; font-weight: 700; letter-spacing: 1px;
                    border: 1px solid {border}; border-radius: 2px;
                }}
                QPushButton:hover {{ background-color: {hover}; color: {text}; }}
            """)
        self.apikey_status_lbl.setStyleSheet(
            "font-size: 8px; font-weight: 700; color: #2E7D32; letter-spacing: 1px; background: transparent; border: none;")

        self.div1h.setStyleSheet(f"background-color: {border};")

        self.div1g.setStyleSheet(f"background-color: {border};")

        self.overlay_panel.setStyleSheet(
            f"background-color: {panel}; border: 1px solid {border};")
        self.overlay_hdr_lbl.setStyleSheet(
            f"font-size: 9px; font-weight: 700; color: {text}; letter-spacing: 1.5px; background: transparent; border: none;")
        self.overlay_sub_lbl.setStyleSheet(
            f"font-size: 8px; color: {muted}; letter-spacing: 1px; background: transparent; border: none;")
        if self._mini_overlay_enabled:
            self.overlay_toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {tog_on_bg}; color: {tog_on_txt};
                    font-size: 8px; font-weight: 700; letter-spacing: 1px;
                    border: 1px solid {tog_on_bg}; border-radius: 2px;
                }}
            """)
        else:
            self.overlay_toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {tog_off_bg}; color: {tog_off_txt};
                    font-size: 8px; font-weight: 700; letter-spacing: 1px;
                    border: 1px solid {border}; border-radius: 2px;
                }}
                QPushButton:hover {{ background-color: {hover}; }}
            """)
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
        if self._camera_scan_btn:
            self._camera_scan_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {tog_off_bg}; color: {tog_off_txt};
                    font-size: 8px; font-weight: 700; letter-spacing: 1px;
                    border: 1px solid {border}; border-radius: 2px;
                }}
                QPushButton:hover {{ background-color: {hover}; color: {text}; }}
                QPushButton:disabled {{ color: {muted}; }}
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

        if hasattr(self, '_custom_mode_panel'):
            self._custom_mode_panel.setStyleSheet(
                f"background-color: {panel}; border: 1px solid {border};")
            self._cmp_hdr_lbl.setStyleSheet(
                f"font-size: 9px; font-weight: 700; color: {text}; letter-spacing: 1.5px; background: transparent; border: none;")
            self._cmp_sub_lbl.setStyleSheet(
                f"font-size: 8px; color: {muted}; letter-spacing: 1px; background: transparent; border: none;")
            combo_style = f"""
                QComboBox {{
                    background: {panel}; color: {text};
                    border: 1px solid {border}; border-radius: 2px;
                    padding: 2px 6px; font-size: 8px; letter-spacing: 1px;
                }}
                QComboBox::drop-down {{ border: none; width: 16px; }}
                QComboBox::down-arrow {{
                    border-left: 3px solid transparent;
                    border-right: 3px solid transparent;
                    border-top: 4px solid {dim};
                    width: 0; height: 0; margin-right: 4px;
                }}
                QComboBox QAbstractItemView {{
                    background: {panel}; color: {text};
                    border: 1px solid {border};
                    selection-background-color: {hover};
                    selection-color: {text}; outline: none;
                }}
                QComboBox:disabled {{ color: {muted}; }}
            """
            if self._custom_mode_combo:
                self._custom_mode_combo.setStyleSheet(combo_style)

        if hasattr(self, 'div1i'):
            self.div1i.setStyleSheet(f"background-color: {border};")

        if hasattr(self, 'meta_gestures_panel'):
            self.meta_gestures_panel.setStyleSheet(
                f"background-color: {panel}; border: 1px solid {border};")
            self.meta_gestures_hdr_lbl.setStyleSheet(
                f"font-size: 9px; font-weight: 700; color: {text}; letter-spacing: 1.5px; background: transparent; border: none;")
            self.meta_gestures_sub_lbl.setStyleSheet(
                f"font-size: 8px; color: {muted}; letter-spacing: 1px; background: transparent; border: none;")
            if self._custom_meta_gestures_enabled:
                self.meta_gestures_toggle_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {tog_on_bg}; color: {tog_on_txt};
                        font-size: 8px; font-weight: 700; letter-spacing: 1px;
                        border: 1px solid {tog_on_bg}; border-radius: 2px;
                    }}
                """)
            else:
                self.meta_gestures_toggle_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {tog_off_bg}; color: {tog_off_txt};
                        font-size: 8px; font-weight: 700; letter-spacing: 1px;
                        border: 1px solid {border}; border-radius: 2px;
                    }}
                    QPushButton:hover {{ background-color: {hover}; }}
                """)
        if hasattr(self, 'div1j'):
            self.div1j.setStyleSheet(f"background-color: {border};")

        if hasattr(self, 'mode_lock_panel'):
            self.mode_lock_panel.setStyleSheet(
                f"background-color: {panel}; border: 1px solid {border};")
            self.mode_lock_hdr_lbl.setStyleSheet(
                f"font-size: 9px; font-weight: 700; color: {text}; letter-spacing: 1.5px; background: transparent; border: none;")
            self.mode_lock_sub_lbl.setStyleSheet(
                f"font-size: 8px; color: {muted}; letter-spacing: 1px; background: transparent; border: none;")
            for name_lbl in self._mode_lock_name_lbls:
                name_lbl.setStyleSheet(
                    f"font-size: 8px; color: {muted}; letter-spacing: 0.5px; background: transparent; border: none;")
            for mode_id, btn in self._mode_lock_btns.items():
                locked = self._mode_switch_locks.get(mode_id, MODE_SWITCH_LOCK_DEFAULTS.get(mode_id, False))
                if locked:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {tog_off_bg}; color: {tog_off_txt};
                            font-size: 8px; font-weight: 700; letter-spacing: 1px;
                            border: 1px solid {border}; border-radius: 2px;
                        }}
                        QPushButton:hover {{ background-color: {hover}; }}
                    """)
                else:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {tog_on_bg}; color: {tog_on_txt};
                            font-size: 8px; font-weight: 700; letter-spacing: 1px;
                            border: 1px solid {tog_on_bg}; border-radius: 2px;
                        }}
                    """)

        if hasattr(self, 'div1l'):
            self.div1l.setStyleSheet(f"background-color: {border};")

        if hasattr(self, 'control_gesture_panel'):
            self.control_gesture_panel.setStyleSheet(
                f"background-color: {panel}; border: 1px solid {border};")
            self.control_gesture_hdr_lbl.setStyleSheet(
                f"font-size: 9px; font-weight: 700; color: {text}; letter-spacing: 1.5px; background: transparent; border: none;")
            self.control_gesture_sub_lbl.setStyleSheet(
                f"font-size: 8px; color: {muted}; letter-spacing: 1px; background: transparent; border: none;")
            for name_lbl in self._control_gesture_name_lbls:
                name_lbl.setStyleSheet(
                    f"font-size: 8px; color: {muted}; letter-spacing: 0.5px; background: transparent; border: none;")
            for mode_id, btn in self._control_gesture_btns.items():
                enabled = self._control_gestures.get(mode_id, CONTROL_GESTURE_DEFAULTS.get(mode_id, False))
                if enabled:
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
                        QPushButton:hover {{ background-color: {hover}; }}
                    """)
