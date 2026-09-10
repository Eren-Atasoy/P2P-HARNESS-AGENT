"""Cross-platform file locking mechanism (Windows + Unix) with timeouts."""
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

if sys.platform == "win32":
    import msvcrt

    def _lock_file(f):
        f.seek(0)
        # Lock 1 byte at position 0
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)

    def _unlock_file(f):
        try:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        except Exception:
            pass

else:
    import fcntl

    def _lock_file(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock_file(f):
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass


class FileLockTimeout(Exception):
    """Raised when acquiring file lock times out."""
    pass


@contextmanager
def file_lock(lock_path: Path, timeout: float = 10.0, delay: float = 0.05) -> Generator[None, None, None]:
    """Acquires an exclusive lock on a lockfile with timeout."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    start_time = time.monotonic()

    # Open file in binary mode
    f = open(lock_path, "a+b")
    try:
        while True:
            try:
                _lock_file(f)
                break
            except (OSError, IOError):
                if time.monotonic() - start_time >= timeout:
                    raise FileLockTimeout(f"Timed out waiting for file lock: {lock_path}")
                time.sleep(delay)
        yield
    finally:
        _unlock_file(f)
        f.close()
