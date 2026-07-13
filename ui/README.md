# UI Notes

Notes preserved from comments removed during a code cleanup pass. These
capture non-obvious constraints/rationale that aren't evident from reading
the code alone.

## Air hockey mode switching (`ui/main_menu.py`, `ui/air_hockey_loading.py`)

AIR HOCKEY needs `num_hands=4` on the MediaPipe detector, which is fixed
at detector-creation time. Crossing that boundary (either entering or
leaving AIR HOCKEY mode) requires a full hand-tracking controller restart
rather than the usual instant `switch_game_mode()` call - hence the
`AirHockeyLoadingOverlay` loading screen shown during the transition.

## `ui/air_hockey_status.py`

- `SKILL_NAMES` is intentionally kept separate from
  `hockey_game/config.py:POWER_FULL_NAME`. The two projects are
  independent; this app only needs the display label, not a shared
  dependency on the hockey game's config.
- `AirHockeyStatusPanel` is a standalone widget (not a reuse of the
  single-player home-dashboard GESTURE/ACTION cards) because those cards
  only represent one hand/gesture at a time and can't show 2 players x 2
  hands each.
