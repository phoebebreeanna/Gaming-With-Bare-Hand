# logic/ notes

Preserved from comments removed during a cleanup pass. Keep these in mind when touching the related code.

## Air Hockey Mode (`logic/modes/air_hockey_mode.py`, `logic/hand_controller.py`)

- Movement is absolute, not key-simulated: each frame, the mover hand's fractional position inside its green box (`AH_CENTER` + `AH_BOX_HALF_W`) is sent as a UDP packet (`player,frac_x,frac_y`) to `hockey_game/remote_input.py` on `127.0.0.1:AH_REMOTE_PORT`. `hockey_game/physics.py:set_paddle_target_fraction` maps that fraction directly onto the paddle's half of the table via `paddle_bounds` - the paddle position IS the hand position, no dead zone, no idle drift. If no fresh packet has arrived for a player (hand out of the box, or `hockey_game` run standalone), `hockey_game/main.py` falls back to `hockey_game/config.py:KEYBINDS` keyboard control for that paddle.
- Skills still simulate real key presses (`hockey_game/config.py:KEYBINDS` powers): P1 skills 1-5 = number row `1`-`5`, P2 skills 1-5 = number row `6`-`0` (`AH_SKILLS`).
- A raw finger count must be held stable for `AH_SKILL_DEBOUNCE` (0.18s) before it fires a skill key, and it won't re-fire until the hand returns to a different count (typically a fist first) - this avoids spamming key presses while a pose is held.
- `_ah_classify` buckets up to 4 detected hands into P1-half/P2-half by wrist x position (capped at 2 hands per half), then assigns mover/skill roles within each half by MediaPipe handedness (Left = mover, Right = skill) - the same Left/Right convention used by `hand_utils.split_hands_by_handedness`.
- Air hockey tracks up to 2 players x 2 hands each, so `hand_controller.py` always creates the MediaPipe `HandLandmarker` with `num_hands=4` (needed whether air hockey is the launch mode or reached later via a gesture/settings mode swap). Every other mode only ever reads the first two hands, which keeps their gesture logic unaffected by the extra tracking capacity.
- The fist+fingers "game option switch" gesture is intentionally skipped while in air hockey mode: with up to 4 hands on screen it would misfire constantly, and it also collides semantically with the right-hand skill-select gesture.

## Mouse control backend (`logic/hand_utils.py`)

- `pynput` is imported and detected (`PYNPUT_AVAILABLE`) but is not currently used. All mouse actions (`_mouse_move`, `_mouse_left_down/up`, clicks, scroll) go through `pyautogui`. The pynput calls remain in the source, commented out, as a ready-made alternate backend if pyautogui ever needs replacing.
