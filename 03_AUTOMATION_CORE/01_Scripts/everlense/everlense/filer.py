import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from everlense import paths, scanner
from everlense.models import MediaItem, Label

def dest_for(item: MediaItem, label: Label) -> Path:
    root = paths.photo_root()
    if label.category == "Business/Properties" and label.project:
        d = root / "Business" / "Properties" / label.project
    elif label.category == "Personal":
        ym = (item.taken_at or "1970-01")[:7]            # YYYY-MM
        d = root / "Personal" / ym[:4] / ym[5:7]
    else:
        d = root / label.category
    return d / Path(item.path).name

def _resolve_collision(dest: Path, item: MediaItem):
    """Return (final_path, state). state in {'new','already_filed','renamed'}.
    Never returns a path that would overwrite a DIFFERENT file."""
    if not dest.exists():
        return dest, "new"
    if scanner.sha256_file(dest) == item.sha256:
        return dest, "already_filed"
    stem, suffix = dest.stem, dest.suffix
    i = 1
    while True:
        cand = dest.with_name(f"{stem} ({i}){suffix}")
        if not cand.exists():
            return cand, "renamed"
        if scanner.sha256_file(cand) == item.sha256:
            return cand, "already_filed"
        i += 1

def _trash_name(item: MediaItem) -> str:
    # hash-prefixed so distinct originals never overwrite each other in _Trash
    return f"{item.sha256[:12]}_{Path(item.path).name}"

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
    final, state = _resolve_collision(dest, item)
    if state != "already_filed":
        # atomic copy: write to .part in the SAME dir (same filesystem), verify, then os.replace
        part = final.with_name(final.name + ".part")
        shutil.copy2(item.path, part)
        if scanner.sha256_file(part) != item.sha256:
            part.unlink(missing_ok=True)
            raise RuntimeError(f"hash mismatch after copy: {item.path}")
        os.replace(part, final)
    # write metadata BEFORE the irreversible trash-move so a failure never strands the original
    _write_nomedia(final.parent)
    rec = _write_sidecar(final, item, label, address=address, ocr=ocr)
    # move original to trash LAST, hash-prefixed (collision-proof). Re-runnable.
    if Path(item.path).exists():
        trash = paths.trash_dir(); trash.mkdir(parents=True, exist_ok=True)
        shutil.move(item.path, str(trash / _trash_name(item)))
    return {"dest": str(final), "category": label.category, "sidecar": rec, "state": state, "dry_run": False}
