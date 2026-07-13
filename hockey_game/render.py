import math
import random

import pygame
import pygame.gfxdraw

import config as cfg
from physics import GameState

Vec2 = pygame.math.Vector2

POWER_ORDER = ["shield", "freeze", "double_puck", "slow_puck", "speed_puck"]
POWER_COOLDOWNS = {
    "shield": cfg.SHIELD_COOLDOWN,
    "freeze": cfg.FREEZE_COOLDOWN,
    "double_puck": cfg.DOUBLE_PUCK_COOLDOWN,
    "slow_puck": cfg.SLOW_PUCK_COOLDOWN,
    "speed_puck": cfg.SPEED_PUCK_COOLDOWN,
}

_TOP_GOAL_OWNER = 2
_BOTTOM_GOAL_OWNER = 1


def transform_point(p: Vec2, rotation: int) -> Vec2:
    if rotation == 0:
        return Vec2(p)
    return Vec2(cfg.TABLE_WIDTH - p.x, cfg.TABLE_HEIGHT - p.y)


def transform_rect(rect: pygame.Rect, rotation: int) -> pygame.Rect:
    if rotation == 0:
        return rect.copy()
    p1 = transform_point(Vec2(rect.left, rect.top), rotation)
    p2 = transform_point(Vec2(rect.right, rect.bottom), rotation)
    x_min, x_max = sorted((p1.x, p2.x))
    y_min, y_max = sorted((p1.y, p2.y))
    return pygame.Rect(int(x_min), int(y_min), int(x_max - x_min), int(y_max - y_min))


def _lerp_color(c1, c2, t):
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


_ice_gradient_cache = {}


def _get_ice_gradient(width: int, height: int) -> pygame.Surface:
    key = (width, height)
    surf = _ice_gradient_cache.get(key)
    if surf is not None:
        return surf
    surf = pygame.Surface((width, height))
    for y in range(height):
        t = y / max(height - 1, 1)
        pygame.draw.line(surf, _lerp_color(cfg.COLOR_ICE_NEAR, cfg.COLOR_ICE_FAR, t), (0, y), (width, y))
    _ice_gradient_cache[key] = surf
    return surf


def _draw_glow_rect(surface: pygame.Surface, rect: pygame.Rect, color, layers=4, max_alpha=80, radius=8):
    glow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    for i in range(layers):
        alpha = int(max_alpha * (1 - i / layers))
        inset = i * 4
        r = pygame.Rect(inset, inset, rect.width - 2 * inset, rect.height - 2 * inset)
        if r.width > 0 and r.height > 0:
            pygame.draw.rect(glow, (*color, alpha), r, border_radius=radius)
    surface.blit(glow, rect.topleft)


_font_cache = {}


def _get_font(size: int, bold: bool = True) -> pygame.font.Font:
    key = (size, bold)
    font = _font_cache.get(key)
    if font is None:
        font = pygame.font.SysFont("arial", size, bold=bold)
        _font_cache[key] = font
    return font


def _aa_filled_circle(surface: pygame.Surface, center, radius: int, color):
    x, y, r = int(center[0]), int(center[1]), int(radius)
    pygame.gfxdraw.filled_circle(surface, x, y, r, color)
    pygame.gfxdraw.aacircle(surface, x, y, r, color)


def _draw_rail_and_ice(surface: pygame.Surface):
    outer = pygame.Rect(0, 0, cfg.TABLE_WIDTH, cfg.TABLE_HEIGHT)
    pygame.draw.rect(surface, cfg.COLOR_RAIL_DARK, outer, border_radius=cfg.CORNER_RADIUS)

    bevel = outer.inflate(-4, -4)
    pygame.draw.rect(surface, cfg.COLOR_RAIL_BEVEL, bevel, border_radius=max(cfg.CORNER_RADIUS - 3, 0))

    wt = cfg.WALL_THICKNESS
    ice_rect = pygame.Rect(wt, wt, cfg.TABLE_WIDTH - 2 * wt, cfg.TABLE_HEIGHT - 2 * wt)
    surface.blit(_get_ice_gradient(ice_rect.width, ice_rect.height), ice_rect.topleft)

    pygame.draw.rect(surface, (*cfg.COLOR_RAIL_BEVEL,), ice_rect, width=2, border_radius=6)


def _draw_goal(surface: pygame.Surface, at_top: bool):
    wt = cfg.WALL_THICKNESS
    owner = _TOP_GOAL_OWNER if at_top else _BOTTOM_GOAL_OWNER
    color = cfg.PLAYER_COLORS[owner]

    slot_y = 0 if at_top else cfg.TABLE_HEIGHT - wt
    slot = pygame.Rect(cfg.GOAL_X_MIN, slot_y, cfg.GOAL_WIDTH, wt)
    pygame.draw.rect(surface, cfg.COLOR_GOAL_MOUTH, slot)

    glow_h = 46
    glow_y = 0 if at_top else cfg.TABLE_HEIGHT - glow_h
    glow_rect = pygame.Rect(cfg.GOAL_X_MIN - 14, glow_y, cfg.GOAL_WIDTH + 28, glow_h)
    _draw_glow_rect(surface, glow_rect, color, layers=5, max_alpha=60, radius=10)

    line_y = wt if at_top else cfg.TABLE_HEIGHT - wt
    pygame.draw.line(surface, color, (cfg.GOAL_X_MIN, line_y), (cfg.GOAL_X_MAX, line_y), 3)


def _draw_center_markings(surface: pygame.Surface):
    dash_w, gap_w = 14, 10
    x = cfg.WALL_THICKNESS
    while x < cfg.TABLE_WIDTH - cfg.WALL_THICKNESS:
        x_end = min(x + dash_w, cfg.TABLE_WIDTH - cfg.WALL_THICKNESS)
        pygame.draw.line(surface, cfg.COLOR_LINE, (x, cfg.CENTER_LINE_Y), (x_end, cfg.CENTER_LINE_Y), 2)
        x += dash_w + gap_w

    center = (cfg.TABLE_WIDTH / 2, cfg.CENTER_LINE_Y)
    pygame.gfxdraw.aacircle(surface, int(center[0]), int(center[1]), cfg.CENTER_CIRCLE_RADIUS, cfg.COLOR_LINE)
    pygame.gfxdraw.aacircle(surface, int(center[0]), int(center[1]), 4, cfg.COLOR_LINE_ACCENT)
    pygame.gfxdraw.filled_circle(surface, int(center[0]), int(center[1]), 3, cfg.COLOR_LINE_ACCENT)


def _draw_shields(surface: pygame.Surface, state: GameState, rotation: int):
    for owner, shield in state.shields.items():
        if shield is None:
            continue
        r = transform_rect(shield.rect, rotation)
        color = cfg.PLAYER_COLORS[owner]
        overlay = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        overlay.fill((*color, 50))
        pygame.draw.rect(overlay, (*color, 200), overlay.get_rect(), width=2, border_radius=4)
        surface.blit(overlay, r.topleft)


def _lerp_pos(entity, alpha: float) -> Vec2:
    return entity.prev_pos.lerp(entity.pos, alpha)


def _draw_pucks(surface: pygame.Surface, state: GameState, rotation: int, alpha: float):
    for puck in state.pucks:
        if puck.vel.length_squared() >= cfg.PUCK_TRAIL_MIN_SPEED ** 2 and len(puck.trail) > 1:
            n = len(puck.trail)
            for i, (tx, ty) in enumerate(puck.trail[:-1]):
                t = (i + 1) / n
                tp = transform_point(Vec2(tx, ty), rotation)
                trail_alpha = int(70 * t)
                radius = max(1, int(puck.radius * (0.25 + 0.55 * t)))
                pygame.gfxdraw.filled_circle(
                    surface, int(tp.x), int(tp.y), radius, (*cfg.COLOR_PUCK_TRAIL, trail_alpha))

        p = transform_point(_lerp_pos(puck, alpha), rotation)
        cx, cy, r = int(p.x), int(p.y), puck.radius
        rim_color = cfg.COLOR_PUCK_EXTRA_RIM if puck.puck_id != 0 else cfg.COLOR_PUCK_RIM
        _aa_filled_circle(surface, (cx, cy), r, rim_color)
        _aa_filled_circle(surface, (cx, cy), max(r - 4, 1), cfg.COLOR_PUCK_BODY)
        pygame.gfxdraw.filled_circle(surface, cx - r // 3, cy - r // 3, max(r // 5, 1), (255, 255, 255, 90))


def _draw_paddles(surface: pygame.Surface, state: GameState, rotation: int, alpha: float):
    flash_on = int(state.game_time * 8) % 2 == 0
    for player, paddle in state.paddles.items():
        p = transform_point(_lerp_pos(paddle, alpha), rotation)
        cx, cy, r = int(p.x), int(p.y), paddle.radius
        frozen = state.is_frozen(player)

        if frozen:
            ring = pygame.Surface((r * 2 + 16, r * 2 + 16), pygame.SRCALPHA)
            pulse = 6 + int(4 * abs((state.game_time * 3) % 2 - 1))
            pygame.gfxdraw.aacircle(ring, r + 8, r + 8, r + pulse, (*cfg.PLAYER_FROZEN_COLOR, 160))
            surface.blit(ring, (cx - r - 8, cy - r - 8))
            body_color = cfg.PLAYER_FROZEN_COLOR if flash_on else cfg.PLAYER_FROZEN_DARK
            knob_color = cfg.PLAYER_FROZEN_DARK if flash_on else cfg.PLAYER_FROZEN_COLOR
        else:
            body_color = cfg.PLAYER_COLORS[player]
            knob_color = cfg.PLAYER_MALLET_KNOB[player]

        _aa_filled_circle(surface, (cx, cy), r, (30, 30, 34))
        _aa_filled_circle(surface, (cx, cy), r - 2, body_color)
        _aa_filled_circle(surface, (cx, cy), max(r - 9, 2), knob_color)

        if state.game_time < state.speed_buff_armed_until[player]:
            pygame.gfxdraw.aacircle(surface, cx, cy, r + 3, cfg.PLAYER_SPEED_BUFF_COLOR)
            pygame.gfxdraw.aacircle(surface, cx, cy, r + 4, cfg.PLAYER_SPEED_BUFF_COLOR)


_FX_LIFE = {"paddle_hit": 0.35, "wall_bounce": 0.25, "shield_block": 0.4, "goal": 0.9}


def _draw_event_fx(surface: pygame.Surface, state: GameState, rotation: int):
    for event in state.events:
        kind = event["kind"]
        life = _FX_LIFE.get(kind)
        if life is None:
            continue
        age = state.game_time - event["time"]
        if not (0.0 <= age < life):
            continue
        frac = age / life
        fade = 1.0 - frac
        p = transform_point(Vec2(event["pos"]), rotation)

        if kind == "goal":
            scorer = event.get("scorer", 1)
            color = cfg.PLAYER_COLORS[scorer]
            if age < 0.22:
                flash = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
                flash.fill((*color, int(42 * (1 - age / 0.22))))
                surface.blit(flash, (0, 0))
            ring_r = int(20 + 180 * frac)
            spark_count, spark_speed, spark_r = 14, 300, 3
        elif kind == "shield_block":
            color = cfg.SHIELD_COLOR
            ring_r = int(12 + 90 * frac)
            spark_count, spark_speed, spark_r = 8, 180, 2
        elif kind == "paddle_hit":
            impact = event.get("impact", 0.0)
            if impact < cfg.WALL_EVENT_MIN_IMPACT:
                continue
            color = cfg.PLAYER_COLORS.get(event.get("player", 1), cfg.COLOR_LINE)
            punch = min(1.0, impact / cfg.PUCK_MAX_SPEED)
            ring_r = int(10 + (40 + 70 * punch) * frac)
            spark_count, spark_speed, spark_r = 4 + int(6 * punch), 140 + 160 * punch, 2
        else:
            color = cfg.COLOR_LINE
            ring_r = int(6 + 30 * frac)
            spark_count, spark_speed, spark_r = 4, 110, 1

        alpha = int(190 * fade)
        cx, cy = int(p.x), int(p.y)
        if 0 <= cx < surface.get_width() and -40 <= cy < surface.get_height() + 40:
            pygame.gfxdraw.aacircle(surface, cx, cy, max(ring_r, 1), (*color, alpha))
            rng = random.Random(event["seq"])
            for _ in range(spark_count):
                ang = rng.uniform(0, math.tau)
                speed = spark_speed * rng.uniform(0.6, 1.0)
                sx = cx + math.cos(ang) * speed * age
                sy = cy + math.sin(ang) * speed * age
                pygame.gfxdraw.filled_circle(
                    surface, int(sx), int(sy), spark_r, (*color, alpha))


def _draw_table_surface(surface: pygame.Surface, state: GameState, rotation: int, alpha: float):
    surface.fill(cfg.COLOR_BG)
    _draw_rail_and_ice(surface)
    _draw_goal(surface, at_top=True)
    _draw_goal(surface, at_top=False)
    _draw_center_markings(surface)
    _draw_shields(surface, state, rotation)
    _draw_pucks(surface, state, rotation, alpha)
    _draw_paddles(surface, state, rotation, alpha)
    _draw_event_fx(surface, state, rotation)


def draw_score_panel(surface: pygame.Surface, state: GameState, viewer_player: int):
    bar = surface.get_rect()
    surface.fill(cfg.COLOR_HUD_PANEL)
    half_w = bar.width // 2
    pygame.draw.rect(surface, cfg.PLAYER_COLORS[1], (0, 0, half_w, bar.height))
    pygame.draw.rect(surface, cfg.PLAYER_COLORS[2], (half_w, 0, bar.width - half_w, bar.height))
    shade = pygame.Surface(bar.size, pygame.SRCALPHA)
    shade.fill((*cfg.COLOR_HUD_PANEL, 165))
    surface.blit(shade, (0, 0))
    pygame.draw.line(surface, cfg.COLOR_RAIL_BEVEL, (0, bar.height - 1), (bar.width, bar.height - 1), 2)

    center_y = bar.height // 2 - 4
    goal_age = state.game_time - (state.pause_until - cfg.GOAL_PAUSE_DURATION)
    for player, dx in ((1, -34), (2, 34)):
        size = 26
        if state.last_scorer == player and 0 <= goal_age < cfg.SCORE_POP_TIME:
            size = int(26 * (1 + 0.5 * (1 - goal_age / cfg.SCORE_POP_TIME)))
        num = _get_font(size).render(str(state.score[player]), True, cfg.PLAYER_COLORS[player])
        surface.blit(num, num.get_rect(center=(bar.centerx + dx, center_y)))
    colon = _get_font(20).render(":", True, cfg.COLOR_TEXT_DIM)
    surface.blit(colon, colon.get_rect(center=(bar.centerx, center_y)))

    pip_y = bar.height - 7
    for player, direction in ((1, -1), (2, 1)):
        for i in range(cfg.SCORE_TO_WIN):
            px = bar.centerx + direction * (16 + i * 11)
            if i < state.score[player]:
                pygame.gfxdraw.filled_circle(surface, px, pip_y, 3, cfg.PLAYER_COLORS[player])
                pygame.gfxdraw.aacircle(surface, px, pip_y, 3, cfg.PLAYER_COLORS[player])
            else:
                pygame.gfxdraw.aacircle(surface, px, pip_y, 3, (*cfg.COLOR_TEXT_DIM, 110))

    you_color = cfg.PLAYER_COLORS[viewer_player]
    you_x = 10 if viewer_player == 1 else bar.width - 10
    align = "left" if viewer_player == 1 else "right"
    _blit_aligned(surface, f"P{viewer_player} (you)", (you_x, bar.height // 2), you_color, align)


def _blit_aligned(surface, text, pos, color, align="left", size=13):
    rendered = _get_font(size).render(text, True, color)
    rect = rendered.get_rect()
    if align == "left":
        rect.midleft = pos
    elif align == "right":
        rect.midright = pos
    else:
        rect.midtop = pos
    surface.blit(rendered, rect)


def draw_power_dock(surface: pygame.Surface, state: GameState, viewer_player: int):
    surface.fill(cfg.COLOR_HUD_PANEL)
    pygame.draw.line(surface, cfg.COLOR_RAIL_BEVEL, (0, 0), (surface.get_width(), 0), 2)

    dock = surface.get_rect()
    chip_w, chip_h, gap = 76, 42, 6
    total_w = 5 * chip_w + 4 * gap
    x0 = (dock.width - total_w) / 2
    y = (dock.height - chip_h) / 2
    color = cfg.PLAYER_COLORS[viewer_player]

    for i, power in enumerate(POWER_ORDER):
        abbrev = cfg.POWER_ABBREV[power]
        key_label = cfg.POWER_KEY_LABEL[viewer_player][power]
        box = pygame.Rect(int(x0 + i * (chip_w + gap)), int(y), chip_w, chip_h)
        ready_at = state.cooldown_ready_at.get((viewer_player, power), 0.0)
        remaining = max(0.0, ready_at - state.game_time)
        total = POWER_COOLDOWNS[power]
        ready_ratio = 0.0 if total <= 0 else 1.0 - min(1.0, remaining / total)

        chip = pygame.Surface(box.size, pygame.SRCALPHA)
        chip.fill((*cfg.COLOR_RAIL_DARK, 235))
        fill_h = int(box.height * ready_ratio)
        if fill_h > 0:
            pygame.draw.rect(chip, (*color, 220), (0, box.height - fill_h, box.width, fill_h))
        pygame.draw.rect(chip, cfg.COLOR_TEXT_DIM, chip.get_rect(), width=1, border_radius=6)
        surface.blit(chip, box.topleft)

        label_color = cfg.COLOR_TEXT if ready_ratio >= 1.0 else cfg.COLOR_TEXT_DIM
        abbrev_text = _get_font(15).render(abbrev, True, label_color)
        surface.blit(abbrev_text, abbrev_text.get_rect(center=(box.centerx, box.top + 14)))
        key_text = _get_font(11, bold=False).render(f"[{key_label}]", True, label_color)
        surface.blit(key_text, key_text.get_rect(center=(box.centerx, box.top + 31)))


def _draw_keycap(surface: pygame.Surface, label: str, midleft, size: int = 14) -> pygame.Rect:
    text = _get_font(size).render(label, True, cfg.COLOR_TEXT)
    cap_w = max(text.get_width() + 16, 28)
    cap_h = 26
    rect = pygame.Rect(int(midleft[0]), int(midleft[1] - cap_h / 2), cap_w, cap_h)
    base = rect.move(0, 2)
    pygame.draw.rect(surface, (14, 18, 26), base, border_radius=6)
    pygame.draw.rect(surface, cfg.COLOR_KEYCAP, rect, border_radius=6)
    pygame.draw.rect(surface, cfg.COLOR_KEYCAP_BORDER, rect, width=1, border_radius=6)
    surface.blit(text, text.get_rect(center=(rect.centerx, rect.centery - 1)))
    return rect


def _draw_mini_rink(surface: pygame.Surface, center, rink_w: int = 500, rink_h: int = 92):
    rect = pygame.Rect(0, 0, rink_w, rink_h)
    rect.center = center
    pygame.draw.rect(surface, cfg.COLOR_RAIL_DARK, rect.inflate(18, 18), border_radius=16)
    pygame.draw.rect(surface, cfg.COLOR_RAIL_BEVEL, rect.inflate(10, 10), width=2, border_radius=13)
    pygame.draw.rect(surface, cfg.COLOR_ICE_NEAR, rect, border_radius=8)

    cy = rect.centery
    y = rect.top + 5
    while y < rect.bottom - 5:
        pygame.draw.line(surface, cfg.COLOR_LINE, (rect.centerx, y), (rect.centerx, min(y + 8, rect.bottom - 5)), 2)
        y += 14
    pygame.gfxdraw.aacircle(surface, rect.centerx, cy, 24, cfg.COLOR_LINE)
    pygame.gfxdraw.filled_circle(surface, rect.centerx, cy, 3, cfg.COLOR_LINE_ACCENT)

    for player, gx in ((1, rect.left), (2, rect.right - 7)):
        pygame.draw.rect(surface, cfg.COLOR_GOAL_MOUTH, (gx, cy - 19, 7, 38))
        pygame.draw.line(surface, cfg.PLAYER_COLORS[player],
                         (rect.left + 8 if player == 1 else rect.right - 8, cy - 19),
                         (rect.left + 8 if player == 1 else rect.right - 8, cy + 19), 2)

    for player, mx in ((1, rect.left + rink_w // 5), (2, rect.right - rink_w // 5)):
        pygame.gfxdraw.filled_circle(surface, mx, cy, 13, (30, 30, 34))
        pygame.gfxdraw.aacircle(surface, mx, cy, 13, (30, 30, 34))
        pygame.gfxdraw.filled_circle(surface, mx, cy, 11, cfg.PLAYER_COLORS[player])
        pygame.gfxdraw.filled_circle(surface, mx, cy, 5, cfg.PLAYER_MALLET_KNOB[player])
        tag = _get_font(11).render(f"P{player}", True, cfg.PLAYER_COLORS[player])
        surface.blit(tag, tag.get_rect(center=(mx, rect.bottom + 16)))
    pygame.gfxdraw.filled_circle(surface, rect.centerx + 46, cy - 14, 8, cfg.COLOR_PUCK_RIM)
    pygame.gfxdraw.filled_circle(surface, rect.centerx + 46, cy - 14, 6, cfg.COLOR_PUCK_BODY)


def draw_intro_screen(surface: pygame.Surface):
    w, h = surface.get_size()
    surface.fill(cfg.COLOR_BG)

    kicker = _get_font(13).render("D U A L - P O V   ·   L O C A L   M U L T I P L A Y E R", True, cfg.COLOR_TEXT_DIM)
    surface.blit(kicker, kicker.get_rect(center=(w / 2, 44)))
    title = _get_font(46).render("AIR HOCKEY", True, cfg.COLOR_TEXT)
    surface.blit(title, title.get_rect(center=(w / 2, 84)))
    bar_w, bar_h, bar_gap = 92, 4, 8
    pygame.draw.rect(surface, cfg.PLAYER_COLORS[1],
                     (w / 2 - bar_w - bar_gap / 2, 112, bar_w, bar_h), border_radius=2)
    pygame.draw.rect(surface, cfg.PLAYER_COLORS[2],
                     (w / 2 + bar_gap / 2, 112, bar_w, bar_h), border_radius=2)
    subtitle = _get_font(15, bold=False).render(
        f"First to {cfg.SCORE_TO_WIN} goals wins  ·  one paddle each  ·  powers on the number row",
        True, cfg.COLOR_TEXT_DIM)
    surface.blit(subtitle, subtitle.get_rect(center=(w / 2, 138)))

    margin, gap = 30, 24
    card_w = (w - 2 * margin - gap) // 2
    card_y, pad = 172, 20
    row_h = 64
    card_h = pad + 30 + 44 + 14 + 5 * row_h + pad - 6

    for player in (1, 2):
        color = cfg.PLAYER_COLORS[player]
        x0 = margin if player == 1 else margin + card_w + gap
        card = pygame.Rect(x0, card_y, card_w, card_h)

        body = pygame.Surface(card.size, pygame.SRCALPHA)
        pygame.draw.rect(body, (*cfg.COLOR_CARD, 235), body.get_rect(), border_radius=14)
        pygame.draw.rect(body, (*color, 110), body.get_rect(), width=1, border_radius=14)
        pygame.draw.rect(body, color, (0, 0, card_w, 5), border_top_left_radius=14, border_top_right_radius=14)
        surface.blit(body, card.topleft)

        cx0 = card.left + pad
        y = card.top + pad + 4
        header = _get_font(21).render(f"PLAYER {player}", True, color)
        surface.blit(header, header.get_rect(midleft=(cx0, y + 10)))
        seat = _get_font(12, bold=False).render(
            "left screen" if player == 1 else "right screen", True, cfg.COLOR_TEXT_DIM)
        surface.blit(seat, seat.get_rect(midright=(card.right - pad, y + 10)))
        y += 40

        move_label = _get_font(12).render("MOVE", True, cfg.COLOR_TEXT_DIM)
        surface.blit(move_label, move_label.get_rect(midleft=(cx0, y + 12)))
        key_x = cx0 + 62
        for key in cfg.MOVE_KEYCAPS[player]:
            cap = _draw_keycap(surface, key, (key_x, y + 12))
            key_x = cap.right + 6
        y += 40

        pygame.draw.line(surface, (42, 52, 68), (cx0, y), (card.right - pad, y), 1)
        y += 14

        for power in POWER_ORDER:
            cap = _draw_keycap(surface, cfg.POWER_KEY_LABEL[player][power], (cx0, y + 20))
            name = _get_font(15).render(cfg.POWER_FULL_NAME[power], True, cfg.COLOR_TEXT)
            surface.blit(name, name.get_rect(bottomleft=(cap.right + 14, y + 22)))
            desc = _get_font(12, bold=False).render(cfg.POWER_DESC[power], True, cfg.COLOR_TEXT_DIM)
            surface.blit(desc, desc.get_rect(topleft=(cap.right + 14, y + 26)))
            y += row_h

    rink_cy = card_y + card_h + 84
    _draw_mini_rink(surface, (w // 2, rink_cy))

    tip = _get_font(13, bold=False).render(
        "Defend your goal, score in theirs  ·  after a goal, the player who conceded serves.",
        True, cfg.COLOR_TEXT_DIM)
    surface.blit(tip, tip.get_rect(center=(w / 2, rink_cy + 82)))

    pulse = (pygame.time.get_ticks() // 500) % 2 == 0
    prompt_color = cfg.COLOR_TEXT if pulse else cfg.COLOR_TEXT_DIM
    prompt_text = _get_font(17).render("PRESS  SPACE  TO  START", True, prompt_color)
    pill = prompt_text.get_rect(center=(w / 2, h - 64)).inflate(48, 22)
    pill_surf = pygame.Surface(pill.size, pygame.SRCALPHA)
    pygame.draw.rect(pill_surf, (*cfg.COLOR_CARD, 235), pill_surf.get_rect(), border_radius=999)
    pygame.draw.rect(pill_surf, (*prompt_color, 140), pill_surf.get_rect(), width=1, border_radius=999)
    surface.blit(pill_surf, pill.topleft)
    surface.blit(prompt_text, prompt_text.get_rect(center=pill.center))
    hint = _get_font(12, bold=False).render("ESC quits  ·  ENTER rematches after a win", True, cfg.COLOR_TEXT_DIM)
    surface.blit(hint, hint.get_rect(center=(w / 2, h - 28)))


def _draw_center_banner(surface: pygame.Surface, rotation: int, text: str, color,
                        sub: str = None, size: int = 40):
    text_surf = _get_font(size).render(text, True, color)
    while text_surf.get_width() > cfg.TABLE_WIDTH - 68 and size > 16:
        size = int(size * 0.9)
        text_surf = _get_font(size).render(text, True, color)
    sub_surf = _get_font(max(int(size * 0.38), 12), bold=False).render(sub, True, cfg.COLOR_TEXT_DIM) if sub else None

    padding = 22
    width = max(text_surf.get_width(), sub_surf.get_width() if sub_surf else 0) + padding * 2
    height = text_surf.get_height() + (sub_surf.get_height() + 8 if sub_surf else 0) + padding
    panel = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*cfg.COLOR_HUD_PANEL, 215), panel.get_rect(), border_radius=14)
    pygame.draw.rect(panel, (*color, 160), panel.get_rect(), width=2, border_radius=14)
    panel.blit(text_surf, text_surf.get_rect(midtop=(width / 2, padding / 2)))
    if sub_surf:
        panel.blit(sub_surf, sub_surf.get_rect(midtop=(width / 2, padding / 2 + text_surf.get_height() + 8)))
    if rotation == 180:
        panel = pygame.transform.rotate(panel, 180)
    surface.blit(panel, panel.get_rect(center=(cfg.TABLE_WIDTH / 2, cfg.TABLE_HEIGHT / 2)))


def render_table(surface: pygame.Surface, state: GameState, rotation: int,
                  viewer_player: int, alpha: float = 1.0):
    _draw_table_surface(surface, state, rotation, alpha)

    if state.winner is not None:
        _draw_center_banner(
            surface, rotation, f"PLAYER {state.winner} WINS!",
            cfg.PLAYER_COLORS[state.winner], sub="Press ENTER for a rematch")
    elif state.game_time < state.pause_until and state.last_scorer is not None:
        age = state.game_time - (state.pause_until - cfg.GOAL_PAUSE_DURATION)
        pop = max(0.0, 1.0 - age / cfg.GOAL_BANNER_POP_TIME)
        scorer = state.last_scorer
        _draw_center_banner(
            surface, rotation, f"P{scorer} SCORES!",
            cfg.PLAYER_COLORS[scorer],
            sub=f"{state.score[1]}  -  {state.score[2]}   ·   first to {cfg.SCORE_TO_WIN}",
            size=int(40 * (1 + 0.45 * pop)))
