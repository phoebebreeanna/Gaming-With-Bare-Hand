import pyautogui

from logic.hand_utils import (
    draw_hand, draw_finger_dot, split_hands, is_metal_sign,
    MOUSE_CONF_THRESH,
)
from logic.gesture_net import run_nn

OW_TAP_THRESHOLD = 0.075
OW_SCORE_THRESH  = 0.7

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
    'thumb_index':      'e',
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
    'grabbing':         'none',
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
                self._ow_release_all()
            self._right_half_mode = devil_horn
            self._set_zone(self.chosen_zone)
        self._devilhorn_mouse = devil_horn

        if devil_horn:
            gesture_m = 'idle'
            if lms_right_dh:
                gesture_m, _, self.mouse_prev_row = run_nn(
                    lms_right_dh, self.mouse_prev_row,
                    self.mouse_model, self.mouse_le, MOUSE_CONF_THRESH)
                self._run_mouse_gesture(gesture_m, lms_right_dh, now)
                draw_hand(display, lms_right_dh)
                draw_finger_dot(display, lms_right_dh, gesture_m,
                                self.tm_drag_active, self._cursor_lm)
            draw_hand(display, lms_left_dh, (255, 100, 0))
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

            detected = {}
            if ow_result and ow_result.gestures:
                for _i, _hg in enumerate(ow_result.gestures):
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
