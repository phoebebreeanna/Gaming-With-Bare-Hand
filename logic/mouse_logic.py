"""Mouse mode constants and gesture-colour map."""

MOUSE_CONF_THRESH  = 0.75
CLICK_COOLDOWN     = 0.5
DRAG_HOLD_THRESH   = 0.5   # seconds of left_click gesture before it becomes a drag
SCROLL_SPEED       = 3
SMOOTHING          = 0.45  # exponential smoothing alpha (higher = more responsive)

TARGET_DIST        = 0.18
DIST_TOL           = 0.03
DIST_OK_HOLD       = 1.0   # seconds in-range before advancing
CALIB_DURATION     = 5.0   # seconds to sweep hand during calibration

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
    'none':            (100, 100, 100),
}
