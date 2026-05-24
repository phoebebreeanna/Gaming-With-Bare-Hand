import os
import json

_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_config.json')


def is_setup_done() -> bool:
    try:
        with open(_CONFIG_FILE) as f:
            return json.load(f).get('setup_complete', False)
    except (FileNotFoundError, json.JSONDecodeError):
        return False


def get_saved_zone() -> str:
    try:
        with open(_CONFIG_FILE) as f:
            return json.load(f).get('zone', 'medium')
    except (FileNotFoundError, json.JSONDecodeError):
        return 'medium'


def mark_setup_done(zone: str = 'medium') -> None:
    config = {}
    try:
        with open(_CONFIG_FILE) as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    config['setup_complete'] = True
    config['zone'] = zone
    with open(_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
