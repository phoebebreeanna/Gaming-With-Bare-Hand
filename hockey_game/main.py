import sys
import time

import pygame

import config as cfg
from physics import (
    GameState,
    move_paddle,
    integrate_puck,
    resolve_side_walls,
    resolve_top_bottom_walls,
    check_goal,
    resolve_shield,
    resolve_paddle_puck,
)
from input_handler import KeyboardInput
from powers import PowerManager
from render import render_table, draw_score_panel, draw_power_dock, draw_intro_screen
import audio


def physics_step(state: GameState, input_source, power_manager: PowerManager, dt: float):
    for paddle in state.paddles.values():
        paddle.prev_pos = pygame.math.Vector2(paddle.pos)
    for puck in state.pucks:
        puck.prev_pos = pygame.math.Vector2(puck.pos)

    for player, paddle in state.paddles.items():
        if state.is_frozen(player):
            paddle.vel = pygame.math.Vector2(0, 0)
            continue
        direction = input_source.get_paddle_position(player)
        move_paddle(paddle, direction, dt)

    power_manager.step_cleanup(state)

    if (state.winner is None and state.game_time >= state.pause_until
            and state.game_time >= state.hitstop_until):
        for puck in list(state.pucks):
            slow_mult = power_manager.slow_multiplier(state, puck)
            integrate_puck(puck, dt, slow_mult)
            for wall_impact in (resolve_side_walls(puck), resolve_top_bottom_walls(puck)):
                if wall_impact is not None and wall_impact >= cfg.WALL_EVENT_MIN_IMPACT:
                    state.emit("wall_bounce", puck.pos, impact=wall_impact)

            scorer = check_goal(puck) if state.game_time >= state.goal_lock_until else None
            if scorer is not None:
                state.score[scorer] += 1
                state.last_scorer = scorer
                state.emit("goal", puck.pos, scorer=scorer)
                if state.score[scorer] >= cfg.SCORE_TO_WIN:
                    state.winner = scorer
                    state.emit("win", puck.pos, winner=scorer)
                state.reset_after_goal(conceder=state.opponent(scorer))
                continue

            for owner, shield in list(state.shields.items()):
                if shield is not None and resolve_shield(puck, shield):
                    state.shields[owner] = None
                    state.emit("shield_block", puck.pos, player=owner)

            for player, paddle in state.paddles.items():
                impact = resolve_paddle_puck(puck, paddle)
                if impact is not None:
                    state.emit("paddle_hit", puck.pos, impact=impact, player=player)
                    if (impact >= cfg.HITSTOP_MIN_IMPACT
                            and state.game_time >= state.hitstop_until + cfg.HITSTOP_COOLDOWN):
                        state.hitstop_until = state.game_time + cfg.HITSTOP_DURATION
                    power_manager.maybe_apply_speed_buff(state, player, puck)

            puck.trail.append((puck.pos.x, puck.pos.y))
            if len(puck.trail) > cfg.PUCK_TRAIL_LENGTH:
                puck.trail.pop(0)

    state.game_time += dt


def main():
    pygame.init()
    audio.init()
    pygame.display.set_caption("Dual-POV Air Hockey")
    screen = pygame.display.set_mode((cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT), pygame.DOUBLEBUF, vsync=1)
    clock = pygame.time.Clock()

    def half_rects(offset_x):
        top = pygame.Rect(offset_x, 0, cfg.TABLE_WIDTH, cfg.HUD_TOP_HEIGHT)
        ice = pygame.Rect(offset_x, cfg.TABLE_Y_OFFSET, cfg.TABLE_WIDTH, cfg.TABLE_HEIGHT)
        bottom = pygame.Rect(offset_x, cfg.TABLE_Y_OFFSET + cfg.TABLE_HEIGHT, cfg.TABLE_WIDTH, cfg.HUD_BOTTOM_HEIGHT)
        return top, ice, bottom

    p1_top, p1_ice, p1_bottom = (screen.subsurface(r) for r in half_rects(cfg.P1_VIEW_OFFSET_X))
    p2_top, p2_ice, p2_bottom = (screen.subsurface(r) for r in half_rects(cfg.P2_VIEW_OFFSET_X))

    state = GameState()
    input_source = KeyboardInput()
    power_manager = PowerManager()

    showing_intro = True

    accumulator = 0.0
    audio_seq = 0
    running = True
    prev_frame_time = time.perf_counter()
    while running:
        clock.tick(60)
        now = time.perf_counter()
        frame_dt = min(now - prev_frame_time, 0.25)
        prev_frame_time = now

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == cfg.QUIT_KEY:
                    running = False
                elif event.key == cfg.START_KEY and showing_intro:
                    showing_intro = False
                elif event.key == cfg.RESTART_KEY and state.winner is not None:
                    state = GameState()
                    accumulator = 0.0
                    audio_seq = 0

        input_source.update(events)

        if showing_intro:
            draw_intro_screen(screen)
            pygame.display.flip()
            continue

        power_manager.handle_triggers(state, input_source)

        accumulator += frame_dt
        steps = 0
        while accumulator >= cfg.PHYSICS_DT and steps < cfg.MAX_STEPS_PER_FRAME:
            physics_step(state, input_source, power_manager, cfg.PHYSICS_DT)
            accumulator -= cfg.PHYSICS_DT
            steps += 1

        audio_seq = audio.play_new_events(state, audio_seq)

        alpha = min(accumulator / cfg.PHYSICS_DT, 1.0)
        render_table(p1_ice, state, rotation=0, viewer_player=1, alpha=alpha)
        render_table(p2_ice, state, rotation=180, viewer_player=2, alpha=alpha)
        draw_score_panel(p1_top, state, viewer_player=1)
        draw_score_panel(p2_top, state, viewer_player=2)
        draw_power_dock(p1_bottom, state, viewer_player=1)
        draw_power_dock(p2_bottom, state, viewer_player=2)

        screen.fill(cfg.COLOR_DIVIDER, pygame.Rect(cfg.TABLE_WIDTH, 0, cfg.DIVIDER_THICKNESS, cfg.WINDOW_HEIGHT))
        seam_x = cfg.TABLE_WIDTH + cfg.DIVIDER_THICKNESS // 2
        pygame.draw.line(screen, cfg.COLOR_DIVIDER_BEVEL, (seam_x, 0), (seam_x, cfg.WINDOW_HEIGHT), 2)
        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
