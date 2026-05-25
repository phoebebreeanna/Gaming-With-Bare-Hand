import contextlib
import io
import os
import time

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QSizePolicy, QStackedWidget, QScrollArea,
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QPixmap, QImage

_LOGIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logic")

CONF_MAP = {
    "Mouse":  os.path.join(_LOGIC_DIR, "conf", "mouse_control.conf"),
    "Subway": os.path.join(_LOGIC_DIR, "conf", "subway_surfers.conf"),
    "Racing": os.path.join(_LOGIC_DIR, "conf", "racing.conf"),
}

class _SignalIO(io.RawIOBase):
    def __init__(self, emit_fn):
        super().__init__()
        self._emit = emit_fn
        self._buf  = ""

    def writable(self):
        return True

    def write(self, text):
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="replace")
        self._buf += text
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line.strip():
                self._emit(line)
        return len(text)

    def flush(self):
        if self._buf.strip():
            self._emit(self._buf)
            self._buf = ""

class _Worker(QThread):
    log_line     = Signal(str)
    finished_ok  = Signal(object)
    finished_err = Signal(str)

    def __init__(self, fn, *args):
        super().__init__()
        self._fn   = fn
        self._args = args

    def run(self):
        sio = _SignalIO(self.log_line.emit)
        wrapper = io.TextIOWrapper(sio, line_buffering=True)
        with contextlib.redirect_stdout(wrapper):
            try:
                result = self._fn(*self._args)
                self.finished_ok.emit(result)
            except Exception as exc:
                self.finished_err.emit(str(exc))

class PipelineUI(QWidget):
    on_menu_toggle    = Signal()
    training_complete = Signal()

    _PAGE_IDLE    = 0
    _PAGE_COLLECT = 1
    _PAGE_LOG     = 2
    _PAGE_REVIEW  = 3

    def __init__(self, is_dark=False):
        super().__init__()
        self.is_dark          = is_dark
        self.current_mode     = "Mouse"
        self._mirror_aug      = False
        self._cfg             = None
        self._worker          = None
        self._training_result = None
        self._epoch           = 0
        self._total_epochs    = 0
        self._raw_ready       = False
        self._processed_ready = False
        self._trained         = False

        self._collect = {
            'worker': None, 'cfg': None, 'counts': {},
            'current_label': None, 'collecting': False,
            'last_saved_pos': None, 'csv_file': None, 'csv_writer': None,
            'confirm_delete': False, 'confirm_timer': 0.0,
        }
        self._review = {
            'current_idx': 0, 'flagged_idx': [], 'flagged_meta': [],
            'df': None, 'feature_cols': [], 'to_remove': [],
        }
        self._review_pixmap = None

        self.init_ui()
        self._load_conf()
        self.apply_theme(is_dark)

    def init_ui(self):
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
        cl.setContentsMargins(24, 12, 24, 12)
        cl.setSpacing(8)

        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        self.page_title = QLabel("GESTURE PIPELINE")
        title_row.addWidget(self.page_title)
        title_row.addStretch()
        self.mode_tabs = {}
        for mode in ("Mouse", "Subway", "Racing"):
            btn = QPushButton(mode.upper())
            btn.setFixedHeight(26)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, m=mode: self._switch_mode(m))
            self.mode_tabs[mode] = btn
            title_row.addWidget(btn)
        cl.addLayout(title_row)

        self.top_stack = QStackedWidget()
        cl.addWidget(self.top_stack, stretch=3)
        self._build_idle_page()
        self._build_collect_page()
        self._build_log_page()
        self._build_review_page()

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)
        bottom_row.addWidget(self._build_counts_panel(), stretch=1)
        bottom_row.addWidget(self._build_steps_panel(), stretch=1)
        cl.addLayout(bottom_row, stretch=2)

        self.progress_label = QLabel("TRAINING  ·  0 / 0")
        self.progress_label.hide()
        cl.addWidget(self.progress_label)

        self.progress_bar_bg = QWidget()
        self.progress_bar_bg.setFixedHeight(4)
        self.progress_bar_bg.hide()
        self.progress_bar_fill = QWidget(self.progress_bar_bg)
        self.progress_bar_fill.setGeometry(0, 0, 0, 4)
        cl.addWidget(self.progress_bar_bg)

        root.addWidget(content, stretch=1)

    def _build_idle_page(self):
        page = QWidget()
        pl = QVBoxLayout(page)
        pl.setAlignment(Qt.AlignCenter)
        self._idle_lbl = QLabel("SELECT A STEP BELOW TO BEGIN")
        self._idle_lbl.setAlignment(Qt.AlignCenter)
        pl.addWidget(self._idle_lbl)
        self.top_stack.addWidget(page)

    def _build_collect_page(self):
        page = QWidget()
        ph = QHBoxLayout(page)
        ph.setContentsMargins(0, 0, 0, 0)
        ph.setSpacing(8)

        self._collect_cam_lbl = QLabel("Loading camera…")
        self._collect_cam_lbl.setAlignment(Qt.AlignCenter)
        self._collect_cam_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        ph.addWidget(self._collect_cam_lbl, stretch=1)

        self._collect_ctrl = QWidget()
        self._collect_ctrl.setFixedWidth(210)
        cv = QVBoxLayout(self._collect_ctrl)
        cv.setContentsMargins(10, 10, 10, 10)
        cv.setSpacing(6)

        self._collect_status = QLabel("SELECT A GESTURE")
        self._collect_status.setWordWrap(True)
        cv.addWidget(self._collect_status)

        self._collect_sep1 = QWidget()
        self._collect_sep1.setFixedHeight(1)
        cv.addWidget(self._collect_sep1)

        self._gesture_btns_container = QWidget()
        self._gesture_btns_layout = QVBoxLayout(self._gesture_btns_container)
        self._gesture_btns_layout.setContentsMargins(0, 0, 0, 0)
        self._gesture_btns_layout.setSpacing(4)
        self._gesture_btns = {}

        self._collect_scroll = QScrollArea()
        self._collect_scroll.setWidgetResizable(True)
        self._collect_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._collect_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._collect_scroll.setFrameShape(QScrollArea.NoFrame)
        self._collect_scroll.setWidget(self._gesture_btns_container)
        cv.addWidget(self._collect_scroll, stretch=1)

        self._collect_sep2 = QWidget()
        self._collect_sep2.setFixedHeight(1)
        cv.addWidget(self._collect_sep2)

        self._record_btn = QPushButton("RECORD")
        self._record_btn.setFixedHeight(32)
        self._record_btn.setCursor(Qt.PointingHandCursor)
        self._record_btn.clicked.connect(self._toggle_recording)
        cv.addWidget(self._record_btn)

        self._delete_btn = QPushButton("DELETE GESTURE")
        self._delete_btn.setFixedHeight(28)
        self._delete_btn.setCursor(Qt.PointingHandCursor)
        self._delete_btn.clicked.connect(self._on_delete_gesture)
        cv.addWidget(self._delete_btn)

        self._collect_done_btn = QPushButton("DONE")
        self._collect_done_btn.setFixedHeight(32)
        self._collect_done_btn.setCursor(Qt.PointingHandCursor)
        self._collect_done_btn.clicked.connect(self._finish_collect)
        cv.addWidget(self._collect_done_btn)

        ph.addWidget(self._collect_ctrl)
        self.top_stack.addWidget(page)

    def _build_log_page(self):
        page = QWidget()
        pl = QVBoxLayout(page)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(4)
        self._log_hdr = QLabel("LOG OUTPUT")
        pl.addWidget(self._log_hdr)
        self._log_sep = QWidget()
        self._log_sep.setFixedHeight(1)
        pl.addWidget(self._log_sep)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Courier New", 9))
        pl.addWidget(self.log_area, stretch=1)
        self.top_stack.addWidget(page)

    def _build_review_page(self):
        page = QWidget()
        ph = QHBoxLayout(page)
        ph.setContentsMargins(0, 0, 0, 0)
        ph.setSpacing(8)

        self._review_hand_lbl = QLabel()
        self._review_hand_lbl.setAlignment(Qt.AlignCenter)
        self._review_hand_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        ph.addWidget(self._review_hand_lbl, stretch=1)

        self._review_ctrl = QWidget()
        self._review_ctrl.setFixedWidth(210)
        rv = QVBoxLayout(self._review_ctrl)
        rv.setContentsMargins(10, 10, 10, 10)
        rv.setSpacing(6)

        _review_info = QWidget()
        _review_info_layout = QVBoxLayout(_review_info)
        _review_info_layout.setContentsMargins(0, 0, 0, 0)
        _review_info_layout.setSpacing(6)

        self._review_counter = QLabel("0 / 0")
        _review_info_layout.addWidget(self._review_counter)

        self._review_badge = QLabel("")
        _review_info_layout.addWidget(self._review_badge)

        self._review_sep1 = QWidget()
        self._review_sep1.setFixedHeight(1)
        _review_info_layout.addWidget(self._review_sep1)

        self._review_true_hdr = QLabel("TRUE LABEL")
        _review_info_layout.addWidget(self._review_true_hdr)
        self._review_true = QLabel("")
        _review_info_layout.addWidget(self._review_true)

        self._review_pred_hdr = QLabel("PREDICTED")
        _review_info_layout.addWidget(self._review_pred_hdr)
        self._review_pred = QLabel("")
        _review_info_layout.addWidget(self._review_pred)

        self._review_conf_hdr = QLabel("CONFIDENCE")
        _review_info_layout.addWidget(self._review_conf_hdr)
        self._review_conf = QLabel("")
        _review_info_layout.addWidget(self._review_conf)

        _review_info_layout.addStretch()

        self._review_scroll = QScrollArea()
        self._review_scroll.setWidgetResizable(True)
        self._review_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._review_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._review_scroll.setFrameShape(QScrollArea.NoFrame)
        self._review_scroll.setWidget(_review_info)
        rv.addWidget(self._review_scroll, stretch=1)

        self._review_sep2 = QWidget()
        self._review_sep2.setFixedHeight(1)
        rv.addWidget(self._review_sep2)

        self._review_removed = QLabel("0 marked for removal")
        rv.addWidget(self._review_removed)

        btns_row = QHBoxLayout()
        btns_row.setSpacing(6)
        self._keep_btn = QPushButton("KEEP")
        self._keep_btn.setFixedHeight(32)
        self._keep_btn.setCursor(Qt.PointingHandCursor)
        self._keep_btn.clicked.connect(self._review_keep)
        btns_row.addWidget(self._keep_btn)
        self._remove_btn = QPushButton("REMOVE")
        self._remove_btn.setFixedHeight(32)
        self._remove_btn.setCursor(Qt.PointingHandCursor)
        self._remove_btn.clicked.connect(self._review_remove)
        btns_row.addWidget(self._remove_btn)
        rv.addLayout(btns_row)

        self._review_done_btn = QPushButton("DONE")
        self._review_done_btn.setFixedHeight(32)
        self._review_done_btn.setCursor(Qt.PointingHandCursor)
        self._review_done_btn.clicked.connect(self._finish_review)
        rv.addWidget(self._review_done_btn)

        ph.addWidget(self._review_ctrl)
        self.top_stack.addWidget(page)

    def _build_counts_panel(self):
        self.counts_panel = QWidget()
        self.counts_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        cp = QVBoxLayout(self.counts_panel)
        cp.setContentsMargins(14, 10, 14, 10)
        cp.setSpacing(6)

        hdr_row = QHBoxLayout()
        self._counts_hdr = QLabel("GESTURE DATA")
        hdr_row.addWidget(self._counts_hdr)
        hdr_row.addStretch()
        self.refresh_btn = QPushButton("REFRESH")
        self.refresh_btn.setFixedHeight(22)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self._refresh_counts)
        hdr_row.addWidget(self.refresh_btn)
        cp.addLayout(hdr_row)

        self._counts_sep = QWidget()
        self._counts_sep.setFixedHeight(1)
        cp.addWidget(self._counts_sep)
        cp.addSpacing(2)

        self._gesture_container = QWidget()
        self._gc_layout = QVBoxLayout(self._gesture_container)
        self._gc_layout.setContentsMargins(0, 4, 0, 0)
        self._gc_layout.setSpacing(2)
        cp.addWidget(self._gesture_container)
        cp.addStretch()
        return self.counts_panel

    def _build_steps_panel(self):
        self.steps_panel = QWidget()
        self.steps_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sp = QVBoxLayout(self.steps_panel)
        sp.setContentsMargins(14, 10, 14, 10)
        sp.setSpacing(0)

        self._steps_hdr = QLabel("PIPELINE STEPS")
        sp.addWidget(self._steps_hdr)
        self._steps_sep = QWidget()
        self._steps_sep.setFixedHeight(1)
        sp.addWidget(self._steps_sep)
        sp.addSpacing(4)

        self._step_widgets = {}
        for key, label, note in [
            ("collect",    "01  ·  COLLECT DATA",    "Collect gesture samples with your camera"),
            ("preprocess", "02  ·  PREPROCESS",      "Requires: collected data"),
            ("train",      "03  ·  TRAIN MODEL",     "Requires: preprocessed data"),
            ("review",     "04  ·  REVIEW SAMPLES",  "Requires: completed training"),
        ]:
            row = QWidget()
            row.setFixedHeight(48)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(12, 0, 12, 0)
            rl.setSpacing(10)

            text_col = QVBoxLayout()
            text_col.setSpacing(2)
            name_lbl = QLabel(label)
            note_lbl = QLabel(note)
            text_col.addWidget(name_lbl)
            text_col.addWidget(note_lbl)
            rl.addLayout(text_col, stretch=1)

            status_lbl = QLabel("LOCKED")
            status_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            rl.addWidget(status_lbl)

            row.setProperty("pipeline_key", key)
            row.setCursor(Qt.PointingHandCursor)
            row.mousePressEvent = lambda e, k=key: self._on_step_click(k)

            self._step_widgets[key] = {
                "row": row, "name": name_lbl,
                "note": note_lbl, "status": status_lbl,
            }
            sp.addWidget(row)

            sep = QWidget()
            sep.setFixedHeight(1)
            self._step_widgets[key]["sep"] = sep
            sp.addWidget(sep)

            if key == 'preprocess':
                self._mirror_row = QWidget()
                self._mirror_row.setFixedHeight(44)
                mr = QHBoxLayout(self._mirror_row)
                mr.setContentsMargins(12, 0, 12, 0)
                mr.setSpacing(10)
                mc = QVBoxLayout()
                mc.setSpacing(2)
                self._mirror_name_lbl = QLabel("MIRROR AUG  ·  Left Hand Support")
                self._mirror_desc_lbl = QLabel("Disable if gestures include left / right direction")
                mc.addWidget(self._mirror_name_lbl)
                mc.addWidget(self._mirror_desc_lbl)
                mr.addLayout(mc, stretch=1)
                self._mirror_toggle = QPushButton("OFF")
                self._mirror_toggle.setFixedSize(44, 22)
                self._mirror_toggle.setCursor(Qt.PointingHandCursor)
                self._mirror_toggle.clicked.connect(self._toggle_mirror)
                mr.addWidget(self._mirror_toggle)
                sp.addWidget(self._mirror_row)
                self._mirror_sep = QWidget()
                self._mirror_sep.setFixedHeight(1)
                sp.addWidget(self._mirror_sep)

        sp.addStretch()
        return self.steps_panel

    def _load_conf(self):
        from logic.gesture_pipeline import load_conf
        path = CONF_MAP[self.current_mode]
        try:
            self._cfg = load_conf(path)
        except Exception as exc:
            self._cfg = None
            self._log(f"Error loading conf: {exc}")
        self._training_result = None
        self._trained = False
        self._refresh_counts()

    def _refresh_counts(self):
        while self._gc_layout.count():
            item = self._gc_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._gesture_rows = []

        if not self._cfg:
            self._raw_ready = False
            self._processed_ready = False
            self._update_step_states()
            return

        from logic.gesture_pipeline import count_existing
        counts = count_existing(self._cfg['raw_csv'], self._cfg['gestures'])
        target = self._cfg['target']
        self._raw_ready = sum(counts.values()) > 0
        self._processed_ready = (
            os.path.exists(self._cfg['processed_csv']) and
            os.path.getsize(self._cfg['processed_csv']) > 0
        )

        for g in self._cfg['gestures']:
            n    = counts.get(g, 0)
            done = n >= target
            frac = min(n / target, 1.0)

            row = QWidget()
            row.setFixedHeight(32)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(10, 4, 10, 4)
            rl.setSpacing(8)

            name_lbl = QLabel(g)
            name_lbl.setMinimumWidth(70)
            name_lbl.setMaximumWidth(120)
            rl.addWidget(name_lbl)

            bar_bg = QWidget()
            bar_bg.setFixedHeight(6)
            bar_bg.setMinimumWidth(20)
            bar_fill = QWidget(bar_bg)
            bar_fill.setGeometry(0, 0, 0, 6)
            rl.addWidget(bar_bg, stretch=1)

            count_lbl = QLabel(f"{n}/{target}")
            count_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            count_lbl.setFixedWidth(46)
            rl.addWidget(count_lbl)

            self._gesture_rows.append({
                "row": row, "name": name_lbl, "bar_bg": bar_bg,
                "bar_fill": bar_fill, "count": count_lbl,
                "done": done, "frac": frac,
            })
            self._gc_layout.addWidget(row)

        if hasattr(self, "_theme_ready"):
            self.apply_theme(self.is_dark)
        self._update_step_states()

    def _update_step_states(self):
        states = {
            "collect":    True,
            "preprocess": self._raw_ready,
            "train":      self._processed_ready,
            "review":     self._trained,
        }
        for key, enabled in states.items():
            w = self._step_widgets[key]
            w["row"].setEnabled(enabled)
            w["row"].setCursor(Qt.PointingHandCursor if enabled else Qt.ForbiddenCursor)
            if enabled:
                if key == "review" and self._trained:
                    w["status"].setText("READY")
                elif key == "collect":
                    w["status"].setText("START" if not self._raw_ready else "ADD MORE")
                elif key == "preprocess":
                    w["status"].setText("RUN" if not self._processed_ready else "RE-RUN")
                elif key == "train":
                    w["status"].setText("RUN" if not self._trained else "RE-RUN")
                else:
                    w["status"].setText("RUN")
            else:
                w["status"].setText("LOCKED")

        if hasattr(self, "_theme_ready"):
            self.apply_theme(self.is_dark)

    def _switch_mode(self, mode):
        if self._collect['worker'] is not None:
            self._finish_collect()
        self.current_mode = mode
        self._log(f"Switched to {mode} mode.")
        self._load_conf()
        self.apply_theme(self.is_dark)

    def _log(self, text: str):
        self.log_area.append(f"> {text}")
        sb = self.log_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _set_busy(self, busy: bool):
        for btn in self.mode_tabs.values():
            btn.setEnabled(not busy)
        self.refresh_btn.setEnabled(not busy)
        if busy:
            for w in self._step_widgets.values():
                w["row"].setEnabled(False)
        else:
            self._update_step_states()

    def _on_step_click(self, key: str):
        if not self._step_widgets[key]["row"].isEnabled():
            return
        {"collect": self._on_collect, "preprocess": self._on_preprocess,
         "train": self._on_train, "review": self._on_review}[key]()

    def _on_collect(self):
        if not self._cfg or self._collect['worker'] is not None:
            return
        from logic.gesture_pipeline import _CameraWorker, _open_csv, count_existing

        cfg = self._cfg
        self._collect['cfg'] = cfg
        self._collect['counts'] = count_existing(cfg['raw_csv'], cfg['gestures'])
        self._collect['current_label'] = None
        self._collect['collecting'] = False
        self._collect['last_saved_pos'] = None
        self._collect['confirm_delete'] = False

        fh, cw = _open_csv(cfg['raw_csv'], cfg['gestures'])
        self._collect['csv_file'] = fh
        self._collect['csv_writer'] = cw

        while self._gesture_btns_layout.count():
            item = self._gesture_btns_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._gesture_btns = {}
        for i, g in enumerate(cfg['gestures']):
            btn = QPushButton(f"{i}  {g}")
            btn.setFixedHeight(28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._select_gesture(idx))
            self._gesture_btns[g] = btn
            self._gesture_btns_layout.addWidget(btn)

        self._update_collect_ui()
        self.top_stack.setCurrentIndex(self._PAGE_COLLECT)

        cam_idx = 0
        try:
            from logic.app_config import get_camera_index
            cam_idx = get_camera_index()
        except Exception:
            pass

        worker = _CameraWorker(cam_idx=cam_idx)
        worker.frame_ready.connect(self._on_collect_frame)
        self._collect['worker'] = worker
        worker.start()

        for w in self._step_widgets.values():
            w["row"].setEnabled(False)

    def _select_gesture(self, idx: int):
        self._collect['collecting'] = False
        self._collect['current_label'] = idx
        self._collect['last_saved_pos'] = None
        self._collect['confirm_delete'] = False
        self._delete_btn.setText("DELETE GESTURE")
        self._update_collect_ui()

    def _toggle_recording(self):
        c = self._collect
        if c['current_label'] is None:
            self._collect_status.setText("SELECT A GESTURE FIRST")
            return
        c['collecting'] = not c['collecting']
        c['last_saved_pos'] = None
        c['confirm_delete'] = False
        self._delete_btn.setText("DELETE GESTURE")
        self._update_collect_ui()

    def _on_delete_gesture(self):
        c = self._collect
        if c['current_label'] is None:
            self._collect_status.setText("SELECT A GESTURE FIRST")
            return
        if not c['confirm_delete']:
            c['confirm_delete'] = True
            c['confirm_timer'] = time.time()
            c['collecting'] = False
            g = self._cfg['gestures'][c['current_label']]
            self._delete_btn.setText("CONFIRM DELETE")
            self._collect_status.setText(f"Tap again to delete '{g}'")
        else:
            from logic.gesture_pipeline import delete_label_from_csv, _open_csv
            g = self._cfg['gestures'][c['current_label']]
            c['collecting'] = False
            c['csv_file'].flush()
            c['csv_file'].close()
            removed = delete_label_from_csv(self._cfg['raw_csv'], g)
            c['counts'][g] = 0
            c['confirm_delete'] = False
            c['csv_file'], c['csv_writer'] = _open_csv(self._cfg['raw_csv'], self._cfg['gestures'])
            self._delete_btn.setText("DELETE GESTURE")
            self._collect_status.setText(f"Deleted {removed} rows for '{g}'")
            self._update_collect_ui()

    def _update_collect_ui(self):
        c = self._collect
        cfg = c['cfg']
        target = cfg['target'] if cfg else 0

        if c['confirm_delete'] and c['current_label'] is not None:
            g   = cfg['gestures'][c['current_label']]
            rem = max(0.0, 3.0 - (time.time() - c['confirm_timer']))
            self._collect_status.setText(f"Confirm delete '{g}' ({rem:.0f}s)")
        elif c['collecting'] and c['current_label'] is not None:
            g = cfg['gestures'][c['current_label']]
            n = c['counts'].get(g, 0)
            self._collect_status.setText(f"● RECORDING  {g}\n[{n} / {target}]")
        elif c['current_label'] is not None:
            g = cfg['gestures'][c['current_label']]
            n = c['counts'].get(g, 0)
            self._collect_status.setText(f"Ready · {g}\n[{n} / {target}]")
        else:
            self._collect_status.setText("SELECT A GESTURE")

        self._record_btn.setText("STOP RECORDING" if c['collecting'] else "RECORD")

        gestures = cfg['gestures'] if cfg else []
        for g, btn in self._gesture_btns.items():
            n = c['counts'].get(g, 0)
            done = n >= target if target else False
            idx = gestures.index(g) if g in gestures else 0
            btn.setText(f"{idx}  {g}  [{n}/{target}]")

        if hasattr(self, '_theme_ready'):
            self.apply_theme(self.is_dark)

    def _on_collect_frame(self, frame_bgr, result):
        import cv2
        from logic.gesture_pipeline import wrist_dist, draw_landmarks_collect

        c = self._collect
        cfg = c['cfg']
        if cfg is None:
            return

        has_hand = bool(result and result.hand_landmarks)
        lms = result.hand_landmarks[0] if has_hand else None

        if c['confirm_delete'] and (time.time() - c['confirm_timer']) > 3.0:
            c['confirm_delete'] = False
            self._delete_btn.setText("DELETE GESTURE")
            self._update_collect_ui()

        if lms and c['collecting'] and c['current_label'] is not None:
            wx, wy = lms[0].x, lms[0].y
            row = []
            for lm in lms:
                row.extend([lm.x - wx, lm.y - wy, lm.z - lms[0].z])
            dist  = wrist_dist(lms, c['last_saved_pos'])
            moved = (dist == float('inf') or dist >= cfg['min_record_dist'])
            if moved:
                c['csv_writer'].writerow(row + [cfg['gestures'][c['current_label']]])
                c['csv_file'].flush()
                g = cfg['gestures'][c['current_label']]
                c['counts'][g] = c['counts'].get(g, 0) + 1
                c['last_saved_pos'] = (lms[0].x, lms[0].y)
                self._update_collect_ui()

        if not lms:
            c['last_saved_pos'] = None

        display = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w = display.shape[:2]
        if lms:
            draw_landmarks_collect(display, lms, w, h)
            if c['collecting'] and c['current_label'] is not None:
                g = cfg['gestures'][c['current_label']]
                n = c['counts'].get(g, 0)
                bar_w = int((min(n, cfg['target']) / max(cfg['target'], 1)) * (w - 20))
                cv2.rectangle(display, (10, h - 26), (w - 10, h - 10), (40, 40, 40), -1)
                cv2.rectangle(display, (10, h - 26), (10 + bar_w, h - 10), (0, 180, 100), -1)

        qimg = QImage(display.data, w, h, 3 * w, QImage.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(qimg)
        size = self._collect_cam_lbl.size()
        if size.width() > 0 and size.height() > 0:
            self._collect_cam_lbl.setPixmap(
                pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _finish_collect(self):
        c = self._collect
        if c['worker'] and c['worker'].isRunning():
            c['worker'].stop()
            c['worker'].wait(2000)
        c['worker'] = None
        c['collecting'] = False
        if c['csv_file'] and not c['csv_file'].closed:
            c['csv_file'].close()
        c['csv_file'] = None
        c['csv_writer'] = None
        self.top_stack.setCurrentIndex(self._PAGE_IDLE)
        self._refresh_counts()

    def _toggle_mirror(self):
        self._mirror_aug = not self._mirror_aug
        self._mirror_toggle.setText("ON" if self._mirror_aug else "OFF")
        if hasattr(self, '_theme_ready'):
            self.apply_theme(self.is_dark)

    def _on_preprocess(self):
        if not self._cfg:
            return
        self.top_stack.setCurrentIndex(self._PAGE_LOG)
        self._set_busy(True)
        state = "ON" if self._mirror_aug else "OFF"
        self._log(f"Starting preprocessing  (mirror aug: {state}) ...")
        from logic.gesture_pipeline import run_preprocess
        self._worker = _Worker(run_preprocess, self._cfg, self._mirror_aug)
        self._worker.log_line.connect(self._log)
        self._worker.finished_ok.connect(lambda _: self._preprocess_done())
        self._worker.finished_err.connect(self._step_error)
        self._worker.start()

    def _preprocess_done(self):
        self._processed_ready = True
        self._step_done("Preprocessing complete.")

    def _on_train(self):
        if not self._cfg:
            return
        self.top_stack.setCurrentIndex(self._PAGE_LOG)
        self._set_busy(True)
        self._training_result = None
        self._trained = False
        self._epoch = 0
        self._total_epochs = self._cfg['epochs']
        self.progress_label.setText(f"TRAINING  ·  0 / {self._total_epochs}")
        self.progress_label.show()
        self.progress_bar_bg.show()
        self._set_progress(0.0)
        self._log(f"Starting training - {self._total_epochs} epochs ...")
        from logic.gesture_pipeline import run_training
        import numpy as np
        np.random.seed(42)
        self._worker = _Worker(run_training, self._cfg)
        self._worker.log_line.connect(self._on_train_log)
        self._worker.finished_ok.connect(self._on_train_done)
        self._worker.finished_err.connect(self._step_error)
        self._worker.start()

    def _on_train_log(self, line: str):
        self._log(line)
        if "Epoch" in line and "val_acc=" in line:
            parts = line.split()
            for i, p in enumerate(parts):
                if p == "Epoch" and i + 1 < len(parts):
                    try:
                        ep = int(parts[i + 1])
                        self._epoch = ep
                        self.progress_label.setText(f"TRAINING  ·  {ep} / {self._total_epochs}")
                        self._set_progress(ep / max(self._total_epochs, 1))
                    except ValueError:
                        pass
                    break

    def _on_train_done(self, result):
        self._training_result = result
        self._trained = True
        self.progress_label.setText(
            f"TRAINING COMPLETE  ·  {self._total_epochs} / {self._total_epochs}")
        self._set_progress(1.0)
        self._step_done("Training complete.")
        self.training_complete.emit()

    def _on_review(self):
        if not self._cfg or not self._training_result:
            self._log("Run training first to generate flagged samples.")
            return
        import pandas as pd

        flagged_idx, _, flagged_meta = self._training_result
        if not flagged_idx:
            self._log("No flagged samples to review.")
            return

        df = pd.read_csv(self._cfg['processed_csv'])
        feature_cols = [c for c in df.columns if c != 'label']

        r = self._review
        r['flagged_idx']  = flagged_idx
        r['flagged_meta'] = flagged_meta
        r['df']           = df
        r['feature_cols'] = feature_cols
        r['current_idx']  = 0
        r['to_remove']    = []

        self._show_review_sample(0)
        self.top_stack.setCurrentIndex(self._PAGE_REVIEW)

    def _show_review_sample(self, i: int):
        from logic.gesture_pipeline import _render_hand_pixmap
        import numpy as np

        r = self._review
        n = len(r['flagged_idx'])

        if i >= n:
            self._finish_review()
            return

        r['current_idx'] = i
        orig_idx = r['flagged_idx'][i]
        meta     = r['flagged_meta'][i]

        row = r['df'].iloc[orig_idx]
        lms = np.array([row[c] for c in r['feature_cols']][:63], dtype=np.float32).reshape(21, 3)

        self._review_counter.setText(f"{i + 1} / {n}")
        self._review_badge.setText(meta['status'])
        self._review_true.setText(meta['true'])
        self._review_pred.setText(meta['pred'])
        self._review_conf.setText(f"{meta['conf']:.1%}")
        self._review_removed.setText(f"{len(r['to_remove'])} marked for removal")

        self._review_pixmap = _render_hand_pixmap(lms)
        self._scale_review_pixmap()

        if hasattr(self, '_theme_ready'):
            self.apply_theme(self.is_dark)

    def _scale_review_pixmap(self):
        if self._review_pixmap is None:
            return
        size = self._review_hand_lbl.size()
        if size.width() > 0 and size.height() > 0:
            self._review_hand_lbl.setPixmap(
                self._review_pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self._review_hand_lbl.setPixmap(self._review_pixmap)

    def _review_keep(self):
        r = self._review
        r['current_idx'] += 1
        self._show_review_sample(r['current_idx'])

    def _review_remove(self):
        r = self._review
        r['to_remove'].append(r['flagged_idx'][r['current_idx']])
        r['current_idx'] += 1
        self._show_review_sample(r['current_idx'])

    def _finish_review(self):
        import shutil
        r = self._review
        if r['to_remove'] and r['df'] is not None:
            csv_path = self._cfg['processed_csv']
            tmp = csv_path + '.tmp'
            r['df'].drop(index=r['to_remove']).reset_index(drop=True).to_csv(tmp, index=False)
            shutil.move(tmp, csv_path)
            self._log(f"Removed {len(r['to_remove'])} samples.")
        else:
            self._log("Review complete - no samples removed.")
        self._review_pixmap = None
        self.top_stack.setCurrentIndex(self._PAGE_IDLE)

    def _step_done(self, msg: str):
        self._set_busy(False)
        self._log(msg)
        self._worker = None

    def _step_error(self, err: str):
        self._set_busy(False)
        self._log(f"ERROR: {err}")
        self._worker = None

    def _set_progress(self, frac: float):
        w = self.progress_bar_bg.width()
        if w > 0:
            self.progress_bar_fill.setGeometry(0, 0, int(frac * w), 4)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.progress_bar_bg.isVisible() and self._total_epochs > 0:
            self._set_progress(self._epoch / self._total_epochs)
        for info in getattr(self, "_gesture_rows", []):
            w = info["bar_bg"].width()
            if w > 0:
                info["bar_fill"].setGeometry(0, 0, int(info["frac"] * w), 6)
        self._scale_review_pixmap()

    def apply_theme(self, is_dark: bool):
        self.is_dark      = is_dark
        self._theme_ready = True

        if is_dark:
            bg   = "#0a0a0a"; panel = "#111111"; border = "#262626"
            text = "#e8e8e8"; dim   = "#9a9a9a"; muted  = "#6b6b6b"
            pri_bg = "#e8e8e8"; pri_txt = "#111111"; hover = "#161616"
            bar_fill_col = "#e8e8e8"; bar_bg_col = "#262626"
            log_bg = "#050508"; log_txt = "#9a9a9a"
            success = "#00cc66"; locked_col = "#3a3a3a"; step_hover = "#1a1a1a"
            warn = "#cc4444"; cam_bg = "#000000"
        else:
            bg   = "#F4F4F4"; panel = "#FFFFFF"; border = "#D8CEC7"
            text = "#111111"; dim   = "#6F655F"; muted  = "#B8B0AB"
            pri_bg = "#111111"; pri_txt = "#FFFFFF"; hover = "#EDE5DF"
            bar_fill_col = "#111111"; bar_bg_col = "#E8E0DA"
            log_bg = "#FAFAFA"; log_txt = "#4A4A4A"
            success = "#00A36C"; locked_col = "#D8D0CA"; step_hover = "#F0EBE7"
            warn = "#B44545"; cam_bg = "#000000"

        self.setStyleSheet(f"background-color: {bg};")
        self.header.setStyleSheet(f"background-color: {bg}; border-bottom: 1px solid {border};")
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

        for mode, btn in self.mode_tabs.items():
            active = (mode == self.current_mode)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {pri_bg if active else 'transparent'};
                    color: {pri_txt if active else dim};
                    border: 1px solid {pri_bg if active else border};
                    font-size: 8px; font-weight: 700; letter-spacing: 1.3px; padding: 0 10px;
                }}
                {"" if active else f"QPushButton:hover {{ background-color: {hover}; color: {text}; }}"}
            """)

        self._idle_lbl.setStyleSheet(
            f"color: {muted}; font-size: 11px; font-weight: 700; letter-spacing: 2px; background: transparent; border: none;")

        self._collect_cam_lbl.setStyleSheet(f"background-color: {cam_bg}; border: 1px solid {border};")
        self._collect_ctrl.setStyleSheet(f"background-color: {panel}; border: 1px solid {border};")
        self._collect_scroll.setStyleSheet(f"background-color: {panel}; border: none;")
        self._collect_scroll.viewport().setStyleSheet(f"background-color: {panel}; border: none;")
        self._collect_sep1.setStyleSheet(f"background-color: {border};")
        self._collect_sep2.setStyleSheet(f"background-color: {border};")

        collecting = self._collect.get('collecting', False)
        self._collect_status.setStyleSheet(
            f"color: {warn if collecting else text}; font-size: 8px; font-weight: 700; "
            f"letter-spacing: 1px; background: transparent; border: none;")

        c   = self._collect
        cfg = c.get('cfg')
        gestures = cfg['gestures'] if cfg else []
        target   = cfg['target'] if cfg else 0
        cur_lbl  = c.get('current_label')
        counts   = c.get('counts', {})

        for g, btn in self._gesture_btns.items():
            n       = counts.get(g, 0)
            done    = n >= target if target else False
            is_cur  = (cur_lbl is not None and cur_lbl < len(gestures) and gestures[cur_lbl] == g)
            if is_cur:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {pri_bg}; color: {pri_txt};
                        border: 1px solid {pri_bg};
                        font-size: 8px; font-weight: 700; letter-spacing: 1px;
                        text-align: left; padding: 2px 8px;
                    }}
                """)
            elif done:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent; color: {success};
                        border: 1px solid {border};
                        font-size: 8px; font-weight: 700; letter-spacing: 1px;
                        text-align: left; padding: 2px 8px;
                    }}
                    QPushButton:hover {{ background-color: {hover}; }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent; color: {dim};
                        border: 1px solid {border};
                        font-size: 8px; letter-spacing: 1px;
                        text-align: left; padding: 2px 8px;
                    }}
                    QPushButton:hover {{ background-color: {hover}; color: {text}; }}
                """)

        if collecting:
            self._record_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {warn}; color: #ffffff;
                    border: 1px solid {warn};
                    font-size: 8px; font-weight: 700; letter-spacing: 1.2px;
                }}
            """)
        else:
            self._record_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {pri_bg}; color: {pri_txt};
                    border: 1px solid {pri_bg};
                    font-size: 8px; font-weight: 700; letter-spacing: 1.2px;
                }}
                QPushButton:hover {{ background-color: {"#2A2A2A" if not is_dark else hover}; }}
            """)

        for btn in (self._delete_btn, self._collect_done_btn):
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; color: {dim};
                    border: 1px solid {border};
                    font-size: 8px; font-weight: 700; letter-spacing: 1.2px;
                }}
                QPushButton:hover {{ background-color: {hover}; color: {text}; }}
            """)

        self._log_hdr.setStyleSheet(
            f"color: {muted}; font-size: 8px; font-weight: 700; letter-spacing: 1.4px; background: transparent; border: none;")
        self._log_sep.setStyleSheet(f"background-color: {border};")
        self.log_area.setStyleSheet(f"""
            QTextEdit {{
                background-color: {log_bg}; color: {log_txt};
                border: 1px solid {border}; border-radius: 2px;
                font-family: 'Courier New', monospace; font-size: 9px;
            }}
        """)

        self._review_hand_lbl.setStyleSheet(f"background-color: {cam_bg}; border: 1px solid {border};")
        self._review_ctrl.setStyleSheet(f"background-color: {panel}; border: 1px solid {border};")
        self._review_scroll.setStyleSheet(f"background-color: {panel}; border: none;")
        self._review_scroll.viewport().setStyleSheet(f"background-color: {panel}; border: none;")
        self._review_sep1.setStyleSheet(f"background-color: {border};")
        self._review_sep2.setStyleSheet(f"background-color: {border};")

        self._review_counter.setStyleSheet(
            f"color: {text}; font-size: 14px; font-weight: 800; background: transparent; border: none;")

        r    = self._review
        ri   = r.get('current_idx', 0)
        meta = r['flagged_meta'][ri] if r['flagged_meta'] and ri < len(r['flagged_meta']) else None

        is_wrong    = meta and meta['status'] == 'WRONG'
        badge_color = "#cc88ff" if is_wrong else "#88aaff"
        self._review_badge.setStyleSheet(
            f"color: {badge_color}; font-size: 9px; font-weight: 700; background: transparent; border: none;")

        for lbl in (self._review_true_hdr, self._review_pred_hdr, self._review_conf_hdr):
            lbl.setStyleSheet(
                f"color: {muted}; font-size: 7px; font-weight: 700; letter-spacing: 1.3px; background: transparent; border: none;")

        self._review_true.setStyleSheet(
            f"color: {success}; font-size: 12px; font-weight: 700; background: transparent; border: none;")

        pred_color = warn if is_wrong else "#ccaa00"
        self._review_pred.setStyleSheet(
            f"color: {pred_color}; font-size: 12px; font-weight: 700; background: transparent; border: none;")

        conf_val   = meta['conf'] if meta else 0.0
        conf_color = success if conf_val >= 0.8 else ("#ccaa00" if conf_val >= 0.6 else warn)
        self._review_conf.setStyleSheet(
            f"color: {conf_color}; font-size: 12px; font-weight: 700; background: transparent; border: none;")

        self._review_removed.setStyleSheet(
            f"color: {dim}; font-size: 8px; background: transparent; border: none;")

        self._keep_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {pri_bg}; color: {pri_txt};
                border: 1px solid {pri_bg};
                font-size: 8px; font-weight: 700; letter-spacing: 1.2px;
            }}
            QPushButton:hover {{ background-color: {"#2A2A2A" if not is_dark else hover}; }}
        """)
        self._remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {warn};
                border: 1px solid {warn};
                font-size: 8px; font-weight: 700; letter-spacing: 1.2px;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
        """)
        self._review_done_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {dim};
                border: 1px solid {border};
                font-size: 8px; font-weight: 700; letter-spacing: 1.2px;
            }}
            QPushButton:hover {{ background-color: {hover}; color: {text}; }}
        """)

        self.counts_panel.setStyleSheet(f"background-color: {panel}; border: 1px solid {border};")
        self._counts_hdr.setStyleSheet(
            f"color: {muted}; font-size: 8px; font-weight: 700; letter-spacing: 1.4px; background: transparent; border: none;")
        self._counts_sep.setStyleSheet(f"background-color: {border};")
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {dim};
                border: 1px solid {border};
                font-size: 7px; font-weight: 700; letter-spacing: 1.2px; padding: 0 6px;
            }}
            QPushButton:hover {{ background-color: {hover}; color: {text}; }}
        """)

        for info in getattr(self, "_gesture_rows", []):
            done = info["done"]
            info["name"].setStyleSheet(
                f"color: {success if done else dim}; font-size: 9px; font-weight: {'700' if done else '400'}; background: transparent; border: none;")
            info["count"].setStyleSheet(
                f"color: {success if done else muted}; font-size: 8px; letter-spacing: 1px; background: transparent; border: none;")
            info["bar_bg"].setStyleSheet(
                f"background-color: {bar_bg_col}; border-radius: 2px; border: none;")
            info["bar_fill"].setStyleSheet(
                f"background-color: {success if done else bar_fill_col}; border-radius: 2px; border: none;")
            w = info["bar_bg"].width()
            if w > 0:
                info["bar_fill"].setGeometry(0, 0, int(info["frac"] * w), 6)

        self._mirror_row.setStyleSheet(f"background-color: {panel}; border: none;")
        self._mirror_sep.setStyleSheet(f"background-color: {border};")
        self._mirror_name_lbl.setStyleSheet(
            f"color: {text}; font-size: 9px; font-weight: 700; letter-spacing: 1px; background: transparent; border: none;")
        self._mirror_desc_lbl.setStyleSheet(
            f"color: {muted}; font-size: 8px; letter-spacing: 1px; background: transparent; border: none;")
        if self._mirror_aug:
            self._mirror_toggle.setStyleSheet(f"""
                QPushButton {{
                    background-color: {pri_bg}; color: {pri_txt};
                    font-size: 7px; font-weight: 700; letter-spacing: 1px;
                    border: 1px solid {pri_bg}; border-radius: 2px;
                }}
            """)
        else:
            self._mirror_toggle.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; color: {dim};
                    font-size: 7px; font-weight: 700; letter-spacing: 1px;
                    border: 1px solid {border}; border-radius: 2px;
                }}
                QPushButton:hover {{ background-color: {hover}; color: {text}; }}
            """)

        self.steps_panel.setStyleSheet(f"background-color: {panel}; border: 1px solid {border};")
        self._steps_hdr.setStyleSheet(
            f"color: {muted}; font-size: 8px; font-weight: 700; letter-spacing: 1.4px; background: transparent; border: none;")
        self._steps_sep.setStyleSheet(f"background-color: {border};")

        states = {
            "collect": True, "preprocess": self._raw_ready,
            "train": self._processed_ready, "review": self._trained,
        }
        for key, sw in self._step_widgets.items():
            enabled = states.get(key, False)
            sw["sep"].setStyleSheet(f"background-color: {border};")
            if enabled:
                sw["row"].setStyleSheet(f"""
                    QWidget {{ background-color: {panel}; }}
                    QWidget:hover {{ background-color: {step_hover}; }}
                """)
                sw["name"].setStyleSheet(
                    f"color: {text}; font-size: 10px; font-weight: 700; letter-spacing: 1px; background: transparent; border: none;")
                sw["note"].setStyleSheet(
                    f"color: {muted}; font-size: 8px; letter-spacing: 1px; background: transparent; border: none;")
                s_color = success if sw["status"].text() in ("READY", "DONE") else text
                sw["status"].setStyleSheet(
                    f"color: {s_color}; font-size: 8px; font-weight: 700; letter-spacing: 1.2px; background: transparent; border: none;")
            else:
                sw["row"].setStyleSheet(f"QWidget {{ background-color: {panel}; }}")
                for lbl in (sw["name"], sw["note"], sw["status"]):
                    lbl.setStyleSheet(
                        f"color: {locked_col}; font-size: {'10' if lbl is sw['name'] else '8'}px; "
                        f"font-weight: {'700' if lbl is not sw['note'] else '400'}; "
                        f"letter-spacing: 1px; background: transparent; border: none;")

        self.progress_label.setStyleSheet(
            f"color: {muted}; font-size: 8px; font-weight: 700; letter-spacing: 1.4px; background: transparent; border: none;")
        self.progress_bar_bg.setStyleSheet(f"background-color: {border}; border-radius: 2px; border: none;")
        self.progress_bar_fill.setStyleSheet(f"background-color: {bar_fill_col}; border-radius: 2px; border: none;")
