import pyautogui

from logic.hand_utils import (
    draw_hand, draw_finger_dot, is_devil_horn,
    split_hands_by_handedness, MOUSE_CONF_THRESH,
)
from logic.gesture_net import run_nn

CUSTOM_CONF_THRESH = 0.75

class CustomModeMixin:

    def _custom_release_all(self):
        if self.custom_held_key:
            try: pyautogui.keyUp(self.custom_held_key)
            except Exception: pass
            self.custom_held_key = None

    def _tick_custom_mode(self, lms, lms2, result, display, now, game_opt_frac):
        user_left, user_right = split_hands_by_handedness(result)

        if self._mouse_side == 'right':
            devil_hand_lms = user_right
            mouse_hand_lms = user_left
        else:
            devil_hand_lms = user_left
            mouse_hand_lms = user_right

        devil_horn = (self._mouse_in_game_enabled and self._custom_meta_gestures_enabled and
                      devil_hand_lms is not None and is_devil_horn(devil_hand_lms))
        if devil_horn != self._devilhorn_mouse:
            self.mouse_prev_row     = None
            self.left_click_entry_t = None
            self.right_click_armed  = True
            self.scroll_entry_t     = None
            self.scroll_active      = False
            if not devil_horn:
                self._release_drag()
            self._custom_release_all()
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
                draw_finger_dot(display, mouse_hand_lms, gesture_m,
                                self.tm_drag_active, self._cursor_lm)
            draw_hand(display, devil_hand_lms, (255, 100, 0))
            self.gesture_changed.emit(
                f'MOUSE: {gesture_m.upper().replace("_", " ")}',
                'Devil horn mouse mode')
            self.running_data.emit({
                'mode': 'custom', 'devilhorn': True,
                'gesture': gesture_m,
                'game_opt_num': self.game_opt_number or 0,
                'game_opt_frac': game_opt_frac,
                'meta': {'game_opt': game_opt_frac},
            })
            return

        gesture = 'none'
        conf    = 0.0
        if lms:
            gesture, conf, self.custom_prev_row = run_nn(
                lms, self.custom_prev_row,
                self.custom_model, self.custom_le, CUSTOM_CONF_THRESH)
        else:
            self.custom_prev_row = None

        desired_key = self.custom_key_map.get(gesture) if gesture not in ('idle', 'none') else None
        if desired_key != self.custom_held_key:
            if self.custom_held_key:
                try: pyautogui.keyUp(self.custom_held_key)
                except Exception: pass
            if desired_key:
                try: pyautogui.keyDown(desired_key)
                except Exception: pass
            self.custom_held_key = desired_key

        if lms:  draw_hand(display, lms)
        if lms2: draw_hand(display, lms2)

        _act = f'Key: {self.custom_held_key.upper()}' if self.custom_held_key else 'Idle'
        self.gesture_changed.emit(gesture.upper().replace('_', ' '), _act)
        self.running_data.emit({
            'mode': 'custom',
            'gesture': gesture,
            'conf': round(conf, 2),
            'held_key': self.custom_held_key or '',
            'game_opt_num': self.game_opt_number or 0,
            'game_opt_frac': game_opt_frac,
            'meta': {'game_opt': game_opt_frac},
        })
