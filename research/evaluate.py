import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("[WARN] matplotlib not found - skipping plots")

try:
    import seaborn as sns
    HAS_SNS = True
except ImportError:
    HAS_SNS = False

try:
    from sklearn.metrics import (classification_report, confusion_matrix,
                                 ConfusionMatrixDisplay)
    HAS_SKL = True
except ImportError:
    HAS_SKL = False
    print("[WARN] scikit-learn not found - metrics will be computed manually")

try:
    import torch
    import torch.nn as nn
    import joblib
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    print("[WARN] torch / joblib not found - neural evaluation skipped")

try:
    from pillow_heif import register_heif_opener
    from PIL import Image as PILImage
    register_heif_opener()
    HAS_HEIF = True
except ImportError:
    HAS_HEIF = False
    print("[WARN] pillow-heif not found - .HEIC files will be skipped (pip install pillow-heif)")

PINCH_THRESH = 0.28

def _hand_size(lms):
    return np.hypot(lms[0].x - lms[9].x, lms[0].y - lms[9].y)

def _tip_dist(lms, a, b):
    return np.hypot(lms[a].x - lms[b].x, lms[a].y - lms[b].y)

def _pinch_ratio(lms, a, b):
    hs = _hand_size(lms)
    return _tip_dist(lms, a, b) / hs if hs > 0 else 999.0

def _is_extended(lms, tip, pip):
    return (np.hypot(lms[tip].x - lms[0].x, lms[tip].y - lms[0].y) >
            np.hypot(lms[pip].x - lms[0].x, lms[pip].y - lms[0].y))

def rule_gesture(lms):
    if _pinch_ratio(lms, 4, 8) < PINCH_THRESH:
        return 'index_pinch'
    if _pinch_ratio(lms, 4, 12) < PINCH_THRESH:
        return 'tm_pinch'
    idx  = _is_extended(lms, 8,  6)
    mid  = _is_extended(lms, 12, 10)
    ring = _is_extended(lms, 16, 14)
    pky  = _is_extended(lms, 20, 18)
    if idx and mid and ring and not pky:
        return 'scroll_up'
    if not idx and not mid and not ring and not pky:
        return 'scroll_down'
    itd = np.hypot(lms[8].x - lms[0].x, lms[8].y - lms[0].y)
    curled = lambda t: np.hypot(lms[t].x - lms[0].x, lms[t].y - lms[0].y) < itd * 0.85
    if idx and curled(12) and curled(16) and curled(20):
        return 'move'
    return 'idle'

class GestureNet(nn.Module if HAS_TORCH else object):
    def __init__(self, input_size, num_classes):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 256), nn.BatchNorm1d(256), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(256, 128),        nn.BatchNorm1d(128), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(128, 64),         nn.BatchNorm1d(64),  nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, num_classes)
        )
    def forward(self, x):
        return self.net(x)

def normalize_landmarks(lms, prev_row):
    wx, wy, wz = lms[0].x, lms[0].y, lms[0].z
    scale = math.sqrt((lms[9].x - wx)**2 + (lms[9].y - wy)**2 + (lms[9].z - wz)**2)
    scale = max(scale, 1e-6)
    row = []
    for lm in lms:
        row.extend([(lm.x - wx)/scale, (lm.y - wy)/scale, (lm.z - wz)/scale])
    delta    = [c - p for c, p in zip(row, prev_row)] if prev_row is not None else [0.0]*63
    return row + delta, row

def load_neural(nn_model_path, encoder_path):
    if not HAS_TORCH:
        return None, None
    try:
        le = joblib.load(encoder_path)
        model = GestureNet(126, len(le.classes_))
        model.load_state_dict(torch.load(nn_model_path, map_location='cpu'))
        model.eval()
        return model, le
    except Exception as e:
        print(f"[WARN] Could not load neural model: {e}")
        return None, None

def neural_gesture(lms, model, le, conf_thresh, prev_row):
    import torch
    features, new_prev = normalize_landmarks(lms, prev_row)
    x = torch.tensor([features], dtype=torch.float32)
    with torch.no_grad():
        probs     = torch.softmax(model(x), dim=1)[0]
        conf, idx = probs.max(0)
    gesture = le.inverse_transform([idx.item()])[0] if conf.item() >= conf_thresh else 'idle'
    return gesture, conf.item(), new_prev

RULE_EXPECTED = {
    'left_click':          'index_pinch',
    'right_click':         'tm_pinch',
    'scroll_up':           'scroll_up',
    'scroll_down':         'scroll_down',
    'release_left_click':  'move',
    'release_right_click': 'move',
}

NEURAL_EXPECTED = {
    'left_click':          'left_click',
    'right_click':         'right_click',
    'scroll_up':           'scroll_up',
    'scroll_down':         'scroll_down',
    'release_left_click':  'move',
    'release_right_click': 'move',
}

RULE_FORBIDDEN = {
    'release_left_click':  'index_pinch',
    'release_right_click': 'tm_pinch',
}
NEURAL_FORBIDDEN = {
    'release_left_click':  'left_click',
    'release_right_click': 'right_click',
}

RELEASE_LABELS = {'release_left_click', 'release_right_click'}

RULE_GESTURE_TO_DATASET = {
    'index_pinch': 'left_click',
    'tm_pinch':    'right_click',
    'scroll_up':   'scroll_up',
    'scroll_down': 'scroll_down',
    'move':        'release_left_click',
}

NEURAL_GESTURE_TO_DATASET = {
    'left_click':  'left_click',
    'right_click': 'right_click',
    'scroll_up':   'scroll_up',
    'scroll_down': 'scroll_down',
    'move':        'release_left_click',
}

def dataset_pred_label(detected, true_label, gesture_to_dataset, forbidden_map=None):
    if true_label in RELEASE_LABELS and forbidden_map and true_label in forbidden_map:
        if detected != forbidden_map[true_label]:
            return true_label
        return gesture_to_dataset.get(detected, detected)
    return gesture_to_dataset.get(detected, detected)

IMG_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.heic', '.heif'}

KNOWN_LABELS = set(RULE_EXPECTED)


def load_image(img_path):
    if img_path.suffix.lower() in ('.heic', '.heif'):
        if not HAS_HEIF:
            return None
        try:
            pil_img = PILImage.open(str(img_path)).convert('RGB')
            return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        except Exception:
            return None
    return cv2.imread(str(img_path))

def manual_metrics(y_true, y_pred, classes):
    from collections import defaultdict
    tp = defaultdict(int); fp = defaultdict(int); fn = defaultdict(int)
    for t, p in zip(y_true, y_pred):
        if t == p:
            tp[t] += 1
        else:
            fp[p] += 1
            fn[t] += 1
    report = {}
    for c in classes:
        prec = tp[c] / (tp[c] + fp[c]) if (tp[c] + fp[c]) else 0.0
        rec  = tp[c] / (tp[c] + fn[c]) if (tp[c] + fn[c]) else 0.0
        f1   = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        sup  = tp[c] + fn[c]
        report[c] = {'precision': prec, 'recall': rec, 'f1-score': f1, 'support': sup}
    report['accuracy'] = sum(t == p for t, p in zip(y_true, y_pred)) / len(y_true) if y_true else 0.0
    return report

def build_cm(y_true, y_pred, classes):
    idx = {c: i for i, c in enumerate(classes)}
    n = len(classes)
    cm = [[0]*n for _ in range(n)]
    for t, p in zip(y_true, y_pred):
        if t in idx and p in idx:
            cm[idx[t]][idx[p]] += 1
    return cm

def per_label_acc(records, label):
    recs = [r for r in records if r['label'] == label]
    if not recs:
        return 0.0, 0, 0
    correct = sum(r['correct'] for r in recs)
    return correct / len(recs), correct, len(recs)

def plot_evaluation(rule_data, neural_data, labels_found, output_dir):
    if not HAS_MPL:
        return

    n_systems = sum(1 for d in [rule_data, neural_data] if d is not None)
    fig, axes = plt.subplots(n_systems, 3, figsize=(18, 6 * n_systems))
    if n_systems == 1:
        axes = [axes]

    for row_idx, (data, title) in enumerate(
        [(d, t) for d, t in [(rule_data, 'Rule-Based'), (neural_data, 'Neural')]
         if d is not None]
    ):
        y_true    = data['y_true']
        y_pred    = data['y_pred']
        latencies = data['latencies']
        records   = data['records']
        report    = data['report']
        classes   = data.get('cm_dataset_classes', sorted(set(y_true + y_pred)))
        cm_raw    = data.get('cm_dataset', data['cm'])

        ax = axes[row_idx][0]
        cm_arr = np.array(cm_raw)
        if HAS_SNS:
            sns.heatmap(cm_arr, annot=True, fmt='d', cmap='Blues',
                        xticklabels=classes, yticklabels=classes, ax=ax)
        else:
            im = ax.imshow(cm_arr, cmap='Blues')
            for i in range(len(classes)):
                for j in range(len(classes)):
                    ax.text(j, i, cm_arr[i, j], ha='center', va='center', fontsize=9)
            ax.set_xticks(range(len(classes))); ax.set_xticklabels(classes)
            ax.set_yticks(range(len(classes))); ax.set_yticklabels(classes)
        ax.set_title(f'{title} - Confusion Matrix')
        ax.set_xlabel('Predicted'); ax.set_ylabel('True')
        plt.setp(ax.get_xticklabels(), rotation=30, ha='right', fontsize=8)
        plt.setp(ax.get_yticklabels(), rotation=0, fontsize=8)

        ax = axes[row_idx][1]
        lbl_accs = []
        for lbl in labels_found:
            acc, _, _ = per_label_acc(records, lbl)
            lbl_accs.append(acc * 100)
        bar_colors = ['#2ecc71' if a >= 80 else '#e67e22' if a >= 50 else '#e74c3c'
                      for a in lbl_accs]
        bars = ax.bar(labels_found, lbl_accs, color=bar_colors)
        overall = report['accuracy'] * 100
        ax.axhline(overall, color='navy', linestyle='--', linewidth=1.5,
                   label=f'Overall {overall:.1f}%')
        ax.set_ylim(0, 115)
        ax.set_title(f'{title} - Accuracy per Label')
        ax.set_ylabel('Accuracy (%)')
        ax.legend(fontsize=8)
        for bar, val in zip(bars, lbl_accs):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{val:.1f}%', ha='center', va='bottom', fontsize=8)
        plt.setp(ax.get_xticklabels(), rotation=30, ha='right', fontsize=8)

        ax = axes[row_idx][2]
        lat_lbls = [l for l in labels_found if latencies[l]]
        lat_med  = [float(np.median(latencies[l]))    for l in lat_lbls]
        lat_p25  = [float(np.percentile(latencies[l], 25)) for l in lat_lbls]
        lat_p75  = [float(np.percentile(latencies[l], 75)) for l in lat_lbls]
        if lat_lbls:
            err_lo = [max(0.0, m - lo) for m, lo in zip(lat_med, lat_p25)]
            err_hi = [max(0.0, hi - m) for m, hi in zip(lat_med, lat_p75)]
            bars = ax.bar(lat_lbls, lat_med, yerr=[err_lo, err_hi], capsize=4,
                          color='#3498db', alpha=0.85,
                          error_kw={'ecolor': '#555555', 'linewidth': 1})
            for bar, med, hi in zip(bars, lat_med, lat_p75):
                ax.text(bar.get_x() + bar.get_width()/2, hi + 0.3,
                       f'{med:.1f}ms', ha='center', va='bottom', fontsize=8)
            ax.set_ylim(0, max(lat_p75) * 1.25)
        ax.set_title(f'{title} - Latency per Label (median, IQR)')
        ax.set_ylabel('Latency (ms)')
        plt.setp(ax.get_xticklabels(), rotation=30, ha='right', fontsize=8)

    plt.tight_layout()
    p = output_dir / 'evaluation.png'
    plt.savefig(p, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Saved] {p}")

    if rule_data is not None and neural_data is not None:
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        fig.suptitle('Rule-Based vs Neural - Side-by-Side', fontsize=13, fontweight='bold')

        ax = axes[0]
        x = np.arange(len(labels_found))
        w = 0.35
        rule_accs   = [per_label_acc(rule_data['records'],   l)[0]*100 for l in labels_found]
        neural_accs = [per_label_acc(neural_data['records'], l)[0]*100 for l in labels_found]
        ax.bar(x - w/2, rule_accs,   w, label='Rule-Based', color='#3498db', alpha=0.85)
        ax.bar(x + w/2, neural_accs, w, label='Neural',     color='#e74c3c', alpha=0.85)
        ax.set_xticks(x); ax.set_xticklabels(labels_found, rotation=30, ha='right', fontsize=8)
        ax.set_ylim(0, 115); ax.set_ylabel('Accuracy (%)')
        ax.set_title('Accuracy by Label')
        ax.axhline(rule_data['report']['accuracy']*100,   linestyle='--', color='#3498db',
                   linewidth=1, label=f"Rule overall {rule_data['report']['accuracy']*100:.1f}%")
        ax.axhline(neural_data['report']['accuracy']*100, linestyle='--', color='#e74c3c',
                   linewidth=1, label=f"Neural overall {neural_data['report']['accuracy']*100:.1f}%")
        ax.legend(fontsize=7)

        ax = axes[1]
        rule_lats   = [np.mean(rule_data['latencies'][l])   if rule_data['latencies'][l]   else 0 for l in labels_found]
        neural_lats = [np.mean(neural_data['latencies'][l]) if neural_data['latencies'][l] else 0 for l in labels_found]
        ax.bar(x - w/2, rule_lats,   w, label='Rule-Based', color='#3498db', alpha=0.85)
        ax.bar(x + w/2, neural_lats, w, label='Neural',     color='#e74c3c', alpha=0.85)
        ax.set_xticks(x); ax.set_xticklabels(labels_found, rotation=30, ha='right', fontsize=8)
        ax.set_ylabel('Avg Latency (ms)')
        ax.set_title('Avg Latency by Label')
        ax.legend(fontsize=7)

        plt.tight_layout()
        p = output_dir / 'comparison.png'
        plt.savefig(p, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"[Saved] {p}")

def run_evaluation(dataset_dir, detector, labels_found, expected_map,
                   predict_fn, system_name, forbidden_map=None):
    y_true, y_pred = [], []
    cm_y_true, cm_y_pred = [], []
    latencies = {lbl: [] for lbl in labels_found}
    records   = []

    print(f"\n{'─'*60}")
    print(f"  {system_name}")
    print(f"{'─'*60}")

    for label in labels_found:
        expected = expected_map[label]
        folder   = dataset_dir / label
        images   = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMG_EXTS)

        n_correct = 0
        n_total   = 0

        for img_path in images:
            img = load_image(img_path)
            if img is None:
                continue
            rgb    = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            t0     = time.perf_counter()
            result = detector.detect(mp_img)
            det_ms = (time.perf_counter() - t0) * 1000

            if not result.hand_landmarks:
                detected = 'no_hand'
                gesture_ms = det_ms
            else:
                t1 = time.perf_counter()
                detected = predict_fn(result.hand_landmarks[0])
                gesture_ms = det_ms + (time.perf_counter() - t1) * 1000

            if forbidden_map and label in forbidden_map:
                correct = (detected != forbidden_map[label])
            else:
                correct = (detected == expected)
            y_true.append(expected)
            y_pred.append(detected)
            cm_y_true.append(label)
            cm_y_pred.append(dataset_pred_label(detected, label, RULE_GESTURE_TO_DATASET, RULE_FORBIDDEN))
            latencies[label].append(gesture_ms)
            records.append({
                'label': label, 'expected': expected,
                'detected': detected, 'correct': correct,
                'latency_ms': round(gesture_ms, 3),
                'file': img_path.name,
            })
            n_correct += int(correct)
            n_total   += 1

        acc = 100 * n_correct / n_total if n_total else 0
        avg_lat = np.mean(latencies[label]) if latencies[label] else 0
        print(f"  {label:<25}  {n_correct:>4}/{n_total:<4}  "
              f"acc={acc:5.1f}%  avg_lat={avg_lat:6.2f}ms")

    if not y_true:
        print(f"\n  [SKIP] No images processed - add images to the dataset subfolders.")
        return None

    all_classes = sorted(set(y_true + y_pred))
    if HAS_SKL:
        report = classification_report(y_true, y_pred, labels=all_classes,
                                       zero_division=0, output_dict=True)
        cm = confusion_matrix(y_true, y_pred, labels=all_classes).tolist()
    else:
        report = manual_metrics(y_true, y_pred, all_classes)
        cm = build_cm(y_true, y_pred, all_classes)

    report['accuracy'] = sum(r['correct'] for r in records) / len(records)
    cm_dataset = build_cm(cm_y_true, cm_y_pred, labels_found)

    return {
        'y_true': y_true, 'y_pred': y_pred,
        'latencies': latencies, 'records': records,
        'report': report, 'cm': cm,
        'classes': all_classes,
        'cm_dataset': cm_dataset,
        'cm_dataset_classes': list(labels_found),
    }

def print_summary(data, system_name, labels_found, expected_map, forbidden_map=None):
    report = data['report']
    print(f"\n{'═'*72}")
    print(f"  {system_name}   overall accuracy: {report['accuracy']*100:.2f}%")
    print(f"{'═'*72}")
    print(f"  {'Label':<25} {'Acc%':>6} {'Prec':>6} {'Rec':>6} {'F1':>6} {'AvgLat':>9}  Expected → Detected classes")
    print(f"  {'─'*68}")
    for lbl in labels_found:
        acc, nc, nt = per_label_acc(data['records'], lbl)
        exp     = expected_map[lbl]
        r       = data['report'].get(exp, {})
        avg_lat = np.mean(data['latencies'][lbl]) if data['latencies'][lbl] else 0
        wrong   = [(r['detected'], r['file']) for r in data['records']
                   if r['label'] == lbl and not r['correct']]
        wrong_summary = ', '.join(
            f"{g}({sum(1 for x in wrong if x[0]==g)})"
            for g in dict.fromkeys(w[0] for w in wrong)
        )[:35]
        exp_label = f"not {forbidden_map[lbl]}" if (forbidden_map and lbl in forbidden_map) else exp
        print(f"  {lbl:<25} {acc*100:6.1f} {r.get('precision',0)*100:6.1f} "
              f"{r.get('recall',0)*100:6.1f} {r.get('f1-score',0)*100:6.1f} "
              f"{avg_lat:9.2f}  [{exp_label}] ← err: {wrong_summary or '-'}")
    print(f"{'═'*72}")

def print_comparison(rule_data, neural_data, labels_found):
    print(f"\n{'═'*72}")
    print("  RULE-BASED  vs  NEURAL  -  Head-to-Head")
    print(f"{'═'*72}")
    print(f"  {'Label':<25} {'Rule Acc%':>10} {'Neural Acc%':>12} {'Rule ms':>9} {'Neural ms':>10}")
    print(f"  {'─'*68}")
    for lbl in labels_found:
        ra, _, _ = per_label_acc(rule_data['records'], lbl)
        na, _, _ = per_label_acc(neural_data['records'], lbl)
        rl = np.mean(rule_data['latencies'][lbl])   if rule_data['latencies'][lbl]   else 0
        nl = np.mean(neural_data['latencies'][lbl]) if neural_data['latencies'][lbl] else 0
        winner = '← Rule' if ra > na else ('← Neural' if na > ra else '  tie')
        print(f"  {lbl:<25} {ra*100:10.1f} {na*100:12.1f} {rl:9.2f} {nl:10.2f}  {winner}")
    ro = rule_data['report']['accuracy'] * 100
    no = neural_data['report']['accuracy'] * 100
    print(f"  {'─'*68}")
    print(f"  {'OVERALL':<25} {ro:10.1f} {no:12.1f}")
    print(f"{'═'*72}")

def plot_misclassified(data, dataset_dir, output_dir, system_name, n=5):
    if not HAS_MPL:
        return
    wrong = [r for r in data['records'] if not r['correct']]
    if not wrong:
        print(f"[{system_name}] No misclassified samples to show.")
        return
    samples = wrong[:n]
    fig, axes = plt.subplots(1, len(samples), figsize=(4 * len(samples), 4))
    if len(samples) == 1:
        axes = [axes]
    fig.suptitle(f'{system_name} - Misclassified Samples', fontsize=13, fontweight='bold')
    for ax, rec in zip(axes, samples):
        img_path = dataset_dir / rec['label'] / rec['file']
        img = load_image(Path(img_path))
        if img is None:
            ax.axis('off')
            continue
        ax.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        ax.set_title(f"True: {rec['label']}\nPred: {rec['detected']}", fontsize=8, color='red')
        ax.axis('off')
    plt.tight_layout()
    tag = system_name.lower().split()[0]
    p = output_dir / f'misclassified_{tag}.png'
    plt.savefig(p, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Saved] {p}")


def main():
    ap = argparse.ArgumentParser(description='Gesture recognition evaluation')
    ap.add_argument('dataset',              help='Dataset folder with gesture subfolders')
    ap.add_argument('--model',   default='hand_landmarker.task')
    ap.add_argument('--nn-model',default='data/mouse_gesture_model_best.pt')
    ap.add_argument('--encoder', default='data/mouse_label_encoder.pkl')
    ap.add_argument('--output',  default='eval_results')
    ap.add_argument('--thresh',  type=float, default=0.51,
                    help='Neural confidence threshold (default 0.51)')
    args = ap.parse_args()

    dataset_dir = Path(args.dataset)
    output_dir  = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not dataset_dir.is_dir():
        print(f"[ERROR] Dataset folder not found: {dataset_dir}")
        sys.exit(1)

    labels_found = sorted([
        d.name for d in dataset_dir.iterdir()
        if d.is_dir() and d.name in KNOWN_LABELS
    ])
    if not labels_found:
        print(f"[ERROR] No recognised subfolders in {dataset_dir}")
        print(f"        Expected any of: {sorted(KNOWN_LABELS)}")
        sys.exit(1)

    total_images = sum(
        len([p for p in (dataset_dir/l).iterdir() if p.suffix.lower() in IMG_EXTS])
        for l in labels_found
    )
    print(f"\nDataset : {dataset_dir}")
    print(f"Labels  : {labels_found}")
    print(f"Images  : {total_images}")
    print(f"Output  : {output_dir}\n")

    if total_images == 0:
        print("[ERROR] All subfolders are empty. Add images (jpg/png/bmp) and re-run.")
        sys.exit(1)

    base     = mp_python.BaseOptions(model_asset_path=args.model)
    opts     = mp_vision.HandLandmarkerOptions(base_options=base, num_hands=1)
    detector = mp_vision.HandLandmarker.create_from_options(opts)

    results_all = {}

    rule_data = run_evaluation(
        dataset_dir, detector, labels_found, RULE_EXPECTED,
        predict_fn=rule_gesture,
        system_name='RULE-BASED  (landmark.py)',
        forbidden_map=RULE_FORBIDDEN,
    )
    if rule_data is not None:
        results_all['rule_based'] = {
            'overall_accuracy':      round(rule_data['report']['accuracy'], 4),
            'per_label_accuracy':    {l: round(per_label_acc(rule_data['records'], l)[0], 4)
                                      for l in labels_found},
            'per_label_avg_lat_ms':  {l: round(np.mean(rule_data['latencies'][l]), 3)
                                      for l in labels_found if rule_data['latencies'][l]},
            'classification_report': rule_data['report'],
        }

    neural_data = None
    if HAS_TORCH:
        nn_model, le = load_neural(args.nn_model, args.encoder)
        if nn_model is not None:

            _state = {'prev': None}
            def neural_predict(lms):
                g, _, new_prev = neural_gesture(lms, nn_model, le, args.thresh, _state['prev'])
                _state['prev'] = new_prev
                return g

            original_run = run_evaluation

            def run_neural_eval():
                y_true, y_pred = [], []
                cm_y_true, cm_y_pred = [], []
                latencies = {lbl: [] for lbl in labels_found}
                records   = []
                print(f"\n{'─'*60}")
                print(f"  NEURAL  (neural.py)")
                print(f"{'─'*60}")

                for label in labels_found:
                    expected = NEURAL_EXPECTED[label]
                    folder   = dataset_dir / label
                    images   = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMG_EXTS)

                    n_correct = n_total = 0
                    for img_path in images:
                        _state['prev'] = None
                        img = load_image(img_path)
                        if img is None:
                            continue
                        rgb    = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                        t0     = time.perf_counter()
                        result = detector.detect(mp_img)
                        det_ms = (time.perf_counter() - t0) * 1000

                        if not result.hand_landmarks:
                            detected = 'no_hand'
                            lat = det_ms
                        else:
                            t1       = time.perf_counter()
                            detected = neural_predict(result.hand_landmarks[0])
                            lat      = det_ms + (time.perf_counter() - t1) * 1000

                        if label in NEURAL_FORBIDDEN:
                            correct = (detected != NEURAL_FORBIDDEN[label])
                        else:
                            correct = (detected == expected)
                        y_true.append(expected); y_pred.append(detected)
                        cm_y_true.append(label)
                        cm_y_pred.append(dataset_pred_label(detected, label, NEURAL_GESTURE_TO_DATASET, NEURAL_FORBIDDEN))
                        latencies[label].append(lat)
                        records.append({
                            'label': label, 'expected': expected,
                            'detected': detected, 'correct': correct,
                            'latency_ms': round(lat, 3), 'file': img_path.name,
                        })
                        n_correct += int(correct); n_total += 1

                    acc = 100 * n_correct / n_total if n_total else 0
                    avg_lat = np.mean(latencies[label]) if latencies[label] else 0
                    print(f"  {label:<25}  {n_correct:>4}/{n_total:<4}  "
                          f"acc={acc:5.1f}%  avg_lat={avg_lat:6.2f}ms")

                if not y_true:
                    print(f"\n  [SKIP] No images processed for neural eval.")
                    return None

                all_classes = sorted(set(y_true + y_pred))
                if HAS_SKL:
                    report = classification_report(y_true, y_pred, labels=all_classes,
                                                   zero_division=0, output_dict=True)
                    cm = confusion_matrix(y_true, y_pred, labels=all_classes).tolist()
                else:
                    report = manual_metrics(y_true, y_pred, all_classes)
                    cm = build_cm(y_true, y_pred, all_classes)

                report['accuracy'] = sum(r['correct'] for r in records) / len(records)
                cm_dataset = build_cm(cm_y_true, cm_y_pred, labels_found)

                return {
                    'y_true': y_true, 'y_pred': y_pred,
                    'latencies': latencies, 'records': records,
                    'report': report, 'cm': cm, 'classes': all_classes,
                    'cm_dataset': cm_dataset,
                    'cm_dataset_classes': list(labels_found),
                }

            neural_data = run_neural_eval()
            if neural_data is not None:
                results_all['neural'] = {
                    'overall_accuracy':      round(neural_data['report']['accuracy'], 4),
                    'per_label_accuracy':    {l: round(per_label_acc(neural_data['records'], l)[0], 4)
                                              for l in labels_found},
                    'per_label_avg_lat_ms':  {l: round(np.mean(neural_data['latencies'][l]), 3)
                                              for l in labels_found if neural_data['latencies'][l]},
                    'classification_report': neural_data['report'],
                }

    detector.close()

    if rule_data is not None:
        print_summary(rule_data, 'RULE-BASED', labels_found, RULE_EXPECTED, RULE_FORBIDDEN)
    if neural_data is not None:
        print_summary(neural_data, 'NEURAL', labels_found, NEURAL_EXPECTED, NEURAL_FORBIDDEN)
    if rule_data is not None and neural_data is not None:
        print_comparison(rule_data, neural_data, labels_found)

    json_path = output_dir / 'results.json'
    json_path.write_text(json.dumps(results_all, indent=2))
    print(f"\n[Saved] {json_path}")

    for tag, data in [('rule', rule_data), ('neural', neural_data)]:
        if data is None:
            continue
        csv_path = output_dir / f'per_image_{tag}.csv'
        with open(csv_path, 'w') as f:
            f.write('file,label,expected,detected,correct,latency_ms\n')
            for r in data['records']:
                f.write(f"{r['file']},{r['label']},{r['expected']},"
                        f"{r['detected']},{r['correct']},{r['latency_ms']}\n")
        print(f"[Saved] {csv_path}")

    plot_evaluation(rule_data, neural_data, labels_found, output_dir)

    if rule_data is not None:
        plot_misclassified(rule_data, dataset_dir, output_dir, 'Rule-Based')
    if neural_data is not None:
        plot_misclassified(neural_data, dataset_dir, output_dir, 'Neural')

    print("\nDone.")


if __name__ == '__main__':
    main()
