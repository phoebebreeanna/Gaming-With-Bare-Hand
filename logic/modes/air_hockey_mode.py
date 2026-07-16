import socket

import cv2
import pyautogui

from logic.hand_utils import (
    draw_hand, draw_zone_rect, draw_wrist_marker, draw_finger_dot, count_vertical_fingers_5,
    is_devil_horn, split_hands_by_handedness, MOUSE_CONF_THRESH,
)
from logic.gesture_net import run_nn

AH_REMOTE_PORT = 51246

AH_SKILLS = {
    1: {1: '1', 2: '2', 3: '3', 4: '4', 5: '5'},
    2: {1: '6', 2: '7', 3: '8', 4: '9', 5: '0'},
}

AH_QUARTER_W = 0.25
AH_CENTER = {1: (0.375, 0.5), 2: (0.875, 0.5)}

AH_BOX_HALF_W = AH_QUARTER_W * 0.70 / 2
AH_MOVER_LM = 8

AH_SKILL_DEBOUNCE = 0.18

AH_COLOR_MOVER = (80, 200, 255)
AH_COLOR_SKILL = (255, 170, 60)
AH_COLOR_DIVIDER = (120, 120, 120)
AH_COLOR_DEVILHORN = (255, 100, 0)


class AirHockeyModeMixin:

    def _init_ah_state(self):
        self.ah_skill_raw         = {1: 0, 2: 0}
        self.ah_skill_count_since = {1: None, 2: None}
        self.ah_last_fired        = {1: 0, 2: 0}
        if getattr(self, '_ah_udp_sock', None) is None:
            try:
                self._ah_udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            except OSError:
                self._ah_udp_sock = None

    def _ah_release_all(self):
        pass

    def _ah_classify(self, result, display):
        h, w = display.shape[:2]
        box_half_h = AH_BOX_HALF_W * (w / h)

        def in_box(hand, player):
            pt = hand[AH_MOVER_LM]
            cx, cy = AH_CENTER[player]
            return abs(pt.x - cx) <= AH_BOX_HALF_W and abs(pt.y - cy) <= box_half_h

        buckets = {1: [], 2: []}
        if result and result.hand_landmarks:
            for i, hand in enumerate(result.hand_landmarks):
                half = 1 if hand[AH_MOVER_LM].x < 0.5 else 2
                if len(buckets[half]) >= 2:
                    continue
                handed = None
                if result.handedness and i < len(result.handedness):
                    handed = result.handedness[i][0].category_name
                buckets[half].append((hand, handed))

        roles = {1: {'mover': None, 'skill': None}, 2: {'mover': None, 'skill': None}}
        for half, hands in buckets.items():
            for hand, handed in hands:
                if handed == 'Left' and roles[half]['mover'] is None:
                    roles[half]['mover'] = hand
                elif handed == 'Right' and roles[half]['skill'] is None:
                    roles[half]['skill'] = hand
            for hand, handed in hands:
                if hand is roles[half]['mover'] or hand is roles[half]['skill']:
                    continue
                if roles[half]['mover'] is None:
                    roles[half]['mover'] = hand
                elif roles[half]['skill'] is None:
                    roles[half]['skill'] = hand
            if roles[half]['mover'] is not None and not in_box(roles[half]['mover'], half):
                roles[half]['mover'] = None
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
        h, w = display.shape[:2]
        box_half_h = AH_BOX_HALF_W * (w / h)

        if mover_lms is not None:
            cx, cy = AH_CENTER[player]
            pt = mover_lms[AH_MOVER_LM]
            frac_x = (pt.x - (cx - AH_BOX_HALF_W)) / (2 * AH_BOX_HALF_W)
            frac_y = (pt.y - (cy - box_half_h)) / (2 * box_half_h)
            frac_x = max(0.0, min(1.0, frac_x))
            frac_y = max(0.0, min(1.0, frac_y))
            if self._ah_udp_sock is not None:
                try:
                    self._ah_udp_sock.sendto(
                        f"{player},{frac_x:.4f},{frac_y:.4f}".encode("ascii"),
                        ("127.0.0.1", AH_REMOTE_PORT))
                except OSError:
                    pass
            draw_hand(display, mover_lms, AH_COLOR_MOVER)
            draw_wrist_marker(display, mover_lms, AH_COLOR_MOVER, lm_index=AH_MOVER_LM)

        raw_n = count_vertical_fingers_5(skill_lms) if skill_lms is not None else 0
        if raw_n != self.ah_skill_raw[player]:
            self.ah_skill_raw[player]         = raw_n
            self.ah_skill_count_since[player] = now
        held_for = now - (self.ah_skill_count_since[player] or now)
        if held_for >= AH_SKILL_DEBOUNCE:
            if raw_n == 0:
                self.ah_last_fired[player] = 0
            elif (1 <= raw_n <= 5 and raw_n != self.ah_last_fired[player]
                    and mover_lms is not None):
                try: pyautogui.press(AH_SKILLS[player][raw_n])
                except Exception: pass
                self.ah_last_fired[player] = raw_n
        if skill_lms is not None:
            draw_hand(display, skill_lms, AH_COLOR_SKILL)

        return {
            'mover_present': mover_lms is not None,
            'direction':     'TRACKING' if mover_lms is not None else '--',
            'skill_present': skill_lms is not None,
            'skill_count':   raw_n,
            'last_skill':    self.ah_last_fired[player],
        }

    def _tick_air_hockey_mode(self, lms, lms2, result, display, now, game_opt_frac):
        user_left, user_right = split_hands_by_handedness(result)
        if self._mouse_side == 'right':
            devil_hand_lms = user_right
            mouse_hand_lms = user_left
        else:
            devil_hand_lms = user_left
            mouse_hand_lms = user_right

        devil_horn = (self._mouse_in_game_enabled and
                      devil_hand_lms is not None and is_devil_horn(devil_hand_lms))
        if devil_horn != self._devilhorn_mouse:
            self.mouse_prev_row     = None
            self.left_click_entry_t = None
            self.right_click_armed  = True
            self.scroll_entry_t     = None
            self.scroll_active      = False
            if not devil_horn:
                self._release_drag()
            self._ah_release_all()
            self.ah_skill_raw         = {1: 0, 2: 0}
            self.ah_skill_count_since = {1: None, 2: None}
            self.ah_last_fired        = {1: 0, 2: 0}
            self._set_zone(self.chosen_zone)
        self._devilhorn_mouse = devil_horn

        if devil_horn:
            gesture_m = 'idle'
            if mouse_hand_lms:
                gesture_m, _, self.mouse_prev_row = run_nn(
                    mouse_hand_lms, self.mouse_prev_row,
                    self.mouse_model, self.mouse_le, MOUSE_CONF_THRESH)
                self._run_mouse_gesture(gesture_m, mouse_hand_lms, now)
                draw_hand(display, mouse_hand_lms)
                draw_finger_dot(display, mouse_hand_lms, gesture_m, self.tm_drag_active, self._cursor_lm)
            draw_hand(display, devil_hand_lms, AH_COLOR_DEVILHORN)
            self.gesture_changed.emit(
                f'MOUSE: {gesture_m.upper().replace("_", " ")}', 'Devil horn mouse mode')
            self.running_data.emit({
                'mode': 'air_hockey', 'devilhorn': True,
                'gesture': gesture_m,
                'game_opt_num': self.game_opt_number or 0,
                'game_opt_frac': game_opt_frac,
                'meta': {'game_opt': game_opt_frac},
            })
            return

        self._ah_draw_overlay(display)
        roles = self._ah_classify(result, display)
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
