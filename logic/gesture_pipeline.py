import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision as mp_vision
import csv
import os
import platform
import shutil
import time
import sys
import math
import glob
import argparse
from collections import defaultdict, Counter

_IS_WINDOWS = platform.system() == 'Windows'

def _open_camera(index):
    if _IS_WINDOWS:
        return cv2.VideoCapture(index, cv2.CAP_DSHOW)
    return cv2.VideoCapture(index)

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler
import joblib
import configparser

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
)
from PySide6.QtCore import Qt, QThread, Signal, QEventLoop
from PySide6.QtGui import QImage, QPixmap

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_PATH    = os.path.join(PIPELINE_DIR, 'data', 'hand_landmarker.task')

HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),
    (0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),
    (5,9),(9,13),(13,17),
]

FINGERTIPS = {4, 8, 12, 16, 20}
FINGER_COLORS = [
    (255, 100, 100),
    (100, 255, 100),
    (100, 200, 255),
    (255, 150,  50),
    (200, 100, 255),
]
FINGER_LMS = [
    [1,2,3,4], [5,6,7,8], [9,10,11,12], [13,14,15,16], [17,18,19,20],
]

_DARK_BG   = "#0f0f16"
_DARK_CARD = "#1a1a26"
_ACCENT    = "#00cc66"
_WARN      = "#ff4444"
_TEXT      = "#cccccc"
_DIM       = "#666666"

def load_conf(path):
    cfg = configparser.ConfigParser()
    cfg.read(path, encoding='utf-8')
    base         = os.path.dirname(os.path.abspath(path))
    data_dir     = cfg['files'].get('data_dir', 'data')
    full_data_dir = os.path.normpath(os.path.join(base, data_dir))

    if getattr(sys, 'frozen', False):
        parts = full_data_dir.replace('\\', '/').split('/')
        if 'data' in parts and 'custom' in parts:
            marker = max(i for i, p in enumerate(parts) if p == 'data')
            tail   = parts[marker + 2:]
            writable_root = os.path.join(os.path.expanduser('~'), '.handmouse', 'data', 'custom')
            full_data_dir = os.path.join(writable_root, *tail) if tail else writable_root

    os.makedirs(full_data_dir, exist_ok=True)

    def dp(name):
        return os.path.join(full_data_dir, cfg['files'][name])

    return {
        'project':            cfg['project']['name'],
        'gestures':           [g.strip() for g in cfg['gestures']['names'].split(',')],
        'target':             cfg.getint('collection',    'target_per_gesture'),
        'min_record_dist':    cfg.getfloat('collection',  'min_record_dist'),
        'diversity_every':    cfg.getint('collection',    'diversity_every'),
        'aug_per_sample':     cfg.getint('preprocessing', 'aug_per_sample'),
        'noise_std':          cfg.getfloat('preprocessing','noise_std'),
        'rot_max_deg':        cfg.getfloat('preprocessing','rot_max_deg'),
        'scale_jitter':       cfg.getfloat('preprocessing','scale_jitter'),
        'epochs':             cfg.getint('training',      'epochs'),
        'batch_size':         cfg.getint('training',      'batch_size'),
        'lr':                 cfg.getfloat('training',    'learning_rate'),
        'focal_gamma':        cfg.getfloat('training',    'focal_gamma'),
        'low_conf_threshold': cfg.getfloat('training',    'low_conf_threshold'),
        'weak_acc_threshold': cfg.getfloat('training',    'weak_accuracy_threshold'),
        'raw_csv':            dp('raw_csv'),
        'processed_csv':      dp('processed_csv'),
        'model_best':         dp('model_best'),
        'model_out':          dp('model_out'),
        'label_encoder':      dp('label_encoder'),
    }

def banner(text):
    w = 60
    print('\n' + '='*w)
    print(f"  {text}")
    print('='*w)

def diversity_hint(count, diversity_every):
    hints = [
        "vary your DISTANCE - move closer or further",
        "vary your HEIGHT - raise or lower your hand",
        "vary your ANGLE - tilt your wrist slightly",
        "vary your POSITION - move left/right in frame",
        "vary your LIGHTING - try different brightness",
    ]
    return hints[(count // diversity_every) % len(hints)]

def count_existing(csv_path, gestures):
    counts = {g: 0 for g in gestures}
    if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['label'] in counts:
                    counts[row['label']] += 1
    return counts

def delete_label_from_csv(csv_path, label):
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        return 0
    removed = 0
    tmp = csv_path + '.tmp'
    with open(csv_path, 'r', newline='', encoding='utf-8') as fin, \
            open(tmp, 'w', newline='', encoding='utf-8') as fout:
        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=reader.fieldnames)
        writer.writeheader()
        for row in reader:
            if row['label'] == label:
                removed += 1
            else:
                writer.writerow(row)
    shutil.move(tmp, csv_path)
    return removed

def wrist_dist(lms, last_pos):
    if last_pos is None:
        return float('inf')
    dx = lms[0].x - last_pos[0]
    dy = lms[0].y - last_pos[1]
    return math.sqrt(dx*dx + dy*dy)

def draw_landmarks_collect(frame, lms, w, h):
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in lms]
    for a, b in HAND_CONNECTIONS:
        cv2.line(frame, pts[a], pts[b], (0, 200, 255), 1, cv2.LINE_AA)
    for idx, (px, py) in enumerate(pts):
        r = 5 if idx in FINGERTIPS else 3
        cv2.circle(frame, (px, py), r, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(frame, (px, py), r, (0, 150, 255),   1, cv2.LINE_AA)

def _open_csv(csv_path, gestures):
    header_coords = [f'{ax}{i}' for i in range(21) for ax in ['x','y','z']]
    header = header_coords + ['label']
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
    exists = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0
    fh = open(csv_path, 'a', newline='', encoding='utf-8')
    cw = csv.writer(fh)
    if not exists:
        cw.writerow(header)
    return fh, cw

def _qlabel(text, color=_TEXT, size=11, bold=False):
    lbl = QLabel(text)
    weight = "bold" if bold else "normal"
    lbl.setStyleSheet(
        f"color: {color}; font-size: {size}px; font-weight: {weight}; background: transparent;")
    return lbl

class _CameraWorker(QThread):
    frame_ready = Signal(object, object)  

    def __init__(self, task_path=None, cam_idx=0):
        super().__init__()
        self._task_path = task_path or TASK_PATH
        self._cam_idx   = cam_idx
        self._running   = False

    def stop(self):
        self._running = False

    def run(self):
        base_opts = mp_tasks.BaseOptions(model_asset_path=self._task_path)
        options   = mp_vision.HandLandmarkerOptions(base_options=base_opts, num_hands=1)
        detector  = mp_vision.HandLandmarker.create_from_options(options)

        cap = _open_camera(self._cam_idx)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self._running = True
        while self._running and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.flip(frame, 1)
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            try:
                result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
            except Exception:
                result = None
            self.frame_ready.emit(frame, result)

        cap.release()
        detector.close()

class CollectionWindow(QWidget):

    closed_sig = Signal()

    def __init__(self, cfg, target_gestures=None, cam_idx=0):
        super().__init__()
        self.cfg             = cfg
        self.gestures        = cfg['gestures']
        if target_gestures:
            self.gestures    = [g for g in self.gestures if g in target_gestures]
        self.target          = cfg['target']
        self.min_record_dist = cfg['min_record_dist']
        self.diversity_every = cfg['diversity_every']
        self.csv_path        = cfg['raw_csv']

        self.counts          = count_existing(self.csv_path, self.gestures)
        self.current_label   = None
        self.collecting      = False
        self.last_saved_pos  = None
        self.confirm_delete  = False
        self.confirm_timer   = 0.0
        self.CONFIRM_WINDOW  = 3.0

        self._csv_file, self._csv_writer = _open_csv(self.csv_path, self.gestures)

        self._worker = _CameraWorker(cam_idx=cam_idx)
        self._worker.frame_ready.connect(self._on_frame)

        self._build_ui()
        self._worker.start()
        self.setFocus()

    def _hsep(self):
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #333344;")
        return sep

    def _build_ui(self):
        self.setWindowTitle(f"Collect Gestures · {self.cfg['project']}")
        self.setStyleSheet(f"background-color: {_DARK_BG};")
        self.setMinimumSize(940, 520)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(10)

        self.cam_lbl = QLabel("Loading camera…")
        self.cam_lbl.setFixedSize(640, 480)
        self.cam_lbl.setAlignment(Qt.AlignCenter)
        self.cam_lbl.setStyleSheet("background: #050508; border: 1px solid #333;")
        outer.addWidget(self.cam_lbl)

        right = QWidget()
        right.setStyleSheet(f"background: {_DARK_CARD}; border-radius: 6px;")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(12, 12, 12, 12)
        rv.setSpacing(5)

        rv.addWidget(_qlabel(self.cfg['project'], size=14, bold=True))
        rv.addWidget(_qlabel(f"Target: {self.target} per gesture", _DIM, size=10))
        rv.addWidget(self._hsep())
        rv.addWidget(_qlabel("GESTURES", _DIM, size=9, bold=True))

        self._g_lbls = {}
        for i, g in enumerate(self.gestures):
            lbl = _qlabel(f"  {i}: {g}")
            self._g_lbls[g] = lbl
            rv.addWidget(lbl)

        rv.addStretch()
        rv.addWidget(self._hsep())

        self._status_lbl = _qlabel("Select a gesture (0-9)", _DIM)
        rv.addWidget(self._status_lbl)

        rv.addWidget(self._hsep())
        for line in ["0-9  select", "SPC  record", "D    delete (tap twice)", "G/ESC  finish"]:
            rv.addWidget(_qlabel(line, _DIM, size=9))

        outer.addWidget(right)
        self._refresh_labels()

    def _refresh_labels(self):
        now = time.time()
        for i, g in enumerate(self.gestures):
            done   = self.counts[g] >= self.target
            is_cur = (self.current_label == i)
            prefix = "▶ " if is_cur else "  "
            status = "✓" if done else f"{self.counts[g]}/{self.target}"
            color  = _ACCENT if done else ("#ffcc00" if is_cur else _TEXT)
            weight = "bold" if is_cur else "normal"
            self._g_lbls[g].setText(f"{prefix}{i}: {g}  [{status}]")
            self._g_lbls[g].setStyleSheet(
                f"color: {color}; font-size: 11px; font-weight: {weight}; background: transparent;")

        if self.confirm_delete and self.current_label is not None:
            g   = self.gestures[self.current_label]
            rem = max(0.0, self.CONFIRM_WINDOW - (now - self.confirm_timer))
            self._status_lbl.setText(f"⚠ Press D again to DELETE '{g}' ({rem:.1f}s)")
            self._status_lbl.setStyleSheet(f"color: {_WARN}; font-size: 11px; background: transparent;")
        elif self.collecting and self.current_label is not None:
            g = self.gestures[self.current_label]
            self._status_lbl.setText(f"● RECORDING: {g}  [{self.counts[g]}/{self.target}]")
            self._status_lbl.setStyleSheet(f"color: {_WARN}; font-size: 11px; background: transparent;")
        elif self.current_label is not None:
            g = self.gestures[self.current_label]
            self._status_lbl.setText(f"Ready · {g}  (SPACE to record)")
            self._status_lbl.setStyleSheet(f"color: {_ACCENT}; font-size: 11px; background: transparent;")
        else:
            self._status_lbl.setText("Select a gesture (0-9)")
            self._status_lbl.setStyleSheet(f"color: {_DIM}; font-size: 11px; background: transparent;")

    def _on_frame(self, frame_bgr, result):
        now      = time.time()
        has_hand = bool(result and result.hand_landmarks)
        lms      = result.hand_landmarks[0] if has_hand else None

        if self.confirm_delete and (now - self.confirm_timer) > self.CONFIRM_WINDOW:
            self.confirm_delete = False

        if lms:
            wx, wy = lms[0].x, lms[0].y
            row = []
            for lm in lms:
                row.extend([lm.x - wx, lm.y - wy, lm.z - lms[0].z])

            dist  = wrist_dist(lms, self.last_saved_pos)
            moved = (dist == float('inf') or dist >= self.min_record_dist)

            if self.collecting and self.current_label is not None and moved:
                self._csv_writer.writerow(row + [self.gestures[self.current_label]])
                self._csv_file.flush()
                g = self.gestures[self.current_label]
                self.counts[g] += 1
                self.last_saved_pos = (lms[0].x, lms[0].y)
                c = self.counts[g]
                if c % self.diversity_every == 0 and c > 0:
                    print(f"  [{c} samples] Tip: {diversity_hint(c, self.diversity_every)}")
        else:
            self.last_saved_pos = None

        display = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w    = display.shape[:2]
        if lms:
            draw_landmarks_collect(display, lms, w, h)
            if self.collecting and self.current_label is not None:
                g     = self.gestures[self.current_label]
                bar_w = int((min(self.counts[g], self.target) / self.target) * (w - 20))
                cv2.rectangle(display, (10, h-26), (w-10, h-10), (40, 40, 40), -1)
                cv2.rectangle(display, (10, h-26), (10+bar_w, h-10), (0, 180, 100), -1)

        qimg = QImage(display.data, w, h, 3*w, QImage.Format_RGB888).copy()
        self.cam_lbl.setPixmap(QPixmap.fromImage(qimg))
        self._refresh_labels()

    def keyPressEvent(self, event):
        key = event.key()

        if Qt.Key_0 <= key <= Qt.Key_9:
            idx = key - Qt.Key_0
            if idx < len(self.gestures):
                self.collecting     = False
                self.current_label  = idx
                self.last_saved_pos = None
                self.confirm_delete = False
                g = self.gestures[idx]
                print(f"Selected: {g}  ({self.counts[g]} samples)")

        elif key == Qt.Key_Space:
            if self.current_label is None:
                print("Select a gesture first")
            else:
                self.collecting     = not self.collecting
                self.last_saved_pos = None
                self.confirm_delete = False
                state = "started" if self.collecting else "stopped"
                g     = self.gestures[self.current_label]
                print(f"Recording {state} - {g}  ({self.counts[g]} samples)")

        elif key == Qt.Key_D:
            if self.current_label is None:
                print("Select a gesture first")
            elif not self.confirm_delete:
                self.confirm_delete = True
                self.confirm_timer  = time.time()
                self.collecting     = False
                g = self.gestures[self.current_label]
                print(f"Press D again within {self.CONFIRM_WINDOW:.0f}s to DELETE '{g}'")
            else:
                g = self.gestures[self.current_label]
                self.collecting = False
                self._csv_file.flush()
                self._csv_file.close()
                removed = delete_label_from_csv(self.csv_path, g)
                self.counts[g]      = 0
                self.confirm_delete = False
                self.last_saved_pos = None
                print(f"Deleted {removed} rows for '{g}'")
                self._csv_file, self._csv_writer = _open_csv(self.csv_path, self.gestures)

        elif key in (Qt.Key_G, Qt.Key_Escape):
            self._finish()
        else:
            super().keyPressEvent(event)

    def _finish(self):
        self.collecting = False
        if self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(2000)
        if not self._csv_file.closed:
            self._csv_file.close()
        self.close()

    def closeEvent(self, event):
        if self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(2000)
        if not self._csv_file.closed:
            self._csv_file.close()
        self.closed_sig.emit()
        event.accept()

def normalize(raw_row):
    coords = np.array(raw_row, dtype=np.float32).reshape(21, 3)
    scale  = max(math.sqrt(coords[9, 0]**2 + coords[9, 1]**2), 1e-6)
    return (coords / scale).flatten().tolist()

def rotate_2d(coords_63, angle_deg):
    coords        = np.array(coords_63, dtype=np.float32).reshape(21, 3)
    angle         = np.deg2rad(angle_deg)
    cos_a, sin_a  = np.cos(angle), np.sin(angle)
    rotated       = coords.copy()
    rotated[:, 0] = coords[:, 0] * cos_a - coords[:, 1] * sin_a
    rotated[:, 1] = coords[:, 0] * sin_a + coords[:, 1] * cos_a
    return rotated.flatten().tolist()

def augment(coords_63, aug_per_sample, noise_std, rot_max_deg, scale_jitter, mirror=False):
    variants = []
    for _ in range(aug_per_sample):
        c = np.array(coords_63, dtype=np.float32)
        c = np.array(rotate_2d(c.tolist(), np.random.uniform(-rot_max_deg, rot_max_deg)), dtype=np.float32)
        c *= 1.0 + np.random.uniform(-scale_jitter, scale_jitter)
        c += np.random.normal(0, noise_std, c.shape).astype(np.float32)
        variants.append(c.tolist())
    if mirror:
        mirrored = np.array(coords_63, dtype=np.float32)
        for i in range(0, 63, 3):
            mirrored[i] = -mirrored[i]
        for _ in range(aug_per_sample):
            c = mirrored.copy()
            c = np.array(rotate_2d(c.tolist(), np.random.uniform(-rot_max_deg, rot_max_deg)), dtype=np.float32)
            c *= 1.0 + np.random.uniform(-scale_jitter, scale_jitter)
            c += np.random.normal(0, noise_std, c.shape).astype(np.float32)
            variants.append(c.tolist())
    return variants

def compute_delta(current, previous):
    if previous is None:
        return [0.0] * len(current)
    return [c - p for c, p in zip(current, previous)]

def run_preprocess(cfg, mirror=False):
    banner("STEP 2 - PREPROCESSING")
    if mirror:
        print("Mirror augmentation: ON  (left-hand support enabled)")
    else:
        print("Mirror augmentation: OFF")
    raw_path = cfg['raw_csv']
    out_path = cfg['processed_csv']

    if not os.path.exists(raw_path):
        print(f"ERROR: {raw_path} not found.")
        return False

    df           = pd.read_csv(raw_path, dtype={'label': str})
    feature_cols = [c for c in df.columns if c != 'label']
    raw_counts   = df['label'].value_counts().to_dict()
    print(f"Loaded {len(df)} raw samples")
    print("Raw counts:")
    for g in cfg['gestures']:
        print(f"  {g}: {raw_counts.get(g, 0)}")

    class_rows = defaultdict(list)
    for _, row in df.iterrows():
        norm = normalize(row[feature_cols].tolist())
        class_rows[row['label']].append(norm)

    HEADER = (
        [f'{ax}{i}' for i in range(21) for ax in ['x','y','z']] +
        [f'd{ax}{i}' for i in range(21) for ax in ['x','y','z']] +
        ['label']
    )

    out_rows = []
    for label, samples in class_rows.items():
        prev = None
        for norm in samples:
            delta = compute_delta(norm, prev)
            prev  = norm
            out_rows.append(norm + delta + [label])
            aug_prev = norm
            for aug in augment(norm, cfg['aug_per_sample'], cfg['noise_std'],
                               cfg['rot_max_deg'], cfg['scale_jitter'], mirror=mirror):
                out_rows.append(aug + compute_delta(aug, aug_prev) + [label])
                aug_prev = aug

    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerows(out_rows)

    print(f"\nWrote {len(out_rows)} rows to {out_path}")
    final_counts = defaultdict(int)
    for row in out_rows:
        final_counts[row[-1]] += 1
    print("Final counts (raw + augmented):")
    for g in cfg['gestures']:
        raw   = raw_counts.get(g, 0)
        total = final_counts.get(g, 0)
        print(f"  {g}: {raw} raw → {total} total")
    return True

class FocalLoss(nn.Module):
    def __init__(self, gamma=2.0, weight=None):
        super().__init__()
        self.gamma  = gamma
        self.weight = weight

    def forward(self, logits, targets):
        ce   = F.cross_entropy(logits, targets, weight=self.weight, reduction='none')
        pt   = torch.exp(-ce)
        return (((1 - pt) ** self.gamma) * ce).mean()

class GestureNet(nn.Module):
    def __init__(self, input_size, num_classes):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 256), nn.BatchNorm1d(256), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(256, 128),        nn.BatchNorm1d(128), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(128, 64),         nn.BatchNorm1d(64),  nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, num_classes),
        )

    def forward(self, x):
        return self.net(x)

def run_training(cfg):
    banner("STEP 3 - TRAINING")
    data_path = cfg['processed_csv']

    if not os.path.exists(data_path):
        print(f"ERROR: {data_path} not found. Run preprocess first.")
        return None, None, None

    _model_best_path    = cfg['model_best']
    _model_out_path     = cfg['model_out']
    _label_encoder_path = cfg['label_encoder']
    print(f"Output directory: {os.path.dirname(_model_out_path)}")

    df    = pd.read_csv(data_path, dtype={'label': str})
    df    = df[df['label'].isin(cfg['gestures'])].reset_index(drop=True)
    X     = df.drop('label', axis=1).values.astype(np.float32)
    y     = df['label'].values

    print("Samples per gesture:")
    for label, count in sorted(Counter(y).items()):
        print(f"  {label}: {count}")

    le    = LabelEncoder()
    y_enc = le.fit_transform(y)
    joblib.dump(le, _label_encoder_path)
    print(f"\nClasses: {list(le.classes_)}")
    print(f"Features: {X.shape[1]}")

    orig_idx = np.arange(len(X))
    X_train, X_test, y_train, y_test, _, _ = train_test_split(
        X, y_enc, orig_idx, test_size=0.2, random_state=42, stratify=y_enc)

    X_train_t = torch.tensor(X_train)
    y_train_t = torch.tensor(y_train, dtype=torch.long)
    X_test_t  = torch.tensor(X_test)
    y_test_t  = torch.tensor(y_test,  dtype=torch.long)

    class_counts = np.bincount(y_train)
    weights      = 1.0 / class_counts[y_train]
    sampler      = WeightedRandomSampler(weights, len(weights))
    loader       = DataLoader(TensorDataset(X_train_t, y_train_t),
                              batch_size=cfg['batch_size'], sampler=sampler)

    model     = GestureNet(X_train.shape[1], len(le.classes_))
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg['lr'])
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=cfg['epochs'], eta_min=1e-5)
    cls_w     = torch.tensor(1.0 / class_counts, dtype=torch.float32)
    cls_w     = cls_w / cls_w.sum() * len(class_counts)
    criterion = FocalLoss(gamma=cfg['focal_gamma'], weight=cls_w)

    best_acc   = 0.0
    best_epoch = 0
    print(f"\nTraining for {cfg['epochs']} epochs...\n")
    for epoch in range(cfg['epochs']):
        model.train()
        total_loss = 0.0
        for xb, yb in loader:
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        scheduler.step()
        if (epoch + 1) % 10 == 0:
            model.eval()
            with torch.no_grad():
                preds = model(X_test_t).argmax(1)
                acc   = (preds == y_test_t).float().mean().item()
            lr_now = scheduler.get_last_lr()[0]
            print(f"Epoch {epoch+1:3d}  loss={total_loss/len(loader):.4f}  val_acc={acc:.3f}  lr={lr_now:.6f}")
            if acc > best_acc:
                best_acc   = acc
                best_epoch = epoch + 1
                torch.save(model.state_dict(), _model_best_path)

    print(f"\nBest val_acc={best_acc:.3f} at epoch {best_epoch}")
    model.load_state_dict(torch.load(_model_best_path, map_location='cpu', weights_only=False))
    model.eval()

    with torch.no_grad():
        preds_test = model(X_test_t).argmax(1).numpy()
    y_test_labels = le.inverse_transform(y_test)
    y_pred_labels = le.inverse_transform(preds_test)
    print("\nPer-class report:")
    print(classification_report(y_test_labels, y_pred_labels, digits=3))

    weak_gestures = []
    print("Per-class accuracy:")
    for cls in le.classes_:
        mask = y_test_labels == cls
        if mask.sum() == 0: continue
        cls_acc = (y_pred_labels[mask] == cls).mean()
        status  = "OK" if cls_acc >= cfg['weak_acc_threshold'] else "WEAK"
        print(f"  {cls:<22} {cls_acc:.3f}  [{status}]")
        if cls_acc < cfg['weak_acc_threshold']:
            weak_gestures.append(cls)

    X_all_t = torch.tensor(X)
    with torch.no_grad():
        probs_all = torch.softmax(model(X_all_t), dim=1).numpy()
        preds_all = probs_all.argmax(axis=1)

    y_all_labels = le.inverse_transform(y_enc)
    y_all_pred   = le.inverse_transform(preds_all)
    conf_all     = probs_all.max(axis=1)

    wrong_mask    = y_all_pred != y_all_labels
    lowconf_mask  = (conf_all < cfg['low_conf_threshold']) & ~wrong_mask
    flagged_mask  = wrong_mask | lowconf_mask
    flagged_idx   = list(np.where(flagged_mask)[0])

    print(f"\nMisclassified:  {wrong_mask.sum()}")
    print(f"Low confidence: {lowconf_mask.sum()}")
    print(f"Total flagged:  {flagged_mask.sum()} / {len(X)}")

    flagged_meta = [
        {
            'true':   y_all_labels[i],
            'pred':   y_all_pred[i],
            'conf':   float(conf_all[i]),
            'status': 'WRONG' if wrong_mask[i] else 'LOW CONF',
        }
        for i in flagged_idx
    ]

    torch.save(model.state_dict(), _model_out_path)
    print(f"\nSaved: {_model_out_path}  +  {_label_encoder_path}")
    return flagged_idx, weak_gestures, flagged_meta

def _render_hand_pixmap(lms_array, W=400, H=400):
    img = np.zeros((H, W, 3), dtype=np.uint8)
    img[:] = (15, 15, 22)

    cx, cy, scale = W // 2, H // 2 + 40, 145
    pts = []
    for i in range(21):
        px = int(cx + lms_array[i, 0] * scale)
        py = int(cy + lms_array[i, 1] * scale)
        pts.append((px, py))

    finger_map = {}
    for fi, group in enumerate(FINGER_LMS):
        for lm_idx in group:
            finger_map[lm_idx] = fi

    for a, b in HAND_CONNECTIONS:
        fi    = finger_map.get(a, finger_map.get(b, -1))
        color = FINGER_COLORS[fi] if fi >= 0 else (180, 180, 180)
        cv2.line(img, pts[a], pts[b], color, 2, cv2.LINE_AA)

    for idx, (px, py) in enumerate(pts):
        if idx == 0:
            cv2.circle(img, (px, py), 7, (255, 255, 0), -1, cv2.LINE_AA)
            cv2.circle(img, (px, py), 7, (0, 0, 0),     1, cv2.LINE_AA)
        elif idx in FINGERTIPS:
            fi = finger_map.get(idx, 0)
            cv2.circle(img, (px, py), 6, FINGER_COLORS[fi], -1, cv2.LINE_AA)
            cv2.circle(img, (px, py), 6, (0, 0, 0),          1, cv2.LINE_AA)
        else:
            cv2.circle(img, (px, py), 4, (220, 220, 220), -1, cv2.LINE_AA)
            cv2.circle(img, (px, py), 4, (80,  80,  80),  1, cv2.LINE_AA)

    rgb  = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    qimg = QImage(rgb.tobytes(), W, H, 3*W, QImage.Format_RGB888)
    return QPixmap.fromImage(qimg)

class VisualizerWindow(QWidget):

    closed_sig = Signal()

    def __init__(self, cfg, flagged_indices, flagged_meta, df, feature_cols):
        super().__init__()
        self.flagged_indices = flagged_indices
        self.flagged_meta    = flagged_meta
        self.df              = df
        self.feature_cols    = feature_cols
        self.to_remove       = []
        self.current_idx     = 0
        self.n               = len(flagged_indices)
        self._build_ui()
        self._show_sample(0)
        self.setFocus()

    def _hsep(self):
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #333344;")
        return sep

    def _build_ui(self):
        self.setWindowTitle("Review Flagged Samples")
        self.setStyleSheet(f"background-color: {_DARK_BG};")
        self.setMinimumSize(760, 460)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(10)

        self.hand_lbl = QLabel()
        self.hand_lbl.setFixedSize(400, 400)
        self.hand_lbl.setAlignment(Qt.AlignCenter)
        self.hand_lbl.setStyleSheet("background: #0a0a10; border: 1px solid #333;")
        outer.addWidget(self.hand_lbl)

        right = QWidget()
        right.setStyleSheet(f"background: {_DARK_CARD}; border-radius: 6px;")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(14, 14, 14, 14)
        rv.setSpacing(8)

        self.counter_lbl = _qlabel("", size=16, bold=True)
        rv.addWidget(self.counter_lbl)

        self.badge_lbl = _qlabel("")
        rv.addWidget(self.badge_lbl)
        rv.addWidget(self._hsep())

        rv.addWidget(_qlabel("TRUE LABEL", _DIM, size=9, bold=True))
        self.true_lbl = _qlabel("", _ACCENT, size=15, bold=True)
        rv.addWidget(self.true_lbl)

        rv.addWidget(_qlabel("PREDICTED", _DIM, size=9, bold=True))
        self.pred_lbl = _qlabel("", size=15, bold=True)
        rv.addWidget(self.pred_lbl)

        rv.addWidget(_qlabel("CONFIDENCE", _DIM, size=9, bold=True))
        self.conf_lbl = _qlabel("", size=15, bold=True)
        rv.addWidget(self.conf_lbl)

        rv.addStretch()
        rv.addWidget(self._hsep())

        self.removed_lbl = _qlabel("0 marked for removal", _DIM, size=10)
        rv.addWidget(self.removed_lbl)
        rv.addWidget(self._hsep())

        for line in ["SPACE  keep", "X      remove", "ESC    stop review"]:
            rv.addWidget(_qlabel(line, _DIM, size=9))

        outer.addWidget(right)

    def _show_sample(self, i):
        if i >= self.n:
            self.close()
            return

        orig_idx = self.flagged_indices[i]
        meta     = self.flagged_meta[i]
        is_wrong = meta['status'] == 'WRONG'

        row = self.df.iloc[orig_idx]
        lms = np.array([row[c] for c in self.feature_cols][:63], dtype=np.float32).reshape(21, 3)

        self.counter_lbl.setText(f"{i+1} / {self.n}")

        badge_style = (
            "color: #cc88ff; background: #2a1040; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;"
            if is_wrong else
            "color: #88aaff; background: #101840; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;"
        )
        self.badge_lbl.setText(meta['status'])
        self.badge_lbl.setStyleSheet(badge_style)

        self.true_lbl.setText(meta['true'])

        pred_color = _WARN if is_wrong else "#ccaa00"
        self.pred_lbl.setText(meta['pred'])
        self.pred_lbl.setStyleSheet(
            f"color: {pred_color}; font-size: 15px; font-weight: bold; background: transparent;")

        conf       = meta['conf']
        conf_color = _ACCENT if conf >= 0.8 else "#ccaa00" if conf >= 0.6 else _WARN
        self.conf_lbl.setText(f"{conf:.1%}")
        self.conf_lbl.setStyleSheet(
            f"color: {conf_color}; font-size: 15px; font-weight: bold; background: transparent;")

        self.removed_lbl.setText(f"{len(self.to_remove)} marked for removal")
        self.hand_lbl.setPixmap(_render_hand_pixmap(lms))

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Space:
            self.current_idx += 1
            self._show_sample(self.current_idx)
        elif key == Qt.Key_X:
            self.to_remove.append(self.flagged_indices[self.current_idx])
            self.current_idx += 1
            self._show_sample(self.current_idx)
        elif key == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.closed_sig.emit()
        event.accept()

    def get_removed(self):
        return self.to_remove

def run_collection(cfg, target_gestures=None):
    banner(f"STEP 1 - DATA COLLECTION  [{cfg['project']}]")
    gestures = cfg['gestures']
    if target_gestures:
        gestures = [g for g in gestures if g in target_gestures]
    print(f"Gestures to collect: {gestures}")
    print(f"Target per gesture : {cfg['target']} samples")
    print("\nControls (in collection window):")
    print("  0-9  select gesture by index")
    print("  SPACE  start / stop recording")
    print("  D      delete gesture samples (double-tap to confirm)")
    print("  G / ESC  finish and continue\n")
    for i, g in enumerate(gestures):
        print(f"  {i} = {g}")
    print()

    loop = QEventLoop()
    win  = CollectionWindow(cfg, target_gestures)
    win.closed_sig.connect(loop.quit)
    win.show()
    loop.exec()

    counts = win.counts
    banner("Collection complete")
    for g in cfg['gestures']:
        if not target_gestures or g in target_gestures:
            n      = counts.get(g, 0)
            status = "OK" if n >= cfg['target'] else f"NEED {cfg['target'] - n} more"
            print(f"  {g}: {n}  [{status}]")
    return counts

def run_visualizer(cfg, flagged_indices, flagged_meta):
    if not flagged_indices:
        banner("No flagged samples - skipping review")
        return False

    csv_path     = cfg['processed_csv']
    df           = pd.read_csv(csv_path, dtype={'label': str})
    feature_cols = [c for c in df.columns if c != 'label']

    banner(f"STEP 4 - REVIEW  ({len(flagged_indices)} flagged samples)")

    loop = QEventLoop()
    win  = VisualizerWindow(cfg, flagged_indices, flagged_meta, df, feature_cols)
    win.closed_sig.connect(loop.quit)
    win.show()
    loop.exec()

    to_remove = win.get_removed()
    if not to_remove:
        print("No samples removed.")
        return False

    tmp = csv_path + '.tmp'
    df.drop(index=to_remove).reset_index(drop=True).to_csv(tmp, index=False)
    shutil.move(tmp, csv_path)
    banner(f"Removed {len(to_remove)} samples - {len(df) - len(to_remove)} remaining")
    return True

def main():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    app.setStyle("Fusion")

    parser = argparse.ArgumentParser(description='Gesture Pipeline')
    parser.add_argument('conf', nargs='?', default=None)
    args = parser.parse_args()

    if args.conf:
        conf_path = args.conf
    else:
        conf_files = glob.glob('*.conf')
        if not conf_files:
            print("No .conf file found in current directory.")
            conf_path = input("Enter path to .conf file: ").strip()
        elif len(conf_files) == 1:
            conf_path = conf_files[0]
        else:
            print("Multiple .conf files found:")
            for i, f in enumerate(conf_files):
                print(f"  {i} = {f}")
            conf_path = conf_files[int(input("Select (number): ").strip())]

    if not os.path.exists(conf_path):
        print(f"ERROR: {conf_path} not found.")
        sys.exit(1)

    cfg = load_conf(conf_path)

    run_collection(cfg)

    np.random.seed(42)
    ok = run_preprocess(cfg)
    if not ok:
        print("Preprocessing failed. Exiting.")
        sys.exit(1)

    result = run_training(cfg)
    if result is None or result[0] is None:
        print("Training failed. Exiting.")
        sys.exit(1)
    flagged_indices, weak_gestures, flagged_meta = result

    if run_visualizer(cfg, flagged_indices, flagged_meta):
        banner("Retraining after review")
        np.random.seed(42)
        result = run_training(cfg)
        if result and result[0] is not None:
            flagged_indices, weak_gestures, flagged_meta = result

    if weak_gestures:
        banner("Weak gestures detected")
        print(f"Below {cfg['weak_acc_threshold']*100:.0f}% accuracy:")
        for g in weak_gestures:
            print(f"  {g}")
        print()
        if input("Re-collect for weak gestures? (y/n): ").strip().lower() == 'y':
            run_collection(cfg, target_gestures=set(weak_gestures))
            np.random.seed(42)
            run_preprocess(cfg)
            run_training(cfg)

    banner("PIPELINE COMPLETE")
    if os.path.exists(cfg['model_out']):
        print(f"Model:         {cfg['model_out']}")
        print(f"Label encoder: {cfg['label_encoder']}")
    print(f"Project:       {cfg['project']}")

if __name__ == '__main__':
    main()
