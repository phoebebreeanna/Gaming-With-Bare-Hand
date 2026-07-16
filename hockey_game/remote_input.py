import os
import socket
import tempfile
import threading
import time

PORT = 51246
PORT_FILE = os.path.join(tempfile.gettempdir(), "air_hockey_port.txt")
_STALE_AFTER = 0.35

_lock = threading.Lock()
_targets = {1: None, 2: None}
_skills = {1: None, 2: None}
_sock = None
_thread = None
_stop = False


def _bind_socket():
    for port in (PORT, 0):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", port))
            return sock, sock.getsockname()[1]
        except OSError:
            continue
    return None, None


def start():
    global _sock, _thread, _stop
    if _thread is not None:
        return
    _stop = False
    sock, port = _bind_socket()
    if sock is None:
        print("[remote_input] could not bind any UDP port; paddle control disabled")
        return
    sock.settimeout(0.5)
    try:
        with open(PORT_FILE, "w") as f:
            f.write(str(port))
    except OSError:
        pass
    if port != PORT:
        print(f"[remote_input] port {PORT} unavailable; using {port} instead")
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
            parts = data.decode("ascii").split(",")
            tag, player = parts[0], int(parts[1])
        except (ValueError, UnicodeDecodeError, IndexError):
            continue
        if player not in (1, 2):
            continue
        if tag == "M" and len(parts) == 4:
            try:
                fx = max(0.0, min(1.0, float(parts[2])))
                fy = max(0.0, min(1.0, float(parts[3])))
            except ValueError:
                continue
            with _lock:
                _targets[player] = (fx, fy, time.monotonic())
        elif tag == "K" and len(parts) == 3:
            try:
                n = int(parts[2])
            except ValueError:
                continue
            with _lock:
                _skills[player] = (n, time.monotonic())


def get_target_fraction(player: int):
    with _lock:
        entry = _targets.get(player)
    if entry is None:
        return None
    fx, fy, t = entry
    if time.monotonic() - t > _STALE_AFTER:
        return None
    return fx, fy


def get_skill_state(player: int) -> int:
    with _lock:
        entry = _skills.get(player)
    if entry is None:
        return 0
    n, t = entry
    if time.monotonic() - t > _STALE_AFTER:
        return 0
    return n
