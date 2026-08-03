import os
import platform
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
import time
import threading

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

_IS_WINDOWS = platform.system() == 'Windows'

def _open_camera(index):
    if _IS_WINDOWS:
        return cv2.VideoCapture(index, cv2.CAP_DSHOW)
    return cv2.VideoCapture(index)

def _open_camera_retry(index, attempts=5, delay=0.4):
    cap = None
    for attempt in range(attempts):
        cap = _open_camera(index)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                return cap
        cap.release()
        if attempt < attempts - 1:
            time.sleep(delay)
    return cap

try:
    import torch
    import torch.nn as nn
    import joblib
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from logic.hand_utils import (
    SCREEN_W, SCREEN_H,
    ZONE_PRESETS,
    TARGET_DIST, DIST_TOL, DIST_OK_HOLD,
    INTRO_DURATION, ZONE_INTRO_DURATION, ZONE_DURATION, GUIDE_DURATION,
    SKIP_LOCKOUT, HOLD_META, HOLD_CLOSE, HOLD_GAME, ZONE_CONFIRM_TIME,
    hand_size, count_fingers_up, is_thumbs_up, is_open_palm,
    is_fist, is_peace_sign, is_devil_horn, get_game_option, tick_game_opt,
    split_hands, draw_hand, draw_zone_rect, draw_finger_dot,
    landmark_gesture,
)
from logic.gesture_net import GestureNet, load_nn, run_nn
from logic.app_config import CONTROL_GESTURE_DEFAULTS

from logic.modes.mouse_mode      import MouseModeMixin
from logic.modes.subway_mode     import SubwayModeMixin
from logic.modes.racing_mode     import RacingModeMixin
from logic.modes.open_world_mode import OpenWorldModeMixin, OW_GESTURE_KEY_MAP
from logic.modes.custom_mode     import CustomModeMixin
from logic.modes.air_hockey_mode import AirHockeyModeMixin

import sys as _sys
if getattr(_sys, 'frozen', False):
    LOGIC_DIR       = os.path.join(_sys._MEIPASS, 'logic')
    _CUSTOM_DATA_DIR = os.path.join(os.path.expanduser('~'), '.handmouse', 'data')
else:
    LOGIC_DIR       = os.path.dirname(os.path.abspath(__file__))
    _CUSTOM_DATA_DIR = os.path.join(LOGIC_DIR, 'data')
DATA_DIR   = os.path.join(LOGIC_DIR, 'data')
CUSTOM_DIR = os.path.join(_CUSTOM_DATA_DIR, 'custom')
MODEL_PATH = os.path.join(DATA_DIR, 'hand_landmarker.task')

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

OW_MODEL_PATH = os.path.join(DATA_DIR, 'hagridv2_gesture_recognizer.task')

MP_PRESENCE_THRESH   = 0.7
CONFIRM_CLOSE_HOLD   = 3.0

_MODE_SWITCH_LOCK_DEFAULTS = {
    'mouse':      False,
    'subway':     False,
    'racing':     True,
    'open_world': True,
    'air_hockey': True,
}

_MODE_NAME_BY_OPT = {
    None: 'mouse', 2: 'subway', 3: 'racing',
    4: 'open_world', 5: 'custom', 6: 'air_hockey',
}

def list_cameras(max_test=6):
    available = []
    devnull  = os.open(os.devnull, os.O_WRONLY)
    saved_fd = os.dup(2)
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        for i in range(max_test):
            cap = _open_camera(i)
            if cap.isOpened():
                available.append(i)
                cap.release()
    finally:
        os.dup2(saved_fd, 2)
        os.close(saved_fd)
    return available

class CameraPreviewThread(QThread):
    frame_ready     = Signal(QImage)
    distance_ready  = Signal(float, bool)
    fingers_ready   = Signal(int,   bool)
    telemetry_ready = Signal(str,   str)
    error_occurred  = Signal(str)

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index  = camera_index
        self._running      = False
        self._telem_frame  = 0

    def stop(self):
        self._running = False

    def run(self):
        import numpy as np
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

        cap = _open_camera_retry(self.camera_index)
        if not cap.isOpened():
            cap.release()
            detector.close()
            self.error_occurred.emit(f"Cannot open camera {self.camera_index}")
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS,          30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)

        try:
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
                    gray    = cv2.cvtColor(display, cv2.COLOR_RGB2GRAY)
                    mean_b  = float(np.mean(gray))
                    lighting = "DIM" if mean_b < 55 else ("BRIGHT" if mean_b > 200 else "GOOD")

                    h_f, w_f = gray.shape
                    corners = [
                        gray[:h_f//4, :w_f//4],
                        gray[:h_f//4, 3*w_f//4:],
                        gray[3*h_f//4:, :w_f//4],
                        gray[3*h_f//4:, 3*w_f//4:],
                    ]
                    corner_std  = float(np.mean([np.std(c) for c in corners]))
                    background  = "CLEAR" if corner_std < 20 else ("OK" if corner_std < 50 else "CLUTTERED")
                    self.telemetry_ready.emit(lighting, background)

                h, w, ch = display.shape
                qt_img = QImage(display.data, w, h, ch * w, QImage.Format_RGB888)
                self.frame_ready.emit(qt_img.copy())
        except Exception as e:
            print(f"[Preview] Tracking loop crashed: {e}")
        finally:
            try:
                cap.release()
            except Exception:
                pass
            try:
                detector.close()
            except Exception:
                pass

class HandControllerThread(
    MouseModeMixin, SubwayModeMixin, RacingModeMixin, OpenWorldModeMixin, CustomModeMixin,
    AirHockeyModeMixin,
    QThread
):
    frame_ready       = Signal(QImage)
    gesture_changed   = Signal(str, str)
    state_changed     = Signal(str)
    error_occurred    = Signal(str)
    game_mode_changed = Signal(str)
    distance_live     = Signal(float, bool)
    nn_latency        = Signal(float)
    close_requested   = Signal()

    slide_progress  = Signal(float, float)
    distance_update = Signal(float, bool, float)
    zone_pick_data  = Signal(str, str, float, float, float, float)
    running_data    = Signal(object)
    stopped_data    = Signal(float, float)

    def __init__(self, camera_index=0, initial_zone='large', skip_intro=False,
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

        self._mouse_in_game_enabled = sources.get('mouse_in_game', True)
        cursor_point                = sources.get('cursor_point', 'knuckle')
        self._cursor_lm             = 5 if cursor_point == 'knuckle' else 8
        self._cursor_point          = cursor_point
        self._right_half_mode       = False
        self._mouse_side            = sources.get('mouse_side', 'right')
        self._custom_meta_gestures_enabled = sources.get('custom_meta_gestures', True)
        self._mode_switch_locks = dict(sources.get('mode_locks', {}))
        self._control_gestures = dict(CONTROL_GESTURE_DEFAULTS)
        self._control_gestures.update(sources.get('control_gestures', {}))

        def _pick(mode, default_w, default_e, custom_w, custom_e):
            if sources.get(mode) == 'custom' and os.path.exists(custom_w) and os.path.exists(custom_e):
                print(f"[{mode.upper()}] Using custom model")
                return custom_w, custom_e
            return default_w, default_e

        mw, me = _pick('mouse', MOUSE_WEIGHTS, MOUSE_ENCODER, MOUSE_WEIGHTS_CUSTOM, MOUSE_ENCODER_CUSTOM)
        self.mouse_model, self.mouse_le = load_nn(mw, me, tag='MOUSE')

        sw, se = _pick('subway', SUBWAY_WEIGHTS, SUBWAY_ENCODER, SUBWAY_WEIGHTS_CUSTOM, SUBWAY_ENCODER_CUSTOM)
        rw, re = _pick('racing', RACING_WEIGHTS, RACING_ENCODER, RACING_WEIGHTS_CUSTOM, RACING_ENCODER_CUSTOM)
        self.subway_model, self.subway_le = load_nn(sw, se, tag='SUBWAY')
        self.racing_model, self.racing_le = load_nn(rw, re, tag='RACING')

        try:
            from logic.app_config import get_key_bindings
            self.ss_key_map = get_key_bindings('subway')
            self.rc_key_map = get_key_bindings('racing')
            self.ow_key_map = get_key_bindings('open_world')
        except Exception:
            self.ss_key_map = {'jump': 'up', 'roll': 'down', 'left': 'left', 'right': 'right', 'space': 'space'}
            self.rc_key_map = {'accel': 'up', 'brake': 'down', 'steer_left': 'left', 'steer_right': 'right'}
            self.ow_key_map = {}

        self.custom_mode_id = ''
        self.custom_model    = None
        self.custom_le       = None
        self.custom_key_map  = {}
        try:
            from logic.app_config import get_selected_custom_mode_id
            self._load_custom_model(get_selected_custom_mode_id())
        except Exception:
            pass

        self._init_state()

    def _load_custom_model(self, mode_id: str):
        self.custom_mode_id = mode_id or ''
        self.custom_model   = None
        self.custom_le      = None
        self.custom_key_map = {}
        if not mode_id:
            return
        try:
            from logic.app_config import get_custom_mode_dir, get_key_bindings
            mode_dir = get_custom_mode_dir(mode_id)
            weights  = os.path.join(mode_dir, 'gesture_model_best.pt')
            encoder  = os.path.join(mode_dir, 'label_encoder.pkl')
            self.custom_model, self.custom_le = load_nn(weights, encoder, tag='CUSTOM')
            self.custom_key_map = get_key_bindings(f'custom_{mode_id}')
        except Exception:
            pass

    def set_custom_mode(self, mode_id: str):
        self._load_custom_model(mode_id)
        self.custom_prev_row = None
        self._custom_release_all()

    def _init_state(self):
        self.app_state          = 'intro'
        self.intro_start_t      = None
        self.zone_intro_start_t = None
        self.zone_start_t       = None
        self.guide_start_t      = None
        self.chosen_zone        = 'large'
        self.dist_ok_since      = None
        self.range_min_x = self.range_max_x = None
        self.range_min_y = self.range_max_y = None
        self.last_left_click_t  = 0.0
        self.last_right_click_t = 0.0
        self.scroll_entry_t     = None
        self.scroll_active      = False
        self.smooth_x = SCREEN_W / 2
        self.smooth_y = SCREEN_H / 2
        self.meta_hold = {k: None for k in ('start', 'stop', 'close', 'game_opt')}
        self.game_option_pending = None
        self.game_opt_number     = None
        self.active_game_mode    = None
        self._pending_mode       = None

        self.mouse_prev_row      = None
        self.left_click_entry_t  = None
        self._pending_left_click = False
        self.right_click_armed   = True
        self.right_click_entry_t = None
        self.tm_drag_active      = False
        self._drag_release_votes = 0
        self._devilhorn_mouse    = False

        self.ss_current_zone  = 'neutral'
        self.ss_last_key_t    = 0.0
        self.ss_last_space_t  = 0.0
        self.ss_space_pressed = False
        self.ss_prev_row      = None

        self.rc_held_keys      = set()
        self.rc_prev_row_left  = None
        self.rc_prev_row_right = None
        self.rc_tap_cooldown   = {}

        self.ow_gesture_start_times   = {}
        self.ow_held_keys             = set()
        self.ow_rel_mouse_active      = False
        self.ow_rel_mouse_prev_pos    = None
        self._current_frame_t         = 0.0
        self._confirm_close_from      = None
        self._confirm_close_hold_t    = None
        self._ow_rebuild_eff_map()

        self.custom_prev_row = None
        self.custom_held_key = None

        self._init_ah_state()

    def _full_reset(self):
        self._release_drag()
        self._rc_release_all()
        self._ow_release_all()
        self._custom_release_all()
        self._ah_release_all()
        self.active_game_mode    = None
        self.app_state           = 'distance_check'
        self.dist_ok_since       = None
        self.smooth_x = SCREEN_W / 2
        self.smooth_y = SCREEN_H / 2
        self.last_left_click_t  = 0.0
        self.last_right_click_t = 0.0
        self.scroll_entry_t      = None
        self.scroll_active       = False
        self.tm_drag_active      = False
        self._drag_release_votes = 0
        self.mouse_prev_row      = None
        self.left_click_entry_t  = None
        self._pending_left_click = False
        self.right_click_armed   = True
        self.right_click_entry_t = None
        self.meta_hold           = {k: None for k in self.meta_hold}
        self.game_option_pending = None
        self.ss_current_zone  = 'neutral'
        self.ss_last_key_t    = 0.0
        self.ss_last_space_t  = 0.0
        self.ss_space_pressed = False
        self.ss_prev_row      = None
        self.rc_prev_row_left      = None
        self.rc_prev_row_right     = None
        self.rc_tap_cooldown       = {}
        self._devilhorn_mouse      = False
        self.ow_rel_mouse_active   = False
        self.ow_rel_mouse_prev_pos = None
        self.custom_prev_row       = None

    def _set_zone(self, zone_name):
        size = ZONE_PRESETS.get(zone_name, 0.55)
        if self._mouse_side == 'right':
            self.range_min_x = 0.5
            self.range_max_x = 0.5 + size
        elif self._mouse_side == 'left':
            self.range_min_x = 0.5 - size
            self.range_max_x = 0.5
        else:
            half = size / 2
            self.range_min_x = 0.5 - half
            self.range_max_x = 0.5 + half
        half_y = size / 2
        self.range_min_y = 0.5 - half_y
        self.range_max_y = 0.5 + half_y

    def _map_cursor(self, tx, ty):
        import numpy as np
        sx = self.range_max_x - self.range_min_x
        sy = self.range_max_y - self.range_min_y
        rx = 0.5 if sx < 0.01 else float(np.clip((tx - self.range_min_x) / sx, 0, 1))
        ry = 0.5 if sy < 0.01 else float(np.clip((ty - self.range_min_y) / sy, 0, 1))
        return rx * SCREEN_W, ry * SCREEN_H

    def _tick_control_gestures(self, mode_name, lms, lms2, now, release_fn):
        fracs = {'start': 0.0, 'stop': 0.0, 'close': 0.0}
        if not self._control_gestures.get(mode_name, False):
            self.meta_hold['start'] = None
            self.meta_hold['stop']  = None
            self.meta_hold['close'] = None
            return fracs, False

        both_open = lms is not None and lms2 is not None and is_open_palm(lms) and is_open_palm(lms2)
        if both_open:
            if self.meta_hold['stop'] is None: self.meta_hold['stop'] = now
            fracs['stop'] = min((now - self.meta_hold['stop']) / HOLD_META, 1.0)
            if fracs['stop'] >= 1.0:
                release_fn()
                self.app_state = 'stopped'
                self.meta_hold = {k: None for k in self.meta_hold}
                self.state_changed.emit('stopped')
                return fracs, True
        else:
            self.meta_hold['stop'] = None

        both_peace = lms and lms2 and is_peace_sign(lms) and is_peace_sign(lms2)
        if both_peace:
            if self.meta_hold['start'] is None: self.meta_hold['start'] = now
            fracs['start'] = min((now - self.meta_hold['start']) / HOLD_META, 1.0)
        else:
            self.meta_hold['start'] = None

        game_opt_now = get_game_option(lms, lms2)
        both_fists   = lms and lms2 and is_fist(lms) and is_fist(lms2)
        if both_fists and game_opt_now is None:
            if self.meta_hold['close'] is None: self.meta_hold['close'] = now
            fracs['close'] = min((now - self.meta_hold['close']) / HOLD_CLOSE, 1.0)
            if fracs['close'] >= 1.0:
                release_fn()
                self._confirm_close_from   = 'running'
                self._confirm_close_hold_t = None
                self.meta_hold = {k: None for k in self.meta_hold}
                self.app_state = 'confirm_close'
                self.state_changed.emit('confirm_close')
                return fracs, True
        else:
            self.meta_hold['close'] = None

        return fracs, False

    def set_control_gestures_enabled(self, mode: str, enabled: bool):
        self._control_gestures[mode] = enabled

    def _activate_game_mode(self, opt):
        self._release_drag()
        self._rc_release_all()
        self._custom_release_all()
        self._ah_release_all()
        if opt == 1:
            self.active_game_mode = None
            self._right_half_mode = False
            self._set_zone(self.chosen_zone)
            self.game_mode_changed.emit('mouse')
        elif opt == 2:
            self.active_game_mode = 2
            self._right_half_mode = False
            self._set_zone(self.chosen_zone)
            self.ss_current_zone  = 'neutral'
            self.ss_last_key_t    = 0.0
            self.ss_last_space_t  = 0.0
            self.ss_space_pressed = False
            self.ss_prev_row      = None
            self.game_mode_changed.emit('subway')
        elif opt == 3:
            self.active_game_mode  = 3
            self._right_half_mode  = False
            self._set_zone(self.chosen_zone)
            self.rc_prev_row_left  = None
            self.rc_prev_row_right = None
            self.game_mode_changed.emit('racing')
        elif opt == 4:
            self.active_game_mode   = 4
            self._right_half_mode   = False
            self._set_zone(self.chosen_zone)
            self._ow_release_all()
            self._devilhorn_mouse   = False
            self.mouse_prev_row     = None
            self.left_click_entry_t = None
            self._pending_left_click = False
            self.right_click_armed  = True
            self.scroll_entry_t     = None
            self.scroll_active      = False
            self.game_mode_changed.emit('open_world')
        elif opt == 5:
            self.active_game_mode  = 5
            self._right_half_mode  = False
            self._set_zone(self.chosen_zone)
            self._devilhorn_mouse   = False
            self.custom_prev_row    = None
            self.mouse_prev_row     = None
            self.left_click_entry_t = None
            self._pending_left_click = False
            self.right_click_armed  = True
            self.scroll_entry_t     = None
            self.scroll_active      = False
            self.game_mode_changed.emit('custom')
        elif opt == 6:
            self.active_game_mode  = 6
            self._right_half_mode  = False
            self._set_zone(self.chosen_zone)
            self._init_ah_state()
            self._devilhorn_mouse   = False
            self.mouse_prev_row     = None
            self.left_click_entry_t = None
            self._pending_left_click = False
            self.right_click_armed  = True
            self.scroll_entry_t     = None
            self.scroll_active      = False
            self.game_mode_changed.emit('air_hockey')

    def switch_game_mode(self, mode: str):
        self._pending_mode = mode

    def set_camera(self, index):
        self.camera_index = index

    def set_cursor_point(self, point: str):
        self._cursor_point = point
        self._cursor_lm    = 5 if point == 'knuckle' else 8
        self._set_zone(self.chosen_zone)

    def set_zone(self, zone: str):
        self.chosen_zone = zone
        self._set_zone(zone)

    def set_model_source(self, mode: str, source: str):
        def _paths(default_w, default_e, custom_w, custom_e):
            if source == 'custom' and os.path.exists(custom_w) and os.path.exists(custom_e):
                return custom_w, custom_e
            return default_w, default_e
        if mode == 'mouse':
            w, e = _paths(MOUSE_WEIGHTS, MOUSE_ENCODER, MOUSE_WEIGHTS_CUSTOM, MOUSE_ENCODER_CUSTOM)
            self.mouse_model, self.mouse_le = load_nn(w, e, tag='MOUSE')
            self.mouse_prev_row = None
        elif mode == 'subway':
            w, e = _paths(SUBWAY_WEIGHTS, SUBWAY_ENCODER, SUBWAY_WEIGHTS_CUSTOM, SUBWAY_ENCODER_CUSTOM)
            self.subway_model, self.subway_le = load_nn(w, e, tag='SUBWAY')
            self.ss_prev_row = None
        elif mode == 'racing':
            w, e = _paths(RACING_WEIGHTS, RACING_ENCODER, RACING_WEIGHTS_CUSTOM, RACING_ENCODER_CUSTOM)
            self.racing_model, self.racing_le = load_nn(w, e, tag='RACING')
            self.rc_prev_row_left = None
            self.rc_prev_row_right = None

    def set_key_binding(self, mode: str, gesture: str, key: str):
        if mode == 'subway':
            self.ss_key_map[gesture] = key
        elif mode == 'racing':
            self.rc_key_map[gesture] = key
            self._rc_release_all()
        elif mode == 'open_world':
            self.ow_key_map[gesture] = key
            self._ow_rebuild_eff_map()
        elif mode.startswith('custom_') and mode == f'custom_{self.custom_mode_id}':
            self.custom_key_map[gesture] = key
            self._custom_release_all()

    def set_mouse_in_game(self, enabled: bool):
        self._mouse_in_game_enabled = enabled

    def set_custom_meta_gestures_enabled(self, enabled: bool):
        self._custom_meta_gestures_enabled = enabled

    def set_mode_switch_locked(self, mode: str, locked: bool):
        self._mode_switch_locks[mode] = locked

    def set_mouse_side(self, side: str):
        self._mouse_side = side
        self._set_zone(self.chosen_zone)

    def pause(self):
        self.app_state = 'stopped'
        self.meta_hold = {k: None for k in self.meta_hold}
        self.state_changed.emit('stopped')

    def resume(self):
        if self.app_state == 'stopped':
            self.app_state = 'running'
            self.meta_hold = {k: None for k in self.meta_hold}
            self.state_changed.emit('running')

    def stop(self):
        self._running = False
        self._paused_event.set()

    def run(self):
        import numpy as np
        self._running = True
        self._init_state()

        _devnull  = os.open(os.devnull, os.O_WRONLY)
        _saved_fd = os.dup(2)
        os.dup2(_devnull, 2)
        os.close(_devnull)
        _init_err = None
        ow_recognizer = None
        try:
            num_hands = 4 if self.initial_game_mode == 'air_hockey' else 2
            base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
            options      = mp_vision.HandLandmarkerOptions(
                base_options=base_options,
                running_mode=mp_vision.RunningMode.VIDEO,
                num_hands=num_hands,
            )
            detector = mp_vision.HandLandmarker.create_from_options(options)

            if os.path.exists(OW_MODEL_PATH):
                try:
                    ow_opts = mp_vision.GestureRecognizerOptions(
                        base_options=mp_python.BaseOptions(model_asset_path=OW_MODEL_PATH),
                        running_mode=mp_vision.RunningMode.VIDEO,
                        num_hands=2,
                    )
                    ow_recognizer = mp_vision.GestureRecognizer.create_from_options(ow_opts)
                except Exception as e:
                    print(f'[OW] Could not load GestureRecognizer: {e}')
        except Exception as e:
            _init_err = str(e)
        finally:
            os.dup2(_saved_fd, 2)
            os.close(_saved_fd)

        if _init_err:
            self.error_occurred.emit(f"Hand tracker init failed: {_init_err}")
            return

        if ow_recognizer is not None:
            print('[OW] GestureRecognizer loaded')

        cap = _open_camera_retry(self.camera_index)
        if not cap.isOpened():
            self.error_occurred.emit(f"Cannot open camera {self.camera_index}")
            cap.release()
            detector.close()
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS,          30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)

        _latest_frame      = [None]
        _latest_ts         = [0]
        _latest_result     = [None]
        _latest_result_ts  = [0.0]
        _latest_ow_result  = [None]
        _latest_rgb        = [None]
        _latest_rgb_ts     = [0]
        _fl  = threading.Lock()
        _rl  = threading.Lock()
        _owl = threading.Lock()
        _rgl = threading.Lock()
        _stop = [False]

        def _detect_landmarks():
            last_ts = -1
            while not _stop[0]:
                with _fl:
                    frame = _latest_frame[0]
                    ts    = _latest_ts[0]
                if frame is None or ts == last_ts:
                    time.sleep(0.001); continue
                last_ts = ts
                rgb = frame
                try:
                    result = detector.detect_for_video(
                        mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts)
                except Exception as e:
                    print(f"[MediaPipe] detection error: {e}")
                    continue
                with _rl:
                    _latest_result[0]    = result
                    _latest_result_ts[0] = ts / 1000.0
                with _rgl:
                    _latest_rgb[0]    = rgb
                    _latest_rgb_ts[0] = ts

        def _detect_gestures():
            last_ts = -1
            was_active = False
            while not _stop[0]:
                if ow_recognizer is None or self.active_game_mode != 4:
                    if was_active:
                        with _owl: _latest_ow_result[0] = None
                        was_active = False
                    time.sleep(0.03); continue
                was_active = True
                with _rgl:
                    rgb = _latest_rgb[0]
                    ts  = _latest_rgb_ts[0]
                if rgb is None or ts == last_ts:
                    time.sleep(0.001); continue
                last_ts = ts
                try:
                    ow_r = ow_recognizer.recognize_for_video(
                        mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts)
                except Exception:
                    ow_r = None
                with _owl: _latest_ow_result[0] = ow_r

        det    = threading.Thread(target=_detect_landmarks, daemon=True)
        det_ow = threading.Thread(target=_detect_gestures,  daemon=True)
        det.start()
        det_ow.start()

        if self.skip_intro:
            self.chosen_zone = self.initial_zone
            self._set_zone(self.chosen_zone)
            self.app_state = 'running'
            self.state_changed.emit('running')
            _opt_map = {'mouse': 1, 'subway': 2, 'racing': 3, 'open_world': 4, 'custom': 5, 'air_hockey': 6}
            _opt = _opt_map.get(self.initial_game_mode, 1)
            if _opt != 1:
                self._activate_game_mode(_opt)
        else:
            self.intro_start_t = time.time()

        thumb_hold_t     = None
        zone_finger_hold = {}
        game_opt_hold_t  = None
        game_opt_frac    = 0.0

        try:
            while self._running and cap.isOpened():
                if not self._paused_event.is_set():
                    time.sleep(0.01); continue

                ret, frame = cap.read()
                if not ret: break
                t_frame = time.time()

                frame = cv2.flip(frame, 1)
                rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                ts_ms = int(t_frame * 1000)
                with _fl:
                    _latest_frame[0] = rgb.copy()
                    _latest_ts[0]    = ts_ms
                with _rl:
                    result    = _latest_result[0]
                    result_ts = _latest_result_ts[0]
                self._current_frame_t = result_ts

                has_hand = bool(result and result.hand_landmarks)
                lms  = result.hand_landmarks[0] if has_hand else None
                lms2 = result.hand_landmarks[1] if (has_hand and len(result.hand_landmarks) > 1) else None
                display = rgb
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
                        _opt_map = {'mouse': 1, 'subway': 2, 'racing': 3, 'open_world': 4, 'custom': 5, 'air_hockey': 6}
                        self._activate_game_mode(_opt_map.get(self._pending_mode, 1))
                        game_opt_hold_t = None; self.game_opt_number = None; game_opt_frac = 0.0
                        self._pending_mode = None

                    _current_mode_name = _MODE_NAME_BY_OPT.get(self.active_game_mode, 'mouse')
                    if _current_mode_name == 'custom':
                        _switch_locked = not self._custom_meta_gestures_enabled
                    else:
                        _switch_locked = self._mode_switch_locks.get(
                            _current_mode_name,
                            _MODE_SWITCH_LOCK_DEFAULTS.get(_current_mode_name, False))

                    if _switch_locked:
                        game_opt_hold_t = None; self.game_opt_number = None; game_opt_frac = 0.0
                    else:
                        _any_devil = (lms and is_devil_horn(lms)) or (lms2 and is_devil_horn(lms2))
                        if _any_devil:
                            game_opt_hold_t = None; self.game_opt_number = None; game_opt_frac = 0.0
                        else:
                            game_opt_hold_t, self.game_opt_number, game_opt_frac, triggered_opt = \
                                tick_game_opt(lms, lms2, now, game_opt_hold_t, self.game_opt_number)
                            if triggered_opt is not None:
                                self._activate_game_mode(6 if triggered_opt == 5 else triggered_opt)
                                game_opt_hold_t = None; self.game_opt_number = None; game_opt_frac = 0.0

                    if self.range_min_x is not None and (self.active_game_mode != 6 or self._devilhorn_mouse):
                        draw_zone_rect(display,
                                       self.range_min_x, self.range_max_x,
                                       self.range_min_y, self.range_max_y)

                    if self.active_game_mode is None:
                        self._tick_mouse_mode(lms, lms2, result, display, now, game_opt_frac)
                        if not self._running:
                            break

                    elif self.active_game_mode == 2:
                        self._tick_subway_mode(lms, lms2, result, display, now, game_opt_frac)

                    elif self.active_game_mode == 3:
                        self._tick_racing_mode(lms, lms2, result, display, now, game_opt_frac)

                    elif self.active_game_mode == 4:
                        with _owl: ow_result = _latest_ow_result[0]
                        self._tick_open_world_mode(lms, lms2, result, display, now, game_opt_frac, ow_result)

                    elif self.active_game_mode == 5:
                        self._tick_custom_mode(lms, lms2, result, display, now, game_opt_frac)

                    elif self.active_game_mode == 6:
                        self._tick_air_hockey_mode(lms, lms2, result, display, now, game_opt_frac)

                    if lms is not None and self._current_frame_t > 0:
                        self.nn_latency.emit((time.time() - self._current_frame_t) * 1000)

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
                            self.meta_hold['close'] = None
                            self._confirm_close_from   = 'stopped'
                            self._confirm_close_hold_t = None
                            self.app_state = 'confirm_close'
                            self.state_changed.emit('confirm_close')
                    else:
                        self.meta_hold['close'] = None

                    if lms:  draw_hand(display, lms)
                    if lms2: draw_hand(display, lms2)
                    self.stopped_data.emit(resume_frac, close_frac)
                    self.distance_live.emit(hand_size(lms) if lms else 0.0, lms is not None)

                elif self.app_state == 'confirm_close':
                    both_fists = lms and lms2 and is_fist(lms) and is_fist(lms2)
                    confirm_frac = 0.0
                    if both_fists:
                        if self._confirm_close_hold_t is None:
                            self._confirm_close_hold_t = now
                        confirm_frac = min((now - self._confirm_close_hold_t) / CONFIRM_CLOSE_HOLD, 1.0)
                        if confirm_frac >= 1.0:
                            self._release_drag()
                            self._rc_release_all()
                            self._ow_release_all()
                            self.close_requested.emit()
                            self._running = False
                            break
                    else:
                        if self._confirm_close_hold_t is not None:
                            self._confirm_close_hold_t = None
                            self.app_state = self._confirm_close_from or 'running'
                            self._confirm_close_from = None
                            self.state_changed.emit(self.app_state)
                    if lms:  draw_hand(display, lms)
                    if lms2: draw_hand(display, lms2)
                    self.stopped_data.emit(0.0, confirm_frac)
                    self.distance_live.emit(hand_size(lms) if lms else 0.0, lms is not None)

                h_img, w_img, ch = display.shape
                qt_img = QImage(display.data, w_img, h_img, ch * w_img, QImage.Format_RGB888)
                self.frame_ready.emit(qt_img.copy())

        except Exception as e:
            print(f"[HandController] Tracking loop crashed: {e}")
            self.error_occurred.emit(f"Gesture tracking stopped unexpectedly: {e}")
        finally:
            for _cleanup in (self._release_drag, self._rc_release_all,
                              self._ow_release_all, self._ah_release_all):
                try:
                    _cleanup()
                except Exception:
                    pass
            _stop[0] = True
            det.join(timeout=2.0)
            det_ow.join(timeout=2.0)
            try:
                cap.release()
            except Exception:
                pass
            try:
                detector.close()
            except Exception:
                pass
            if ow_recognizer is not None:
                try: ow_recognizer.close()
                except Exception: pass
            self.state_changed.emit('idle')
