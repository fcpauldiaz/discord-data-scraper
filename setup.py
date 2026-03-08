from setuptools import setup

APP = ["notification_app.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "includes": ["notification_watcher", "webhook_sender"],
    "packages": ["rumps", "objc", "Foundation", "AppKit"],
    "plist": {
        "CFBundleName": "Notification Watcher",
        "CFBundleDisplayName": "Notification Watcher",
        "CFBundleIdentifier": "com.notificationwatcher.app",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
    },
}

setup(
    name="Notification Watcher",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
