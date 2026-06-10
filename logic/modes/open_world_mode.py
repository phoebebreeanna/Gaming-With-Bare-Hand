import pyautogui

from logic.hand_utils import (
    draw_hand, draw_finger_dot, is_devil_horn,
    split_hands_by_handedness, MOUSE_CONF_THRESH,
    _mouse_move_relative,
)
from logic.gesture_net import run_nn

OW_TAP_THRESHOLD     = 0.075
OW_SCORE_THRESH      = 0.7
OW_MOUSE_SENSITIVITY = 1.5

OW_GESTURE_KEY_MAP = {
    'two_up':           'controller',
    'two_up_inverted':  'controller',
    'three_gun':        'controller',
    'like':             'shift',
    'palm':             'space',
    'one':              '1',
    'peace':            '2',
    'three':            '3',
    'four':             '4',
    'rock':             'none',
    'call':             'r',
    'dislike':          'q',
    'ok':               'f',
    'grip':             'alt',
    'thumb_index':      'left_click',
    'little_finger':    'right_click',
    'holy':             'esc',
    'three2':           'tab',
    'peace_inverted':   't',
    'three3':           'g',
    'fist':             'none',
    'stop_inverted':    'none',
    'stop':             'none',
    'mute':             'none',
    'point':            'none',
    'grabbing':         'e',
    'middle_finger':    'none',
}

def _ow_move(gesture_name, landmarks):
    if gesture_name == 'two_up':
        return 'w'
    if gesture_name == 'two_up_inverted':
        return 's'
    if gesture_name == 'three_gun' and landmarks:
        return 'a' if landmarks[8].x < landmarks[0].x else 'd'
    return None

class OpenWorldModeMixin:

    def _ow_release_all(self):
        for k in list(self.ow_held_keys):
            try:
                if k == 'left_click':    pyautogui.mouseUp(button='left')
                elif k == 'right_click': pyautogui.mouseUp(button='right')
                else:                    pyautogui.keyUp(k)
            except Exception:
                pass
        self.ow_held_keys.clear()
        self.ow_gesture_start_times.clear()

    def _tick_open_world_mode(self, lms, lms2, result, display, now, game_opt_frac, ow_result):
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
                self._ow_release_all()
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
                'mode': 'open_world', 'devilhorn': True,
                'gesture': gesture_m,
                'game_opt_num': self.game_opt_number or 0,
                'game_opt_frac': game_opt_frac,
                'meta': {'game_opt': game_opt_frac},
            })
        else:
            eff_map = dict(OW_GESTURE_KEY_MAP)
            for _g, _k in self.ow_key_map.items():
                if _g in eff_map:
                    eff_map[_g] = _k

            right_one_lms = None
            right_one_idx = -1
            if ow_result and ow_result.gestures:
                for _i, _hg in enumerate(ow_result.gestures):
                    _g0 = _hg[0]
                    if _g0.category_name == 'one' and _g0.score >= OW_SCORE_THRESH:
                        _raw_hand = (ow_result.handedness[_i][0].category_name
                                     if ow_result.handedness and _i < len(ow_result.handedness) else '')
                        if _raw_hand == 'Left':
                            right_one_lms = (ow_result.hand_landmarks[_i]
                                             if ow_result.hand_landmarks and _i < len(ow_result.hand_landmarks) else None)
                            right_one_idx = _i
                            break

            if right_one_lms is not None:
                wrist = right_one_lms[0]
                if not self.ow_rel_mouse_active:
                    self.ow_rel_mouse_active   = True
                    self.ow_rel_mouse_prev_pos = (wrist.x, wrist.y)
                else:
                    dx = wrist.x - self.ow_rel_mouse_prev_pos[0]
                    dy = wrist.y - self.ow_rel_mouse_prev_pos[1]
                    move_x = int(dx * 1000 * OW_MOUSE_SENSITIVITY)
                    move_y = int(dy * 1000 * OW_MOUSE_SENSITIVITY)
                    if move_x != 0 or move_y != 0:
                        _mouse_move_relative(move_x, move_y)
                    self.ow_rel_mouse_prev_pos = (wrist.x, wrist.y)
            else:
                self.ow_rel_mouse_active   = False
                self.ow_rel_mouse_prev_pos = None

            detected = {}
            if ow_result and ow_result.gestures:
                for _i, _hg in enumerate(ow_result.gestures):
                    if _i == right_one_idx:
                        continue
                    _g0 = _hg[0]
                    if _g0.score < OW_SCORE_THRESH:
                        continue
                    _gname = _g0.category_name
                    _lms_ow = (ow_result.hand_landmarks[_i]
                               if ow_result.hand_landmarks and
                               _i < len(ow_result.hand_landmarks) else None)
                    _key = eff_map.get(_gname)
                    if not _key or _key == 'none':
                        continue
                    if _key == 'controller':
                        _mk = _ow_move(_gname, _lms_ow)
                        if _mk:
                            detected[_gname] = _mk
                    else:
                        detected[_gname] = _key

            keys_this_frame = set()
            for _gname, _key in detected.items():
                if eff_map.get(_gname) == 'controller':
                    keys_this_frame.add(_key)
                    self.ow_gesture_start_times[_gname] = now
                else:
                    if _gname not in self.ow_gesture_start_times:
                        self.ow_gesture_start_times[_gname] = now
                    elif (now - self.ow_gesture_start_times[_gname]) >= OW_TAP_THRESHOLD:
                        keys_this_frame.add(_key)

            ended = set(self.ow_gesture_start_times) - set(detected)
            for _gname in ended:
                _key = eff_map.get(_gname)
                if _key and _key not in ('none', 'controller'):
                    if (now - self.ow_gesture_start_times[_gname]) < OW_TAP_THRESHOLD:
                        try:
                            if _key == 'left_click':    pyautogui.click()
                            elif _key == 'right_click': pyautogui.rightClick()
                            else:                        pyautogui.press(_key)
                        except Exception:
                            pass
            for _gname in ended:
                del self.ow_gesture_start_times[_gname]

            for _key in (keys_this_frame - self.ow_held_keys):
                if _key in ('none', 'controller'):
                    continue
                try:
                    if _key == 'left_click':    pyautogui.mouseDown(button='left')
                    elif _key == 'right_click': pyautogui.mouseDown(button='right')
                    else:                        pyautogui.keyDown(_key)
                except Exception:
                    pass
                self.ow_held_keys.add(_key)

            for _key in list(self.ow_held_keys - keys_this_frame):
                try:
                    if _key == 'left_click':    pyautogui.mouseUp(button='left')
                    elif _key == 'right_click': pyautogui.mouseUp(button='right')
                    else:                        pyautogui.keyUp(_key)
                except Exception:
                    pass
                self.ow_held_keys.discard(_key)

            if lms:  draw_hand(display, lms)
            if lms2: draw_hand(display, lms2)

            _top      = list(detected.keys())[0] if detected else 'none'
            _keys_str = ', '.join(sorted(self.ow_held_keys)) or 'Idle'
            self.gesture_changed.emit(_top.upper(), _keys_str)
            self.running_data.emit({
                'mode': 'open_world',
                'gesture': _top,
                'held_keys': list(self.ow_held_keys),
                'game_opt_num': self.game_opt_number or 0,
                'game_opt_frac': game_opt_frac,
                'meta': {'game_opt': game_opt_frac},
            })
