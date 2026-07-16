import socket
import threading
import time

PORT = 51246
_STALE_AFTER = 0.35

_lock = threading.Lock()
_targets = {1: None, 2: None}
_sock = None
_thread = None
_stop = False


def start():
    global _sock, _thread, _stop
    if _thread is not None:
        return
    _stop = False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("127.0.0.1", PORT))
        sock.settimeout(0.5)
    except OSError:
        return
    _sock = sock
    _thread = threading.Thread(target=_listen, daemon=True)
    _thread.start()


def stop():
    global _stop, _sock, _thread
    _stop = True
    if _sock is not None:
        _sock.close()
        _sock = None
    _thread = None


def _listen():
    while not _stop:
        try:
            data, _ = _sock.recvfrom(64)
        except OSError:
            continue
        try:
            player_s, fx_s, fy_s = data.decode("ascii").split(",")
            player = int(player_s)
            fx = max(0.0, min(1.0, float(fx_s)))
            fy = max(0.0, min(1.0, float(fy_s)))
        except (ValueError, UnicodeDecodeError):
            continue
        if player not in (1, 2):
            continue
        with _lock:
            _targets[player] = (fx, fy, time.monotonic())


def get_target_fraction(player: int):
    with _lock:
        entry = _targets.get(player)
    if entry is None:
        return None
    fx, fy, t = entry
    if time.monotonic() - t > _STALE_AFTER:
        return None
    return fx, fy
