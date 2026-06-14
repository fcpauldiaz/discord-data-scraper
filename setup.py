from setuptools import setup

from notification_watcher.version import __version__

APP = ["notification_app.py"]
DATA_FILES = [("assets", ["assets/icon.icns", "assets/icon.png"])]
OPTIONS = {
    "argv_emulation": False,
    "iconfile": "assets/icon.icns",
    "includes": ["notification_watcher", "webhook_sender"],
    "packages": ["rumps", "objc", "Foundation", "AppKit"],
    "plist": {
        "CFBundleName": "Notification Watcher",
        "CFBundleDisplayName": "Notification Watcher",
        "CFBundleIdentifier": "com.notificationwatcher.app",
        "CFBundleVersion": __version__,
        "CFBundleShortVersionString": __version__,
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
        "SUFeedURL": "https://github.com/fcpauldiaz/discord-data-scraper/releases/latest/download/appcast.xml",
    },
}

setup(
    name="Notification Watcher",
    version=__version__,
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
