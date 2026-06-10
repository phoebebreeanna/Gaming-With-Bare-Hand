import pyautogui

from logic.hand_utils import (
    draw_hand, draw_finger_dot, is_devil_horn,
    split_hands, split_hands_by_handedness, get_steer_angle, MOUSE_CONF_THRESH,
)
from logic.gesture_net import run_nn

RC_STEER_DEADZONE = 20
RC_STEER_MAX      = 40
RC_CONF_THRESH    = 0.6
RC_TAP_COOLDOWN   = 0.4

class RacingModeMixin:

    def _rc_set_held_keys(self, desired):
        for k in list(self.rc_held_keys - desired):
            try: pyautogui.keyUp(k)
            except Exception: pass
            self.rc_held_keys.discard(k)
        for k in list(desired - self.rc_held_keys):
            try: pyautogui.keyDown(k)
            except Exception: pass
            self.rc_held_keys.add(k)

    def _rc_release_all(self):
        for k in list(self.rc_held_keys):
            try: pyautogui.keyUp(k)
            except: pass
        self.rc_held_keys.clear()

    def _tick_racing_mode(self, lms, lms2, result, display, now, game_opt_frac):
        user_left, user_right = split_hands_by_handedness(result)
        lms_left, lms_right   = split_hands(result) if (result and result.hand_landmarks) else (None, None)

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
            self._rc_release_all()
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
                'mode': 'racing', 'devilhorn': True,
                'gesture': gesture_m,
                'game_opt_num': self.game_opt_number or 0,
                'game_opt_frac': game_opt_frac,
                'meta': {'game_opt': game_opt_frac},
            })
        else:
            if lms_left  is None: self.rc_prev_row_left  = None
            if lms_right is None: self.rc_prev_row_right = None
            desired   = set(); angle = 0.0; steer_dir = 'none'
            accel = brake = horn = camera_tapped = False
            gest_l = gest_r = 'none'; conf_l = conf_r = 0.0

            if lms_left:
                gest_l, conf_l, self.rc_prev_row_left = run_nn(
                    lms_left, self.rc_prev_row_left, self.racing_model, self.racing_le, RC_CONF_THRESH)
            if lms_right:
                gest_r, conf_r, self.rc_prev_row_right = run_nn(
                    lms_right, self.rc_prev_row_right, self.racing_model, self.racing_le, RC_CONF_THRESH)

            accel = gest_r == 'thumb'
            brake = gest_l == 'thumb'
            horn  = gest_r == 'index_middle'

            if accel: desired.add(self.rc_key_map.get('accel', 'up'))
            if brake: desired.add(self.rc_key_map.get('brake', 'down'))
            if horn:  desired.add(self.rc_key_map.get('horn', 'h'))

            camera_key = self.rc_key_map.get('camera', 'c')
            if gest_l == 'index_middle':
                last_tap = self.rc_tap_cooldown.get(camera_key, 0)
                if now - last_tap >= RC_TAP_COOLDOWN:
                    pyautogui.press(camera_key)
                    self.rc_tap_cooldown[camera_key] = now
                    camera_tapped = True

            if lms_left and lms_right:
                angle = get_steer_angle(lms_left, lms_right)
                if   angle < -RC_STEER_DEADZONE: steer_dir = 'left'
                elif angle >  RC_STEER_DEADZONE: steer_dir = 'right'
            if steer_dir == 'left':  desired.add(self.rc_key_map.get('steer_left',  'left'))
            if steer_dir == 'right': desired.add(self.rc_key_map.get('steer_right', 'right'))
            self._rc_set_held_keys(desired)

            if lms_left:  draw_hand(display, lms_left,  (255, 180, 80))
            if lms_right: draw_hand(display, lms_right, (255, 80, 180))

            _sl    = {'left': 'LEFT ←', 'right': 'RIGHT →', 'none': 'Straight'}[steer_dir]
            _ped   = ' · ACCEL' if accel else (' · BRAKE' if brake else '')
            _extras = (' · HORN' if horn else '') + (' · CAM' if camera_tapped else '')
            _act   = ('Accelerate' if accel else ('Brake' if brake else 'Idle')) + f'  ·  Steer {_sl}'
            self.gesture_changed.emit(f'STEER {_sl}{_ped}{_extras}', _act)
            self.running_data.emit({
                'mode': 'racing',
                'steer': steer_dir,
                'angle': round(angle, 1),
                'accel': accel,
                'brake': brake,
                'horn': horn,
                'camera': camera_tapped,
                'gest_l': gest_l, 'conf_l': round(conf_l, 2),
                'gest_r': gest_r, 'conf_r': round(conf_r, 2),
                'game_opt_num': self.game_opt_number or 0,
                'game_opt_frac': game_opt_frac,
                'meta': {'game_opt': game_opt_frac},
            })
