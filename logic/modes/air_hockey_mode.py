import cv2
import pyautogui

from logic.hand_utils import draw_hand, draw_zone_rect, draw_wrist_marker, count_fingers_up_5

AH_KEYS = {
    1: {
        'up': 'w', 'down': 's', 'left': 'a', 'right': 'd',
        'skills': {1: '1', 2: '2', 3: '3', 4: '4', 5: '5'},
    },
    2: {
        'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right',
        'skills': {1: '6', 2: '7', 3: '8', 4: '9', 5: '0'},
    },
}

AH_QUARTER_W = 0.25
AH_CENTER = {1: (0.125, 0.5), 2: (0.625, 0.5)}
AH_DEADZONE = 0.07

AH_BOX_HALF_W = AH_QUARTER_W * 0.70 / 2

AH_SKILL_DEBOUNCE = 0.18

AH_COLOR_MOVER = (80, 200, 255)
AH_COLOR_SKILL = (255, 170, 60)
AH_COLOR_DIVIDER = (120, 120, 120)


class AirHockeyModeMixin:

    def _init_ah_state(self):
        self.ah_held_keys         = {1: set(), 2: set()}
        self.ah_skill_raw         = {1: 0, 2: 0}
        self.ah_skill_count_since = {1: None, 2: None}
        self.ah_last_fired        = {1: 0, 2: 0}

    def _ah_set_held_keys(self, player, desired):
        held = self.ah_held_keys[player]
        for k in list(held - desired):
            try: pyautogui.keyUp(k)
            except Exception: pass
            held.discard(k)
        for k in list(desired - held):
            try: pyautogui.keyDown(k)
            except Exception: pass
            held.add(k)

    def _ah_release_all(self):
        if not hasattr(self, 'ah_held_keys'):
            return
        for player in (1, 2):
            for k in list(self.ah_held_keys.get(player, ())):
                try: pyautogui.keyUp(k)
                except Exception: pass
            self.ah_held_keys[player] = set()

    def _ah_classify(self, result):
        buckets = {1: [], 2: []}
        if result and result.hand_landmarks:
            for i, hand in enumerate(result.hand_landmarks):
                half = 1 if hand[0].x < 0.5 else 2
                if len(buckets[half]) >= 2:
                    continue
                handed = None
                if result.handedness and i < len(result.handedness):
                    handed = result.handedness[i][0].category_name
                buckets[half].append((hand, handed))

        roles = {1: {'mover': None, 'skill': None}, 2: {'mover': None, 'skill': None}}
        for half, hands in buckets.items():
            for hand, handed in hands:
                if handed == 'Right' and roles[half]['mover'] is None:
                    roles[half]['mover'] = hand
                elif handed == 'Left' and roles[half]['skill'] is None:
                    roles[half]['skill'] = hand
            for hand, handed in hands:
                if hand is roles[half]['mover'] or hand is roles[half]['skill']:
                    continue
                if roles[half]['mover'] is None:
                    roles[half]['mover'] = hand
                elif roles[half]['skill'] is None:
                    roles[half]['skill'] = hand
        return roles

    def _ah_draw_overlay(self, display):
        h, w = display.shape[:2]
        cv2.line(display, (w // 2, 0), (w // 2, h), AH_COLOR_DIVIDER, 1)
        box_half_h = AH_BOX_HALF_W * (w / h)
        for player in (1, 2):
            cx, cy = AH_CENTER[player]
            draw_zone_rect(display,
                           cx - AH_BOX_HALF_W, cx + AH_BOX_HALF_W,
                           cy - box_half_h, cy + box_half_h)

    def _ah_tick_player(self, player, mover_lms, skill_lms, now, display):
        keys = AH_KEYS[player]

        dir_x = dir_y = None
        if mover_lms is not None:
            cx, cy = AH_CENTER[player]
            dx = mover_lms[0].x - cx
            dy = mover_lms[0].y - cy
            if dx < -AH_DEADZONE: dir_x = 'left'
            elif dx > AH_DEADZONE: dir_x = 'right'
            if dy < -AH_DEADZONE: dir_y = 'up'
            elif dy > AH_DEADZONE: dir_y = 'down'
            draw_hand(display, mover_lms, AH_COLOR_MOVER)
            draw_wrist_marker(display, mover_lms, AH_COLOR_MOVER)

        desired = set()
        if dir_x: desired.add(keys[dir_x])
        if dir_y: desired.add(keys[dir_y])
        self._ah_set_held_keys(player, desired)

        raw_n = count_fingers_up_5(skill_lms) if skill_lms is not None else 0
        if raw_n != self.ah_skill_raw[player]:
            self.ah_skill_raw[player]         = raw_n
            self.ah_skill_count_since[player] = now
        held_for = now - (self.ah_skill_count_since[player] or now)
        if held_for >= AH_SKILL_DEBOUNCE:
            if raw_n == 0:
                self.ah_last_fired[player] = 0
            elif 1 <= raw_n <= 5 and raw_n != self.ah_last_fired[player]:
                try: pyautogui.press(keys['skills'][raw_n])
                except Exception: pass
                self.ah_last_fired[player] = raw_n
        if skill_lms is not None:
            draw_hand(display, skill_lms, AH_COLOR_SKILL)

        if mover_lms is None:
            direction = '--'
        else:
            direction = '-'.join(p.upper() for p in (dir_y, dir_x) if p) or 'IDLE'

        return {
            'mover_present': mover_lms is not None,
            'direction':     direction,
            'skill_present': skill_lms is not None,
            'skill_count':   raw_n,
            'last_skill':    self.ah_last_fired[player],
        }

    def _tick_air_hockey_mode(self, lms, lms2, result, display, now, game_opt_frac):
        self._ah_draw_overlay(display)
        roles = self._ah_classify(result)
        p1 = self._ah_tick_player(1, roles[1]['mover'], roles[1]['skill'], now, display)
        p2 = self._ah_tick_player(2, roles[2]['mover'], roles[2]['skill'], now, display)

        def _summary(p, s):
            base = f'P{p}: {s["direction"]}'
            return base + (f' · SKILL {s["last_skill"]}' if s['last_skill'] else '')

        self.gesture_changed.emit(_summary(1, p1), _summary(2, p2))
        self.running_data.emit({
            'mode': 'air_hockey',
            'p1_mover_present': p1['mover_present'],
            'p1_direction':     p1['direction'],
            'p1_skill_present': p1['skill_present'],
            'p1_skill_count':   p1['skill_count'],
            'p1_last_skill':    p1['last_skill'],
            'p2_mover_present': p2['mover_present'],
            'p2_direction':     p2['direction'],
            'p2_skill_present': p2['skill_present'],
            'p2_skill_count':   p2['skill_count'],
            'p2_last_skill':    p2['last_skill'],
            'game_opt_num':  self.game_opt_number or 0,
            'game_opt_frac': game_opt_frac,
            'meta': {'game_opt': game_opt_frac},
        })
