import pyautogui

from logic.hand_utils import (
    draw_hand, draw_finger_dot, split_hands, is_metal_sign,
    MOUSE_CONF_THRESH,
)
from logic.gesture_net import run_nn

SS_KEY_COOLDOWN      = 0.3
SS_SPACE_COOLDOWN    = 1.0
SS_CONFIDENCE_THRESH = 0.75

class SubwayModeMixin:

    def _tick_subway_mode(self, lms, lms2, result, display, now, game_opt_frac):
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
                        self.ss_space_pressed = True
                        self.ss_last_space_t  = now
                    self.ss_current_zone = 'neutral'
                else:
                    self.ss_space_pressed = False
                    if gesture_ss in self.ss_key_map:
                        if gesture_ss != self.ss_current_zone and (now - self.ss_last_key_t) > SS_KEY_COOLDOWN:
                            pyautogui.press(self.ss_key_map[gesture_ss])
                            self.ss_last_key_t   = now
                            self.ss_current_zone = gesture_ss
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
