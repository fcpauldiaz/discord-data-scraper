import sys
from types import ModuleType

from notification_watcher import macos, windows


def get_backend() -> ModuleType:
    if sys.platform == "darwin":
        return macos
    if sys.platform == "win32":
        return windows
    raise RuntimeError(f"Unsupported platform: {sys.platform}")
