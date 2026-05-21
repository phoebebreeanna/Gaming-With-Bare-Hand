import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import pyautogui
import time
import threading
import torch
import torch.nn as nn
import joblib
import math

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

TARGET_DIST       = 0.18
DIST_TOL          = 0.03
DIST_OK_HOLD      = 1.0
KEY_COOLDOWN      = 0.3
SPACE_COOLDOWN    = 1.0
CONFIDENCE_THRESH = 0.75

GESTURE_KEY = {
    'jump':  'up',
    'roll':  'down',
    'left':  'left',
    'right': 'right',
    'space': 'space',
}

GESTURE_COLOR = {
    'jump':  (  0, 220, 255),
    'roll':  ( 80, 180, 255),
    'left':  (255, 180,  80),
    'right': (255,  80, 180),
    'space': (180,  80, 255),
    'idle':  (160, 160, 160),
    'none':  (100, 100, 100),
}

CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),
    (0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),
    (5,9),(9,13),(13,17)
]


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


le            = joblib.load('data/subway_label_encoder.pkl')
gesture_model = GestureNet(126, len(le.classes_))
gesture_model.load_state_dict(torch.load('data/subway_gesture_model.pt', map_location='cpu'))
gesture_model.eval()
print(f"[NN] classes: {list(le.classes_)}")

app_state     = 'distance_check'
dist_ok_since = None
current_zone  = 'idle'
last_key_t    = 0.0
prev_row      = None

_latest_frame  = None
_latest_result = None
_frame_lock    = threading.Lock()
_result_lock   = threading.Lock()
_stop_thread   = False


def hand_size(lms):
    return np.hypot(lms[0].x - lms[9].x, lms[0].y - lms[9].y)


def extract_features(lms, prev_row):
    wx, wy, wz = lms[0].x, lms[0].y, lms[0].z
    scale = math.sqrt((lms[9].x - wx)**2 + (lms[9].y - wy)**2 + (lms[9].z - wz)**2)
    scale = max(scale, 1e-6)
    row   = []
    for lm in lms:
        row.extend([(lm.x - wx)/scale, (lm.y - wy)/scale, (lm.z - wz)/scale])
    delta = [c - p for c, p in zip(row, prev_row)] if prev_row is not None else [0.0]*63
    return row + delta, row


def get_gesture(lms, prev_row):
    features, new_prev = extract_features(lms, prev_row)
    x = torch.tensor([features], dtype=torch.float32)
    with torch.no_grad():
        probs     = torch.softmax(gesture_model(x), dim=1)[0]
        conf, idx = probs.max(0)
    if conf.item() < CONFIDENCE_THRESH:
        return 'none', conf.item(), new_prev
    return le.inverse_transform([idx.item()])[0], conf.item(), new_prev


def draw_hand(img, lms):
    if lms is None:
        return
    h, w = img.shape[:2]
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in lms]
    for a, b in CONNECTIONS:
        cv2.line(img, pts[a], pts[b], (0, 200, 100), 2)
    for pt in pts:
        cv2.circle(img, pt, 5, (255, 255, 255), -1)
        cv2.circle(img, pt, 5, (0, 150, 80), 2)


def draw_distance_ui(img, dist, has_hand, ok_since):
    h, w = img.shape[:2]
    cv2.rectangle(img, (0, 0), (w, 80), (20, 20, 20), -1)
    if not has_hand:
        cv2.putText(img, "Show your hand to the camera",
                    (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (200, 200, 200), 2)
        return
    if dist > TARGET_DIST + DIST_TOL:   msg, color = "Move FARTHER from camera",    (0,  80, 255)
    elif dist < TARGET_DIST - DIST_TOL: msg, color = "Move CLOSER to camera",       (0, 200, 255)
    else:                               msg, color = "Distance OK!  Hold still...", (0, 220,  80)
    cv2.putText(img, msg, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.85, color, 2)
    bar_x, bar_y, bar_w = 10, 90, w - 20
    cv2.rectangle(img, (bar_x, bar_y), (bar_x + bar_w, bar_y + 18), (60, 60, 60), -1)
    fill = int(np.clip(dist / (TARGET_DIST * 2), 0, 1) * bar_w)
    cv2.rectangle(img, (bar_x, bar_y), (bar_x + fill, bar_y + 18), color, -1)
    lo = int((TARGET_DIST - DIST_TOL) / (TARGET_DIST * 2) * bar_w) + bar_x
    hi = int((TARGET_DIST + DIST_TOL) / (TARGET_DIST * 2) * bar_w) + bar_x
    cv2.rectangle(img, (lo, bar_y), (hi, bar_y + 18), (0, 255, 100), 2)
    if ok_since is not None:
        elapsed = time.time() - ok_since
        frac    = min(elapsed / DIST_OK_HOLD, 1.0)
        cv2.rectangle(img, (10, 116), (10 + int(frac * (w - 20)), 130), (0, 220, 80), -1)
        cv2.putText(img, f"Hold... {DIST_OK_HOLD - elapsed:.1f}s",
                    (10, 148), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 80), 1)


def draw_running_ui(img, gesture, conf, lms, fw, fh):
    h, w = img.shape[:2]
    color  = GESTURE_COLOR.get(gesture, (200, 200, 200))
    action = {
        'jump':  "JUMP  (up arrow)",
        'roll':  "ROLL  (down arrow)",
        'left':  "LEFT  (left arrow)",
        'right': "RIGHT  (right arrow)",
        'space': "SPACE  (space)",
        'idle':  "IDLE",
        'none':  "none",
    }.get(gesture, gesture)

    cv2.rectangle(img, (0, 0), (w, 44), (30, 30, 30), -1)
    cv2.putText(img, f"{action}  [{conf:.2f}]",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

    legend = [
        ("jump    = UP arrow",        GESTURE_COLOR['jump']),
        ("roll    = DOWN arrow",      GESTURE_COLOR['roll']),
        ("left    = LEFT arrow",      GESTURE_COLOR['left']),
        ("right   = RIGHT arrow",     GESTURE_COLOR['right']),
        ("space   = SPACE",           GESTURE_COLOR['space']),
        ("idle/none = no input",      GESTURE_COLOR['idle']),
        ("R = distance reset",        (100, 100, 100)),
    ]
    for i, (txt, col) in enumerate(legend):
        cv2.putText(img, txt, (10, h - 12 - (len(legend) - 1 - i) * 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, col, 1)

    if lms is not None:
        fx = int(lms[8].x * fw)
        fy = int(lms[8].y * fh)
        cv2.circle(img, (fx, fy), 12, color, 2)
        cv2.circle(img, (fx, fy),  4, color, -1)


base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
options      = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1)
detector     = vision.HandLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS,          30)
cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)


def detection_worker():
    global _latest_result
    while not _stop_thread:
        with _frame_lock:
            frame = _latest_frame
        if frame is None:
            time.sleep(0.001)
            continue
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        with _result_lock:
            _latest_result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))


_det_thread = threading.Thread(target=detection_worker, daemon=True)
_det_thread.start()

print("ESC to quit  |  R to reset distance")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    with _frame_lock:
        _latest_frame = frame.copy()
    with _result_lock:
        result = _latest_result

    has_hand = bool(result and result.hand_landmarks)
    lms      = result.hand_landmarks[0] if has_hand else None
    display  = frame.copy()
    fh, fw   = display.shape[:2]

    if not has_hand:
        prev_row = None

    if app_state == 'distance_check':
        dist     = hand_size(lms) if lms else 0.0
        in_range = lms and abs(dist - TARGET_DIST) <= DIST_TOL

        if in_range:
            if dist_ok_since is None:
                dist_ok_since = time.time()
            elif time.time() - dist_ok_since >= DIST_OK_HOLD:
                app_state     = 'running'
                dist_ok_since = None
        else:
            dist_ok_since = None

        draw_hand(display, lms)
        draw_distance_ui(display, dist, has_hand, dist_ok_since)

    elif app_state == 'running':
        gesture = 'none'
        conf    = 0.0

        if lms:
            gesture, conf, prev_row = get_gesture(lms, prev_row)
            now = time.time()

            if gesture in GESTURE_KEY:
                cooldown = SPACE_COOLDOWN if gesture == 'space' else KEY_COOLDOWN
                if gesture != current_zone and (now - last_key_t) > cooldown:
                    pyautogui.press(GESTURE_KEY[gesture])
                    last_key_t   = now
                    current_zone = gesture
            else:
                current_zone = 'idle'

        draw_hand(display, lms)
        draw_running_ui(display, gesture, conf, lms, fw, fh)

        if not has_hand:
            cv2.rectangle(display, (0, 46), (fw, 80), (40, 20, 20), -1)
            cv2.putText(display, "No hand detected!",
                        (10, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 100, 255), 2)

    cv2.imshow('Subway Surfer Controller', display)
    key = cv2.waitKey(1) & 0xFF
    if key == 27:
        break
    elif key in (ord('r'), ord('R')):
        app_state     = 'distance_check'
        dist_ok_since = None
        current_zone  = 'idle'
        last_key_t    = 0.0
        prev_row      = None

_stop_thread = True
_det_thread.join(timeout=1.0)
cap.release()
cv2.destroyAllWindows()
detector.close()