import os
import sys
import subprocess

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFileDialog, QLineEdit, QFrame,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

class _PipelineRunner(QThread):
    output_line = Signal(str)
    finished_ok = Signal()

    def __init__(self, conf_path):
        super().__init__()
        self.conf_path = conf_path

    def run(self):
        pipeline = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                'logic', 'gesture_pipeline.py')
        proc = subprocess.Popen(
            [sys.executable, pipeline, self.conf_path],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        for line in proc.stdout:
            self.output_line.emit(line.rstrip())
        proc.wait()
        self.finished_ok.emit()

class CustomGesture(QWidget):
    def __init__(self):
        super().__init__()
        self.is_dark   = False
        self._runner   = None
        self.conf_path = ''
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        self.title = QLabel("Custom Gesture Trainer")
        self.title.setStyleSheet("font-size:22px;font-weight:bold;")
        root.addWidget(self.title)

        divider = QFrame()
        divider.setFixedHeight(2)
        divider.setStyleSheet("background:#6B35C7;border:none;")
        root.addWidget(divider)

        self.info = QLabel(
            "Train your own gesture model using a .conf file.\n"
            "The pipeline collects samples, preprocesses, trains, and reviews flagged samples.\n"
            "Put the output .pt and .pkl files in the logic/ folder to use them in the app."
        )
        self.info.setWordWrap(True)
        self.info.setStyleSheet(
            "font-size:12px;padding:10px;border-radius:8px;"
            "background:rgba(107,53,199,0.12);color:#7C5CFC;")
        root.addWidget(self.info)

        conf_row = QHBoxLayout()
        self.conf_lbl = QLabel("Config (.conf):")
        self.conf_lbl.setStyleSheet("font-size:12px;font-weight:600;")
        conf_row.addWidget(self.conf_lbl)

        self.conf_edit = QLineEdit()
        self.conf_edit.setPlaceholderText("No file selected…")
        self.conf_edit.setReadOnly(True)
        self.conf_edit.setFixedHeight(30)
        self.conf_edit.setStyleSheet(
            "border:1px solid #ccc;border-radius:6px;padding:4px 8px;font-size:12px;")
        conf_row.addWidget(self.conf_edit, stretch=1)

        self.browse_btn = QPushButton("Browse…")
        self.browse_btn.setFixedHeight(30)
        self.browse_btn.setCursor(Qt.PointingHandCursor)
        self.browse_btn.setStyleSheet(
            "QPushButton{background:#F3E8FF;color:#7C3AED;border:1px solid #DDD6FE;"
            "border-radius:6px;padding:4px 12px;font-size:12px;font-weight:600;}"
            "QPushButton:hover{background:#DDD6FE;}")
        self.browse_btn.clicked.connect(self._browse)
        conf_row.addWidget(self.browse_btn)
        root.addLayout(conf_row)

        btn_row = QHBoxLayout()
        self.run_btn = QPushButton("▶  Run Pipeline")
        self.run_btn.setFixedHeight(38)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.setEnabled(False)
        self._style_run_btn(False)
        self.run_btn.clicked.connect(self._run_pipeline)
        btn_row.addWidget(self.run_btn)

        self.clear_btn = QPushButton("Clear Log")
        self.clear_btn.setFixedHeight(38)
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setStyleSheet(
            "QPushButton{background:#F1F5F9;color:#64748B;border:1px solid #E2E8F0;"
            "border-radius:8px;padding:6px 18px;font-size:13px;font-weight:bold;}"
            "QPushButton:hover{background:#E2E8F0;}")
        self.clear_btn.clicked.connect(lambda: self.log.clear())
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        log_lbl = QLabel("Pipeline Output")
        log_lbl.setStyleSheet("font-size:11px;font-weight:600;color:#9CA3AF;letter-spacing:0.5px;")
        root.addWidget(log_lbl)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Menlo", 11))
        self.log.setStyleSheet(
            "background:#1E1E2E;color:#CDD6F4;border:1px solid #313244;"
            "border-radius:8px;padding:8px;")
        root.addWidget(self.log, stretch=1)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("font-size:11px;color:#9CA3AF;")
        root.addWidget(self.status_lbl)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select .conf file", "", "Config (*.conf)")
        if path:
            self.conf_path = path
            self.conf_edit.setText(path)
            self.run_btn.setEnabled(True)
            self._style_run_btn(True)
            self.status_lbl.setText(f"Ready: {os.path.basename(path)}")

    def _run_pipeline(self):
        if not self.conf_path or self._runner and self._runner.isRunning():
            return
        self.log.clear()
        self.run_btn.setEnabled(False)
        self._runner = _PipelineRunner(self.conf_path)
        self._runner.output_line.connect(self._append)
        self._runner.finished_ok.connect(self._on_done)
        self._runner.start()
        self.status_lbl.setText("Pipeline running…")

    def _append(self, line):
        self.log.append(line)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def _on_done(self):
        self.run_btn.setEnabled(True)
        self._style_run_btn(True)
        self.status_lbl.setText("Pipeline finished.")

    def _style_run_btn(self, enabled):
        if enabled:
            self.run_btn.setStyleSheet(
                "QPushButton{background:#7C5CFC;color:white;border:none;"
                "border-radius:8px;padding:8px 22px;font-size:13px;font-weight:bold;}"
                "QPushButton:hover{background:#6D50E0;}"
                "QPushButton:disabled{background:#4B5563;color:#9CA3AF;}")
        else:
            self.run_btn.setStyleSheet(
                "QPushButton{background:#4B5563;color:#9CA3AF;border:none;"
                "border-radius:8px;padding:8px 22px;font-size:13px;font-weight:bold;}")

    def apply_theme(self, dark: bool):
        self.is_dark = dark
        if dark:
            self.title.setStyleSheet("font-size:22px;font-weight:bold;color:#FFFFFF;")
            self.info.setStyleSheet(
                "font-size:12px;padding:10px;border-radius:8px;"
                "background:rgba(124,92,252,0.15);color:#9D80FF;")
            self.conf_lbl.setStyleSheet("font-size:12px;font-weight:600;color:#CDD6F4;")
            self.conf_edit.setStyleSheet(
                "background:#212631;color:#CDD6F4;border:1px solid #4E576A;"
                "border-radius:6px;padding:4px 8px;font-size:12px;")
        else:
            self.title.setStyleSheet("font-size:22px;font-weight:bold;color:#1A1A2E;")
            self.info.setStyleSheet(
                "font-size:12px;padding:10px;border-radius:8px;"
                "background:rgba(107,53,199,0.12);color:#7C5CFC;")
            self.conf_lbl.setStyleSheet("font-size:12px;font-weight:600;color:#374151;")
            self.conf_edit.setStyleSheet(
                "border:1px solid #D1D5DB;border-radius:6px;"
                "padding:4px 8px;font-size:12px;color:#111827;")

