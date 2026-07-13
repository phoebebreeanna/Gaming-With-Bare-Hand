import array
import math
import random

import pygame

import config as cfg

_sounds = {}
_enabled = False
_rate = 22050
_channels = 1


def init():
    global _enabled, _rate, _channels
    if not cfg.SOUND_ENABLED:
        return
    try:
        if pygame.mixer.get_init() is not None:
            pygame.mixer.quit()
        pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        got = pygame.mixer.get_init()
        if got is None:
            return
        _rate, _, _channels = got[0], got[1], got[2]
        _build_all()
        _enabled = True
    except Exception:
        _enabled = False


def _render(duration, sample_fn):
    n = int(_rate * duration)
    buf = array.array("h")
    for i in range(n):
        t = i / _rate
        v = int(32767 * max(-1.0, min(1.0, sample_fn(t))))
        for _ in range(abs(_channels)):
            buf.append(v)
    return buf


def _tone(freqs, duration, vol=0.6, decay=6.0):
    k = 2 * math.pi

    def sample(t):
        s = sum(math.sin(k * f * t) for f in freqs) / len(freqs)
        return vol * math.exp(-decay * t) * s

    return _render(duration, sample)


def _thock(freq, duration, vol=0.8, decay=22.0, noise=0.35):
    rng = random.Random(int(freq))
    k = 2 * math.pi

    def sample(t):
        body = math.sin(k * freq * t)
        crack = noise * (rng.random() * 2 - 1) * math.exp(-90.0 * t)
        return vol * (math.exp(-decay * t) * body + crack)

    return _render(duration, sample)


def _concat(*bufs):
    out = array.array("h")
    for b in bufs:
        out.extend(b)
    return out


def _sound(buf):
    return pygame.mixer.Sound(buffer=buf.tobytes())


def _build_all():
    _sounds["paddle_soft"] = _sound(_thock(165, 0.07, vol=0.55))
    _sounds["paddle_hard"] = _sound(_thock(210, 0.10, vol=0.95, noise=0.55))
    _sounds["wall"] = _sound(_thock(1050, 0.03, vol=0.30, decay=60.0, noise=0.15))
    _sounds["shield"] = _sound(_tone((330, 660), 0.15, vol=0.6, decay=14.0))
    _sounds["power"] = _sound(_tone((720, 1080), 0.09, vol=0.5, decay=20.0))
    _sounds["goal"] = _sound(_tone((392, 494, 587), 0.55, vol=0.9, decay=4.5))
    _sounds["win"] = _sound(_concat(
        _tone((523,), 0.12, vol=0.7, decay=9.0),
        _tone((659,), 0.12, vol=0.7, decay=9.0),
        _tone((784,), 0.12, vol=0.7, decay=9.0),
        _tone((1047, 523), 0.6, vol=0.8, decay=3.5),
    ))


def _play(name, volume=1.0):
    snd = _sounds.get(name)
    if snd is None:
        return
    snd.set_volume(max(0.0, min(1.0, cfg.SOUND_VOLUME * volume)))
    snd.play()


def play_new_events(state, last_seq: int) -> int:
    for event in state.events:
        if event["seq"] <= last_seq:
            continue
        last_seq = event["seq"]
        if not _enabled:
            continue
        kind = event["kind"]
        if kind == "paddle_hit":
            impact = event.get("impact", 0.0)
            if impact < cfg.WALL_EVENT_MIN_IMPACT:
                continue
            loud = 0.35 + 0.65 * min(1.0, impact / cfg.PUCK_MAX_SPEED)
            _play("paddle_hard" if impact >= cfg.HITSTOP_MIN_IMPACT else "paddle_soft", loud)
        elif kind == "wall_bounce":
            impact = event.get("impact", 0.0)
            _play("wall", 0.3 + 0.7 * min(1.0, impact / cfg.PUCK_MAX_SPEED))
        elif kind == "shield_block":
            _play("shield")
        elif kind == "power":
            _play("power")
        elif kind == "goal":
            _play("goal")
        elif kind == "win":
            _play("win")
    return last_seq
