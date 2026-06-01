import os
from pathlib import Path

_DEFAULT_ROOT = "/mnt/sdcard/AA_MY_DRIVE/04_MEDIA_LIBRARY/Photos"
_DEFAULT_DCIM = "/sdcard/DCIM"

def photo_root() -> Path:
    return Path(os.environ.get("EVERLENSE_PHOTO_ROOT", _DEFAULT_ROOT)).expanduser()

def state_dir() -> Path:
    return photo_root() / ".everlense"

def trash_dir() -> Path:
    return photo_root() / "_Trash"

def dcim_sources() -> list[Path]:
    base = Path(os.environ.get("EVERLENSE_DCIM", _DEFAULT_DCIM))
    return [base / "Camera", base / "Screenshots"]

def social_sources() -> list[Path]:
    base = Path(os.environ.get("EVERLENSE_PICTURES", "/sdcard/Pictures"))
    return [base / n for n in ("WhatsApp", "Instagram", "Messenger", "Threads", "Twitter")]
