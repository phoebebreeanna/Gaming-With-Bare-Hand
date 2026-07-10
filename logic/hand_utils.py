import cv2
import numpy as np
import math
import pyautogui

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

MOUSE_SMOOTHING    = 0.45
MOUSE_CONF_THRESH  = 0.60
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
HOLD_GAME           = 3.0
ZONE_CONFIRM_TIME   = 3.0

LANDMARK_PINCH_THRESH = 0.03

CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),
    (0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),
    (5,9),(9,13),(13,17),
]

ZONE_PRESETS = {
    'small':  0.1,
    'medium': 0.2,
    'large':  0.3,
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

def is_devil_horn(lms):
    f = fingers_extended(lms)
    return f['index'] and f['pinky'] and not f['middle'] and not f['ring']

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

def split_hands_by_handedness(result):
    if not result or not result.hand_landmarks:
        return None, None
    user_left = user_right = None
    for i, hand in enumerate(result.hand_landmarks):
        if result.handedness and i < len(result.handedness):
            if result.handedness[i][0].category_name == 'Left':
                user_left = hand
            else:
                user_right = hand
        else:
            if hand[0].x < 0.5:
                user_left = hand
            else:
                user_right = hand
    return user_left, user_right

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
        cv2.circle(img, pt, 5, _JOINT,   -1)
        cv2.circle(img, pt, 5, _JOINT_B,  2)

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
    # if PYNPUT_AVAILABLE:
    #     _mouse_ctrl.position = (int(x), int(y))
    # else:
        pyautogui.moveTo(int(x), int(y))

def _mouse_left_down():
    # if PYNPUT_AVAILABLE:
    #     _mouse_ctrl.press(_PynputButton.left)
    # else:
        pyautogui.mouseDown()

def _mouse_left_up():
    # if PYNPUT_AVAILABLE:
    #     _mouse_ctrl.release(_PynputButton.left)
    # else:
        pyautogui.mouseUp()

def _mouse_left_click():
    # if PYNPUT_AVAILABLE:
    #     _mouse_ctrl.click(_PynputButton.left)
    # else:
        pyautogui.click()

def _mouse_right_click():
    # if PYNPUT_AVAILABLE:
    #     _mouse_ctrl.click(_PynputButton.right)
    # else:
        pyautogui.rightClick()

def _mouse_scroll(amount):
    # if PYNPUT_AVAILABLE:
    #     _mouse_ctrl.scroll(0, amount)
    # else:
        pyautogui.scroll(amount)

def _mouse_move_relative(dx, dy):
    pyautogui.move(int(dx), int(dy))
