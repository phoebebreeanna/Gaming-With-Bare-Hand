import pyautogui

from logic.hand_utils import (
    draw_hand, draw_finger_dot, is_devil_horn,
    split_hands_by_handedness, MOUSE_CONF_THRESH,
)
from logic.gesture_net import run_nn

SS_KEY_COOLDOWN      = 0.3
SS_SPACE_COOLDOWN    = 1.0
SS_CONFIDENCE_THRESH = 0.75

class SubwayModeMixin:

    def _tick_subway_mode(self, lms, lms2, result, display, now, game_opt_frac):
        meta_hold_fracs, meta_handled = self._tick_control_gestures(
            'subway', lms, lms2, now, self._release_drag)
        meta_hold_fracs['game_opt'] = game_opt_frac
        if meta_handled:
            return

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
            self._right_half_mode = devil_horn
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
            draw_hand(display, devil_hand_lms, (255, 100, 0))
            self.gesture_changed.emit(
                f'MOUSE: {gesture_m.upper().replace("_", " ")}', 'Devil horn mouse mode')
            self.running_data.emit({
                'mode': 'subway', 'devilhorn': True,
                'gesture': gesture_m,
                'game_opt_num': self.game_opt_number or 0,
                'game_opt_frac': game_opt_frac,
                'meta': meta_hold_fracs,
            })
        else:
            gesture_ss = 'none'; conf_ss = 0.0
            if lms:
                gesture_ss, conf_ss, self.ss_prev_row = run_nn(
                    lms, self.ss_prev_row, self.subway_model, self.subway_le, SS_CONFIDENCE_THRESH)
                if gesture_ss == 'space':
                    if not self.ss_space_pressed and (now - self.ss_last_space_t) > SS_SPACE_COOLDOWN:
                        try: pyautogui.press(self.ss_key_map.get('space', 'space'))
                        except Exception: pass
                        self.ss_space_pressed = True
                        self.ss_last_space_t  = now
                    self.ss_current_zone = 'neutral'
                else:
                    self.ss_space_pressed = False
                    if gesture_ss in self.ss_key_map:
                        if gesture_ss != self.ss_current_zone and (now - self.ss_last_key_t) > SS_KEY_COOLDOWN:
                            try: pyautogui.press(self.ss_key_map[gesture_ss])
                            except Exception: pass
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
                'meta': meta_hold_fracs,
            })
