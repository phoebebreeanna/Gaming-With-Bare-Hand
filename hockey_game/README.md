# Dual-POV Air Hockey

Local multiplayer air hockey, one paddle per player. Run with `make run` from
this directory, or `python3 main.py` directly. Tests: `make test` or
`python3 -m unittest test_goal_detection -v`.

## Architecture

- `config.py` — constants: table geometry, physics tuning, keybinds.
- `physics.py` — the ONE shared simulation: entities, movement,
  circle-circle collision, walls, goal detection.
- `input_handler.py` — abstract input interface (`InputSource`) + keyboard
  impl, and the explicit Player-2 view->shared coordinate transform.
- `powers.py` — the 5 special powers: cooldowns, trigger rules, timed
  effects.
- `render.py` — `render_table(surface, state, rotation)` draws the ice
  table; called TWICE per frame with different rotations/surfaces.
  `draw_score_panel`/`draw_power_dock` draw the HUD into separate strips
  outside the ice (never overlaid on top of it). ALL rendering lives here;
  ZERO game logic does.
- `main.py` — fixed-timestep game loop wiring everything together.

Physics runs on a fixed timestep (`config.PHYSICS_DT`) via an accumulator,
so simulation behavior is identical regardless of display frame rate.
Rendering runs once per real frame at whatever rate the display allows.

## Coordinate space

All measurements are in one SHARED PHYSICS COORDINATE SPACE: one table,
origin (0, 0) at the top-left corner.
- The TOP wall (y = 0) is Player 2's goal.
- The BOTTOM wall (y = TABLE_HEIGHT) is Player 1's goal.

This is fixed and never changes, regardless of how each player's half of
the screen is rotated for rendering.

`render.transform_point()` is the single place that converts a shared-space
point into a point on a given player's half. For rotation=180 it maps
`(x, y) -> (TABLE_WIDTH - x, TABLE_HEIGHT - y)` (a point reflection through
the table's center = a 180-degree rotation about the middle). Effect: both
players always see their own goal at the bottom of their own screen, from
one identical shared simulation; the opponent's goal always renders at the
top of a player's own half.

`input_handler.view_to_shared_direction()` is the mirror-image transform for
input: Player 2's view is rotated 180 degrees, so a raw "up/down/left/right"
key intent must be negated on BOTH axes before it reaches physics, or paddle
movement desyncs from what the player sees. If a future feature reads raw
keys anywhere else, this correctness guarantee breaks.

Input is view-relative by design: ONE paddle per player, moved by ONE hand.
This mirrors how real hand-tracking input would work — a tracked hand
position drives the paddle, and a gesture made with that same hand (fist,
palm, ...) triggers a power. Swapping keyboard controls for gesture/hand
tracking later is just a matter of writing a new `InputSource` subclass;
nothing in `physics.py`, `powers.py`, `main.py`, or `render.py` needs to
change.

## Table geometry notes

- A real air-hockey table (e.g. 8-foot: 96in x 48in) runs about 2:1
  length-to-width. `TABLE_HEIGHT` is the goal-to-goal axis, so it's roughly
  double `TABLE_WIDTH` on purpose.
- `CORNER_RADIUS` is kept <= `WALL_THICKNESS` so the sharp-cornered ice
  rectangle (inset by `WALL_THICKNESS`) stays fully tucked under the rail's
  rounded corner.
- Each half is the ice table plus dedicated HUD strips above (score) and
  below (power cooldowns) — HUD is intentionally never overlaid on the ice,
  or it would visually cover the goal mouths. An early version alpha-blended
  the scoreboard over the rink and it buried the goal mouth; splitting into
  top-HUD / ice / bottom-HUD strips fixed that for good.
- The window is two side-by-side 1:1 copies of the table, so no scaling
  transform is needed between physics space and screen pixels (only the
  rotation + offset in `render.py`).
- Power keys are on the plain number row for both players (no numpad
  required) so laptops without a numpad still work: P1 gets 1-5, P2 gets
  6-0, same left-to-right order as the power dock UI (Shield, Freeze,
  Double, Slow, Speed).

## Goal detection (two historical bugs, now regression-tested)

`test_goal_detection.py` pins down two "goals aren't counted" bugs:

1. **Stalled goal** — detection used to require the puck's full circle past
   the outer table edge (29px beyond the drawn goal line); combined with
   friction, a slow shot could die inside the mouth uncounted, soft-locking
   the match.
2. **Robbed angled goal** — the old wall resolver re-tested the goal gap
   every tick while the puck was behind the wall plane, so a diagonal shot
   that drifted sideways inside the mouth got clamped back onto the ice
   un-scored.

Fix: a goal now counts the moment the puck's CENTER crosses the goal line
(inner face of the wall band). Once behind the wall plane, only the
channel's side posts contain the puck — it is never clamped back onto the
ice. The solid (non-mouth) wall still recovers a puck shoved behind the
wall plane outside the mouth (e.g. by a paddle's positional correction), so
nothing can score "through" the solid rail.

## Game feel / tuning notes

- Hit-stop is an ACCENT, not a rhythm: it must fire rarely (only truly big
  smashes, never twice in quick succession) or the game reads as stuttery.
  First tuning pass (45ms at 420 px/s, no cooldown) froze the puck for ~13%
  of an aggressive rally — measurably not smooth. Current values:
  `HITSTOP_DURATION = 0.03s`, `HITSTOP_MIN_IMPACT = 520 px/s`,
  `HITSTOP_COOLDOWN = 0.8s`.
- `clock.tick()`'s integer-millisecond return value is too coarse for the
  physics accumulator (16 vs 17 ms truncation makes the step count
  oscillate, causing visible judder) — `main.py` measures real dt with
  `time.perf_counter()` instead, clamped to 0.25s so a stall can't cause a
  catch-up burst.
- Colors follow a "bright ice in a dark cabinet" theme, like a real arcade
  air-hockey table: pale ice framed by near-black cabinet rails. This is a
  readability decision, not just style — the dark puck needs maximum
  contrast against the ice, and both mallet colors must pop without glow
  tricks. Rink markings are classic hockey blue with a red faceoff dot,
  since white lines would vanish on white ice.
- Frozen-paddle flash uses saturated cyan-teal tones, deliberately offset
  from both the pale ice and Player 1's blue, so a locked paddle is
  unmistakable at a glance.

## Events / audio / fx pattern

`GameState.events` is a semantic gameplay event log (hits, bounces, goals,
power triggers) — data only, no rendering logic. Each event carries a
monotonically increasing `seq` so one-shot consumers (audio) can track what
they've already played; age-based consumers (render particle fx) just read
event time. Pruned by age (`EVENT_MAX_AGE`) on append.

`render._draw_event_fx` renders impact fx as a pure function of an event's
`seq` (seeding a tiny PRNG) and its age — no particle state is stored
anywhere, which keeps both rotated views in perfect sync for free.

`audio.play_new_events()` is the only runtime entry point into `audio.py`:
it walks events past the caller's last-seen seq and voices each one exactly
once. Everything is guarded — if the mixer can't initialize (no audio
device, headless CI), the module silently degrades to a no-op and the game
runs exactly as before.

## Powers design rules

- Cooldowns are tracked per `(player, power)`; a trigger is rejected
  outright (silently, no queueing) if the cooldown hasn't elapsed. Every
  power's cooldown is strictly longer than its own max active duration, so
  a single cooldown gate is also sufficient to prevent re-trigger stacking.
- Invalid triggers (freezing an already-frozen opponent, double-puck while
  one is already active) are dropped WITHOUT starting a cooldown, since
  nothing actually happened — the placeholder key press stands in for a
  gesture the player may not even realize failed.
