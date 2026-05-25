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

try:
    from pynput.mouse import Controller as _PynputMouse, Button as _PynputButton
    _mouse_ctrl = _PynputMouse()
    PYNPUT_AVAILABLE = True
except ImportError:
    _mouse_ctrl = None
    PYNPUT_AVAILABLE = False

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

SCREEN_W, SCREEN_H = pyautogui.size()

LOGIC_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(LOGIC_DIR, 'data')
CUSTOM_DIR  = os.path.join(DATA_DIR, 'custom')
MODEL_PATH  = os.path.join(DATA_DIR, 'hand_landmarker.task')

MOUSE_WEIGHTS  = os.path.join(DATA_DIR, 'mouse_gesture_model_best.pt')
MOUSE_ENCODER  = os.path.join(DATA_DIR, 'mouse_label_encoder.pkl')
SUBWAY_WEIGHTS = os.path.join(DATA_DIR, 'subway_gesture_model_best.pt')
SUBWAY_ENCODER = os.path.join(DATA_DIR, 'subway_label_encoder.pkl')
RACING_WEIGHTS = os.path.join(DATA_DIR, 'racing_gesture_model_best.pt')
RACING_ENCODER = os.path.join(DATA_DIR, 'racing_label_encoder.pkl')

MOUSE_WEIGHTS_CUSTOM  = os.path.join(CUSTOM_DIR, 'mouse_gesture_model_best.pt')
MOUSE_ENCODER_CUSTOM  = os.path.join(CUSTOM_DIR, 'mouse_label_encoder.pkl')
SUBWAY_WEIGHTS_CUSTOM = os.path.join(CUSTOM_DIR, 'subway_gesture_model_best.pt')
SUBWAY_ENCODER_CUSTOM = os.path.join(CUSTOM_DIR, 'subway_label_encoder.pkl')
RACING_WEIGHTS_CUSTOM = os.path.join(CUSTOM_DIR, 'racing_gesture_model_best.pt')
RACING_ENCODER_CUSTOM = os.path.join(CUSTOM_DIR, 'racing_label_encoder.pkl')

MOUSE_SMOOTHING    = 0.45
MOUSE_CONF_THRESH  = 0.75
DRAG_HOLD_THRESH   = 0.5
MP_PRESENCE_THRESH = 0.7
CLICK_COOLDOWN     = 0.5
SCROLL_SPEED       = 3

TARGET_DIST   = 0.18
DIST_TOL      = 0.03
DIST_OK_HOLD  = 3.0

INTRO_DURATION      = 30.0
ZONE_INTRO_DURATION = 30.0
ZONE_DURATION       = 30.0
GUIDE_DURATION      = 30.0
SKIP_LOCKOUT        = 3.0
HOLD_META           = 3.0
HOLD_CLOSE          = 3.0
HOLD_GAME           = 5.0
ZONE_CONFIRM_TIME   = 3.0

SS_KEY_COOLDOWN      = 0.3
SS_SPACE_COOLDOWN    = 1.0
SS_CONFIDENCE_THRESH = 0.75

RC_STEER_DEADZONE = 5
RC_STEER_MAX      = 40
RC_CONF_THRESH    = 0.6
RC_TAP_COOLDOWN   = 0.4


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

_BONE    = (0, 200, 110)
_JOINT   = (255, 255, 255)
_JOINT_B = (0, 150, 80)
_ZONE_C  = (0, 220, 90)

_DOT_CLR = {
    'move':            (255, 200,   0),
    'pre_left_click':  (160, 160, 160),
    'left_click':      (  0, 200, 255),
    'pre_right_click': (160, 160, 160),
    'right_click':     (255,  70, 180),
    'scroll_up':       (180, 255,  80),
    'scroll_down':     ( 80, 180, 255),
    'idle':            (120, 120, 130),
    'drag':            (  0, 120, 255),
}

def list_cameras(max_test=6):
    available = []
    for i in range(max_test):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            available.append(i)
            cap.release()
    return available

class CameraPreviewThread(QThread):
    frame_ready    = Signal(QImage)
    distance_ready = Signal(float, bool)  
    fingers_ready  = Signal(int,   bool)  
    telemetry_ready = Signal(str,  str)   

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self._running = False
        self._telem_frame = 0

    def stop(self):
        self._running = False

    def run(self):
        self._running = True
        base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
        options = mp_vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_hands=1,
        )
        try:
            detector = mp_vision.HandLandmarker.create_from_options(options)
        except Exception as e:
            print(f"[Preview] detector error: {e}")
            return

        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            detector.close()
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS,          30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)

        while self._running and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame  = cv2.flip(frame, 1)
            ts_ms  = int(time.time() * 1000)
            rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            try:
                result = detector.detect_for_video(
                    mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts_ms)
            except Exception:
                result = None

            display  = rgb.copy()
            has_hand = bool(result and result.hand_landmarks)
            lms      = result.hand_landmarks[0] if has_hand else None

            if lms:
                draw_hand(display, lms)
                self.distance_ready.emit(hand_size(lms), True)
                self.fingers_ready.emit(count_fingers_up(lms), True)
            else:
                self.distance_ready.emit(0.0, False)
                self.fingers_ready.emit(0, False)

            self._telem_frame += 1
            if self._telem_frame % 10 == 0:
                gray = cv2.cvtColor(display, cv2.COLOR_RGB2GRAY)
                mean_b = float(np.mean(gray))
                if mean_b < 55:
                    lighting = "DIM"
                elif mean_b > 200:
                    lighting = "BRIGHT"
                else:
                    lighting = "GOOD"

                h_f, w_f = gray.shape
                corners = [
                    gray[:h_f // 4, :w_f // 4],
                    gray[:h_f // 4, 3 * w_f // 4:],
                    gray[3 * h_f // 4:, :w_f // 4],
                    gray[3 * h_f // 4:, 3 * w_f // 4:],
                ]
                corner_std = float(np.mean([np.std(c) for c in corners]))
                if corner_std < 20:
                    background = "CLEAR"
                elif corner_std < 50:
                    background = "OK"
                else:
                    background = "CLUTTERED"

                self.telemetry_ready.emit(lighting, background)

            h, w, ch = display.shape
            qt_img = QImage(display.data, w, h, ch * w, QImage.Format_RGB888)
            self.frame_ready.emit(qt_img.copy())

        cap.release()
        detector.close()

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
        print(f"[NN:{tag}] Loaded - classes: {list(le.classes_)}")
        return net, le
    except FileNotFoundError:
        print(f"[NN:{tag}] Model not found: {weights_path}")
        return None, None
    except Exception as e:
        print(f"[NN:{tag}] Load error: {e}")
        return None, None

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

def count_vertical_fingers(lms):
    tips_mcps = [(8, 5), (12, 9), (16, 13), (20, 17)]
    count = 0
    for tip, mcp in tips_mcps:
        if not is_finger_extended(lms, tip, tip - 2):
            continue
        dy = lms[mcp].y - lms[tip].y
        dz = abs(lms[tip].z - lms[mcp].z)
        dx = abs(lms[tip].x - lms[mcp].x)
        if dy > dz and dy > dx:
            count += 1
    return count

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

LANDMARK_PINCH_THRESH = 0.03

def landmark_gesture(lms):
    f = fingers_extended(lms)
    if f['index'] and f['middle'] and f['ring'] and not f['pinky']:
        return 'scroll_up'
    if not f['index'] and not f['middle'] and not f['ring'] and not f['pinky']:
        return 'scroll_down'
    if tip_dist(lms, 4, 12) < LANDMARK_PINCH_THRESH:
        return 'left_click'
    if tip_dist(lms, 4, 16) < LANDMARK_PINCH_THRESH:
        return 'right_click'
    index_d = np.hypot(lms[8].x - lms[0].x, lms[8].y - lms[0].y)
    if f['index'] and all(
        np.hypot(lms[t].x - lms[0].x, lms[t].y - lms[0].y) < index_d * 0.85
        for t in (12, 16, 20)
    ):
        return 'move'
    return 'idle'

def is_peace_sign(lms):
    f = fingers_extended(lms)
    return f['index'] and f['middle'] and not f['ring'] and not f['pinky']

def get_game_option(lms, lms2):
    if lms is None or lms2 is None:
        return None
    for fist_hand, finger_hand in [(lms, lms2), (lms2, lms)]:
        if is_fist(fist_hand):
            n = count_vertical_fingers(finger_hand)
            if 1 <= n <= 4:
                return n
    return None

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

def draw_finger_dot(img, lms, gesture, drag_active, cursor_lm=8):
    h, w = img.shape[:2]
    fx, fy = int(lms[cursor_lm].x * w), int(lms[cursor_lm].y * h)
    col = _DOT_CLR['drag'] if drag_active else _DOT_CLR.get(gesture, _DOT_CLR['idle'])
    cv2.circle(img, (fx, fy), 12, col, 2)
    cv2.circle(img, (fx, fy),  4, col, -1)

def _mouse_move(x, y):
    if PYNPUT_AVAILABLE:
        _mouse_ctrl.position = (int(x), int(y))
    else:
        pyautogui.moveTo(int(x), int(y))

def _mouse_left_down():
    if PYNPUT_AVAILABLE:
        _mouse_ctrl.press(_PynputButton.left)
    else:
        pyautogui.mouseDown()

def _mouse_left_up():
    if PYNPUT_AVAILABLE:
        _mouse_ctrl.release(_PynputButton.left)
    else:
        pyautogui.mouseUp()

def _mouse_left_click():
    if PYNPUT_AVAILABLE:
        _mouse_ctrl.click(_PynputButton.left)
    else:
        pyautogui.click()

def _mouse_right_click():
    if PYNPUT_AVAILABLE:
        _mouse_ctrl.click(_PynputButton.right)
    else:
        pyautogui.rightClick()

def _mouse_scroll(amount):
    if PYNPUT_AVAILABLE:
        _mouse_ctrl.scroll(0, amount)
    else:
        pyautogui.scroll(amount)

class HandControllerThread(QThread):

    frame_ready       = Signal(QImage)
    gesture_changed   = Signal(str, str)
    state_changed     = Signal(str)
    error_occurred    = Signal(str)
    game_mode_changed = Signal(str)
    distance_live     = Signal(float, bool)

    slide_progress  = Signal(float, float)
    distance_update = Signal(float, bool, float)
    zone_pick_data  = Signal(str, str, float, float, float, float)
    running_data    = Signal(object)
    stopped_data    = Signal(float, float)

    def __init__(self, camera_index=0, initial_zone='medium', skip_intro=False,
                 model_sources=None, initial_game_mode='mouse'):
        super().__init__()
        self.camera_index      = camera_index
        self.initial_zone      = initial_zone
        self.skip_intro        = skip_intro
        self.initial_game_mode = initial_game_mode
        self._running          = False
        self._paused_event     = threading.Event()
        self._paused_event.set()

        sources = model_sources or {}

        self._mouse_use_landmark = (sources.get('mouse') == 'landmark')
        self._mouse_in_game_enabled = sources.get('mouse_in_game', True)
        cursor_point = sources.get('cursor_point', 'tip')
        self._cursor_lm = 5 if cursor_point == 'knuckle' else 8

        def _pick(mode, default_w, default_e, custom_w, custom_e):
            if sources.get(mode) == 'custom' and os.path.exists(custom_w) and os.path.exists(custom_e):
                print(f"[{mode.upper()}] Using custom model")
                return custom_w, custom_e
            return default_w, default_e

        if self._mouse_use_landmark:
            print("[MOUSE] Using landmark-based gesture detection (no NN)")
            self.mouse_model = self.mouse_le = None
        else:
            mw, me = _pick('mouse', MOUSE_WEIGHTS, MOUSE_ENCODER, MOUSE_WEIGHTS_CUSTOM, MOUSE_ENCODER_CUSTOM)
            self.mouse_model, self.mouse_le = _load_nn(mw, me, 'MOUSE')

        sw, se = _pick('subway', SUBWAY_WEIGHTS, SUBWAY_ENCODER, SUBWAY_WEIGHTS_CUSTOM, SUBWAY_ENCODER_CUSTOM)
        rw, re = _pick('racing', RACING_WEIGHTS, RACING_ENCODER, RACING_WEIGHTS_CUSTOM, RACING_ENCODER_CUSTOM)
        self.subway_model, self.subway_le = _load_nn(sw, se, 'SUBWAY')
        self.racing_model, self.racing_le = _load_nn(rw, re, 'RACING')

        try:
            from logic.app_config import get_key_bindings
            self.ss_key_map = get_key_bindings('subway')
            self.rc_key_map = get_key_bindings('racing')
            self.ow_key_map = get_key_bindings('open_world')
        except Exception:
            self.ss_key_map = {'jump':'up','roll':'down','left':'left','right':'right','space':'space'}
            self.rc_key_map = {'accel':'up','brake':'down','steer_left':'left','steer_right':'right'}
            self.ow_key_map = {'jump':'w','roll':'s','left':'a','right':'d','space':'f'}

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
        self.last_click_t       = 0.0
        self.scroll_entry_t     = None
        self.scroll_active      = False
        self.smooth_x = SCREEN_W / 2
        self.smooth_y = SCREEN_H / 2
        self.meta_hold = {k: None for k in ('start','stop','close','game_opt')}
        self.game_option_pending = None
        self.game_opt_number     = None
        self.active_game_mode    = None
        self._pending_mode       = None

        self.mouse_prev_row    = None
        self.left_click_entry_t = None
        self.right_click_armed  = True
        self.tm_drag_active     = False
        self._devilhorn_mouse   = False

        self.ss_current_zone  = 'neutral'
        self.ss_last_key_t    = 0.0
        self.ss_last_space_t  = 0.0
        self.ss_space_pressed = False
        self.ss_prev_row      = None

        self.rc_held_keys      = set()
        self.rc_prev_row_left  = None
        self.rc_prev_row_right = None
        self.rc_tap_cooldown   = {}

    def _full_reset(self):
        self._release_drag()
        self._rc_release_all()
        self.active_game_mode    = None
        self.app_state           = 'distance_check'
        self.dist_ok_since       = None
        self.smooth_x = SCREEN_W / 2
        self.smooth_y = SCREEN_H / 2
        self.last_click_t        = 0.0
        self.scroll_entry_t      = None
        self.scroll_active       = False
        self.tm_drag_active      = False
        self.mouse_prev_row      = None
        self.left_click_entry_t  = None
        self.right_click_armed   = True
        self.meta_hold           = {k: None for k in self.meta_hold}
        self.game_option_pending = None
        self.ss_current_zone  = 'neutral'
        self.ss_last_key_t    = 0.0
        self.ss_last_space_t  = 0.0
        self.ss_space_pressed = False
        self.ss_prev_row      = None
        self.rc_prev_row_left  = None
        self.rc_prev_row_right = None
        self.rc_tap_cooldown   = {}
        self._devilhorn_mouse  = False

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

    def _release_drag(self):
        if self.tm_drag_active:
            _mouse_left_up()
            self.tm_drag_active = False

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

    def _run_mouse_gesture(self, gesture, lms, now):
        tx, ty = self._map_cursor(lms[self._cursor_lm].x, lms[self._cursor_lm].y)
        self.smooth_x += (tx - self.smooth_x) * MOUSE_SMOOTHING
        self.smooth_y += (ty - self.smooth_y) * MOUSE_SMOOTHING
        _mouse_move(self.smooth_x, self.smooth_y)

        if gesture == 'move':
            self._release_drag()
            self.left_click_entry_t = None
            self.right_click_armed  = True
            self.scroll_entry_t     = None
            self.scroll_active      = False
        elif gesture in ('pre_left_click', 'pre_right_click'):
            pass
        elif gesture == 'left_click':
            self.scroll_entry_t = None
            self.scroll_active  = False
            if self.left_click_entry_t is None:
                self.left_click_entry_t = now
            if (now - self.left_click_entry_t) >= DRAG_HOLD_THRESH and not self.tm_drag_active:
                _mouse_left_down()
                self.tm_drag_active = True
        elif gesture == 'right_click':
            self._release_drag()
            self.left_click_entry_t = None
            if self.right_click_armed and now - self.last_click_t > CLICK_COOLDOWN:
                _mouse_right_click()
                self.last_click_t      = now
                self.right_click_armed = False
            self.scroll_entry_t = None
            self.scroll_active  = False
        elif gesture in ('scroll_up', 'scroll_down'):
            self._release_drag()
            self.left_click_entry_t = None
            self.right_click_armed  = True
            if self.scroll_entry_t is None:
                self.scroll_entry_t = now
                self.scroll_active  = False
            elif not self.scroll_active:
                self.scroll_active = True
            if self.scroll_active:
                _mouse_scroll(SCROLL_SPEED if gesture == 'scroll_up' else -SCROLL_SPEED)
        else:
            self._release_drag()
            self.left_click_entry_t = None
            self.right_click_armed  = True
            self.scroll_entry_t     = None
            self.scroll_active      = False

        if gesture != 'left_click' and self.left_click_entry_t is not None and not self.tm_drag_active:
            held = now - self.left_click_entry_t
            if held < DRAG_HOLD_THRESH and now - self.last_click_t > CLICK_COOLDOWN:
                _mouse_left_click()
                self.last_click_t = now
            self.left_click_entry_t = None

        if gesture != 'right_click':
            self.right_click_armed = True

    def _activate_game_mode(self, opt):
        self._release_drag()
        self._rc_release_all()
        if opt == 1:
            self.active_game_mode = None
            self.game_mode_changed.emit('mouse')
        elif opt == 2:
            self.active_game_mode = 2
            self.ss_current_zone  = 'neutral'
            self.ss_last_key_t    = 0.0
            self.ss_last_space_t  = 0.0
            self.ss_space_pressed = False
            self.ss_prev_row      = None
            self.game_mode_changed.emit('subway')
        elif opt == 3:
            self.active_game_mode  = 3
            self.rc_prev_row_left  = None
            self.rc_prev_row_right = None
            self.game_mode_changed.emit('racing')
        elif opt == 4:
            self.active_game_mode = 4
            self.ss_current_zone  = 'neutral'
            self.ss_last_key_t    = 0.0
            self.ss_last_space_t  = 0.0
            self.ss_space_pressed = False
            self.ss_prev_row      = None
            self.game_mode_changed.emit('open_world')

    def switch_game_mode(self, mode: str):
        self._pending_mode = mode

    def set_camera(self, index):
        self.camera_index = index
        if self._running:
            self.stop(); self.wait()
            self._init_state(); self.start()

    def set_cursor_point(self, point: str):
        self._cursor_lm = 5 if point == 'knuckle' else 8

    def set_key_binding(self, mode: str, gesture: str, key: str):
        if mode == 'subway':
            self.ss_key_map[gesture] = key
        elif mode == 'racing':
            self.rc_key_map[gesture] = key
            self._rc_release_all()
        elif mode == 'open_world':
            self.ow_key_map[gesture] = key

    def set_mouse_in_game(self, enabled: bool):
        self._mouse_in_game_enabled = enabled

    def pause(self):  self._paused_event.clear()
    def resume(self): self._paused_event.set()

    def stop(self):
        self._running = False
        self._paused_event.set()

    def run(self):
        self._running = True
        self._init_state()

        base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
        options      = mp_vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_hands=2,
        )
        detector = mp_vision.HandLandmarker.create_from_options(options)

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

        if self.skip_intro:
            self.chosen_zone = self.initial_zone
            self._set_zone(self.chosen_zone)
            self.app_state = 'running'
            self.state_changed.emit('running')
            _opt_map = {'mouse': 1, 'subway': 2, 'racing': 3, 'open_world': 4}
            _opt = _opt_map.get(self.initial_game_mode, 1)
            if _opt != 1:
                self._activate_game_mode(_opt)
        else:
            self.intro_start_t = time.time()

        thumb_hold_t         = None
        zone_finger_hold     = {}
        game_opt_hold_t      = None
        game_opt_frac        = 0.0

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
            now     = time.time()

            if not has_hand:
                self.mouse_prev_row = None

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
                        self.app_state     = 'guide'
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
                        self.app_state     = 'guide'
                        self.guide_start_t = now
                        thumb_hold_t = None
                        self.state_changed.emit('guide')
                else:
                    if not (lms and is_thumbs_up(lms)): thumb_hold_t = None
                if elapsed >= ZONE_DURATION and self.app_state == 'zone_pick':
                    self._set_zone(self.chosen_zone)
                    self.app_state     = 'guide'
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

                if self._pending_mode is not None:
                    _opt_map = {'mouse': 1, 'subway': 2, 'racing': 3, 'open_world': 4}
                    self._activate_game_mode(_opt_map.get(self._pending_mode, 1))
                    game_opt_hold_t = None; self.game_opt_number = None; game_opt_frac = 0.0
                    self._pending_mode = None

                game_opt_hold_t, self.game_opt_number, game_opt_frac, triggered_opt = \
                    tick_game_opt(lms, lms2, now, game_opt_hold_t, self.game_opt_number)
                if triggered_opt is not None:
                    self._activate_game_mode(triggered_opt)
                    game_opt_hold_t = None; self.game_opt_number = None; game_opt_frac = 0.0

                if self.range_min_x is not None:
                    draw_zone_rect(display,
                                   self.range_min_x, self.range_max_x,
                                   self.range_min_y, self.range_max_y)

                if self.active_game_mode is None:

                    meta_hold_fracs = {k: 0.0 for k in ('start','stop','close','game_opt')}
                    triggered_meta  = None

                    both_open = lms is not None and lms2 is not None and is_open_palm(lms) and is_open_palm(lms2)
                    if both_open:
                        if self.meta_hold['stop'] is None: self.meta_hold['stop'] = now
                        meta_hold_fracs['stop'] = min((now - self.meta_hold['stop']) / HOLD_META, 1.0)
                        if meta_hold_fracs['stop'] >= 1.0: triggered_meta = 'stop'
                    else:
                        self.meta_hold['stop'] = None

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
                        self._release_drag()
                        self.app_state = 'stopped'
                        self.meta_hold = {k: None for k in self.meta_hold}
                        self.state_changed.emit('stopped')
                    elif triggered_meta == 'close':
                        self._release_drag()
                        self._running = False
                        break

                    any_meta = any(v is not None for v in self.meta_hold.values()) or game_opt_frac > 0
                    gesture  = 'idle'

                    if lms and triggered_meta is None and not any_meta:

                        mp_ok = True
                        try:
                            mp_ok = result.handedness[0][0].score >= MP_PRESENCE_THRESH
                        except Exception:
                            pass

                        if not mp_ok:
                            self.mouse_prev_row = None
                            gesture = 'idle'
                        elif self._mouse_use_landmark:
                            gesture = landmark_gesture(lms)
                        else:
                            gesture, _, self.mouse_prev_row = run_nn(
                                lms, self.mouse_prev_row,
                                self.mouse_model, self.mouse_le, MOUSE_CONF_THRESH)

                        self._run_mouse_gesture(gesture, lms, now)

                        draw_hand(display, lms)
                        if lms2: draw_hand(display, lms2)
                        draw_finger_dot(display, lms, gesture, self.tm_drag_active, self._cursor_lm)

                    else:
                        self._release_drag()
                        self.scroll_entry_t = None
                        self.scroll_active  = False
                        if lms:  draw_hand(display, lms)
                        if lms2: draw_hand(display, lms2)

                    _act = {
                        'move':            'Moving cursor',
                        'pre_left_click':  'Pre left click',
                        'left_click':      'Click / Drag',
                        'pre_right_click': 'Pre right click',
                        'right_click':     'Right click',
                        'scroll_up':       'Scroll up',
                        'scroll_down':     'Scroll down',
                        'idle':            'Idle',
                    }
                    self.gesture_changed.emit(gesture.upper().replace('_', ' '), _act.get(gesture, gesture))
                    self.running_data.emit({
                        'mode': 'mouse',
                        'gesture': gesture,
                        'drag': self.tm_drag_active,
                        'click_entry': self.left_click_entry_t,
                        'meta': meta_hold_fracs,
                        'game_opt_num': self.game_opt_number or 0,
                        'game_opt_frac': game_opt_frac,
                    })

                elif self.active_game_mode == 2:

                    lms_left_dh = lms_right_dh = None
                    if result and result.hand_landmarks:
                        lms_left_dh, lms_right_dh = split_hands(result)

                    devil_horn = (self._mouse_in_game_enabled and
                                  lms_left_dh is not None and is_metal_sign(lms_left_dh))
                    if devil_horn != self._devilhorn_mouse:
                        self.mouse_prev_row     = None
                        self.left_click_entry_t = None
                        self.right_click_armed  = True
                        self.scroll_entry_t     = None
                        self.scroll_active      = False
                        if not devil_horn:
                            self._release_drag()
                    self._devilhorn_mouse = devil_horn

                    if devil_horn:
                        gesture_m = 'idle'
                        if lms_right_dh:
                            gesture_m, _, self.mouse_prev_row = run_nn(
                                lms_right_dh, self.mouse_prev_row,
                                self.mouse_model, self.mouse_le, MOUSE_CONF_THRESH)
                            self._run_mouse_gesture(gesture_m, lms_right_dh, now)
                            draw_hand(display, lms_right_dh)
                            draw_finger_dot(display, lms_right_dh, gesture_m, self.tm_drag_active, self._cursor_lm)
                        draw_hand(display, lms_left_dh, (255, 100, 0))
                        self.gesture_changed.emit(
                            f'MOUSE: {gesture_m.upper().replace("_", " ")}', 'Devil horn mouse mode')
                        self.running_data.emit({
                            'mode': 'subway', 'devilhorn': True,
                            'gesture': gesture_m,
                            'game_opt_num': self.game_opt_number or 0,
                            'game_opt_frac': game_opt_frac,
                            'meta': {'game_opt': game_opt_frac},
                        })
                    else:
                        gesture_ss = 'none'; conf_ss = 0.0
                        if lms:
                            gesture_ss, conf_ss, self.ss_prev_row = run_nn(
                                lms, self.ss_prev_row, self.subway_model, self.subway_le, SS_CONFIDENCE_THRESH)
                            if gesture_ss == 'space':
                                if not self.ss_space_pressed and (now - self.ss_last_space_t) > SS_SPACE_COOLDOWN:
                                    pyautogui.press(self.ss_key_map.get('space', 'space'))
                                    self.ss_space_pressed = True; self.ss_last_space_t = now
                                self.ss_current_zone = 'neutral'
                            else:
                                self.ss_space_pressed = False
                                if gesture_ss in self.ss_key_map:
                                    if gesture_ss != self.ss_current_zone and (now - self.ss_last_key_t) > SS_KEY_COOLDOWN:
                                        pyautogui.press(self.ss_key_map[gesture_ss])
                                        self.ss_last_key_t = now; self.ss_current_zone = gesture_ss
                                else:
                                    self.ss_current_zone = 'neutral'
                        else:
                            self.ss_prev_row = None

                        if lms:  draw_hand(display, lms)
                        if lms2: draw_hand(display, lms2)

                        _ss_action = {
                            'jump':  'Arrow UP',
                            'roll':  'Arrow DOWN',
                            'left':  'Arrow LEFT',
                            'right': 'Arrow RIGHT',
                            'space': 'SPACE / Jump',
                            'idle':  'Idle',
                            'none':  'Idle',
                        }
                        self.gesture_changed.emit(gesture_ss.upper(), _ss_action.get(gesture_ss, gesture_ss))
                        self.running_data.emit({
                            'mode': 'subway',
                            'gesture': gesture_ss,
                            'conf': conf_ss,
                            'game_opt_num': self.game_opt_number or 0,
                            'game_opt_frac': game_opt_frac,
                            'meta': {'game_opt': game_opt_frac},
                        })

                elif self.active_game_mode == 3:

                    lms_left = lms_right = None
                    if result and result.hand_landmarks:
                        lms_left, lms_right = split_hands(result)

                    devil_horn = (self._mouse_in_game_enabled and
                                  lms_left is not None and is_metal_sign(lms_left))
                    if devil_horn != self._devilhorn_mouse:
                        self.mouse_prev_row     = None
                        self.left_click_entry_t = None
                        self.right_click_armed  = True
                        self.scroll_entry_t     = None
                        self.scroll_active      = False
                        if not devil_horn:
                            self._release_drag()
                        self._rc_release_all()
                    self._devilhorn_mouse = devil_horn

                    if devil_horn:
                        gesture_m = 'idle'
                        if lms_right:
                            gesture_m, _, self.mouse_prev_row = run_nn(
                                lms_right, self.mouse_prev_row,
                                self.mouse_model, self.mouse_le, MOUSE_CONF_THRESH)
                            self._run_mouse_gesture(gesture_m, lms_right, now)
                            draw_hand(display, lms_right)
                            draw_finger_dot(display, lms_right, gesture_m, self.tm_drag_active, self._cursor_lm)
                        draw_hand(display, lms_left, (255, 100, 0))
                        self.gesture_changed.emit(
                            f'MOUSE: {gesture_m.upper().replace("_", " ")}', 'Devil horn mouse mode')
                        self.running_data.emit({
                            'mode': 'racing', 'devilhorn': True,
                            'gesture': gesture_m,
                            'game_opt_num': self.game_opt_number or 0,
                            'game_opt_frac': game_opt_frac,
                            'meta': {'game_opt': game_opt_frac},
                        })
                    else:
                        if lms_left  is None: self.rc_prev_row_left  = None
                        if lms_right is None: self.rc_prev_row_right = None
                        desired   = set(); angle = 0.0; steer_dir = 'none'
                        accel = brake = horn = camera_tapped = False
                        gest_l = gest_r = 'none'; conf_l = conf_r = 0.0
                        if lms_left:
                            gest_l, conf_l, self.rc_prev_row_left = run_nn(
                                lms_left, self.rc_prev_row_left, self.racing_model, self.racing_le, RC_CONF_THRESH)
                        if lms_right:
                            gest_r, conf_r, self.rc_prev_row_right = run_nn(
                                lms_right, self.rc_prev_row_right, self.racing_model, self.racing_le, RC_CONF_THRESH)

                        accel = gest_r == 'thumb'
                        brake = gest_l == 'thumb'
                        horn  = gest_r == 'index_middle'

                        if accel: desired.add(self.rc_key_map.get('accel', 'up'))
                        if brake: desired.add(self.rc_key_map.get('brake', 'down'))
                        if horn:  desired.add(self.rc_key_map.get('horn', 'h'))

                        camera_key = self.rc_key_map.get('camera', 'c')
                        if gest_l == 'index_middle':
                            last_tap = self.rc_tap_cooldown.get(camera_key, 0)
                            if now - last_tap >= RC_TAP_COOLDOWN:
                                pyautogui.press(camera_key)
                                self.rc_tap_cooldown[camera_key] = now
                                camera_tapped = True

                        if lms_left and lms_right:
                            angle = get_steer_angle(lms_left, lms_right)
                            if   angle < -RC_STEER_DEADZONE: steer_dir = 'left'
                            elif angle >  RC_STEER_DEADZONE: steer_dir = 'right'
                        if steer_dir == 'left':  desired.add(self.rc_key_map.get('steer_left',  'left'))
                        if steer_dir == 'right': desired.add(self.rc_key_map.get('steer_right', 'right'))
                        self._rc_set_held_keys(desired)

                        if lms_left:  draw_hand(display, lms_left,  (255, 180, 80))
                        if lms_right: draw_hand(display, lms_right, (255, 80, 180))

                        _sl  = {'left': 'LEFT ←', 'right': 'RIGHT →', 'none': 'Straight'}[steer_dir]
                        _ped = ' · ACCEL' if accel else (' · BRAKE' if brake else '')
                        _extras = (' · HORN' if horn else '') + (' · CAM' if camera_tapped else '')
                        _act = ('Accelerate' if accel else ('Brake' if brake else 'Idle')) + f'  ·  Steer {_sl}'
                        self.gesture_changed.emit(f'STEER {_sl}{_ped}{_extras}', _act)
                        self.running_data.emit({
                            'mode': 'racing',
                            'steer': steer_dir,
                            'angle': round(angle, 1),
                            'accel': accel,
                            'brake': brake,
                            'horn': horn,
                            'camera': camera_tapped,
                            'gest_l': gest_l, 'conf_l': round(conf_l, 2),
                            'gest_r': gest_r, 'conf_r': round(conf_r, 2),
                            'game_opt_num': self.game_opt_number or 0,
                            'game_opt_frac': game_opt_frac,
                            'meta': {'game_opt': game_opt_frac},
                        })

                elif self.active_game_mode == 4:
                    gesture_ow = 'none'; conf_ow = 0.0
                    if lms:
                        gesture_ow, conf_ow, self.ss_prev_row = run_nn(
                            lms, self.ss_prev_row, self.subway_model, self.subway_le, SS_CONFIDENCE_THRESH)
                        if gesture_ow == 'space':
                            if not self.ss_space_pressed and (now - self.ss_last_space_t) > SS_SPACE_COOLDOWN:
                                pyautogui.press(self.ow_key_map.get('space', 'f'))
                                self.ss_space_pressed = True; self.ss_last_space_t = now
                            self.ss_current_zone = 'neutral'
                        else:
                            self.ss_space_pressed = False
                            if gesture_ow in self.ow_key_map:
                                if gesture_ow != self.ss_current_zone and (now - self.ss_last_key_t) > SS_KEY_COOLDOWN:
                                    pyautogui.press(self.ow_key_map[gesture_ow])
                                    self.ss_last_key_t = now; self.ss_current_zone = gesture_ow
                            else:
                                self.ss_current_zone = 'neutral'
                    else:
                        self.ss_prev_row = None
                    if lms:  draw_hand(display, lms)
                    if lms2: draw_hand(display, lms2)
                    _ow_act = {
                        'jump': self.ow_key_map.get('jump','w').upper(),
                        'roll': self.ow_key_map.get('roll','s').upper(),
                        'left': self.ow_key_map.get('left','a').upper(),
                        'right':self.ow_key_map.get('right','d').upper(),
                        'space':self.ow_key_map.get('space','f').upper(),
                        'idle': 'Idle', 'none': 'Idle',
                    }
                    self.gesture_changed.emit(gesture_ow.upper(), _ow_act.get(gesture_ow, gesture_ow))
                    self.running_data.emit({
                        'mode': 'open_world',
                        'gesture': gesture_ow,
                        'conf': conf_ow,
                        'game_opt_num': self.game_opt_number or 0,
                        'game_opt_frac': game_opt_frac,
                        'meta': {'game_opt': game_opt_frac},
                    })

                self.distance_live.emit(hand_size(lms) if lms else 0.0, lms is not None)

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
                self.distance_live.emit(hand_size(lms) if lms else 0.0, lms is not None)

            h_img, w_img, ch = display.shape
            qt_img = QImage(display.data, w_img, h_img, ch * w_img, QImage.Format_RGB888)
            self.frame_ready.emit(qt_img.copy())

        self._release_drag()
        self._rc_release_all()
        _stop[0] = True
        det.join(timeout=2.0)
        cap.release()
        detector.close()
        self.state_changed.emit('idle')

