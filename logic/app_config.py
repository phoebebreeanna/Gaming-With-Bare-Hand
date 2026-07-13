import os
import sys
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
        'like': 'shift', 'palm': 'space', 'grabbing': 'e',
        'ok': 'f', 'call': 'r', 'dislike': 'q', 'holy': 'esc',
        'grip': 'alt', 'one': '1', 'peace': '2', 'three': '3', 'four': '4',
        'peace_inverted': 't', 'three2': 'tab', 'three3': 'g',
    },
}

if getattr(sys, 'frozen', False):
    _config_dir = os.path.join(os.path.expanduser('~'), '.handmouse')
    os.makedirs(_config_dir, exist_ok=True)
    _CONFIG_FILE = os.path.join(_config_dir, 'app_config.json')
else:
    _CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_config.json')

def _read() -> dict:
    try:
        with open(_CONFIG_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _write(config: dict) -> None:
    try:
        with open(_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except OSError:
        pass

def is_setup_done() -> bool:
    return _read().get('setup_complete', False)

def get_saved_zone() -> str:
    return _read().get('zone', 'large')

def mark_setup_done(zone: str = 'large') -> None:
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
    return _read().get('mouse_enabled', True)

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

def get_show_perf_stats() -> bool:
    return _read().get('show_perf_stats', True)

def set_show_perf_stats(enabled: bool) -> None:
    config = _read()
    config['show_perf_stats'] = enabled
    _write(config)

def get_chatbot_enabled() -> bool:
    return _read().get('chatbot_enabled', True)

def set_chatbot_enabled(enabled: bool) -> None:
    config = _read()
    config['chatbot_enabled'] = enabled
    _write(config)

def get_mini_overlay_enabled() -> bool:
    return _read().get('mini_overlay_enabled', True)

def set_mini_overlay_enabled(enabled: bool) -> None:
    config = _read()
    config['mini_overlay_enabled'] = enabled
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

def get_custom_modes() -> list:
    return _read().get('custom_modes', [])

def add_custom_mode(name: str, gestures: list) -> dict:
    import time as _t
    modes   = get_custom_modes()
    mode_id = f"cm_{int(_t.time())}"
    mode    = {'id': mode_id, 'name': name, 'gestures': list(gestures)}
    config  = _read()
    config.setdefault('custom_modes', []).append(mode)
    _write(config)
    return mode

def update_custom_mode(mode_id: str, name: str = None, gestures: list = None) -> None:
    config = _read()
    for m in config.get('custom_modes', []):
        if m['id'] == mode_id:
            if name is not None:
                m['name'] = name
            if gestures is not None:
                m['gestures'] = list(gestures)
            break
    _write(config)

def delete_custom_mode(mode_id: str) -> None:
    config = _read()
    config['custom_modes'] = [m for m in config.get('custom_modes', []) if m['id'] != mode_id]
    if config.get('selected_custom_mode_id') == mode_id:
        remaining = config['custom_modes']
        config['selected_custom_mode_id'] = remaining[0]['id'] if remaining else ''
    if 'key_bindings' in config:
        config['key_bindings'].pop(f'custom_{mode_id}', None)
    _write(config)

def get_selected_custom_mode_id() -> str:
    config = _read()
    modes  = config.get('custom_modes', [])
    saved  = config.get('selected_custom_mode_id', '')
    if saved and any(m['id'] == saved for m in modes):
        return saved
    return modes[0]['id'] if modes else ''

def set_selected_custom_mode_id(mode_id: str) -> None:
    config = _read()
    config['selected_custom_mode_id'] = mode_id
    _write(config)

def get_selected_custom_mode_source() -> str:
    return _read().get('selected_custom_mode_source', 'custom')

def set_selected_custom_mode_source(source: str) -> None:
    config = _read()
    config['selected_custom_mode_source'] = source
    _write(config)

def get_custom_data_root() -> str:
    logic_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(logic_dir, 'data', 'custom')

def get_custom_mode_dir(mode_id: str) -> str:
    return os.path.join(get_custom_data_root(), mode_id)

def generate_custom_conf(mode: dict) -> str:
    import configparser
    mode_id  = mode['id']
    mode_dir = get_custom_mode_dir(mode_id)
    os.makedirs(mode_dir, exist_ok=True)
    conf_path = os.path.join(mode_dir, 'custom.conf')
    gestures  = mode.get('gestures') or ['idle']
    cfg = configparser.ConfigParser()
    cfg['project']       = {'name': mode.get('name', 'Custom')}
    cfg['gestures']      = {'names': ', '.join(gestures)}
    cfg['collection']    = {
        'target_per_gesture': '50',
        'min_record_dist':    '0.02',
        'diversity_every':    '50',
    }
    cfg['preprocessing'] = {
        'aug_per_sample': '4',
        'noise_std':      '0.008',
        'rot_max_deg':    '20.0',
        'scale_jitter':   '0.12',
    }
    cfg['training'] = {
        'epochs':                    '150',
        'batch_size':                '64',
        'learning_rate':             '0.001',
        'focal_gamma':               '2.0',
        'low_conf_threshold':        '0.70',
        'weak_accuracy_threshold':   '0.80',
    }
    cfg['files'] = {
        'data_dir':     '.',
        'raw_csv':      'raw_gestures.csv',
        'processed_csv':'gesture_data.csv',
        'model_best':   'gesture_model_best.pt',
        'model_out':    'gesture_model.pt',
        'label_encoder':'label_encoder.pkl',
    }
    with open(conf_path, 'w') as f:
        cfg.write(f)
    return conf_path
