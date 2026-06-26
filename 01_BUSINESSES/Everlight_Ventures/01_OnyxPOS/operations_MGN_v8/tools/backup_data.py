"""Automated backups for the MGN POS data (the resilience gap: one mini PC = one
dead drive from losing the business).

create_backup() tar.gz's the whole data folder (all CSVs), rotates to the last N,
optionally ENCRYPTS with openssl AES-256 (if MGN_BACKUP_PASSPHRASE is set), and
optionally copies to an offsite/USB path (MGN_BACKUP_OFFSITE). Pure stdlib + the
openssl CLI (already on any PC) -- no pip installs.

Env:
  MGN_BACKUP_DIR        where backups land (default: <data>/../MGN_Backups)
  MGN_BACKUP_PASSPHRASE if set + openssl present -> encrypt to .tar.gz.enc
  MGN_BACKUP_OFFSITE    if set -> also copy the backup there (USB / network share)
"""
import os
import shutil
import subprocess
import tarfile
from datetime import datetime
from pathlib import Path

_EXCLUDE_NAMES = {"MGN_Backups", ".git", ".venv", "__pycache__", "node_modules"}


def _excluded(name):
    base = os.path.basename(name)
    return base in _EXCLUDE_NAMES or ".bak" in base or base.endswith(".pyc")


def _data_dir(data_dir=None):
    return Path(data_dir or os.environ.get("MGN_DATA_DIR")
               or Path(__file__).resolve().parent.parent)


def backup_dir(data_dir=None):
    dd = _data_dir(data_dir)
    return Path(os.environ.get("MGN_BACKUP_DIR") or (dd.parent / "MGN_Backups"))


def create_backup(data_dir=None, keep=14, passphrase=None, stamp=None):
    dd = _data_dir(data_dir)
    dest = backup_dir(dd)
    dest.mkdir(parents=True, exist_ok=True)
    stamp = stamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    path = dest / f"mgn_backup_{stamp}.tar.gz"

    def _filter(ti):
        return None if _excluded(ti.name) else ti

    with tarfile.open(path, "w:gz") as tar:
        for child in sorted(dd.iterdir()):
            if _excluded(child.name):
                continue
            tar.add(child, arcname=child.name, filter=_filter)

    result = {"file": str(path), "encrypted": False, "size": path.stat().st_size}

    passphrase = passphrase or os.environ.get("MGN_BACKUP_PASSPHRASE", "")
    if passphrase and shutil.which("openssl"):
        enc = str(path) + ".enc"
        try:
            subprocess.run(
                ["openssl", "enc", "-aes-256-cbc", "-salt", "-pbkdf2",
                 "-in", str(path), "-out", enc, "-pass", f"pass:{passphrase}"],
                check=True, capture_output=True)
            os.remove(path)
            result.update(file=enc, encrypted=True, size=os.path.getsize(enc))
        except Exception as e:
            result["encrypt_error"] = str(e)

    offsite = os.environ.get("MGN_BACKUP_OFFSITE", "")
    if offsite:
        try:
            Path(offsite).mkdir(parents=True, exist_ok=True)
            shutil.copy2(result["file"], offsite)
            result["offsite"] = offsite
        except Exception as e:
            result["offsite_error"] = str(e)

    backups = sorted(dest.glob("mgn_backup_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[keep:]:
        try:
            old.unlink()
        except Exception:
            pass
    result["kept"] = min(len(backups), keep)
    return result


def list_backups(data_dir=None):
    dest = backup_dir(data_dir)
    if not dest.exists():
        return []
    out = []
    for p in sorted(dest.glob("mgn_backup_*"), key=lambda p: p.stat().st_mtime, reverse=True):
        st = p.stat()
        out.append({"name": p.name, "size_kb": round(st.st_size / 1024, 1),
                    "when": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")})
    return out


if __name__ == "__main__":
    print(create_backup())
