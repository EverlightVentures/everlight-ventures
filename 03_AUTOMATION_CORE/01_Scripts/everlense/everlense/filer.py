import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from everlense import paths, scanner
from everlense.models import MediaItem, Label

def _category_dir(label: Label) -> Path:
    root = paths.photo_root()
    if label.category == "Business/Properties" and label.project:
        return root / "Business" / "Properties" / label.project
    if label.category == "Personal" and not label.signals:
        # date sub-bucket for plain personal
        pass
    return root / label.category

def dest_for(item: MediaItem, label: Label) -> Path:
    d = _category_dir(label)
    if label.category == "Personal":
        ym = (item.taken_at or "1970-01")[:7]            # YYYY-MM
        d = paths.photo_root() / "Personal" / ym[:4] / ym[5:7]
    return d / Path(item.path).name

def _write_nomedia(folder: Path):
    (folder / ".nomedia").touch()

def _write_sidecar(dest: Path, item: MediaItem, label: Label, address=None, ocr=None, stamped=False):
    rec = {
        "sha256": item.sha256, "source": item.source, "original_path": item.path,
        "taken_at": item.taken_at, "category": label.category, "project": label.project,
        "address": address, "gps": item.gps, "tags": [], "ocr_text": ocr, "stamped": stamped,
        "classified_by": {"tier": label.tier, "confidence": label.confidence, "signals": label.signals},
        "filed_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }
    dest.with_suffix(".json").write_text(json.dumps(rec, indent=2))
    return rec

def file_item(item: MediaItem, label: Label, dry_run: bool = True, address=None, ocr=None) -> dict:
    dest = dest_for(item, label)
    if dry_run:
        return {"planned_dest": str(dest), "category": label.category, "dry_run": True}
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and scanner.sha256_file(dest) == item.sha256:
        return {"dest": str(dest), "skipped": "already filed"}
    # 1. copy
    shutil.copy2(item.path, dest)
    # 2. verify
    if scanner.sha256_file(dest) != item.sha256:
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"hash mismatch after copy: {item.path}")
    # 3. move original to trash (NOT delete)
    trash = paths.trash_dir(); trash.mkdir(parents=True, exist_ok=True)
    shutil.move(item.path, trash / Path(item.path).name)
    # 4. gallery + sidecar
    _write_nomedia(dest.parent)
    rec = _write_sidecar(dest, item, label, address=address, ocr=ocr)
    return {"dest": str(dest), "category": label.category, "sidecar": rec, "dry_run": False}
