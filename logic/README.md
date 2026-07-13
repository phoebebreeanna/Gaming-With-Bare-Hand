# logic/ notes

Preserved from comments removed during a cleanup pass. Keep these in mind when touching the related code.

## Air Hockey Mode (`logic/modes/air_hockey_mode.py`, `logic/hand_controller.py`)

- Key bindings mirror `hockey_game/config.py:KEYBINDS` exactly. `hockey_game` itself is untouched - this mode just simulates the same key presses a human would make.
  - P1 (left half of frame): move = WASD, skills 1-5 = number row `1`-`5`.
  - P2 (right half of frame): move = arrow keys, skills 1-5 = number row `6`-`0`.
- The neutral center per half (`AH_CENTER`) is fixed - there is no calibration step. A wrist offset beyond `AH_DEADZONE` on a given axis holds that axis's key(s); diagonal offsets hold two keys at once.
- A raw finger count must be held stable for `AH_SKILL_DEBOUNCE` (0.18s) before it fires a skill key, and it won't re-fire until the hand returns to a different count (typically a fist first) - this avoids spamming key presses while a pose is held.
- `_ah_classify` buckets up to 4 detected hands into P1-half/P2-half by wrist x position (capped at 2 hands per half), then assigns mover/skill roles within each half by MediaPipe handedness (Left = mover, Right = skill) - the same Left/Right convention used by `hand_utils.split_hands_by_handedness`.
- Air hockey tracks up to 2 players x 2 hands each, so `hand_controller.py` raises MediaPipe's `num_hands` to 4 only when air hockey mode is active at startup. Every other mode only ever reads the first two hands, which keeps the extra detection cost out of solo use.
- The fist+fingers "game option switch" gesture is intentionally skipped while in air hockey mode: with up to 4 hands on screen it would misfire constantly, and it also collides semantically with the right-hand skill-select gesture.

## Mouse control backend (`logic/hand_utils.py`)

- `pynput` is imported and detected (`PYNPUT_AVAILABLE`) but is not currently used. All mouse actions (`_mouse_move`, `_mouse_left_down/up`, clicks, scroll) go through `pyautogui`. The pynput calls remain in the source, commented out, as a ready-made alternate backend if pyautogui ever needs replacing.
