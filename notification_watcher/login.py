import os
import plistlib
import subprocess
import sys
from pathlib import Path

LAUNCH_AGENT_ID = "com.notificationwatcher.app"
REGISTRY_APP_NAME = "NotificationWatcher"


def _macos_app_path() -> Path | None:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent.parent
    return None


def is_launch_at_login_enabled() -> bool:
    if sys.platform == "darwin":
        plist_path = (
            Path.home() / "Library" / "LaunchAgents" / f"{LAUNCH_AGENT_ID}.plist"
        )
        return plist_path.exists()
    if sys.platform == "win32":
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
            ) as key:
                winreg.QueryValueEx(key, REGISTRY_APP_NAME)
                return True
        except OSError:
            return False
    return False


def set_launch_at_login(enabled: bool, app_path: Path | None = None) -> None:
    if sys.platform == "darwin":
        _set_macos_launch_at_login(enabled, app_path)
    elif sys.platform == "win32":
        _set_windows_launch_at_login(enabled, app_path)


def _set_macos_launch_at_login(enabled: bool, app_path: Path | None) -> None:
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCH_AGENT_ID}.plist"
    if enabled:
        resolved = app_path or _macos_app_path()
        if resolved is None:
            return
        plist_path.parent.mkdir(parents=True, exist_ok=True)
        plist = {
            "Label": LAUNCH_AGENT_ID,
            "ProgramArguments": ["open", "-a", str(resolved)],
            "RunAtLoad": True,
        }
        plist_path.write_bytes(plistlib.dumps(plist))
    elif plist_path.exists():
        plist_path.unlink()


def _set_windows_launch_at_login(enabled: bool, app_path: Path | None) -> None:
    import winreg

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
    ) as key:
        if enabled:
            exe = app_path or Path(sys.executable)
            winreg.SetValueEx(key, REGISTRY_APP_NAME, 0, winreg.REG_SZ, str(exe))
        else:
            try:
                winreg.DeleteValue(key, REGISTRY_APP_NAME)
            except OSError:
                pass


def open_full_disk_access_settings() -> None:
    if sys.platform != "darwin":
        return
    subprocess.run(
        ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"],
        check=False,
        timeout=5,
    )
