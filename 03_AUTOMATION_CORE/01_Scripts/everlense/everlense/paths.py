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
    # Use EVERLENSE_PICTURES if set; fall back to EVERLENSE_DCIM parent if that is set
    # (test isolation: when EVERLENSE_DCIM is overridden, social dirs live under the same tmp root)
    if "EVERLENSE_PICTURES" in os.environ:
        base = Path(os.environ["EVERLENSE_PICTURES"])
    elif "EVERLENSE_DCIM" in os.environ:
        base = Path(os.environ["EVERLENSE_DCIM"])
    else:
        base = Path("/sdcard/Pictures")
    return [base / n for n in ("WhatsApp", "Instagram", "Messenger", "Threads", "Twitter")]
