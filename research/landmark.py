import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import pyautogui
import time
import threading

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

SCREEN_W, SCREEN_H = pyautogui.size()

SMOOTHING       = 0.3
PINCH_THRESH    = 0.28
CLICK_COOLDOWN  = 0.5
SCROLL_SPEED    = 3
LONG_PRESS_TIME = 0.5

CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),
    (0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),
    (5,9),(9,13),(13,17)
]

last_click_t   = 0.0
prev_scroll_y  = None
scroll_entry_t = None
SCROLL_BUFFER  = 0
scroll_active  = False

ip_pinch_start = None
ip_drag_active = False

_latest_frame      = None
_latest_result     = None
_frame_lock        = threading.Lock()
_result_lock       = threading.Lock()
_detection_running = False
_stop_thread       = False


def hand_size(lms):
    return np.hypot(lms[0].x - lms[9].x, lms[0].y - lms[9].y)

def tip_dist(lms, a, b):
    return np.hypot(lms[a].x - lms[b].x, lms[a].y - lms[b].y)

def pinch_ratio(lms, a, b):
    hs = hand_size(lms)
    return tip_dist(lms, a, b) / hs if hs > 0 else 999

def is_finger_extended(lms, tip, pip):
    tip_d = np.hypot(lms[tip].x - lms[0].x, lms[tip].y - lms[0].y)
    pip_d = np.hypot(lms[pip].x - lms[0].x, lms[pip].y - lms[0].y)
    return tip_d > pip_d

def fingers_extended(lms):
    return {
        'index':  is_finger_extended(lms, 8,  6),
        'middle': is_finger_extended(lms, 12, 10),
        'ring':   is_finger_extended(lms, 16, 14),
        'pinky':  is_finger_extended(lms, 20, 18),
    }

def get_gesture(lms):
    f = fingers_extended(lms)

    if pinch_ratio(lms, 4, 8) < PINCH_THRESH:
        return 'index_pinch'

    if pinch_ratio(lms, 4, 12) < PINCH_THRESH:
        return 'tm_pinch'

    if f['index'] and f['middle'] and f['ring'] and not f['pinky']:
        return 'scroll_up'

    if not f['index'] and not f['middle'] and not f['ring'] and not f['pinky']:
        return 'scroll_down'

    index_tip_dist = np.hypot(lms[8].x - lms[0].x, lms[8].y - lms[0].y)
    def other_curled(tip_idx):
        d = np.hypot(lms[tip_idx].x - lms[0].x, lms[tip_idx].y - lms[0].y)
        return d < index_tip_dist * 0.85

    if f['index'] and other_curled(12) and other_curled(16) and other_curled(20):
        return 'move'

    return 'idle'

def draw_hand(img, lms):
    h, w = img.shape[:2]
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in lms]
    for a, b in CONNECTIONS:
        cv2.line(img, pts[a], pts[b], (0, 200, 100), 2)
    for pt in pts:
        cv2.circle(img, pt, 5, (255, 255, 255), -1)
        cv2.circle(img, pt, 5, (0, 150, 80), 2)

def handle_pinch_release(now):
    global ip_pinch_start, ip_drag_active, last_click_t
    if ip_pinch_start is None:
        return
    held = now - ip_pinch_start
    if ip_drag_active:
        pyautogui.mouseUp()
        ip_drag_active = False
        print("[DRAG END → DROP]")
    elif held < LONG_PRESS_TIME and (now - last_click_t > CLICK_COOLDOWN):
        pyautogui.click()
        last_click_t = now
        print("[LEFT CLICK]")
    ip_pinch_start = None

GESTURE_COLOR = {
    'move':        (255, 200,   0),
    'left_click':  (  0, 200, 255),
    'right_click': (255,  80, 200),
    'drag':        (  0, 120, 255),
    'scroll_up':   (180, 255,  80),
    'scroll_down': ( 80, 180, 255),
    'idle':        (180, 180, 180),
}

def draw_running_ui(img, gesture, scroll_entry_t, scroll_active,
                    ip_pinch_start, ip_drag_active):
    h, w = img.shape[:2]

    if ip_drag_active:
        label = "DRAG & DROP  [HOLDING]"
        color = GESTURE_COLOR['drag']
    elif gesture == 'index_pinch' and ip_pinch_start is not None:
        held  = time.time() - ip_pinch_start
        pct   = min(held / LONG_PRESS_TIME, 1.0)
        color = GESTURE_COLOR['left_click']
        label = f"PINCH  {held:.2f}s"
        cv2.rectangle(img, (0, 42), (380, 60), (40, 40, 40), -1)
        fill_w    = int(pct * 380)
        bar_color = (0, int(200 * (1 - pct)), int(255 * pct))
        cv2.rectangle(img, (0, 42), (fill_w, 60), bar_color, -1)
        hint = ">> DRAG MODE" if pct >= 1.0 else f"release = CLICK  |  hold {LONG_PRESS_TIME}s = DRAG"
        cv2.putText(img, hint, (10, 57),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (220, 220, 220), 1)
    elif gesture == 'tm_pinch':
        label = "RIGHT CLICK"
        color = GESTURE_COLOR['right_click']
    elif gesture == 'move':
        label = "MOVE"
        color = GESTURE_COLOR['move']
    elif gesture in ('scroll_up', 'scroll_down'):
        label = gesture.upper()
        color = GESTURE_COLOR[gesture]
    else:
        label = "IDLE"
        color = GESTURE_COLOR['idle']

    cv2.rectangle(img, (0, 0), (420, 40), (30, 30, 30), -1)
    cv2.putText(img, f"Gesture: {label}", (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    if gesture in ('scroll_up', 'scroll_down') and scroll_entry_t is not None and not scroll_active:
        elapsed   = time.time() - scroll_entry_t
        remaining = max(0.0, SCROLL_BUFFER - elapsed)
        cv2.rectangle(img, (0, 42), (320, 72), (40, 40, 20), -1)
        cv2.putText(img, f"Scroll locks in {remaining:.1f}s...", (10, 63),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 1)
    elif gesture in ('scroll_up', 'scroll_down') and scroll_active:
        direction = "UP  ▲" if gesture == 'scroll_up' else "DOWN  ▼"
        cv2.rectangle(img, (0, 42), (280, 72), (20, 50, 20), -1)
        cv2.putText(img, f"Scrolling {direction}", (10, 63),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (100, 255, 100), 2)

    legend = [
        ("Index up                = MOVE",                      GESTURE_COLOR['move']),
        (f"Thumb+Index (OK) < {LONG_PRESS_TIME}s = LEFT CLICK", GESTURE_COLOR['left_click']),
        (f"Thumb+Index >= {LONG_PRESS_TIME}s      = DRAG & DROP", GESTURE_COLOR['drag']),
        ("Thumb + Middle          = RIGHT CLICK",                GESTURE_COLOR['right_click']),
        ("Index+Mid+Ring up       = SCROLL UP",                  GESTURE_COLOR['scroll_up']),
        ("All 4 fingers curled    = SCROLL DOWN",                GESTURE_COLOR['scroll_down']),
    ]
    for i, (text, col) in enumerate(legend):
        cv2.putText(img, text, (10, h - 12 - (len(legend) - 1 - i) * 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.43, col, 1)


base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
options      = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1)
detector     = vision.HandLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS,          30)
cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)

smooth_x, smooth_y = SCREEN_W / 2, SCREEN_H / 2

def detection_worker():
    global _latest_result, _detection_running, _stop_thread
    while not _stop_thread:
        with _frame_lock:
            frame = _latest_frame

        if frame is None:
            time.sleep(0.001)
            continue

        _detection_running = True
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result    = detector.detect(mp_image)

        with _result_lock:
            _latest_result = result

        _detection_running = False

_det_thread = threading.Thread(target=detection_worker, daemon=True)
_det_thread.start()

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
    display  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    fh, fw   = display.shape[:2]

    gesture = 'idle'

    if lms:
        gesture = get_gesture(lms)
        now     = time.time()

        target_x = lms[8].x * SCREEN_W
        target_y = lms[8].y * SCREEN_H
        smooth_x += (target_x - smooth_x) * (1 - SMOOTHING)
        smooth_y += (target_y - smooth_y) * (1 - SMOOTHING)

        if gesture == 'move':
            handle_pinch_release(now)
            pyautogui.moveTo(int(smooth_x), int(smooth_y))
            scroll_entry_t = None
            scroll_active  = False
            prev_scroll_y  = None

        elif gesture == 'index_pinch':
            if ip_pinch_start is None:
                ip_pinch_start = now
            held = now - ip_pinch_start
            if not ip_drag_active and held >= LONG_PRESS_TIME:
                pyautogui.mouseDown()
                ip_drag_active = True
                print("[DRAG START]")
            if ip_drag_active:
                pyautogui.moveTo(int(smooth_x), int(smooth_y))
            scroll_entry_t = None
            scroll_active  = False
            prev_scroll_y  = None

        elif gesture == 'tm_pinch':
            handle_pinch_release(now)
            if now - last_click_t > CLICK_COOLDOWN:
                pyautogui.rightClick()
                last_click_t = now
                print("[RIGHT CLICK]")
            scroll_entry_t = None
            scroll_active  = False
            prev_scroll_y  = None

        elif gesture == 'scroll_up':
            handle_pinch_release(now)
            if scroll_entry_t is None:
                scroll_entry_t = now
                scroll_active  = False
                print("[SCROLL UP] buffer started")
            elif not scroll_active and (now - scroll_entry_t) >= SCROLL_BUFFER:
                scroll_active = True
                print("[SCROLL UP] activated")
            if scroll_active:
                pyautogui.scroll(SCROLL_SPEED)
            prev_scroll_y = None

        elif gesture == 'scroll_down':
            handle_pinch_release(now)
            if scroll_entry_t is None:
                scroll_entry_t = now
                scroll_active  = False
                print("[SCROLL DOWN] buffer started")
            elif not scroll_active and (now - scroll_entry_t) >= SCROLL_BUFFER:
                scroll_active = True
                print("[SCROLL DOWN] activated")
            if scroll_active:
                pyautogui.scroll(-SCROLL_SPEED)
            prev_scroll_y = None

        else:
            handle_pinch_release(now)
            scroll_entry_t = None
            scroll_active  = False
            prev_scroll_y  = None

        fx, fy    = int(lms[8].x * fw), int(lms[8].y * fh)
        dot_color = GESTURE_COLOR['drag'] if ip_drag_active else GESTURE_COLOR.get(gesture, (255, 255, 255))
        cv2.circle(display, (fx, fy), 12, dot_color, 2)
        cv2.circle(display, (fx, fy),  4, dot_color, -1)

        draw_hand(display, lms)
        draw_running_ui(display, gesture, scroll_entry_t, scroll_active,
                        ip_pinch_start, ip_drag_active)

    else:
        handle_pinch_release(time.time())
        scroll_entry_t = None
        scroll_active  = False
        prev_scroll_y  = None
        draw_running_ui(display, 'idle', None, False, None, False)

    output = cv2.cvtColor(display, cv2.COLOR_RGB2BGR)
    cv2.imshow('Virtual Mouse', output)

    key = cv2.waitKey(1) & 0xFF
    if key == 27:
        if ip_drag_active:
            pyautogui.mouseUp()
        break

_stop_thread = True
_det_thread.join(timeout=1.0)
cap.release()
cv2.destroyAllWindows()
detector.close()
