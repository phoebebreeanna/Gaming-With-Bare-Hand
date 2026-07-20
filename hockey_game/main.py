import sys
import time

import pygame

import config as cfg
import remote_input
from physics import (
    GameState,
    move_paddle,
    set_paddle_target_fraction,
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
        remote_target = remote_input.get_target_fraction(player)
        if remote_target is not None:
            set_paddle_target_fraction(paddle, remote_target[0], remote_target[1], dt)
        else:
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


def _initial_window_size():
    try:
        avail_w, avail_h = pygame.display.get_desktop_sizes()[0]
    except Exception:
        avail_w, avail_h = cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT
    margin_w, margin_h = 80, 120
    max_w = max(avail_w - margin_w, 480)
    max_h = max(avail_h - margin_h, 480)
    scale = min(1.0, max_w / cfg.WINDOW_WIDTH, max_h / cfg.WINDOW_HEIGHT)
    return int(cfg.WINDOW_WIDTH * scale), int(cfg.WINDOW_HEIGHT * scale)


def _blit_scaled_to_fit(display_surface, virtual_surface):
    dw, dh = display_surface.get_size()
    sw, sh = virtual_surface.get_size()
    scale = min(dw / sw, dh / sh)
    new_w, new_h = max(1, round(sw * scale)), max(1, round(sh * scale))
    display_surface.fill(cfg.COLOR_BG)
    if (new_w, new_h) == (sw, sh):
        scaled = virtual_surface
    else:
        scaled = pygame.transform.smoothscale(virtual_surface, (new_w, new_h))
    display_surface.blit(scaled, ((dw - new_w) // 2, (dh - new_h) // 2))


def _bring_window_to_foreground():
    try:
        wm_info = pygame.display.get_wm_info()
    except Exception:
        return
    hwnd = wm_info.get('window')
    if not hwnd:
        return
    if sys.platform == 'win32':
        try:
            import ctypes
            user32 = ctypes.windll.user32
            SW_RESTORE = 9
            user32.ShowWindow(hwnd, SW_RESTORE)
            user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
    elif sys.platform == 'darwin':
        try:
            import objc
            from AppKit import NSApplication, NSApplicationActivateIgnoringOtherApps
            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        except Exception:
            pass


def main():
    pygame.init()
    audio.init()
    remote_input.start()
    pygame.display.set_caption("Air Hockey")
    window_w, window_h = _initial_window_size()
    screen = pygame.display.set_mode(
        (window_w, window_h), pygame.RESIZABLE | pygame.DOUBLEBUF, vsync=1
    )
    _bring_window_to_foreground()
    virtual = pygame.Surface((cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT)).convert()
    clock = pygame.time.Clock()

    top_bar = virtual.subsurface(pygame.Rect(0, 0, cfg.TABLE_WIDTH, cfg.HUD_TOP_HEIGHT))
    ice = virtual.subsurface(pygame.Rect(0, cfg.TABLE_Y_OFFSET, cfg.TABLE_WIDTH, cfg.TABLE_HEIGHT))
    bottom_bar = virtual.subsurface(
        pygame.Rect(0, cfg.TABLE_Y_OFFSET + cfg.TABLE_HEIGHT, cfg.TABLE_WIDTH, cfg.HUD_BOTTOM_HEIGHT))
    dock_w = cfg.TABLE_WIDTH // 2
    p1_dock = bottom_bar.subsurface(pygame.Rect(0, 0, dock_w, cfg.HUD_BOTTOM_HEIGHT))
    p2_dock = bottom_bar.subsurface(pygame.Rect(dock_w, 0, cfg.TABLE_WIDTH - dock_w, cfg.HUD_BOTTOM_HEIGHT))

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
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(
                    (event.w, event.h), pygame.RESIZABLE | pygame.DOUBLEBUF, vsync=1
                )
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
            draw_intro_screen(virtual)
            _blit_scaled_to_fit(screen, virtual)
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
        render_table(ice, state, alpha=alpha)
        draw_score_panel(top_bar, state)
        draw_power_dock(p1_dock, state, viewer_player=1)
        draw_power_dock(p2_dock, state, viewer_player=2)

        _blit_scaled_to_fit(screen, virtual)
        pygame.display.flip()

    remote_input.stop()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
