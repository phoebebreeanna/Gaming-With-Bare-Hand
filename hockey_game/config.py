import pygame

TABLE_WIDTH = 420
TABLE_HEIGHT = 840
WALL_THICKNESS = 16
CORNER_RADIUS = 16
DIVIDER_THICKNESS = 16

HUD_TOP_HEIGHT = 44
HUD_BOTTOM_HEIGHT = 52
VIEW_HEIGHT = HUD_TOP_HEIGHT + TABLE_HEIGHT + HUD_BOTTOM_HEIGHT
TABLE_Y_OFFSET = HUD_TOP_HEIGHT

WINDOW_WIDTH = TABLE_WIDTH * 2 + DIVIDER_THICKNESS
WINDOW_HEIGHT = VIEW_HEIGHT
P1_VIEW_OFFSET_X = 0
P2_VIEW_OFFSET_X = TABLE_WIDTH + DIVIDER_THICKNESS

CENTER_LINE_Y = TABLE_HEIGHT / 2
CENTER_CIRCLE_RADIUS = 62

GOAL_WIDTH = 140
GOAL_X_MIN = (TABLE_WIDTH - GOAL_WIDTH) / 2
GOAL_X_MAX = (TABLE_WIDTH + GOAL_WIDTH) / 2

PUCK_RADIUS = 13
PADDLE_RADIUS = 20

PADDLE_SPEED = 480.0
PUCK_MAX_SPEED = 650.0
WALL_RESTITUTION = 0.95
PUCK_FRICTION_PER_SEC = 0.45

PHYSICS_HZ = 120
PHYSICS_DT = 1.0 / PHYSICS_HZ
MAX_STEPS_PER_FRAME = 8

SCORE_TO_WIN = 7
GOAL_SCORE_DEBOUNCE = 1.0
GOAL_PAUSE_DURATION = 1.2
SERVE_Y_FRAC = 0.75

EVENT_MAX_AGE = 2.0
HITSTOP_DURATION = 0.03
HITSTOP_MIN_IMPACT = 520.0
HITSTOP_COOLDOWN = 0.8
WALL_EVENT_MIN_IMPACT = 60.0
PUCK_TRAIL_LENGTH = 12
PUCK_TRAIL_MIN_SPEED = 180.0
GOAL_BANNER_POP_TIME = 0.28
SCORE_POP_TIME = 0.45

SOUND_ENABLED = True
SOUND_VOLUME = 0.5

SHIELD_DURATION = 2.0
SHIELD_COOLDOWN = 8.0
SHIELD_OFFSET = 120
SHIELD_THICKNESS = 12
SHIELD_MARGIN = 16

FREEZE_DURATION = 1.0
FREEZE_COOLDOWN = 15.0

DOUBLE_PUCK_DURATION = 6.0
DOUBLE_PUCK_COOLDOWN = 20.0

SLOW_PUCK_MAX_DURATION = 3.0
SLOW_PUCK_COOLDOWN = 5.0
SLOW_PUCK_FACTOR = 0.6

SPEED_PUCK_WINDOW = 2.0
SPEED_PUCK_COOLDOWN = 6.0
SPEED_PUCK_BOOST = 1.5

COLOR_BG = (6, 7, 10)

COLOR_RAIL_DARK = (17, 22, 32)
COLOR_RAIL_BEVEL = (70, 86, 110)
COLOR_ICE_NEAR = (218, 234, 245)
COLOR_ICE_FAR = (172, 198, 218)

COLOR_LINE = (58, 110, 168)
COLOR_LINE_ACCENT = (198, 72, 84)
COLOR_GOAL_MOUTH = (10, 12, 16)
COLOR_PUCK_TRAIL = (64, 104, 146)

COLOR_DIVIDER = (12, 14, 18)
COLOR_DIVIDER_BEVEL = (60, 70, 88)

COLOR_PUCK_BODY = (17, 18, 22)
COLOR_PUCK_RIM = (128, 138, 152)
COLOR_PUCK_HIGHLIGHT = (255, 255, 255)
COLOR_PUCK_EXTRA_RIM = (250, 200, 60)

PLAYER_COLORS = {
    1: (72, 156, 255),
    2: (255, 107, 91),
}
PLAYER_MALLET_KNOB = {
    1: (188, 216, 255),
    2: (255, 197, 188),
}
PLAYER_FROZEN_COLOR = (126, 205, 232)
PLAYER_FROZEN_DARK = (40, 100, 132)
PLAYER_SPEED_BUFF_COLOR = (250, 190, 40)

SHIELD_COLOR = (110, 185, 255)

COLOR_TEXT = (235, 242, 245)
COLOR_TEXT_DIM = (170, 185, 195)
COLOR_HUD_PANEL = (10, 13, 18)

COLOR_CARD = (13, 17, 26)
COLOR_KEYCAP = (32, 40, 56)
COLOR_KEYCAP_BORDER = (96, 112, 136)

KEYBINDS = {
    1: {
        "move": {
            "up": pygame.K_w, "down": pygame.K_s,
            "left": pygame.K_a, "right": pygame.K_d,
        },
        "powers": {
            "shield": pygame.K_1,
            "freeze": pygame.K_2,
            "double_puck": pygame.K_3,
            "slow_puck": pygame.K_4,
            "speed_puck": pygame.K_5,
        },
    },
    2: {
        "move": {
            "up": pygame.K_UP, "down": pygame.K_DOWN,
            "left": pygame.K_LEFT, "right": pygame.K_RIGHT,
        },
        "powers": {
            "shield": pygame.K_6,
            "freeze": pygame.K_7,
            "double_puck": pygame.K_8,
            "slow_puck": pygame.K_9,
            "speed_puck": pygame.K_0,
        },
    },
}

RESTART_KEY = pygame.K_RETURN
QUIT_KEY = pygame.K_ESCAPE
START_KEY = pygame.K_SPACE

POWER_ABBREV = {
    "shield": "SH", "freeze": "FR", "double_puck": "DP",
    "slow_puck": "SL", "speed_puck": "SP",
}
POWER_FULL_NAME = {
    "shield": "Shield", "freeze": "Freeze", "double_puck": "Double Puck",
    "slow_puck": "Slow Puck", "speed_puck": "Speed Puck",
}
POWER_KEY_LABEL = {
    1: {"shield": "1", "freeze": "2", "double_puck": "3", "slow_puck": "4", "speed_puck": "5"},
    2: {"shield": "6", "freeze": "7", "double_puck": "8", "slow_puck": "9", "speed_puck": "0"},
}
POWER_DESC = {
    "shield": "Blocks the next shot at your goal (2s)",
    "freeze": "Locks opponent's paddle for 1s",
    "double_puck": "Adds a 2nd puck for 6s -- either can score",
    "slow_puck": "Puck -40% speed on your half (hold, 3s max)",
    "speed_puck": "Next puck hit gets +50% speed (2s window)",
}
MOVE_KEY_LABEL = {1: "W A S D", 2: "Arrow Keys"}
MOVE_KEYCAPS = {1: ["W", "A", "S", "D"], 2: ["↑", "←", "↓", "→"]}
