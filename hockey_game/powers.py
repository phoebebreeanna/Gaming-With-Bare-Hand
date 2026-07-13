from typing import Optional

import pygame

import config as cfg
from physics import GameState, Puck, Shield

Vec2 = pygame.math.Vector2


class PowerManager:
    def __init__(self):
        self._slow_activated_at = {1: -1.0, 2: -1.0}

    def _ready(self, state: GameState, player: int, power: str) -> bool:
        return state.game_time >= state.cooldown_ready_at.get((player, power), 0.0)

    def _start_cooldown(self, state: GameState, player: int, power: str, duration: float):
        state.cooldown_ready_at[(player, power)] = state.game_time + duration

    def handle_triggers(self, state: GameState, input_source):
        for player in (1, 2):
            for power in input_source.get_triggered_powers(player):
                if not self._ready(state, player, power):
                    continue
                fired = {
                    "shield": self._trigger_shield,
                    "freeze": self._trigger_freeze,
                    "double_puck": self._trigger_double_puck,
                    "slow_puck": self._trigger_slow_puck,
                    "speed_puck": self._trigger_speed_puck,
                }[power](state, player)
                if fired:
                    state.emit("power", state.paddles[player].pos,
                               player=player, power=power)

        self._update_slow_hold(state, input_source)

    def _update_slow_hold(self, state: GameState, input_source):
        for player in (1, 2):
            if not state.slow_active[player]:
                continue
            held = input_source.is_power_held(player, "slow_puck")
            expired = state.game_time >= self._slow_activated_at[player] + cfg.SLOW_PUCK_MAX_DURATION
            if not held or expired:
                state.slow_active[player] = False

    def _trigger_shield(self, state: GameState, player: int):
        x_min = cfg.GOAL_X_MIN - cfg.SHIELD_MARGIN
        width = (cfg.GOAL_X_MAX - cfg.GOAL_X_MIN) + 2 * cfg.SHIELD_MARGIN
        if player == 1:
            y_center = cfg.TABLE_HEIGHT - cfg.SHIELD_OFFSET
        else:
            y_center = cfg.SHIELD_OFFSET
        rect = pygame.Rect(
            int(x_min), int(y_center - cfg.SHIELD_THICKNESS / 2),
            int(width), int(cfg.SHIELD_THICKNESS),
        )
        state.shields[player] = Shield(owner=player, rect=rect, expires_at=state.game_time + cfg.SHIELD_DURATION)
        self._start_cooldown(state, player, "shield", cfg.SHIELD_COOLDOWN)
        return True

    def _trigger_freeze(self, state: GameState, player: int):
        opp = state.opponent(player)
        if state.is_frozen(opp):
            return
        state.freeze_until[opp] = state.game_time + cfg.FREEZE_DURATION
        self._start_cooldown(state, player, "freeze", cfg.FREEZE_COOLDOWN)
        return True

    def _trigger_double_puck(self, state: GameState, player: int):
        if state.double_puck_active:
            return
        state.spawn_extra_puck()
        self._start_cooldown(state, player, "double_puck", cfg.DOUBLE_PUCK_COOLDOWN)
        return True

    def _trigger_slow_puck(self, state: GameState, player: int):
        if state.slow_active[player]:
            return
        state.slow_active[player] = True
        self._slow_activated_at[player] = state.game_time
        self._start_cooldown(state, player, "slow_puck", cfg.SLOW_PUCK_COOLDOWN)
        return True

    def _trigger_speed_puck(self, state: GameState, player: int):
        if state.game_time < state.speed_buff_armed_until[player]:
            return
        state.speed_buff_armed_until[player] = state.game_time + cfg.SPEED_PUCK_WINDOW
        self._start_cooldown(state, player, "speed_puck", cfg.SPEED_PUCK_COOLDOWN)
        return True

    def step_cleanup(self, state: GameState):
        if state.double_puck_active and state.game_time >= state.double_puck_expires_at:
            state.clear_extra_puck()

        for player in (1, 2):
            shield = state.shields[player]
            if shield is not None and state.game_time >= shield.expires_at:
                state.shields[player] = None

    def slow_multiplier(self, state: GameState, puck: Puck) -> float:
        y = puck.pos.y
        if state.slow_active[1] and y > cfg.CENTER_LINE_Y:
            return cfg.SLOW_PUCK_FACTOR
        if state.slow_active[2] and y < cfg.CENTER_LINE_Y:
            return cfg.SLOW_PUCK_FACTOR
        return 1.0

    def maybe_apply_speed_buff(self, state: GameState, player: int, puck: Puck):
        if state.game_time >= state.speed_buff_armed_until[player]:
            return
        puck.vel *= cfg.SPEED_PUCK_BOOST
        if puck.vel.length() > cfg.PUCK_MAX_SPEED:
            puck.vel.scale_to_length(cfg.PUCK_MAX_SPEED)
        state.speed_buff_armed_until[player] = -1.0
