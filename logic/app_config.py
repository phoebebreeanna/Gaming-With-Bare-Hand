import os
import json

BINDINGS_DEFAULT = {
    'subway': {
        'jump': 'up', 'roll': 'down', 'left': 'left', 'right': 'right', 'space': 'space',
    },
    'racing': {
        'accel': 'up', 'brake': 'down', 'steer_left': 'left', 'steer_right': 'right',
        'horn': 'h', 'camera': 'c',
    },
    'open_world': {
        'like': 'shift', 'palm': 'space', 'thumb_index': 'e',
        'ok': 'f', 'call': 'r', 'dislike': 'q', 'holy': 'esc',
        'grip': 'alt', 'one': '1', 'peace': '2', 'three': '3', 'four': '4',
        'peace_inverted': 't', 'three2': 'tab', 'three3': 'g',
    },
}

_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_config.json')

def _read() -> dict:
    try:
        with open(_CONFIG_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _write(config: dict) -> None:
    with open(_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def is_setup_done() -> bool:
    return _read().get('setup_complete', False)

def get_saved_zone() -> str:
    return _read().get('zone', 'medium')

def mark_setup_done(zone: str = 'medium') -> None:
    config = _read()
    config['setup_complete'] = True
    config['zone'] = zone
    _write(config)

def get_game_mode() -> str:
    return _read().get('game_mode', 'mouse')

def set_game_mode(mode: str) -> None:
    config = _read()
    config['game_mode'] = mode
    _write(config)

def get_mouse_enabled() -> bool:
    return _read().get('mouse_enabled', False)

def set_mouse_enabled(enabled: bool) -> None:
    config = _read()
    config['mouse_enabled'] = enabled
    _write(config)

def get_model_source(mode: str) -> str:
    return _read().get('model_sources', {}).get(mode, 'default')

def set_model_source(mode: str, source: str) -> None:
    config = _read()
    if 'model_sources' not in config:
        config['model_sources'] = {}
    config['model_sources'][mode] = source
    _write(config)

def get_camera_index() -> int:
    return _read().get('camera_index', 0)

def set_camera_index(idx: int) -> None:
    config = _read()
    config['camera_index'] = idx
    _write(config)

def set_zone(zone: str) -> None:
    config = _read()
    config['zone'] = zone
    _write(config)

def get_mouse_side() -> str:
    return _read().get('mouse_side', 'right')

def set_mouse_side(side: str) -> None:
    config = _read()
    config['mouse_side'] = side
    _write(config)

def get_cursor_point() -> str:
    return _read().get('cursor_point', 'knuckle')

def set_cursor_point(point: str) -> None:
    config = _read()
    config['cursor_point'] = point
    _write(config)

def get_key_bindings(mode: str) -> dict:
    defaults = BINDINGS_DEFAULT.get(mode, {})
    saved    = _read().get('key_bindings', {}).get(mode, {})
    return {**defaults, **saved}

def set_key_binding(mode: str, gesture: str, key: str) -> None:
    config = _read()
    if 'key_bindings' not in config:
        config['key_bindings'] = {}
    if mode not in config['key_bindings']:
        config['key_bindings'][mode] = {}
    config['key_bindings'][mode][gesture] = key
    _write(config)

def reset_key_bindings(mode: str) -> None:
    config = _read()
    if 'key_bindings' in config and mode in config['key_bindings']:
        del config['key_bindings'][mode]
        _write(config)
