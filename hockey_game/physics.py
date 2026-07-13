from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pygame

import config as cfg

Vec2 = pygame.math.Vector2


@dataclass
class Paddle:
    player: int
    pos: Vec2
    vel: Vec2 = field(default_factory=lambda: Vec2(0, 0))
    radius: int = cfg.PADDLE_RADIUS

    def __post_init__(self):
        self.prev_pos = Vec2(self.pos)


@dataclass
class Puck:
    pos: Vec2
    vel: Vec2 = field(default_factory=lambda: Vec2(0, 0))
    radius: int = cfg.PUCK_RADIUS
    puck_id: int = 0
    trail: List[Tuple[float, float]] = field(default_factory=list)

    def __post_init__(self):
        self.prev_pos = Vec2(self.pos)


@dataclass
class Shield:
    owner: int
    rect: pygame.Rect
    expires_at: float


class GameState:
    def __init__(self):
        self.game_time: float = 0.0

        self.paddles: Dict[int, Paddle] = {
            1: Paddle(1, Vec2(cfg.TABLE_WIDTH * 0.5, cfg.TABLE_HEIGHT - 80)),
            2: Paddle(2, Vec2(cfg.TABLE_WIDTH * 0.5, 80)),
        }

        self.pucks: List[Puck] = [Puck(pos=self._center(), vel=Vec2(0, 0), puck_id=0)]
        self._next_puck_id = 1

        self.score: Dict[int, int] = {1: 0, 2: 0}
        self.winner: Optional[int] = None
        self.last_scorer: Optional[int] = None

        self.goal_lock_until: float = 0.0
        self.pause_until: float = 0.0
        self.hitstop_until: float = -1.0

        self.events: List[dict] = []
        self._event_seq: int = 0

        self.shields: Dict[int, Optional[Shield]] = {1: None, 2: None}
        self.freeze_until: Dict[int, float] = {1: -1.0, 2: -1.0}
        self.slow_active: Dict[int, bool] = {1: False, 2: False}
        self.speed_buff_armed_until: Dict[int, float] = {1: -1.0, 2: -1.0}
        self.double_puck_active: bool = False
        self.double_puck_expires_at: float = 0.0

        self.cooldown_ready_at: Dict[Tuple[int, str], float] = {}

    @staticmethod
    def _center() -> Vec2:
        return Vec2(cfg.TABLE_WIDTH / 2, cfg.TABLE_HEIGHT / 2)

    def opponent(self, player: int) -> int:
        return 2 if player == 1 else 1

    def is_frozen(self, player: int) -> bool:
        return self.game_time < self.freeze_until[player]

    def emit(self, kind: str, pos: Vec2, **data):
        self._event_seq += 1
        self.events.append({
            "seq": self._event_seq, "kind": kind, "time": self.game_time,
            "pos": (pos.x, pos.y), **data,
        })
        cutoff = self.game_time - cfg.EVENT_MAX_AGE
        self.events = [e for e in self.events if e["time"] >= cutoff]

    def reset_after_goal(self, conceder: int):
        serve_y = cfg.TABLE_HEIGHT * (cfg.SERVE_Y_FRAC if conceder == 1 else 1 - cfg.SERVE_Y_FRAC)
        self.pucks = [Puck(pos=Vec2(cfg.TABLE_WIDTH / 2, serve_y), vel=Vec2(0, 0), puck_id=0)]
        self.double_puck_active = False
        self.pause_until = self.game_time + cfg.GOAL_PAUSE_DURATION
        self.goal_lock_until = self.game_time + cfg.GOAL_SCORE_DEBOUNCE

    def spawn_extra_puck(self):
        import random
        angle = random.uniform(0, 6.28318)
        nudge = Vec2(1, 0).rotate_rad(angle) * 150.0
        self.pucks.append(Puck(pos=self._center(), vel=nudge, puck_id=self._next_puck_id))
        self._next_puck_id += 1
        self.double_puck_active = True
        self.double_puck_expires_at = self.game_time + cfg.DOUBLE_PUCK_DURATION

    def clear_extra_puck(self):
        self.pucks = [p for p in self.pucks if p.puck_id == 0]
        self.double_puck_active = False


def paddle_bounds(player: int, radius: int) -> Tuple[float, float, float, float]:
    min_x = cfg.WALL_THICKNESS + radius
    max_x = cfg.TABLE_WIDTH - cfg.WALL_THICKNESS - radius
    if player == 1:
        min_y = cfg.CENTER_LINE_Y + radius
        max_y = cfg.TABLE_HEIGHT - cfg.WALL_THICKNESS - radius
    else:
        min_y = cfg.WALL_THICKNESS + radius
        max_y = cfg.CENTER_LINE_Y - radius
    return min_x, max_x, min_y, max_y


def move_paddle(paddle: Paddle, direction: Vec2, dt: float):
    old_pos = Vec2(paddle.pos)
    if direction.length_squared() > 0:
        direction = direction.normalize()
    new_pos = paddle.pos + direction * cfg.PADDLE_SPEED * dt

    min_x, max_x, min_y, max_y = paddle_bounds(paddle.player, paddle.radius)
    new_pos.x = max(min_x, min(max_x, new_pos.x))
    new_pos.y = max(min_y, min(max_y, new_pos.y))

    paddle.pos = new_pos
    paddle.vel = (new_pos - old_pos) / dt if dt > 0 else Vec2(0, 0)


def _in_goal_mouth(x: float) -> bool:
    return cfg.GOAL_X_MIN <= x <= cfg.GOAL_X_MAX


def integrate_puck(puck: Puck, dt: float, slow_multiplier: float):
    decay = (1.0 - cfg.PUCK_FRICTION_PER_SEC) ** dt
    puck.vel *= decay

    speed = puck.vel.length()
    if speed > cfg.PUCK_MAX_SPEED:
        puck.vel.scale_to_length(cfg.PUCK_MAX_SPEED)

    puck.pos += puck.vel * dt * slow_multiplier


def resolve_side_walls(puck: Puck) -> Optional[float]:
    left = cfg.WALL_THICKNESS + puck.radius
    right = cfg.TABLE_WIDTH - cfg.WALL_THICKNESS - puck.radius
    if puck.pos.x < left:
        impact = abs(puck.vel.x)
        puck.pos.x = left
        puck.vel.x = -puck.vel.x * cfg.WALL_RESTITUTION
        return impact
    elif puck.pos.x > right:
        impact = abs(puck.vel.x)
        puck.pos.x = right
        puck.vel.x = -puck.vel.x * cfg.WALL_RESTITUTION
        return impact
    return None


def resolve_top_bottom_walls(puck: Puck) -> Optional[float]:
    top = cfg.WALL_THICKNESS + puck.radius
    bottom = cfg.TABLE_HEIGHT - cfg.WALL_THICKNESS - puck.radius

    if top <= puck.pos.y <= bottom:
        return None

    if _in_goal_mouth(puck.pos.x):
        post_left = cfg.GOAL_X_MIN + puck.radius
        post_right = cfg.GOAL_X_MAX - puck.radius
        if puck.pos.x < post_left:
            impact = abs(puck.vel.x)
            puck.pos.x = post_left
            puck.vel.x = -puck.vel.x * cfg.WALL_RESTITUTION
            return impact
        if puck.pos.x > post_right:
            impact = abs(puck.vel.x)
            puck.pos.x = post_right
            puck.vel.x = -puck.vel.x * cfg.WALL_RESTITUTION
            return impact
        return None

    impact = abs(puck.vel.y)
    if puck.pos.y < top:
        puck.pos.y = top
    else:
        puck.pos.y = bottom
    puck.vel.y = -puck.vel.y * cfg.WALL_RESTITUTION
    return impact


def check_goal(puck: Puck) -> Optional[int]:
    if not _in_goal_mouth(puck.pos.x):
        return None
    if puck.pos.y < cfg.WALL_THICKNESS:
        return 1
    if puck.pos.y > cfg.TABLE_HEIGHT - cfg.WALL_THICKNESS:
        return 2
    return None


def resolve_shield(puck: Puck, shield: Shield) -> bool:
    closest_x = max(shield.rect.left, min(puck.pos.x, shield.rect.right))
    closest_y = max(shield.rect.top, min(puck.pos.y, shield.rect.bottom))
    dx = puck.pos.x - closest_x
    dy = puck.pos.y - closest_y
    if dx * dx + dy * dy >= puck.radius * puck.radius:
        return False

    if puck.pos.y < shield.rect.centery:
        puck.pos.y = shield.rect.top - puck.radius
    else:
        puck.pos.y = shield.rect.bottom + puck.radius
    puck.vel.y = -puck.vel.y * cfg.WALL_RESTITUTION
    return True


def circle_collision(pos_a: Vec2, radius_a: float, pos_b: Vec2, radius_b: float) -> bool:
    dist_sq = (pos_a - pos_b).length_squared()
    return dist_sq < (radius_a + radius_b) ** 2


def resolve_paddle_puck(puck: Puck, paddle: Paddle) -> Optional[float]:
    delta = puck.pos - paddle.pos
    dist = delta.length()
    min_dist = puck.radius + paddle.radius
    if dist >= min_dist:
        return None
    if dist == 0:
        delta = Vec2(0, -1)
        dist = 1.0
    normal = delta.normalize()

    puck.pos = paddle.pos + normal * min_dist

    relative_vel = puck.vel - paddle.vel
    vel_along_normal = relative_vel.dot(normal)
    impact = max(0.0, -vel_along_normal)
    if vel_along_normal < 0:
        relative_vel -= 2 * vel_along_normal * normal
    puck.vel = relative_vel + paddle.vel

    speed = puck.vel.length()
    if speed > cfg.PUCK_MAX_SPEED:
        puck.vel.scale_to_length(cfg.PUCK_MAX_SPEED)
    return impact
