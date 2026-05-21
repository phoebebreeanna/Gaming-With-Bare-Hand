"""Subway Surfer mode constants and gesture-key map."""

SUBWAY_CONF_THRESH = 0.75
KEY_COOLDOWN       = 0.3
SPACE_COOLDOWN     = 1.0

TARGET_DIST        = 0.18
DIST_TOL           = 0.03
DIST_OK_HOLD       = 1.0

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
