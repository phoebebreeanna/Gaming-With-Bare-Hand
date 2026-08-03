import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import time
import threading
import torch
import torch.nn as nn
import joblib
import math
from pynput.mouse import Controller, Button

mouse = Controller()

import pyautogui
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0
SCREEN_W, SCREEN_H = pyautogui.size()

TRACKING_POINT = 'knuckle'

TRACK_LM = {
    'tip':     8,
    'knuckle': 5,
}[TRACKING_POINT]

SMOOTHING          = 0.45
CLICK_COOLDOWN     = 0.35
SCROLL_SPEED       = 3
CONFIDENCE_THRESH  = 0.6
DRAG_HOLD_THRESH   = 0.5
MP_PRESENCE_THRESH = 0.7
IDLE_GRACE         = 0.12

CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),
    (0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),
    (5,9),(9,13),(13,17)
]

GESTURE_COLOR = {
    'move':            (255, 200,   0),
    'pre_left_click':  (160, 160, 160),
    'left_click':      (  0, 200, 255),
    'pre_right_click': (160, 160, 160),
    'right_click':     (255,  80, 200),
    'scroll_up':       (180, 255,  80),
    'scroll_down':     ( 80, 180, 255),
    'idle':            (180, 180, 180),
    'drag':            (  0, 120, 255),
}


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


le            = joblib.load('data/mouse_label_encoder.pkl')
gesture_model = GestureNet(126, len(le.classes_))
gesture_model.load_state_dict(torch.load('data/mouse_gesture_model_best.pt', map_location='cpu'))
gesture_model.eval()
print(f"[NN] classes: {list(le.classes_)}")
print(f"[TRACK] Tracking point: {TRACKING_POINT.upper()} (landmark {TRACK_LM})")

last_click_t       = 0.0
last_right_click_t = 0.0
prev_scroll_y      = None
right_click_armed  = True
left_click_entry_t = None
drag_active        = False
scroll_entry_t     = None
scroll_active      = False
prev_row           = None
last_left_click_t  = None

_latest_frame  = None
_latest_result = None
_frame_lock    = threading.Lock()
_result_lock   = threading.Lock()
_stop_thread   = False

smooth_x, smooth_y = SCREEN_W / 2, SCREEN_H / 2


def normalize_landmarks(lms):
    global prev_row
    wx, wy, wz = lms[0].x, lms[0].y, lms[0].z
    scale = math.sqrt((lms[9].x - wx)**2 + (lms[9].y - wy)**2 + (lms[9].z - wz)**2)
    scale = max(scale, 1e-6)
    row = []
    for lm in lms:
        row.extend([(lm.x - wx)/scale, (lm.y - wy)/scale, (lm.z - wz)/scale])
    delta    = [c - p for c, p in zip(row, prev_row)] if prev_row is not None else [0.0]*63
    prev_row = row
    return row + delta


def get_gesture(lms):
    features = normalize_landmarks(lms)
    x = torch.tensor([features], dtype=torch.float32)
    with torch.no_grad():
        probs     = torch.softmax(gesture_model(x), dim=1)[0]
        conf, idx = probs.max(0)
    if conf.item() < CONFIDENCE_THRESH:
        return 'idle', conf.item(), True
    return le.inverse_transform([idx.item()])[0], conf.item(), False


def map_cursor(tip_x, tip_y):
    return tip_x * SCREEN_W, tip_y * SCREEN_H


def move_cursor(x, y):
    mouse.position = (int(x), int(y))


def release_drag():
    global drag_active
    if drag_active:
        mouse.release(Button.left)
        drag_active = False


def draw_hand(img, lms):
    h, w = img.shape[:2]
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in lms]
    for a, b in CONNECTIONS:
        cv2.line(img, pts[a], pts[b], (0, 200, 100), 2)
    for pt in pts:
        cv2.circle(img, pt, 5, (255, 255, 255), -1)
        cv2.circle(img, pt, 5, (0, 150, 80), 2)
    tx, ty = pts[TRACK_LM]
    cv2.circle(img, (tx, ty), 10, (0, 255, 255), 3)


def draw_running_ui(img, gesture, conf, scroll_entry_t, scroll_active,
                    drag_active, left_click_entry_t, mp_frozen=False):
    h, w = img.shape[:2]
    now  = time.time()

    if drag_active:
        label, color = "DRAGGING", GESTURE_COLOR['drag']
    elif gesture == 'left_click' and left_click_entry_t is not None:
        held  = now - left_click_entry_t
        pct   = int(min(held / DRAG_HOLD_THRESH, 1.0) * 100)
        label = f"LEFT CLICK  (hold {pct}% -> drag)"
        color = GESTURE_COLOR['left_click']
    elif gesture == 'pre_left_click':  label, color = "PRE LEFT CLICK (no action)",  GESTURE_COLOR['pre_left_click']
    elif gesture == 'pre_right_click': label, color = "PRE RIGHT CLICK (no action)", GESTURE_COLOR['pre_right_click']
    elif gesture == 'right_click':     label, color = "RIGHT CLICK",                 GESTURE_COLOR['right_click']
    elif gesture == 'move':            label, color = "MOVE",                        GESTURE_COLOR['move']
    elif gesture == 'scroll_up':       label, color = "SCROLL UP",                   GESTURE_COLOR['scroll_up']
    elif gesture == 'scroll_down':     label, color = "SCROLL DOWN",                 GESTURE_COLOR['scroll_down']
    else:                              label, color = "IDLE",                        GESTURE_COLOR['idle']

    cv2.rectangle(img, (0, 0), (580, 40), (30, 30, 30), -1)
    cv2.putText(img, f"Gesture: {label}  [{conf:.2f}]  | Track: {TRACKING_POINT.upper()} [T]", (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.62, color, 2)

    if mp_frozen:
        cv2.rectangle(img, (0, 42), (380, 72), (0, 0, 160), -1)
        cv2.putText(img, "Hand unstable - cursor frozen", (10, 63),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (80, 150, 255), 2)

    legend = [
        (f"Tracking: index {TRACKING_POINT.upper()} (lm{TRACK_LM})  [T to toggle]", (0, 255, 255)),
        ("move / any non-idle = cursor follows tracked point",                        GESTURE_COLOR['move']),
        (f"left_click <{DRAG_HOLD_THRESH}s              = CLICK",                    GESTURE_COLOR['left_click']),
        (f"left_click >{DRAG_HOLD_THRESH}s              = DRAG",                     GESTURE_COLOR['drag']),
        ("right_click (enter gesture) = RIGHT CLICK, leave to re-arm",               GESTURE_COLOR['right_click']),
        ("scroll_up / scroll_down        = SCROLL",                                  GESTURE_COLOR['scroll_up']),
        ("pre_left / pre_right           = no action",                               GESTURE_COLOR['pre_left_click']),
        ("idle                           = no cursor, no action",                    GESTURE_COLOR['idle']),
        ("ESC = quit   |   T = toggle tip/knuckle",                                  (100, 100, 100)),
    ]
    for i, (text, col) in enumerate(legend):
        cv2.putText(img, text, (10, h - 12 - (len(legend) - 1 - i) * 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, col, 1)


base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
options      = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1)
detector     = vision.HandLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS,          30)
cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)


def detection_worker():
    global _latest_result, _stop_thread
    while not _stop_thread:
        with _frame_lock:
            frame = _latest_frame
        if frame is None:
            time.sleep(0.001)
            continue
        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        with _result_lock:
            _latest_result = result


_det_thread = threading.Thread(target=detection_worker, daemon=True)
_det_thread.start()


def toggle_tracking():
    global TRACKING_POINT, TRACK_LM, prev_row, smooth_x, smooth_y
    global scroll_entry_t, scroll_active, drag_active, right_click_armed
    global left_click_entry_t, last_left_click_t, last_right_click_t, last_click_t
    release_drag()
    if TRACKING_POINT == 'tip':
        TRACKING_POINT = 'knuckle'
        TRACK_LM       = 5
    else:
        TRACKING_POINT = 'tip'
        TRACK_LM       = 8
    smooth_x, smooth_y = SCREEN_W / 2, SCREEN_H / 2
    prev_row           = None
    scroll_entry_t     = None
    scroll_active      = False
    right_click_armed  = True
    left_click_entry_t = None
    last_left_click_t  = None
    last_click_t       = 0.0
    last_right_click_t = 0.0
    print(f"[TRACK] Switched to: {TRACKING_POINT.upper()} (landmark {TRACK_LM})")


print("ESC to quit  |  T to toggle tip/knuckle tracking")

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

    mp_confident = False
    if has_hand:
        try:
            mp_confident = result.handedness[0][0].score >= MP_PRESENCE_THRESH
        except Exception:
            mp_confident = True

    if not has_hand:
        prev_row = None

    if lms:
        now = time.time()

        if not mp_confident:
            prev_row = None
            gesture  = 'idle'
            conf     = 0.0
        else:
            gesture, conf, low_conf = get_gesture(lms)

            raw_x, raw_y = map_cursor(lms[TRACK_LM].x, lms[TRACK_LM].y)
            smooth_x += (raw_x - smooth_x) * SMOOTHING
            smooth_y += (raw_y - smooth_y) * SMOOTHING
            move_cursor(smooth_x, smooth_y)

            if gesture == 'left_click':
                scroll_entry_t    = None
                scroll_active     = False
                last_left_click_t = now
                if left_click_entry_t is None:
                    left_click_entry_t = now
                if (now - left_click_entry_t) >= DRAG_HOLD_THRESH and not drag_active:
                    mouse.press(Button.left)
                    drag_active = True

            elif gesture in ('pre_left_click', 'pre_right_click'):
                if drag_active:
                    release_drag()

            elif gesture == 'move':
                release_drag()
                if left_click_entry_t is not None:
                    held = now - left_click_entry_t
                    if held < DRAG_HOLD_THRESH and now - last_click_t > CLICK_COOLDOWN:
                        mouse.click(Button.left)
                        last_click_t = now
                    left_click_entry_t = None
                scroll_entry_t = None
                scroll_active  = False

            elif gesture == 'right_click':
                release_drag()
                if left_click_entry_t is not None:
                    held = now - left_click_entry_t
                    if held < DRAG_HOLD_THRESH and now - last_click_t > CLICK_COOLDOWN:
                        mouse.click(Button.left)
                        last_click_t = now
                    left_click_entry_t = None
                if right_click_armed:
                    mouse.click(Button.right)
                    last_right_click_t = now
                    right_click_armed  = False
                scroll_entry_t = None
                scroll_active  = False

            elif gesture in ('scroll_up', 'scroll_down'):
                release_drag()
                if left_click_entry_t is not None:
                    held = now - left_click_entry_t
                    if held < DRAG_HOLD_THRESH and now - last_click_t > CLICK_COOLDOWN:
                        mouse.click(Button.left)
                        last_click_t = now
                    left_click_entry_t = None
                if scroll_entry_t is None:
                    scroll_entry_t = now
                    scroll_active  = False
                elif not scroll_active:
                    scroll_active = True
                if scroll_active:
                    mouse.scroll(0, SCROLL_SPEED if gesture == 'scroll_up' else -SCROLL_SPEED)

            else:
                if left_click_entry_t is not None and not drag_active:
                    time_since_lc = (now - last_left_click_t) if last_left_click_t else 999
                    if time_since_lc > IDLE_GRACE:
                        held = now - left_click_entry_t
                        if held < DRAG_HOLD_THRESH and now - last_click_t > CLICK_COOLDOWN:
                            mouse.click(Button.left)
                            last_click_t = now
                        left_click_entry_t = None
                elif drag_active:
                    time_since_lc = (now - last_left_click_t) if last_left_click_t else 999
                    if time_since_lc > IDLE_GRACE:
                        release_drag()
                        left_click_entry_t = None
                scroll_entry_t = None
                scroll_active  = False

            if gesture != 'left_click' and gesture not in ('pre_left_click', 'pre_right_click'):
                if left_click_entry_t is not None and not drag_active:
                    held = now - left_click_entry_t
                    if held < DRAG_HOLD_THRESH:
                        if now - last_click_t > CLICK_COOLDOWN:
                            mouse.click(Button.left)
                            last_click_t       = now
                            left_click_entry_t = None
                    else:
                        left_click_entry_t = None

            if gesture != 'right_click':
                right_click_armed = True

        fx, fy    = int(lms[TRACK_LM].x * fw), int(lms[TRACK_LM].y * fh)
        dot_color = GESTURE_COLOR['drag'] if drag_active else GESTURE_COLOR.get(gesture, (255, 255, 255))
        cv2.circle(display, (fx, fy), 12, dot_color, 2)
        cv2.circle(display, (fx, fy),  4, dot_color, -1)
        draw_hand(display, lms)
        draw_running_ui(display, gesture, conf,
                        scroll_entry_t, scroll_active, drag_active,
                        left_click_entry_t, mp_frozen=not mp_confident)
    else:
        release_drag()
        left_click_entry_t = None
        scroll_entry_t     = None
        scroll_active      = False
        right_click_armed  = True
        draw_running_ui(display, 'idle', 0.0, None, False, False, None)

    cv2.imshow('Mouse Controller', display)
    key = cv2.waitKey(1) & 0xFF
    if key == 27:
        release_drag()
        break
    elif key in (ord('t'), ord('T')):
        toggle_tracking()

_stop_thread = True
_det_thread.join(timeout=1.0)
cap.release()
cv2.destroyAllWindows()
detector.close()
