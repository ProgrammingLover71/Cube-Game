import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WATCHED_PATHS = (ROOT / "src", ROOT / "levels")
POLL_SECONDS = 0.25


def main():
    print("Hot reload launcher started. Press Ctrl+C to stop.")

    while True:
        process = start_game()
        snapshot = collect_snapshot()

        try:
            should_restart = wait_for_change_or_exit(process, snapshot)
        except KeyboardInterrupt:
            stop_game(process)
            print("\nLauncher stopped.")
            return

        if not should_restart:
            return

        print("Change detected. Restarting game...")
        stop_game(process)


def start_game():
    return subprocess.Popen([sys.executable, str(ROOT / "src" / "__main__.py")], cwd=ROOT)


def wait_for_change_or_exit(process, snapshot):
    while process.poll() is None:
        time.sleep(POLL_SECONDS)
        current_snapshot = collect_snapshot()
        if current_snapshot != snapshot:
            return True

    return False


def collect_snapshot():
    snapshot = {}
    for path in iter_watched_files():
        try:
            stat = path.stat()
        except OSError:
            continue

        snapshot[path] = (stat.st_mtime_ns, stat.st_size)

    return snapshot


def iter_watched_files():
    for path in WATCHED_PATHS:
        if path.is_file() and is_watched_file(path):
            yield path
        elif path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and is_watched_file(child):
                    yield child


def is_watched_file(path):
    return path.suffix.lower() in {".py"}


def stop_game(process):
    if process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


if __name__ == "__main__":
    main()
