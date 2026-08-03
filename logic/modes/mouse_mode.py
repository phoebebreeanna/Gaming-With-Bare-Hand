from logic.hand_utils import (
    _mouse_left_up, _mouse_left_down, _mouse_left_click, _mouse_right_click,
    _mouse_move, _mouse_scroll,
    MOUSE_SMOOTHING, MOUSE_CONF_THRESH, DRAG_HOLD_THRESH,
    CLICK_COOLDOWN, SCROLL_SPEED, MP_PRESENCE_THRESH,
    draw_hand, draw_finger_dot,
)

from logic.gesture_net import run_nn

class MouseModeMixin:

    def _release_drag(self):
        if self.tm_drag_active:
            _mouse_left_up()
            self.tm_drag_active = False
        self._drag_release_votes = 0

    def _run_mouse_gesture(self, gesture, lms, now):
        if gesture in ('idle', 'none'):
            return
        tx, ty = self._map_cursor(lms[self._cursor_lm].x, lms[self._cursor_lm].y)
        self.smooth_x += (tx - self.smooth_x) * MOUSE_SMOOTHING
        self.smooth_y += (ty - self.smooth_y) * MOUSE_SMOOTHING
        _mouse_move(self.smooth_x, self.smooth_y)

        if gesture == 'move':
            self._release_drag()
            self.left_click_entry_t   = None
            self._pending_left_click  = False
            self.right_click_armed    = True
            self.right_click_entry_t  = None
            self.scroll_entry_t       = None
            self.scroll_active        = False

        elif gesture == 'pre_left_click':
            if self.tm_drag_active:
                self._drag_release_votes += 1
                if self._drag_release_votes >= 3:
                    self._release_drag()
                    self.left_click_entry_t  = None
                    self._pending_left_click = False
            else:
                self._drag_release_votes = 0

        elif gesture == 'pre_right_click':
            pass

        elif gesture == 'left_click':
            self._drag_release_votes = 0
            self.scroll_entry_t  = None
            self.scroll_active   = False
            if self.left_click_entry_t is None:
                self.left_click_entry_t  = now
                self._pending_left_click = True
            if (now - self.left_click_entry_t) >= DRAG_HOLD_THRESH and not self.tm_drag_active:
                self._pending_left_click = False
                _mouse_left_down()
                self.tm_drag_active = True

        elif gesture == 'right_click':
            self._release_drag()
            self.left_click_entry_t  = None
            self._pending_left_click = False

            if not self.right_click_armed:
                if now - self.last_right_click_t > CLICK_COOLDOWN:
                    self.right_click_armed   = True
                    self.right_click_entry_t = None

            if self.right_click_armed:
                if self.right_click_entry_t is None:
                    self.right_click_entry_t = now
                elif (now - self.right_click_entry_t) >= 0.08:
                    if now - self.last_right_click_t > CLICK_COOLDOWN:
                        _mouse_right_click()
                        self.last_right_click_t  = now
                    self.right_click_armed   = False
                    self.right_click_entry_t = None

            self.scroll_entry_t = None
            self.scroll_active  = False

        elif gesture in ('scroll_up', 'scroll_down'):
            self._release_drag()
            self.left_click_entry_t  = None
            self._pending_left_click = False
            self.right_click_armed   = True
            self.right_click_entry_t = None
            if self.scroll_entry_t is None:
                self.scroll_entry_t = now
                self.scroll_active  = False
            elif not self.scroll_active:
                self.scroll_active = True
            if self.scroll_active:
                _mouse_scroll(SCROLL_SPEED if gesture == 'scroll_up' else -SCROLL_SPEED)

        else:
            self._release_drag()
            self.left_click_entry_t  = None
            self._pending_left_click = False
            self.right_click_armed   = True
            self.right_click_entry_t = None
            self.scroll_entry_t      = None
            self.scroll_active       = False

        if gesture != 'left_click' and self.left_click_entry_t is not None and not self.tm_drag_active:
            if self._pending_left_click and now - self.last_left_click_t > CLICK_COOLDOWN:
                _mouse_left_click()
                self.last_left_click_t = now
            self._pending_left_click = False
            self.left_click_entry_t  = None

        if gesture != 'right_click':
            self.right_click_armed   = True
            self.right_click_entry_t = None

    def _tick_mouse_mode(self, lms, lms2, result, display, now, game_opt_frac):
        meta_hold_fracs, meta_handled = self._tick_control_gestures(
            'mouse', lms, lms2, now, self._release_drag)
        meta_hold_fracs['game_opt'] = game_opt_frac
        if meta_handled:
            return

        any_meta = any(v is not None for v in self.meta_hold.values()) or game_opt_frac > 0
        gesture  = 'idle'

        if lms and not any_meta:
            mp_ok = True
            try:
                mp_ok = result.handedness[0][0].score >= MP_PRESENCE_THRESH
            except Exception:
                pass

            if not mp_ok:
                self.mouse_prev_row = None
                gesture = 'idle'
            else:
                gesture, _, self.mouse_prev_row = run_nn(
                    lms, self.mouse_prev_row,
                    self.mouse_model, self.mouse_le, MOUSE_CONF_THRESH)

            self._run_mouse_gesture(gesture, lms, now)
            draw_hand(display, lms)
            if lms2: draw_hand(display, lms2)
            draw_finger_dot(display, lms, gesture, self.tm_drag_active, self._cursor_lm)
        else:
            self._release_drag()
            self.scroll_entry_t      = None
            self.scroll_active       = False
            self._pending_left_click = False
            self.left_click_entry_t  = None
            if lms:  draw_hand(display, lms)
            if lms2: draw_hand(display, lms2)

        _act = {
            'move':            'Moving cursor',
            'pre_left_click':  'Pre left click',
            'left_click':      'Click / Drag',
            'pre_right_click': 'Pre right click',
            'right_click':     'Right click',
            'scroll_up':       'Scroll up',
            'scroll_down':     'Scroll down',
            'idle':            'Idle',
        }
        self.gesture_changed.emit(gesture.upper().replace('_', ' '), _act.get(gesture, gesture))
        self.running_data.emit({
            'mode': 'mouse',
            'gesture': gesture,
            'drag': self.tm_drag_active,
            'click_entry': self.left_click_entry_t,
            'meta': meta_hold_fracs,
            'game_opt_num': self.game_opt_number or 0,
            'game_opt_frac': game_opt_frac,
        })