import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import csv, os, shutil, time, sys, math, glob, argparse
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler
import joblib
import configparser

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


def load_conf(path):
    cfg = configparser.ConfigParser()
    cfg.read(path)
    gestures = [g.strip() for g in cfg['gestures']['names'].split(',')]
    data_dir  = cfg['files'].get('data_dir', 'data')
    os.makedirs(data_dir, exist_ok=True)
    def dp(name):
        return os.path.join(data_dir, cfg['files'][name])
    return {
        'project':              cfg['project']['name'],
        'gestures':             gestures,
        'target':               cfg.getint('collection',    'target_per_gesture'),
        'min_record_dist':      cfg.getfloat('collection',  'min_record_dist'),
        'diversity_every':      cfg.getint('collection',    'diversity_every'),
        'aug_per_sample':       cfg.getint('preprocessing', 'aug_per_sample'),
        'noise_std':            cfg.getfloat('preprocessing','noise_std'),
        'rot_max_deg':          cfg.getfloat('preprocessing','rot_max_deg'),
        'scale_jitter':         cfg.getfloat('preprocessing','scale_jitter'),
        'epochs':               cfg.getint('training',      'epochs'),
        'batch_size':           cfg.getint('training',      'batch_size'),
        'lr':                   cfg.getfloat('training',    'learning_rate'),
        'focal_gamma':          cfg.getfloat('training',    'focal_gamma'),
        'low_conf_threshold':   cfg.getfloat('training',    'low_conf_threshold'),
        'weak_acc_threshold':   cfg.getfloat('training',    'weak_accuracy_threshold'),
        'raw_csv':              dp('raw_csv'),
        'processed_csv':        dp('processed_csv'),
        'model_best':           dp('model_best'),
        'model_out':            dp('model_out'),
        'label_encoder':        dp('label_encoder'),
    }


def banner(text):
    w = 60
    print('\n' + '='*w)
    print(f"  {text}")
    print('='*w)


def prompt_continue(msg="Press Enter to continue, or type 'skip' to skip this step: "):
    r = input(msg).strip().lower()
    return r != 'skip'


def draw_landmarks_collect(frame, lms, w, h):
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in lms]
    for a, b in HAND_CONNECTIONS:
        cv2.line(frame, pts[a], pts[b], (0, 200, 255), 1, cv2.LINE_AA)
    for idx, (px, py) in enumerate(pts):
        r = 5 if idx in FINGERTIPS else 3
        cv2.circle(frame, (px, py), r, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(frame, (px, py), r, (0, 150, 255),   1, cv2.LINE_AA)


def wrist_dist(lms, last_pos):
    if last_pos is None:
        return float('inf')
    dx = lms[0].x - last_pos[0]
    dy = lms[0].y - last_pos[1]
    return math.sqrt(dx*dx + dy*dy)


def delete_label_from_csv(csv_path, label):
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        return 0
    removed = 0
    tmp = csv_path + '.tmp'
    with open(csv_path, 'r', newline='') as fin, open(tmp, 'w', newline='') as fout:
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


def open_csv(csv_path, gestures):
    header_coords = [f'{ax}{i}' for i in range(21) for ax in ['x','y','z']]
    header = header_coords + ['label']
    exists = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0
    fh = open(csv_path, 'a', newline='')
    cw = csv.writer(fh)
    if not exists:
        cw.writerow(header)
    return fh, cw


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
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['label'] in counts:
                    counts[row['label']] += 1
    return counts


def run_collection(cfg, target_gestures=None):
    gestures        = cfg['gestures']
    target          = cfg['target']
    min_record_dist = cfg['min_record_dist']
    diversity_every = cfg['diversity_every']
    csv_path        = cfg['raw_csv']

    if target_gestures:
        gestures = [g for g in gestures if g in target_gestures]

    banner(f"STEP 1 - DATA COLLECTION  [{cfg['project']}]")
    print(f"Gestures to collect: {gestures}")
    print(f"Target per gesture : {target} samples")
    print()
    print("Controls:")
    print("  0-9  select gesture by index")
    print("  SPACE  start / stop recording")
    print("  D      delete all samples for selected gesture (double-tap)")
    print("  ESC    finish and move on")
    print()

    for i, g in enumerate(gestures):
        print(f"  {i} = {g}")
    print()

    base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
    options      = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1)
    detector     = vision.HandLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)
    W_CAP, H_CAP = 640, 480

    counts         = count_existing(csv_path, gestures)
    current_label  = None
    collecting     = False
    last_saved_pos = None
    confirm_delete = False
    confirm_timer  = 0.0
    CONFIRM_WINDOW = 3.0

    csv_file, csv_writer = open_csv(csv_path, gestures)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame    = cv2.flip(frame, 1)
        rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result   = detector.detect(mp_image)
        h, w     = frame.shape[:2]
        now      = time.time()

        if confirm_delete and (now - confirm_timer) > CONFIRM_WINDOW:
            confirm_delete = False

        moved = False

        if result.hand_landmarks:
            lms = result.hand_landmarks[0]
            wx, wy, wz = lms[0].x, lms[0].y, lms[0].z
            row = []
            for lm in lms:
                row.extend([lm.x - wx, lm.y - wy, lm.z - wz])

            dist  = wrist_dist(lms, last_saved_pos)
            moved = dist == float('inf') or dist >= min_record_dist

            if collecting and current_label is not None and moved:
                csv_writer.writerow(row + [gestures[current_label]])
                csv_file.flush()
                counts[gestures[current_label]] += 1
                last_saved_pos = (lms[0].x, lms[0].y)
                c = counts[gestures[current_label]]
                if c % diversity_every == 0 and c > 0:
                    print(f"  [{c} samples] Tip: {diversity_hint(c, diversity_every)}")
        else:
            last_saved_pos = None

        display = frame.copy()

        for i, g in enumerate(gestures):
            done   = counts[g] >= target
            color  = (0, 255, 0) if done else (180, 180, 180)
            tag    = "OK" if done else f"{counts[g]}/{target}"
            prefix = ">> " if current_label == i else "   "
            cv2.putText(display, f"{prefix}{i}:{g}  {tag}",
                        (w - 310, 30 + i * 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        all_done = all(counts[g] >= target for g in gestures)
        if all_done:
            cv2.putText(display, "ALL DONE  -  ESC to continue",
                        (10, h - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            cv2.putText(display, "G = skip and continue with what you have",
                        (10, h - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (120, 120, 120), 1)

        if confirm_delete and current_label is not None:
            remaining = max(0.0, CONFIRM_WINDOW - (now - confirm_timer))
            msg = f"Press D again to DELETE '{gestures[current_label]}' ({remaining:.1f}s)"
            cv2.rectangle(display, (0, h - 80), (w, h - 55), (0, 0, 160), -1)
            cv2.putText(display, msg, (10, h - 62),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 100, 255), 2)

        if result.hand_landmarks:
            draw_landmarks_collect(display, result.hand_landmarks[0], w, h)
            if collecting and current_label is not None:
                label  = gestures[current_label]
                bar_w  = int((counts[label] / target) * 300)
                gate   = "  [move a bit]" if not moved else ""
                cv2.rectangle(display, (10, h-30), (310, h-10), (60,60,60), -1)
                cv2.rectangle(display, (10, h-30), (10+bar_w, h-10), (0,0,255), -1)
                cv2.putText(display, f"RECORDING: {label}  [{counts[label]}/{target}]{gate}",
                            (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0,0,255), 2)
                c = counts[label]
                if c > 0:
                    cv2.putText(display, f"Tip: {diversity_hint(c, diversity_every)}",
                                (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 200), 1)
            else:
                lname = gestures[current_label] if current_label is not None else 'none selected'
                cv2.putText(display, f"Ready | {lname}  (SPACE=record  D=delete)",
                            (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,200,0), 2)
        else:
            cv2.putText(display, "No hand detected",
                        (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,80,255), 2)

        cv2.imshow('Collect Gestures', display)
        key = cv2.waitKey(1) & 0xFF

        if key == 27:
            break

        elif key in (ord('g'), ord('G')):
            break

        elif key == ord(' '):
            if current_label is None:
                print("Select a gesture first")
            else:
                collecting     = not collecting
                last_saved_pos = None
                confirm_delete = False
                state = "started" if collecting else "stopped"
                print(f"Recording {state} - {gestures[current_label]}  ({counts[gestures[current_label]]} samples)")

        elif key in (ord('d'), ord('D')):
            if current_label is None:
                print("Select a gesture first")
            elif not confirm_delete:
                confirm_delete = True
                confirm_timer  = now
                collecting     = False
                print(f"Press D again within {CONFIRM_WINDOW:.0f}s to DELETE '{gestures[current_label]}'")
            else:
                lbl        = gestures[current_label]
                collecting = False
                csv_file.flush()
                csv_file.close()
                removed = delete_label_from_csv(csv_path, lbl)
                counts[lbl] = 0
                confirm_delete  = False
                last_saved_pos  = None
                print(f"Deleted {removed} rows for '{lbl}'")
                csv_file, csv_writer = open_csv(csv_path, gestures)

        elif ord('0') <= key <= ord('9'):
            idx = key - ord('0')
            if idx < len(gestures):
                collecting     = False
                current_label  = idx
                last_saved_pos = None
                confirm_delete = False
                print(f"Selected: {gestures[idx]}  ({counts[gestures[idx]]} samples)")

    csv_file.close()
    cap.release()
    cv2.destroyAllWindows()
    detector.close()

    banner("Collection complete")
    for g in gestures:
        status = "OK" if counts[g] >= target else f"NEED {target - counts[g]} more"
        print(f"  {g}: {counts[g]}  [{status}]")

    return counts


def normalize(raw_row):
    coords = np.array(raw_row, dtype=np.float32).reshape(21, 3)
    scale  = np.sqrt(coords[9, 0]**2 + coords[9, 1]**2)
    scale  = max(scale, 1e-6)
    normalized = coords.copy()
    normalized[:, 0] /= scale
    normalized[:, 1] /= scale
    normalized[:, 2] /= scale
    return normalized.flatten().tolist()


def rotate_2d(coords_63, angle_deg):
    coords  = np.array(coords_63, dtype=np.float32).reshape(21, 3)
    angle   = np.deg2rad(angle_deg)
    cos_a, sin_a = np.cos(angle), np.sin(angle)
    rotated = coords.copy()
    rotated[:, 0] = coords[:, 0] * cos_a - coords[:, 1] * sin_a
    rotated[:, 1] = coords[:, 0] * sin_a + coords[:, 1] * cos_a
    return rotated.flatten().tolist()


def augment(coords_63, aug_per_sample, noise_std, rot_max_deg, scale_jitter):
    variants = []
    for _ in range(aug_per_sample):
        c = np.array(coords_63, dtype=np.float32)
        c = np.array(rotate_2d(c.tolist(), np.random.uniform(-rot_max_deg, rot_max_deg)), dtype=np.float32)
        c *= 1.0 + np.random.uniform(-scale_jitter, scale_jitter)
        c += np.random.normal(0, noise_std, c.shape).astype(np.float32)
        variants.append(c.tolist())
    return variants


def compute_delta(current, previous):
    if previous is None:
        return [0.0] * len(current)
    return [c - p for c, p in zip(current, previous)]


def run_preprocess(cfg):
    banner("STEP 2 - PREPROCESSING")
    raw_path  = cfg['raw_csv']
    out_path  = cfg['processed_csv']

    if not os.path.exists(raw_path):
        print(f"ERROR: {raw_path} not found.")
        return False

    df = pd.read_csv(raw_path)
    print(f"Loaded {len(df)} raw samples")

    feature_cols = [c for c in df.columns if c != 'label']

    raw_counts = df['label'].value_counts().to_dict()
    print("Raw counts:")
    for g in cfg['gestures']:
        print(f"  {g}: {raw_counts.get(g, 0)}")

    class_rows = defaultdict(list)
    for _, row in df.iterrows():
        raw_feats = row[feature_cols].tolist()
        label     = row['label']
        norm      = normalize(raw_feats)
        class_rows[label].append(norm)

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
            aug_variants = augment(norm,
                                   cfg['aug_per_sample'],
                                   cfg['noise_std'],
                                   cfg['rot_max_deg'],
                                   cfg['scale_jitter'])
            aug_prev = norm
            for aug in aug_variants:
                aug_delta = compute_delta(aug, aug_prev)
                aug_prev  = aug
                out_rows.append(aug + aug_delta + [label])

    with open(out_path, 'w', newline='') as f:
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
        loss = ((1 - pt) ** self.gamma) * ce
        return loss.mean()


class GestureNet(nn.Module):
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


def run_training(cfg):
    banner("STEP 3 - TRAINING")
    data_path = cfg['processed_csv']

    if not os.path.exists(data_path):
        print(f"ERROR: {data_path} not found. Run preprocess first.")
        return None, None

    df = pd.read_csv(data_path)
    df = df[df['label'].isin(cfg['gestures'])].reset_index(drop=True)

    X  = df.drop('label', axis=1).values.astype(np.float32)
    y  = df['label'].values

    print(f"Samples per gesture:")
    for label, count in sorted(Counter(y).items()):
        print(f"  {label}: {count}")

    le    = LabelEncoder()
    y_enc = le.fit_transform(y)
    joblib.dump(le, cfg['label_encoder'])
    print(f"\nClasses: {list(le.classes_)}")
    print(f"Features: {X.shape[1]}")

    original_indices = np.arange(len(X))
    X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
        X, y_enc, original_indices,
        test_size=0.2, random_state=42, stratify=y_enc
    )

    X_train_t = torch.tensor(X_train)
    y_train_t = torch.tensor(y_train, dtype=torch.long)
    X_test_t  = torch.tensor(X_test)
    y_test_t  = torch.tensor(y_test,  dtype=torch.long)

    class_counts = np.bincount(y_train)
    weights      = 1.0 / class_counts[y_train]
    sampler      = WeightedRandomSampler(weights, len(weights))
    loader       = DataLoader(
        TensorDataset(X_train_t, y_train_t),
        batch_size=cfg['batch_size'],
        sampler=sampler
    )

    model     = GestureNet(X_train.shape[1], len(le.classes_))
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg['lr'])
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=cfg['epochs'], eta_min=1e-5
    )
    cls_w     = torch.tensor(1.0 / class_counts, dtype=torch.float32)
    cls_w     = cls_w / cls_w.sum() * len(class_counts)
    criterion = FocalLoss(gamma=cfg['focal_gamma'], weight=cls_w)

    best_acc   = 0.0
    best_epoch = 0

    print(f"\nTraining for {cfg['epochs']} epochs...\n")
    for epoch in range(cfg['epochs']):
        model.train()
        total_loss = 0
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
                torch.save(model.state_dict(), cfg['model_best'])

    print(f"\nBest val_acc={best_acc:.3f} at epoch {best_epoch}")

    model.load_state_dict(torch.load(cfg['model_best']))
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
        if mask.sum() == 0:
            continue
        cls_acc = (y_pred_labels[mask] == cls).mean()
        status  = "OK" if cls_acc >= cfg['weak_acc_threshold'] else "WEAK"
        print(f"  {cls:<22} {cls_acc:.3f}  [{status}]")
        if cls_acc < cfg['weak_acc_threshold']:
            weak_gestures.append(cls)

    X_all_t = torch.tensor(X)
    with torch.no_grad():
        logits_all = model(X_all_t)
        probs_all  = torch.softmax(logits_all, dim=1).numpy()
        preds_all  = probs_all.argmax(axis=1)

    y_all_labels = le.inverse_transform(y_enc)
    y_all_pred   = le.inverse_transform(preds_all)
    conf_all     = probs_all.max(axis=1)

    wrong_mask   = y_all_pred != y_all_labels
    lowconf_mask = (conf_all < cfg['low_conf_threshold']) & ~wrong_mask
    flagged_mask = wrong_mask | lowconf_mask

    flagged_indices = list(np.where(flagged_mask)[0])

    print(f"\nMisclassified:    {wrong_mask.sum()}")
    print(f"Low confidence:   {lowconf_mask.sum()}")
    print(f"Total flagged:    {flagged_mask.sum()} / {len(X)}")

    if flagged_mask.sum() > 0:
        print(f"\n  {'Row':<10} {'True':<22} {'Predicted':<22} {'Conf':>6}  Status")
        print(f"  {'-'*70}")
        for idx in flagged_indices:
            true   = y_all_labels[idx]
            pred   = y_all_pred[idx]
            conf   = conf_all[idx]
            status = "WRONG" if wrong_mask[idx] else "LOW_CONF"
            print(f"  {idx:<10} {true:<22} {pred:<22} {conf:>5.1%}  {status}")

    torch.save(model.state_dict(), cfg['model_out'])
    print(f"\nSaved: {cfg['model_out']}  +  {cfg['label_encoder']}")

    flagged_meta = []
    for idx in flagged_indices:
        flagged_meta.append({
            'true':   y_all_labels[idx],
            'pred':   y_all_pred[idx],
            'conf':   float(conf_all[idx]),
            'status': 'WRONG' if wrong_mask[idx] else 'LOW CONF',
        })

    return flagged_indices, weak_gestures, flagged_meta


def draw_hand_viz(frame, landmarks, cx, cy, scale=160):
    lms = landmarks
    pts = []
    for i in range(21):
        px = int(cx + lms[i, 0] * scale)
        py = int(cy + lms[i, 1] * scale)
        pts.append((px, py))

    finger_map = {}
    for fi, group in enumerate(FINGER_LMS):
        for lm_idx in group:
            finger_map[lm_idx] = fi

    for a, b in HAND_CONNECTIONS:
        fi    = finger_map.get(a, finger_map.get(b, -1))
        color = FINGER_COLORS[fi] if fi >= 0 else (180, 180, 180)
        cv2.line(frame, pts[a], pts[b], color, 2, cv2.LINE_AA)

    for idx, (px, py) in enumerate(pts):
        if idx == 0:
            cv2.circle(frame, (px, py), 7, (255, 255, 0), -1, cv2.LINE_AA)
            cv2.circle(frame, (px, py), 7, (0, 0, 0),     1, cv2.LINE_AA)
        elif idx in FINGERTIPS:
            fi = finger_map.get(idx, 0)
            cv2.circle(frame, (px, py), 6, FINGER_COLORS[fi], -1, cv2.LINE_AA)
            cv2.circle(frame, (px, py), 6, (0, 0, 0),          1, cv2.LINE_AA)
        else:
            cv2.circle(frame, (px, py), 4, (220, 220, 220), -1, cv2.LINE_AA)
            cv2.circle(frame, (px, py), 4, (80,  80,  80),  1, cv2.LINE_AA)
    return pts


def run_visualizer(cfg, flagged_indices, flagged_meta):
    if not flagged_indices:
        banner("No flagged samples - skipping review")
        return False

    csv_path     = cfg['processed_csv']
    df           = pd.read_csv(csv_path)
    feature_cols = [c for c in df.columns if c != 'label']
    n            = len(flagged_indices)
    to_remove    = []

    W, H = 700, 460
    font = cv2.FONT_HERSHEY_SIMPLEX

    banner(f"STEP 4 - REVIEW  ({n} flagged samples)")

    cv2.namedWindow('Review', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Review', W, H)

    for i, (orig_idx, meta) in enumerate(zip(flagged_indices, flagged_meta)):
        true_label = meta['true']
        pred_label = meta['pred']
        conf       = meta['conf']
        status     = meta['status']
        is_wrong   = status == 'WRONG'

        row  = df.iloc[orig_idx]
        lms  = np.array([row[c] for c in feature_cols][:63], dtype=np.float32).reshape(21, 3)

        decision = None
        while decision is None:
            frame = np.zeros((H, W, 3), dtype=np.uint8)
            frame[:] = (15, 15, 22)

            draw_hand_viz(frame, lms, cx=210, cy=280, scale=145)

            badge_col = (0, 60, 200) if is_wrong else (0, 110, 160)
            cv2.rectangle(frame, (10, 10), (130, 38), badge_col, -1)
            cv2.putText(frame, status, (16, 30), font, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

            cv2.putText(frame, f"{i + 1} / {n}", (W - 110, 28), font, 0.55, (100, 100, 120), 1)

            cv2.putText(frame, "TRUE",      (420, 70),  font, 0.42, (100, 100, 120), 1)
            cv2.putText(frame, "PREDICTED", (420, 120), font, 0.42, (100, 100, 120), 1)
            cv2.putText(frame, "CONF",      (420, 170), font, 0.42, (100, 100, 120), 1)

            cv2.putText(frame, true_label, (420, 92), font, 0.65, (0, 210, 90), 2, cv2.LINE_AA)

            pred_col = (0, 80, 220) if is_wrong else (200, 160, 0)
            cv2.putText(frame, pred_label, (420, 142), font, 0.65, pred_col, 2, cv2.LINE_AA)

            bar_max = 240
            bar_fill = int(conf * bar_max)
            bar_col = (0, 200, 80) if conf >= 0.8 else (0, 160, 200) if conf >= 0.6 else (0, 80, 200)
            cv2.rectangle(frame, (420, 178), (420 + bar_max, 194), (40, 40, 40), -1)
            cv2.rectangle(frame, (420, 178), (420 + bar_fill, 194), bar_col, -1)
            cv2.putText(frame, f"{conf:.0%}", (420 + bar_max + 8, 192), font, 0.5, bar_col, 1)

            cv2.line(frame, (0, H - 70), (W, H - 70), (35, 35, 50), 1)
            cv2.putText(frame, "SPACE  keep      X  remove      ESC  stop review",
                        (18, H - 42), font, 0.5, (160, 160, 160), 1, cv2.LINE_AA)
            cv2.putText(frame, f"{len(to_remove)} marked for removal so far",
                        (18, H - 18), font, 0.4, (80, 80, 100), 1)

            cv2.imshow('Review', frame)
            key = cv2.waitKey(30) & 0xFF

            if key == ord(' '):
                decision = 'keep'
            elif key in (ord('x'), ord('X')):
                decision = 'remove'
                to_remove.append(orig_idx)
            elif key == 27:
                decision = 'stop'

        if decision == 'stop':
            break

    cv2.destroyAllWindows()

    if not to_remove:
        print("No samples removed.")
        return False

    tmp = csv_path + '.tmp'
    df.drop(index=to_remove).reset_index(drop=True).to_csv(tmp, index=False)
    shutil.move(tmp, csv_path)
    banner(f"Removed {len(to_remove)} samples - {len(df) - len(to_remove)} remaining")
    return True



def main():
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

    flagged_indices, weak_gestures, flagged_meta = run_training(cfg)

    if run_visualizer(cfg, flagged_indices, flagged_meta):
        banner("Retraining after review")
        np.random.seed(42)
        flagged_indices, weak_gestures, flagged_meta = run_training(cfg)

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
