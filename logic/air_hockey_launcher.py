import subprocess
import sys
from pathlib import Path

HOCKEY_GAME_DIR = Path(__file__).resolve().parent.parent / "hockey_game"


def is_available() -> bool:
    return (HOCKEY_GAME_DIR / "main.py").exists()


def launch() -> subprocess.Popen:
    if not is_available():
        raise FileNotFoundError(f"hockey_game/main.py not found at {HOCKEY_GAME_DIR}")
    return subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=str(HOCKEY_GAME_DIR),
    )
