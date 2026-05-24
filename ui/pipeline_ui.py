import contextlib
import io
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont

_LOGIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logic")

CONF_MAP = {
    "Mouse":  os.path.join(_LOGIC_DIR, "mouse_control.conf"),
    "Subway": os.path.join(_LOGIC_DIR, "subway_surfers.conf"),
    "Racing": os.path.join(_LOGIC_DIR, "racing.conf"),
}

class _SignalIO(io.RawIOBase):
    def __init__(self, emit_fn):
        super().__init__()
        self._emit = emit_fn
        self._buf  = ""

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
    on_menu_toggle = Signal()

    def __init__(self, is_dark=False):
        super().__init__()
        self.is_dark          = is_dark
        self.current_mode     = "Mouse"
        self._cfg             = None
        self._worker          = None
        self._training_result = None
        self._epoch           = 0
        self._total_epochs    = 0

        self._raw_ready       = False   
        self._processed_ready = False   
        self._trained         = False   
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
        cl.setContentsMargins(24, 16, 24, 16)
        cl.setSpacing(10)

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

        body = QHBoxLayout()
        body.setSpacing(12)

        self.counts_panel = QWidget()
        self.counts_panel.setMinimumWidth(220)
        self.counts_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        cp = QVBoxLayout(self.counts_panel)
        cp.setContentsMargins(14, 12, 14, 12)
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

        body.addWidget(self.counts_panel, stretch=1)

        self.steps_panel = QWidget()
        self.steps_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        sp = QVBoxLayout(self.steps_panel)
        sp.setContentsMargins(14, 12, 14, 12)
        sp.setSpacing(0)

        self._steps_hdr = QLabel("PIPELINE STEPS")
        sp.addWidget(self._steps_hdr)
        self._steps_sep = QWidget()
        self._steps_sep.setFixedHeight(1)
        sp.addWidget(self._steps_sep)
        sp.addSpacing(6)

        self._step_widgets = {}  
        for key, label, note in [
            ("collect",    "01  ·  COLLECT DATA",    "Collect gesture samples with your camera"),
            ("preprocess", "02  ·  PREPROCESS",      "Requires: collected data"),
            ("train",      "03  ·  TRAIN MODEL",     "Requires: preprocessed data"),
            ("review",     "04  ·  REVIEW SAMPLES",  "Requires: completed training"),
        ]:
            row = QWidget()
            row.setFixedHeight(52)
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

        sp.addStretch()
        body.addWidget(self.steps_panel, stretch=1)
        cl.addLayout(body)

        self.progress_label = QLabel("TRAINING  ·  0 / 0")
        self.progress_label.hide()
        cl.addWidget(self.progress_label)

        self.progress_bar_bg = QWidget()
        self.progress_bar_bg.setFixedHeight(5)
        self.progress_bar_bg.hide()
        self.progress_bar_fill = QWidget(self.progress_bar_bg)
        self.progress_bar_fill.setGeometry(0, 0, 0, 5)
        cl.addWidget(self.progress_bar_bg)

        self._log_hdr = QLabel("LOG OUTPUT")
        cl.addWidget(self._log_hdr)
        self._log_sep = QWidget()
        self._log_sep.setFixedHeight(1)
        cl.addWidget(self._log_sep)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumHeight(120)
        self.log_area.setFont(QFont("Courier New", 9))
        cl.addWidget(self.log_area, stretch=1)

        root.addWidget(content, stretch=1)

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
        total_collected = sum(counts.values())
        self._raw_ready = total_collected > 0
        self._processed_ready = (
            os.path.exists(self._cfg['processed_csv']) and
            os.path.getsize(self._cfg['processed_csv']) > 0
        )

        for g in self._cfg['gestures']:
            n    = counts.get(g, 0)
            done = n >= target
            frac = min(n / target, 1.0)

            row = QWidget()
            row.setFixedHeight(34)
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
        actions = {
            "collect":    self._on_collect,
            "preprocess": self._on_preprocess,
            "train":      self._on_train,
            "review":     self._on_review,
        }
        actions[key]()

    def _on_collect(self):
        if not self._cfg:
            return
        from logic.gesture_pipeline import run_collection
        self._log(f"Opening collection window for [{self._cfg['project']}] ...")
        try:
            run_collection(self._cfg)
        except Exception as exc:
            self._log(f"Collection error: {exc}")
        self._refresh_counts()
        self._log("Collection window closed.")

    def _on_preprocess(self):
        if not self._cfg:
            return
        self._set_busy(True)
        self._log("Starting preprocessing ...")
        from logic.gesture_pipeline import run_preprocess
        self._worker = _Worker(run_preprocess, self._cfg)
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
        self._set_busy(True)
        self._training_result = None
        self._trained  = False
        self._epoch    = 0
        self._total_epochs = self._cfg['epochs']
        self.progress_label.setText(f"TRAINING  ·  0 / {self._total_epochs}")
        self.progress_label.show()
        self.progress_bar_bg.show()
        self._set_progress(0.0)
        self._log(f"Starting training — {self._total_epochs} epochs ...")
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
                        self.progress_label.setText(
                            f"TRAINING  ·  {ep} / {self._total_epochs}")
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

    def _on_review(self):
        if not self._cfg or not self._training_result:
            self._log("Run training first to generate flagged samples.")
            return
        from logic.gesture_pipeline import run_visualizer
        flagged_idx, _, flagged_meta = self._training_result
        self._log(f"Opening review window ({len(flagged_idx)} flagged samples) ...")
        try:
            run_visualizer(self._cfg, flagged_idx, flagged_meta)
        except Exception as exc:
            self._log(f"Review error: {exc}")
        self._log("Review complete.")

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
            self.progress_bar_fill.setGeometry(0, 0, int(frac * w), 5)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.progress_bar_bg.isVisible() and self._total_epochs > 0:
            self._set_progress(self._epoch / self._total_epochs)

        for info in getattr(self, "_gesture_rows", []):
            w = info["bar_bg"].width()
            if w > 0:
                info["bar_fill"].setGeometry(0, 0, int(info["frac"] * w), 6)

    def apply_theme(self, is_dark: bool):
        self.is_dark     = is_dark
        self._theme_ready = True

        if is_dark:
            bg   = "#0a0a0a"; panel = "#111111"; border = "#262626"
            text = "#e8e8e8"; dim   = "#9a9a9a"; muted  = "#6b6b6b"
            pri_bg = "#e8e8e8"; pri_txt = "#111111"; hover = "#161616"
            bar_fill_col = "#e8e8e8"; bar_bg_col = "#262626"
            log_bg = "#050508"; log_txt = "#9a9a9a"
            success = "#00cc66"; locked_col = "#3a3a3a"
            step_hover = "#1a1a1a"
        else:
            bg   = "#F4F4F4"; panel = "#FFFFFF"; border = "#D8CEC7"
            text = "#111111"; dim   = "#6F655F"; muted  = "#B8B0AB"
            pri_bg = "#111111"; pri_txt = "#FFFFFF"; hover = "#EDE5DF"
            bar_fill_col = "#111111"; bar_bg_col = "#E8E0DA"
            log_bg = "#FAFAFA"; log_txt = "#4A4A4A"
            success = "#00A36C"; locked_col = "#D8D0CA"
            step_hover = "#F0EBE7"

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
            if mode == self.current_mode:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {pri_bg}; color: {pri_txt};
                        border: 1px solid {pri_bg};
                        font-size: 8px; font-weight: 700; letter-spacing: 1.3px; padding: 0 10px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent; color: {dim};
                        border: 1px solid {border};
                        font-size: 8px; font-weight: 700; letter-spacing: 1.3px; padding: 0 10px;
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
            name_color = success if done else dim
            count_color = success if done else muted
            info["name"].setStyleSheet(
                f"color: {name_color}; font-size: 9px; font-weight: {'700' if done else '400'}; background: transparent; border: none;")
            info["count"].setStyleSheet(
                f"color: {count_color}; font-size: 8px; letter-spacing: 1px; background: transparent; border: none;")
            info["bar_bg"].setStyleSheet(
                f"background-color: {bar_bg_col}; border-radius: 2px; border: none;")
            fill_color = success if done else bar_fill_col
            info["bar_fill"].setStyleSheet(
                f"background-color: {fill_color}; border-radius: 2px; border: none;")
            w = info["bar_bg"].width()
            if w > 0:
                info["bar_fill"].setGeometry(0, 0, int(info["frac"] * w), 6)

        self.steps_panel.setStyleSheet(f"background-color: {panel}; border: 1px solid {border};")
        self._steps_hdr.setStyleSheet(
            f"color: {muted}; font-size: 8px; font-weight: 700; letter-spacing: 1.4px; background: transparent; border: none;")
        self._steps_sep.setStyleSheet(f"background-color: {border};")

        states = {
            "collect":    True,
            "preprocess": self._raw_ready,
            "train":      self._processed_ready,
            "review":     self._trained,
        }
        for key, w in self._step_widgets.items():
            enabled = states.get(key, False)
            w["sep"].setStyleSheet(f"background-color: {border};")
            if enabled:
                w["row"].setStyleSheet(f"""
                    QWidget {{
                        background-color: {panel};
                    }}
                    QWidget:hover {{
                        background-color: {step_hover};
                    }}
                """)
                w["name"].setStyleSheet(
                    f"color: {text}; font-size: 10px; font-weight: 700; letter-spacing: 1px; background: transparent; border: none;")
                w["note"].setStyleSheet(
                    f"color: {muted}; font-size: 8px; letter-spacing: 1px; background: transparent; border: none;")
                status_txt = w["status"].text()
                s_color = success if status_txt in ("READY", "DONE") else text
                w["status"].setStyleSheet(
                    f"color: {s_color}; font-size: 8px; font-weight: 700; letter-spacing: 1.2px; background: transparent; border: none;")
            else:
                w["row"].setStyleSheet(f"QWidget {{ background-color: {panel}; }}")
                w["name"].setStyleSheet(
                    f"color: {locked_col}; font-size: 10px; font-weight: 700; letter-spacing: 1px; background: transparent; border: none;")
                w["note"].setStyleSheet(
                    f"color: {locked_col}; font-size: 8px; letter-spacing: 1px; background: transparent; border: none;")
                w["status"].setStyleSheet(
                    f"color: {locked_col}; font-size: 8px; font-weight: 700; letter-spacing: 1.2px; background: transparent; border: none;")

        self.progress_label.setStyleSheet(
            f"color: {muted}; font-size: 8px; font-weight: 700; letter-spacing: 1.4px; background: transparent; border: none;")
        self.progress_bar_bg.setStyleSheet(
            f"background-color: {border}; border-radius: 2px; border: none;")
        self.progress_bar_fill.setStyleSheet(
            f"background-color: {bar_fill_col}; border-radius: 2px; border: none;")

        self._log_hdr.setStyleSheet(
            f"color: {muted}; font-size: 8px; font-weight: 700; letter-spacing: 1.4px; background: transparent; border: none;")
        self._log_sep.setStyleSheet(f"background-color: {border};")
        self.log_area.setStyleSheet(f"""
            QTextEdit {{
                background-color: {log_bg};
                color: {log_txt};
                border: 1px solid {border};
                border-radius: 2px;
                font-family: 'Courier New', monospace;
                font-size: 9px;
            }}
        """)

