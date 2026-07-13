import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

pygame.init()

import config as cfg
from physics import GameState
from powers import PowerManager
from input_handler import InputSource
from main import physics_step

Vec2 = pygame.math.Vector2


class _NullInput(InputSource):
    def update(self, events): pass
    def get_paddle_position(self, player_id): return Vec2(0, 0)
    def get_triggered_powers(self, player_id): return set()
    def is_power_held(self, player_id, power): return False


def _make_state(puck_pos, puck_vel):
    state = GameState()
    state.paddles[1].pos = Vec2(60, cfg.TABLE_HEIGHT - 80)
    state.paddles[2].pos = Vec2(60, 80)
    state.pucks[0].pos = Vec2(puck_pos)
    state.pucks[0].vel = Vec2(puck_vel)
    return state


def _run(state, seconds):
    pm, inp = PowerManager(), _NullInput()
    for _ in range(int(seconds / cfg.PHYSICS_DT)):
        physics_step(state, inp, pm, cfg.PHYSICS_DT)
    return state


class GoalDetectionTests(unittest.TestCase):

    def test_fast_shot_scores_top_goal_for_p1(self):
        state = _run(_make_state((250, cfg.TABLE_HEIGHT / 2), (0, -600)), 3.0)
        self.assertEqual(state.score, {1: 1, 2: 0})
        self.assertEqual(state.last_scorer, 1)

    def test_fast_shot_scores_bottom_goal_for_p2(self):
        state = _run(_make_state((250, cfg.TABLE_HEIGHT / 2), (0, 600)), 3.0)
        self.assertEqual(state.score, {1: 0, 2: 1})
        self.assertEqual(state.last_scorer, 2)

    def test_slow_dribbler_still_scores(self):
        state = _run(_make_state((210, 45), (0, -30)), 8.0)
        self.assertEqual(state.score, {1: 1, 2: 0})

    def test_angled_shot_near_post_still_scores(self):
        state = _run(_make_state((160, 60), (-260, -560)), 3.0)
        self.assertEqual(state.score, {1: 1, 2: 0})

    def test_shot_outside_mouth_bounces_and_never_scores(self):
        state = _make_state((60, 200), (0, -600))
        _run(state, 3.0)
        self.assertEqual(state.score, {1: 0, 2: 0})
        puck = state.pucks[0]
        self.assertGreaterEqual(puck.pos.y, cfg.WALL_THICKNESS + puck.radius - 1e-6)

    def test_paddle_pushthrough_outside_mouth_is_recovered_not_scored(self):
        state = _make_state((60, 45), (0, 0))
        state.paddles[2].pos = Vec2(60, 60)
        _run(state, 1.0)
        self.assertEqual(state.score, {1: 0, 2: 0})
        self.assertGreaterEqual(state.pucks[0].pos.y, cfg.WALL_THICKNESS)

    def test_winning_goal_sets_winner(self):
        state = _make_state((250, cfg.TABLE_HEIGHT / 2), (0, -600))
        state.score[1] = cfg.SCORE_TO_WIN - 1
        _run(state, 3.0)
        self.assertEqual(state.winner, 1)
        self.assertIn("win", [e["kind"] for e in state.events])

    def test_goal_event_emitted_and_serve_goes_to_conceder(self):
        state = _run(_make_state((250, cfg.TABLE_HEIGHT / 2), (0, -600)), 3.0)
        self.assertIn("goal", [e["kind"] for e in state.events])
        puck = state.pucks[0]
        self.assertLess(puck.pos.y, cfg.CENTER_LINE_Y)
        self.assertEqual(puck.vel.length(), 0)

    def test_goal_only_after_center_crosses_line(self):
        from physics import check_goal, Puck
        self.assertIsNone(check_goal(Puck(pos=Vec2(210, cfg.WALL_THICKNESS))))
        self.assertEqual(check_goal(Puck(pos=Vec2(210, cfg.WALL_THICKNESS - 1))), 1)
        self.assertIsNone(check_goal(Puck(pos=Vec2(210, cfg.TABLE_HEIGHT - cfg.WALL_THICKNESS))))
        self.assertEqual(check_goal(Puck(pos=Vec2(210, cfg.TABLE_HEIGHT - cfg.WALL_THICKNESS + 1))), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
