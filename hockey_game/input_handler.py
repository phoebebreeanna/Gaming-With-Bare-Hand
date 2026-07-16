from abc import ABC, abstractmethod
from typing import Dict, Set, Tuple

import pygame

import config as cfg

Vec2 = pygame.math.Vector2


class InputSource(ABC):
    @abstractmethod
    def update(self, events):
        pass

    @abstractmethod
    def get_paddle_position(self, player_id: int) -> Vec2:
        pass

    @abstractmethod
    def get_triggered_powers(self, player_id: int) -> Set[str]:
        pass

    @abstractmethod
    def is_power_held(self, player_id: int, power: str) -> bool:
        pass


class KeyboardInput(InputSource):
    def __init__(self):
        self._pressed: Dict[int, bool] = {}
        self._prev_pressed: Dict[int, bool] = {}

    def update(self, events):
        self._prev_pressed = dict(self._pressed)
        keys = pygame.key.get_pressed()
        self._pressed = {}
        for player_binds in cfg.KEYBINDS.values():
            for key in player_binds["move"].values():
                self._pressed[key] = bool(keys[key])
            for key in player_binds["powers"].values():
                self._pressed[key] = bool(keys[key])

    def _was_just_pressed(self, key: int) -> bool:
        return self._pressed.get(key, False) and not self._prev_pressed.get(key, False)

    def get_paddle_position(self, player_id: int) -> Vec2:
        binds = cfg.KEYBINDS[player_id]["move"]
        raw = Vec2(0, 0)
        if self._pressed.get(binds["up"]):
            raw.y -= 1
        if self._pressed.get(binds["down"]):
            raw.y += 1
        if self._pressed.get(binds["left"]):
            raw.x -= 1
        if self._pressed.get(binds["right"]):
            raw.x += 1
        return raw

    def get_triggered_powers(self, player_id: int) -> Set[str]:
        binds = cfg.KEYBINDS[player_id]["powers"]
        return {name for name, key in binds.items() if self._was_just_pressed(key)}

    def is_power_held(self, player_id: int, power: str) -> bool:
        key = cfg.KEYBINDS[player_id]["powers"][power]
        return self._pressed.get(key, False)
