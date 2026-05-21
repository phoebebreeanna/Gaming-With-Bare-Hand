import os
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
import numpy as np
import pyautogui
import time
import threading
import math

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

try:
    import torch
    import torch.nn as nn
    import joblib
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

SCREEN_W, SCREEN_H = pyautogui.size()

LOGIC_DIR      = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH     = os.path.join(LOGIC_DIR, 'hand_landmarker.task')
SUBWAY_WEIGHTS = os.path.join(LOGIC_DIR, 'gesture_model_subway.pt')
SUBWAY_ENCODER = os.path.join(LOGIC_DIR, 'label_encoder_subway.pkl')
RACING_WEIGHTS = os.path.join(LOGIC_DIR, 'gesture_model_racing.pt')
RACING_ENCODER = os.path.join(LOGIC_DIR, 'label_encoder_racing.pkl')

# ── constants ─────────────────────────────────────────────────────────────────

SMOOTHING        = 0.3
PINCH_THRESH     = 0.03
CLICK_COOLDOWN   = 0.5
SCROLL_SPEED     = 3
LONG_PRESS_TIME  = 0.5
SCROLL_BUFFER    = 0
TARGET_DIST      = 0.18
DIST_TOL         = 0.03
DIST_OK_HOLD     = 3.0
INTRO_DURATION      = 30.0
ZONE_INTRO_DURATION = 30.0
ZONE_DURATION       = 30.0
GUIDE_DURATION      = 30.0
SKIP_LOCKOUT        = 3.0
HOLD_META    = 3.0
HOLD_CLOSE   = 3.0
HOLD_GAME    = 5.0
ZONE_CONFIRM_TIME = 3.0

SS_KEY_COOLDOWN      = 0.3
SS_SPACE_COOLDOWN    = 1.0
SS_CONFIDENCE_THRESH = 0.75

RC_STEER_DEADZONE = 5
RC_STEER_MAX      = 40
RC_CONF_THRESH    = 0.6

CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),
    (0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),
    (5,9),(9,13),(13,17),
]

ZONE_PRESETS = {
    'small':  0.25,
    'medium': 0.55,
    'large':  0.90,
}

# colours used only for the minimal frame overlay (hand skeleton + dot)
_BONE    = (0, 200, 110)
_JOINT   = (255, 255, 255)
_JOINT_B = (0, 150, 80)
_ZONE_C  = (0, 220, 90)
_DOT_CLR = {
    'move':        (255, 200,   0),
    'tm_pinch':    (  0, 200, 255),
    'right_click': (255,  70, 180),
    'drag':        (  0, 120, 255),
    'scroll_up':   (180, 255,  80),
    'scroll_down': ( 80, 180, 255),
    'idle':        (120, 120, 130),
}


def list_cameras(max_test=6):
    available = []
    for i in range(max_test):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            available.append(i)
            cap.release()
    return available


# ── gesture-net ───────────────────────────────────────────────────────────────

class GestureNet(nn.Module if TORCH_AVAILABLE else object):
    def __init__(self, num_classes):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(126, 256), nn.BatchNorm1d(256), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(256, 128), nn.BatchNorm1d(128), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(128,  64), nn.BatchNorm1d( 64), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear( 64, num_classes),
        )
    def forward(self, x):
        return self.net(x)


def _load_nn(weights_path, encoder_path, tag):
    if not TORCH_AVAILABLE:
        return None, None
    try:
        le  = joblib.load(encoder_path)
        net = GestureNet(len(le.classes_))
        net.load_state_dict(torch.load(weights_path, map_location='cpu', weights_only=False))
        net.eval()
        return net, le
    except FileNotFoundError:
        return None, None
    except Exception as e:
        print(f"[NN:{tag}] Load error: {e}")
        return None, None


# ── pure gesture helpers ──────────────────────────────────────────────────────

def _extract_features(lms, prev_row):
    wx, wy, wz = lms[0].x, lms[0].y, lms[0].z
    scale = max(math.sqrt((lms[9].x-wx)**2 + (lms[9].y-wy)**2 + (lms[9].z-wz)**2), 1e-6)
    row = []
    for lm in lms:
        row.extend([(lm.x-wx)/scale, (lm.y-wy)/scale, (lm.z-wz)/scale])
    delta = [c-p for c, p in zip(row, prev_row)] if prev_row else [0.0]*63
    return row + delta, row

def run_nn(lms, prev_row, model, le, conf_thresh):
    if model is None or le is None:
        return 'none', 0.0, prev_row
    features, new_prev = _extract_features(lms, prev_row)
    x = torch.tensor([features], dtype=torch.float32)
    with torch.no_grad():
        probs     = torch.softmax(model(x), dim=1)[0]
        conf, idx = probs.max(0)
    if conf.item() < conf_thresh:
        return 'none', conf.item(), new_prev
    return le.inverse_transform([idx.item()])[0], conf.item(), new_prev

def hand_size(lms):
    return np.hypot(lms[0].x - lms[9].x, lms[0].y - lms[9].y)

def tip_dist(lms, a, b):
    return np.hypot(lms[a].x - lms[b].x, lms[a].y - lms[b].y)

def is_finger_extended(lms, tip, pip):
    return (np.hypot(lms[tip].x-lms[0].x, lms[tip].y-lms[0].y) >
            np.hypot(lms[pip].x-lms[0].x, lms[pip].y-lms[0].y))

def fingers_extended(lms):
    return {
        'index':  is_finger_extended(lms, 8,  6),
        'middle': is_finger_extended(lms, 12, 10),
        'ring':   is_finger_extended(lms, 16, 14),
        'pinky':  is_finger_extended(lms, 20, 18),
    }

def count_fingers_up(lms):
    return sum(fingers_extended(lms).values())

def is_thumbs_up(lms):
    f = fingers_extended(lms)
    return (lms[4].y < lms[3].y < lms[2].y and
            not (f['index'] or f['middle'] or f['ring'] or f['pinky']))

def is_open_palm(lms):
    return all(fingers_extended(lms).values())

def is_fist(lms):
    return not any(fingers_extended(lms).values())

def is_shaka(lms):
    f = fingers_extended(lms)
    return (lms[4].y < lms[3].y) and f['pinky'] and not f['index'] and not f['middle'] and not f['ring']

def is_metal_sign(lms):
    f = fingers_extended(lms)
    return f['index'] and f['pinky'] and not f['middle'] and not f['ring']

def is_peace_sign(lms):
    f = fingers_extended(lms)
    return f['index'] and f['middle'] and not f['ring'] and not f['pinky']

def get_game_option(lms, lms2):
    if lms is None or lms2 is None:
        return None
    for fist_hand, finger_hand in [(lms, lms2), (lms2, lms)]:
        if is_fist(fist_hand):
            n = count_fingers_up(finger_hand)
            if 1 <= n <= 4:
                return n
    return None

def get_gesture_mouse(lms):
    f = fingers_extended(lms)
    if f['index'] and f['middle'] and f['ring'] and not f['pinky']:
        return 'scroll_up'
    if not any(f.values()):
        return 'scroll_down'
    if tip_dist(lms, 4, 12) < PINCH_THRESH:
        return 'tm_pinch'
    if tip_dist(lms, 4, 16) < PINCH_THRESH:
        return 'right_click'
    idx_d = np.hypot(lms[8].x - lms[0].x, lms[8].y - lms[0].y)
    def curled(t):
        return np.hypot(lms[t].x-lms[0].x, lms[t].y-lms[0].y) < idx_d * 0.85
    if f['index'] and curled(12) and curled(16) and curled(20):
        return 'move'
    return 'idle'

def get_steer_angle(lms_left, lms_right):
    return np.degrees(np.arctan2(
        lms_right[0].y - lms_left[0].y,
        lms_right[0].x - lms_left[0].x))

def split_hands(result):
    lms_left = lms_right = None
    for hand in result.hand_landmarks:
        if hand[0].x < 0.5: lms_left  = hand
        else:                lms_right = hand
    return lms_left, lms_right

def tick_game_opt(lms, lms2, now, hold_t, cur_num):
    opt_now = get_game_option(lms, lms2)
    if opt_now is not None:
        if opt_now != cur_num:
            hold_t  = now
            cur_num = opt_now
        elif hold_t is None:
            hold_t = now
        held = now - hold_t
        frac = min(held / HOLD_GAME, 1.0)
        return hold_t, cur_num, frac, (opt_now if frac >= 1.0 else None)
    return None, None, 0.0, None


# ── minimal frame overlay (only what needs to be ON the camera image) ─────────

def draw_hand(img, lms, bone_color=None):
    if lms is None:
        return
    bc = bone_color or _BONE
    h, w = img.shape[:2]
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in lms]
    for a, b in CONNECTIONS:
        cv2.line(img, pts[a], pts[b], bc, 2)
    for pt in pts:
        cv2.circle(img, pt, 5, _JOINT,    -1)
        cv2.circle(img, pt, 5, _JOINT_B,   2)

def draw_zone_rect(img, min_x, max_x, min_y, max_y):
    h, w = img.shape[:2]
    cv2.rectangle(img,
                  (int(min_x * w), int(min_y * h)),
                  (int(max_x * w), int(max_y * h)),
                  _ZONE_C, 1)

def draw_finger_dot(img, lms, gesture, drag_active):
    h, w = img.shape[:2]
    fx, fy = int(lms[8].x * w), int(lms[8].y * h)
    col = _DOT_CLR['drag'] if drag_active else _DOT_CLR.get(gesture, _DOT_CLR['idle'])
    cv2.circle(img, (fx, fy), 12, col, 2)
    cv2.circle(img, (fx, fy),  4, col, -1)


# ── main thread ───────────────────────────────────────────────────────────────

class HandControllerThread(QThread):
    # always-on
    frame_ready     = Signal(QImage)
    gesture_changed = Signal(str, str)   # label, action
    state_changed   = Signal(str)
    error_occurred  = Signal(str)

    # state-specific data signals
    slide_progress  = Signal(float, float)   # elapsed_ratio, skip_frac
    distance_update = Signal(float, bool, float)   # dist, has_hand, hold_frac
    zone_pick_data  = Signal(str, str, float, float, float, float)
    #                  detected, chosen, elapsed_ratio, confirm_frac, secs_left, skip_frac
    running_data    = Signal(object)   # mode-specific dict
    stopped_data    = Signal(float, float)   # resume_frac, close_frac

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index  = camera_index
        self._running      = False
        self._paused_event = threading.Event()
        self._paused_event.set()

        self.subway_model, self.subway_le = _load_nn(SUBWAY_WEIGHTS, SUBWAY_ENCODER, 'SUBWAY')
        self.racing_model, self.racing_le = _load_nn(RACING_WEIGHTS, RACING_ENCODER, 'RACING')

        self._init_state()

    def _init_state(self):
        self.app_state          = 'intro'
        self.intro_start_t      = None
        self.zone_intro_start_t = None
        self.zone_start_t       = None
        self.guide_start_t      = None
        self.chosen_zone        = 'medium'
        self.dist_ok_since      = None
        self.range_min_x = self.range_max_x = None
        self.range_min_y = self.range_max_y = None
        self.last_click_t   = 0.0
        self.prev_scroll_y  = None
        self.scroll_entry_t = None
        self.scroll_active  = False
        self.tm_pinch_start = None
        self.tm_drag_active = False
        self.smooth_x = SCREEN_W / 2
        self.smooth_y = SCREEN_H / 2
        self.meta_hold = {k: None for k in ('start','stop','close','recal','guide','game_opt')}
        self.game_option_pending = None
        self.game_opt_number     = None
        self.active_game_mode    = None
        self.ss_current_zone  = 'neutral'
        self.ss_last_key_t    = 0.0
        self.ss_last_space_t  = 0.0
        self.ss_space_pressed = False
        self.ss_prev_row      = None
        self.rc_held_keys      = set()
        self.rc_prev_row_left  = None
        self.rc_prev_row_right = None

    def _full_reset(self):
        if self.tm_drag_active: pyautogui.mouseUp()
        self._rc_release_all()
        self.active_game_mode = None
        self.app_state        = 'distance_check'
        self.dist_ok_since    = None
        self.smooth_x = SCREEN_W / 2
        self.smooth_y = SCREEN_H / 2
        self.last_click_t   = 0.0
        self.scroll_entry_t = None
        self.scroll_active  = False
        self.tm_pinch_start = None
        self.tm_drag_active = False
        self.meta_hold         = {k: None for k in self.meta_hold}
        self.game_option_pending = None
        self.ss_current_zone  = 'neutral'
        self.ss_last_key_t    = 0.0
        self.ss_last_space_t  = 0.0
        self.ss_space_pressed = False
        self.ss_prev_row      = None
        self.rc_prev_row_left  = None
        self.rc_prev_row_right = None

    def _set_zone(self, zone_name):
        half = ZONE_PRESETS.get(zone_name, 0.55) / 2
        self.range_min_x = 0.5 - half
        self.range_max_x = 0.5 + half
        self.range_min_y = 0.5 - half
        self.range_max_y = 0.5 + half

    def _map_cursor(self, tx, ty):
        sx = self.range_max_x - self.range_min_x
        sy = self.range_max_y - self.range_min_y
        rx = 0.5 if sx < 0.01 else float(np.clip((tx - self.range_min_x) / sx, 0, 1))
        ry = 0.5 if sy < 0.01 else float(np.clip((ty - self.range_min_y) / sy, 0, 1))
        return rx * SCREEN_W, ry * SCREEN_H

    def _pinch_release(self, now):
        if self.tm_pinch_start is None: return
        held = now - self.tm_pinch_start
        if self.tm_drag_active:
            pyautogui.mouseUp(); self.tm_drag_active = False
        elif held < LONG_PRESS_TIME and (now - self.last_click_t > CLICK_COOLDOWN):
            pyautogui.click(); self.last_click_t = now
        self.tm_pinch_start = None

    def _rc_set_held_keys(self, desired):
        for k in list(self.rc_held_keys - desired):
            try: pyautogui.keyUp(k)
            except: pass
            self.rc_held_keys.discard(k)
        for k in list(desired - self.rc_held_keys):
            pyautogui.keyDown(k)
            self.rc_held_keys.add(k)

    def _rc_release_all(self):
        for k in list(self.rc_held_keys):
            try: pyautogui.keyUp(k)
            except: pass
        self.rc_held_keys.clear()

    def _activate_game_mode(self, opt):
        self._pinch_release(time.time())
        self._rc_release_all()
        if opt == 1:
            self.active_game_mode = None
        elif opt == 2:
            self.active_game_mode = 2
            self.ss_current_zone  = 'neutral'
            self.ss_last_key_t    = 0.0
            self.ss_last_space_t  = 0.0
            self.ss_space_pressed = False
            self.ss_prev_row      = None
        elif opt == 3:
            self.active_game_mode  = 3
            self.rc_prev_row_left  = None
            self.rc_prev_row_right = None
        elif opt == 4:
            self.active_game_mode = 4

    def set_camera(self, index):
        self.camera_index = index
        if self._running:
            self.stop(); self.wait()
            self._init_state(); self.start()

    def pause(self):  self._paused_event.clear()
    def resume(self): self._paused_event.set()

    def stop(self):
        self._running = False
        self._paused_event.set()

    # ── main loop ─────────────────────────────────────────────────────────────

    def run(self):
        self._running = True
        self._init_state()

        base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
        options      = mp_vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_hands=2,
        )
        detector     = mp_vision.HandLandmarker.create_from_options(options)

        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            self.error_occurred.emit(f"Cannot open camera {self.camera_index}")
            detector.close()
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS,          30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)

        _latest_frame  = [None]
        _latest_ts     = [0]
        _latest_result = [None]
        _fl = threading.Lock()
        _rl = threading.Lock()
        _stop = [False]

        def _detect():
            last_ts = -1
            while not _stop[0]:
                with _fl:
                    frame = _latest_frame[0]
                    ts    = _latest_ts[0]
                if frame is None or ts == last_ts:
                    time.sleep(0.001); continue
                last_ts = ts
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                try:
                    result = detector.detect_for_video(
                        mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts)
                except Exception as e:
                    print(f"[MediaPipe] detection error: {e}")
                    continue
                with _rl: _latest_result[0] = result

        det = threading.Thread(target=_detect, daemon=True)
        det.start()

        self.intro_start_t = time.time()
        thumb_hold_t    = None
        zone_finger_hold = {}
        game_opt_hold_t  = None
        game_opt_frac    = 0.0

        while self._running and cap.isOpened():
            if not self._paused_event.is_set():
                time.sleep(0.01); continue

            ret, frame = cap.read()
            if not ret: break

            frame = cv2.flip(frame, 1)
            ts_ms = int(time.time() * 1000)
            with _fl:
                _latest_frame[0] = frame.copy()
                _latest_ts[0]    = ts_ms
            with _rl: result = _latest_result[0]

            has_hand = bool(result and result.hand_landmarks)
            lms  = result.hand_landmarks[0] if has_hand else None
            lms2 = result.hand_landmarks[1] if (has_hand and len(result.hand_landmarks) > 1) else None
            display = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            fh, fw  = display.shape[:2]
            now     = time.time()

            # ── state machine ──────────────────────────────────────────────

            if self.app_state == 'intro':
                elapsed   = now - self.intro_start_t
                skip_frac = 0.0
                if elapsed >= SKIP_LOCKOUT and lms and is_thumbs_up(lms):
                    if thumb_hold_t is None: thumb_hold_t = now
                    skip_frac = min((now - thumb_hold_t) / 1.0, 1.0)
                    if skip_frac >= 1.0: elapsed = INTRO_DURATION
                else:
                    if not (lms and is_thumbs_up(lms)): thumb_hold_t = None
                if lms: draw_hand(display, lms)
                self.slide_progress.emit(elapsed / INTRO_DURATION, skip_frac)
                if elapsed >= INTRO_DURATION:
                    self.app_state = 'zone_intro'
                    self.zone_intro_start_t = now
                    thumb_hold_t = None
                    self.state_changed.emit('zone_intro')

            elif self.app_state == 'zone_intro':
                elapsed   = now - self.zone_intro_start_t
                skip_frac = 0.0
                if elapsed >= SKIP_LOCKOUT and lms and is_thumbs_up(lms):
                    if thumb_hold_t is None: thumb_hold_t = now
                    skip_frac = min((now - thumb_hold_t) / 1.0, 1.0)
                    if skip_frac >= 1.0: elapsed = ZONE_INTRO_DURATION
                else:
                    if not (lms and is_thumbs_up(lms)): thumb_hold_t = None
                if lms: draw_hand(display, lms)
                self.slide_progress.emit(elapsed / ZONE_INTRO_DURATION, skip_frac)
                if elapsed >= ZONE_INTRO_DURATION:
                    self.app_state = 'zone_pick'
                    self.zone_start_t = now
                    thumb_hold_t = None
                    self.state_changed.emit('zone_pick')

            elif self.app_state == 'zone_pick':
                elapsed       = now - self.zone_start_t
                detected_zone = None
                if lms:
                    n = count_fingers_up(lms)
                    if   n == 1: detected_zone = 'small'
                    elif n == 2: detected_zone = 'medium'
                    elif n >= 3: detected_zone = 'large'
                confirm_frac = 0.0; confirm_secs = 0.0
                if detected_zone:
                    if detected_zone not in zone_finger_hold:
                        zone_finger_hold = {detected_zone: now}
                    held = now - zone_finger_hold[detected_zone]
                    confirm_frac = min(held / ZONE_CONFIRM_TIME, 1.0)
                    confirm_secs = max(0.0, ZONE_CONFIRM_TIME - held)
                    if confirm_frac >= 1.0:
                        self.chosen_zone = detected_zone
                        self._set_zone(self.chosen_zone)
                        self.app_state   = 'guide'
                        self.guide_start_t = now
                        thumb_hold_t = None; zone_finger_hold = {}
                        self.state_changed.emit('guide')
                else:
                    zone_finger_hold = {}
                skip_frac = 0.0
                if elapsed >= SKIP_LOCKOUT and lms and is_thumbs_up(lms):
                    if thumb_hold_t is None: thumb_hold_t = now
                    skip_frac = min((now - thumb_hold_t) / 1.0, 1.0)
                    if skip_frac >= 1.0:
                        self._set_zone(self.chosen_zone)
                        self.app_state   = 'guide'
                        self.guide_start_t = now
                        thumb_hold_t = None
                        self.state_changed.emit('guide')
                else:
                    if not (lms and is_thumbs_up(lms)): thumb_hold_t = None
                if elapsed >= ZONE_DURATION and self.app_state == 'zone_pick':
                    self._set_zone(self.chosen_zone)
                    self.app_state   = 'guide'
                    self.guide_start_t = now
                    thumb_hold_t = None
                    self.state_changed.emit('guide')
                if lms: draw_hand(display, lms)
                self.zone_pick_data.emit(
                    detected_zone or '', self.chosen_zone,
                    elapsed / ZONE_DURATION, confirm_frac, confirm_secs, skip_frac)

            elif self.app_state == 'guide':
                elapsed   = now - self.guide_start_t
                skip_frac = 0.0
                if elapsed >= SKIP_LOCKOUT and lms and is_thumbs_up(lms):
                    if thumb_hold_t is None: thumb_hold_t = now
                    skip_frac = min((now - thumb_hold_t) / 1.0, 1.0)
                    if skip_frac >= 1.0: elapsed = GUIDE_DURATION
                else:
                    if not (lms and is_thumbs_up(lms)): thumb_hold_t = None
                if lms: draw_hand(display, lms)
                self.slide_progress.emit(elapsed / GUIDE_DURATION, skip_frac)
                if elapsed >= GUIDE_DURATION:
                    self.app_state   = 'distance_check'
                    self.dist_ok_since = None
                    thumb_hold_t = None
                    self.state_changed.emit('distance_check')

            elif self.app_state == 'distance_check':
                dist     = hand_size(lms) if lms else 0.0
                in_range = lms and abs(dist - TARGET_DIST) <= DIST_TOL
                if in_range:
                    if self.dist_ok_since is None: self.dist_ok_since = now
                else:
                    self.dist_ok_since = None
                hold_frac = 0.0
                if self.dist_ok_since:
                    hold_frac = min((now - self.dist_ok_since) / DIST_OK_HOLD, 1.0)
                    if hold_frac >= 1.0:
                        self.app_state   = 'running'
                        self.dist_ok_since = None
                        self.state_changed.emit('running')
                if lms: draw_hand(display, lms)
                self.distance_update.emit(dist, has_hand, hold_frac)

            elif self.app_state == 'running':
                game_opt_hold_t, self.game_opt_number, game_opt_frac, triggered_opt = \
                    tick_game_opt(lms, lms2, now, game_opt_hold_t, self.game_opt_number)
                if triggered_opt is not None:
                    self._activate_game_mode(triggered_opt)
                    game_opt_hold_t = None; self.game_opt_number = None; game_opt_frac = 0.0

                # draw zone rect on frame regardless of mode
                if self.range_min_x is not None:
                    draw_zone_rect(display,
                                   self.range_min_x, self.range_max_x,
                                   self.range_min_y, self.range_max_y)

                if self.active_game_mode is None:
                    # ── mouse mode ──
                    meta_hold_fracs = {k: 0.0 for k in ('start','stop','recal','close','guide','game_opt')}
                    triggered_meta  = None

                    if lms:
                        if is_open_palm(lms):
                            if self.meta_hold['stop'] is None: self.meta_hold['stop'] = now
                            meta_hold_fracs['stop'] = min((now - self.meta_hold['stop']) / HOLD_META, 1.0)
                            if meta_hold_fracs['stop'] >= 1.0: triggered_meta = 'stop'
                        else:
                            self.meta_hold['stop'] = None

                        if is_shaka(lms):
                            if self.meta_hold['recal'] is None: self.meta_hold['recal'] = now
                            meta_hold_fracs['recal'] = min((now - self.meta_hold['recal']) / HOLD_META, 1.0)
                            if meta_hold_fracs['recal'] >= 1.0: triggered_meta = 'recal'
                        else:
                            self.meta_hold['recal'] = None

                        if is_metal_sign(lms):
                            if self.meta_hold['guide'] is None: self.meta_hold['guide'] = now
                            meta_hold_fracs['guide'] = min((now - self.meta_hold['guide']) / HOLD_META, 1.0)
                            if meta_hold_fracs['guide'] >= 1.0: triggered_meta = 'guide'
                        else:
                            self.meta_hold['guide'] = None

                    both_peace = lms and lms2 and is_peace_sign(lms) and is_peace_sign(lms2)
                    if both_peace:
                        if self.meta_hold['start'] is None: self.meta_hold['start'] = now
                        meta_hold_fracs['start'] = min((now - self.meta_hold['start']) / HOLD_META, 1.0)
                    else:
                        self.meta_hold['start'] = None

                    game_opt_now = get_game_option(lms, lms2)
                    both_fists   = lms and lms2 and is_fist(lms) and is_fist(lms2)
                    if both_fists and game_opt_now is None:
                        if self.meta_hold['close'] is None: self.meta_hold['close'] = now
                        meta_hold_fracs['close'] = min((now - self.meta_hold['close']) / HOLD_CLOSE, 1.0)
                        if meta_hold_fracs['close'] >= 1.0: triggered_meta = 'close'
                    else:
                        self.meta_hold['close'] = None

                    meta_hold_fracs['game_opt'] = game_opt_frac

                    if triggered_meta == 'stop':
                        self._pinch_release(now)
                        self.app_state = 'stopped'
                        self.meta_hold = {k: None for k in self.meta_hold}
                        self.state_changed.emit('stopped')
                    elif triggered_meta == 'recal':
                        self._pinch_release(now)
                        self.app_state = 'zone_pick'; self.zone_start_t = now
                        self.meta_hold = {k: None for k in self.meta_hold}
                        self.state_changed.emit('zone_pick')
                    elif triggered_meta == 'guide':
                        self._pinch_release(now)
                        self.app_state = 'guide'; self.guide_start_t = now
                        self.meta_hold = {k: None for k in self.meta_hold}
                        self.state_changed.emit('guide')
                    elif triggered_meta == 'close':
                        self._pinch_release(now)
                        self._running = False
                        break

                    any_meta = any(v is not None for v in self.meta_hold.values()) or game_opt_frac > 0
                    gesture   = 'idle'
                    dist_drift = ''

                    if lms and triggered_meta is None and not any_meta:
                        gesture  = get_gesture_mouse(lms)
                        dist     = hand_size(lms)
                        drift    = dist - TARGET_DIST
                        if   drift >  DIST_TOL * 3: dist_drift = 'WARNING: Too close'
                        elif drift >  DIST_TOL * 2: dist_drift = 'Slightly too close'
                        elif drift < -DIST_TOL * 3: dist_drift = 'WARNING: Too far'
                        elif drift < -DIST_TOL * 2: dist_drift = 'Slightly too far'
                        if not dist_drift:
                            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                            br   = float(np.mean(gray))
                            if   br < 40: dist_drift = 'Poor lighting'
                            elif br < 65: dist_drift = 'Low lighting'

                        tx, ty = self._map_cursor(lms[8].x, lms[8].y)
                        self.smooth_x += (tx - self.smooth_x) * (1 - SMOOTHING)
                        self.smooth_y += (ty - self.smooth_y) * (1 - SMOOTHING)

                        if gesture == 'move':
                            self._pinch_release(now)
                            pyautogui.moveTo(int(self.smooth_x), int(self.smooth_y))
                            self.scroll_entry_t = None; self.scroll_active = False
                        elif gesture == 'tm_pinch':
                            if self.tm_pinch_start is None: self.tm_pinch_start = now
                            held = now - self.tm_pinch_start
                            if not self.tm_drag_active and held >= LONG_PRESS_TIME:
                                pyautogui.mouseDown(); self.tm_drag_active = True
                            if self.tm_drag_active:
                                pyautogui.moveTo(int(self.smooth_x), int(self.smooth_y))
                            self.scroll_entry_t = None; self.scroll_active = False
                        elif gesture == 'right_click':
                            self._pinch_release(now)
                            if now - self.last_click_t > CLICK_COOLDOWN:
                                pyautogui.rightClick(); self.last_click_t = now
                            self.scroll_entry_t = None; self.scroll_active = False
                        elif gesture in ('scroll_up', 'scroll_down'):
                            self._pinch_release(now)
                            if self.scroll_entry_t is None:
                                self.scroll_entry_t = now; self.scroll_active = False
                            elif not self.scroll_active and (now - self.scroll_entry_t) >= SCROLL_BUFFER:
                                self.scroll_active = True
                            if self.scroll_active:
                                pyautogui.scroll(SCROLL_SPEED if gesture == 'scroll_up' else -SCROLL_SPEED)
                        else:
                            self._pinch_release(now)
                            self.scroll_entry_t = None; self.scroll_active = False

                        draw_hand(display, lms)
                        if lms2: draw_hand(display, lms2)
                        draw_finger_dot(display, lms, gesture, self.tm_drag_active)
                    else:
                        self._pinch_release(now)
                        self.scroll_entry_t = None; self.scroll_active = False
                        if lms:  draw_hand(display, lms)
                        if lms2: draw_hand(display, lms2)

                    _act = {
                        'move':'Moving cursor','tm_pinch':'Click / Drag',
                        'right_click':'Right click','scroll_up':'Scroll up',
                        'scroll_down':'Scroll down','idle':'Idle',
                    }
                    self.gesture_changed.emit(gesture.upper().replace('_',' '), _act.get(gesture, gesture))
                    self.running_data.emit({
                        'mode': 'mouse',
                        'gesture': gesture,
                        'drag': self.tm_drag_active,
                        'pinch_start': self.tm_pinch_start,
                        'meta': meta_hold_fracs,
                        'game_opt_num': self.game_opt_number or 0,
                        'game_opt_frac': game_opt_frac,
                        'drift': dist_drift,
                    })

                elif self.active_game_mode == 2:
                    gesture_ss = 'none'; conf_ss = 0.0
                    if lms:
                        gesture_ss, conf_ss, self.ss_prev_row = run_nn(
                            lms, self.ss_prev_row, self.subway_model, self.subway_le, SS_CONFIDENCE_THRESH)
                        if gesture_ss == 'space':
                            if not self.ss_space_pressed and (now - self.ss_last_space_t) > SS_SPACE_COOLDOWN:
                                pyautogui.press('space')
                                self.ss_space_pressed = True; self.ss_last_space_t = now
                            self.ss_current_zone = 'neutral'
                        else:
                            self.ss_space_pressed = False
                            if gesture_ss in ('up','down','left','right'):
                                if gesture_ss != self.ss_current_zone and (now - self.ss_last_key_t) > SS_KEY_COOLDOWN:
                                    pyautogui.press(gesture_ss)
                                    self.ss_last_key_t = now; self.ss_current_zone = gesture_ss
                            else:
                                self.ss_current_zone = 'neutral'
                    else:
                        self.ss_prev_row = None
                    if lms:  draw_hand(display, lms)
                    if lms2: draw_hand(display, lms2)
                    _ss_action = {'up':'Arrow UP','down':'Arrow DOWN','left':'Arrow LEFT',
                                  'right':'Arrow RIGHT','space':'SPACE / Jump','none':'Idle','neutral':'Idle'}
                    self.gesture_changed.emit(gesture_ss.upper(), _ss_action.get(gesture_ss, gesture_ss))
                    self.running_data.emit({
                        'mode': 'subway',
                        'gesture': gesture_ss,
                        'conf': conf_ss,
                        'game_opt_num': self.game_opt_number or 0,
                        'game_opt_frac': game_opt_frac,
                    })

                elif self.active_game_mode == 3:
                    lms_left = lms_right = None
                    if result and result.hand_landmarks:
                        lms_left, lms_right = split_hands(result)
                    if lms_left  is None: self.rc_prev_row_left  = None
                    if lms_right is None: self.rc_prev_row_right = None
                    desired = set(); angle = 0.0; steer_dir = 'none'
                    accel = brake = False; gest_l = gest_r = 'none'; conf_l = conf_r = 0.0
                    if lms_left:
                        gest_l, conf_l, self.rc_prev_row_left = run_nn(
                            lms_left, self.rc_prev_row_left, self.racing_model, self.racing_le, RC_CONF_THRESH)
                    if lms_right:
                        gest_r, conf_r, self.rc_prev_row_right = run_nn(
                            lms_right, self.rc_prev_row_right, self.racing_model, self.racing_le, RC_CONF_THRESH)
                    accel = gest_r == 'thumbs'; brake = gest_l == 'thumbs'
                    if lms_left and lms_right:
                        angle = get_steer_angle(lms_left, lms_right)
                        if   angle < -RC_STEER_DEADZONE: steer_dir = 'left'
                        elif angle >  RC_STEER_DEADZONE: steer_dir = 'right'
                    if steer_dir == 'left':  desired.add('left')
                    if steer_dir == 'right': desired.add('right')
                    if accel: desired.add('up')
                    if brake: desired.add('down')
                    self._rc_set_held_keys(desired)
                    if lms_left:  draw_hand(display, lms_left,  (255,180,80))
                    if lms_right: draw_hand(display, lms_right, (255,80,180))
                    _sl = {'left':'LEFT ←','right':'RIGHT →','none':'Straight'}[steer_dir]
                    self.gesture_changed.emit(f'STEER {_sl}', 'Racing mode')
                    self.running_data.emit({
                        'mode': 'racing',
                        'steer': steer_dir,
                        'angle': round(angle, 1),
                        'accel': accel,
                        'brake': brake,
                        'gest_l': gest_l, 'conf_l': round(conf_l, 2),
                        'gest_r': gest_r, 'conf_r': round(conf_r, 2),
                        'game_opt_num': self.game_opt_number or 0,
                        'game_opt_frac': game_opt_frac,
                    })

                elif self.active_game_mode == 4:
                    if lms:  draw_hand(display, lms)
                    if lms2: draw_hand(display, lms2)
                    self.gesture_changed.emit('FREE MODE', 'Opt 4 - custom slot')
                    self.running_data.emit({
                        'mode': 'free',
                        'game_opt_num': self.game_opt_number or 0,
                        'game_opt_frac': game_opt_frac,
                    })

            elif self.app_state == 'stopped':
                both_peace = lms and lms2 and is_peace_sign(lms) and is_peace_sign(lms2)
                both_fists = lms and lms2 and is_fist(lms) and is_fist(lms2)
                resume_frac = 0.0; close_frac = 0.0

                if both_peace:
                    if thumb_hold_t is None: thumb_hold_t = now
                    resume_frac = min((now - thumb_hold_t) / HOLD_META, 1.0)
                    if resume_frac >= 1.0:
                        self.app_state = 'running'; thumb_hold_t = None
                        self.meta_hold = {k: None for k in self.meta_hold}
                        self.state_changed.emit('running')
                else:
                    thumb_hold_t = None

                if both_fists:
                    if self.meta_hold['close'] is None: self.meta_hold['close'] = now
                    close_frac = min((now - self.meta_hold['close']) / HOLD_CLOSE, 1.0)
                    if close_frac >= 1.0:
                        self._running = False; break
                else:
                    self.meta_hold['close'] = None

                if lms:  draw_hand(display, lms)
                if lms2: draw_hand(display, lms2)
                self.stopped_data.emit(resume_frac, close_frac)

            # ── emit frame (RGB format, hand skeleton only) ────────────────
            h_img, w_img, ch = display.shape
            qt_img = QImage(display.data, w_img, h_img, ch * w_img, QImage.Format_RGB888)
            self.frame_ready.emit(qt_img.copy())

        self._pinch_release(time.time())
        self._rc_release_all()
        _stop[0] = True
        det.join(timeout=2.0)   # wait for detect thread before closing detector
        cap.release()
        detector.close()
        self.state_changed.emit('idle')
