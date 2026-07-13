import platform
import subprocess
import sys


def main():
    pip_cmd = [sys.executable, "-m", "pip", "install"]

    if platform.system() == "Windows":
        subprocess.run(
            pip_cmd + [
                "llama-cpp-python",
                "--prefer-binary",
                "--extra-index-url",
                "https://abetlen.github.io/llama-cpp-python/whl/cpu",
            ],
            check=True,
        )

    subprocess.run(pip_cmd + ["-r", "requirements.txt"], check=True)


if __name__ == "__main__":
    main()
