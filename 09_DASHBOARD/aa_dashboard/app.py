import json
import mimetypes
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"


def load_config() -> Dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "roots": [str(Path.cwd())],
        "default_root": str(Path.cwd()),
        "max_list_items": 2000,
        "max_search_results": 500,
        "recent_limit": 40,
        "ignore_dirs": [],
        "follow_symlinks": False,
        "apps": [],
    }


CONFIG = load_config()
ROOTS = [Path(p).resolve() for p in CONFIG.get("roots", []) if Path(p).exists()]
DEFAULT_ROOT = Path(CONFIG.get("default_root", ROOTS[0] if ROOTS else ".")).resolve()
if DEFAULT_ROOT not in ROOTS and ROOTS:
    DEFAULT_ROOT = ROOTS[0]
MAX_LIST = int(CONFIG.get("max_list_items", 2000))
MAX_SEARCH = int(CONFIG.get("max_search_results", 500))
RECENT_LIMIT = int(CONFIG.get("recent_limit", 40))
IGNORE_DIRS = set(CONFIG.get("ignore_dirs", []))
FOLLOW_SYMLINKS = bool(CONFIG.get("follow_symlinks", False))
APPS = CONFIG.get("apps", [])

app = FastAPI(title="AA Dashboard", version="0.2.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


class RootNotFound(Exception):
    pass


def get_root(root_id: Optional[int]) -> Path:
    if not ROOTS:
        raise RootNotFound("No roots configured")
    if root_id is None:
        root = DEFAULT_ROOT
    else:
        try:
            root = ROOTS[int(root_id)]
        except (ValueError, IndexError):
            raise RootNotFound("Invalid root id")
    return root


def is_within(root: Path, target: Path) -> bool:
    try:
        target.relative_to(root)
        return True
    except ValueError:
        return False


def safe_path(root: Path, rel_path: str) -> Path:
    rel_path = rel_path.lstrip("/")
    target = (root / rel_path).resolve()
    if not is_within(root, target):
        raise HTTPException(status_code=403, detail="Path outside root")
    if not FOLLOW_SYMLINKS and target.is_symlink():
        raise HTTPException(status_code=403, detail="Symlinks are disabled")
    return target


EXT_MIME = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".mp4": "video/mp4",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}

def guess_mime(target: Path) -> str:
    mime = guess_mime(target)
    if mime:
        return mime
    return EXT_MIME.get(target.suffix.lower(), "application/octet-stream")

def file_info(root: Path, target: Path) -> Dict:
    stat = target.stat()
    rel = str(target.relative_to(root)) if is_within(root, target) else str(target)
    mime = guess_mime(target)
    return {
        "name": target.name,
        "path": rel,
        "is_dir": target.is_dir(),
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "mtime_iso": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "mime": mime,
    }


def iter_dir(root: Path, target: Path) -> List[Dict]:
    items = []
    try:
        for entry in os.scandir(target):
            try:
                p = Path(entry.path)
                info = file_info(root, p)
                items.append(info)
            except FileNotFoundError:
                continue
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    return items[:MAX_LIST]


def search(root: Path, query: str) -> Tuple[List[Dict], bool]:
    results = []
    truncated = False
    query = query.lower().strip()
    if not query:
        return [], False
    for dirpath, dirnames, filenames in os.walk(root):
        dirpath = Path(dirpath)
        if not FOLLOW_SYMLINKS:
            dirnames[:] = [d for d in dirnames if not (dirpath / d).is_symlink()]
        if IGNORE_DIRS:
            dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for name in dirnames + filenames:
            if query in name.lower():
                p = dirpath / name
                try:
                    results.append(file_info(root, p))
                except FileNotFoundError:
                    continue
                if len(results) >= MAX_SEARCH:
                    truncated = True
                    return results, truncated
    return results, truncated


def recent_files(root: Path) -> List[Dict]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirpath = Path(dirpath)
        if not FOLLOW_SYMLINKS:
            dirnames[:] = [d for d in dirnames if not (dirpath / d).is_symlink()]
        if IGNORE_DIRS:
            dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for name in filenames:
            p = dirpath / name
            try:
                info = file_info(root, p)
                if not info["is_dir"]:
                    files.append(info)
            except (FileNotFoundError, PermissionError):
                continue
    files.sort(key=lambda x: x["mtime"], reverse=True)
    return files[:RECENT_LIMIT]


def parse_range(range_header: Optional[str], file_size: int) -> Optional[Tuple[int, int]]:
    if not range_header:
        return None
    if not range_header.startswith("bytes="):
        return None
    range_val = range_header.replace("bytes=", "", 1)
    if "," in range_val:
        return None
    start_str, end_str = range_val.split("-", 1)
    if start_str == "":
        length = int(end_str)
        start = max(file_size - length, 0)
        end = file_size - 1
    else:
        start = int(start_str)
        end = int(end_str) if end_str else file_size - 1
    if start > end or start < 0:
        return None
    return start, min(end, file_size - 1)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/view", response_class=HTMLResponse)
def view(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/roots")
def api_roots():
    roots = []
    for idx, root in enumerate(ROOTS):
        roots.append({"id": idx, "name": root.name or str(root), "path": str(root)})
    default_id = None
    for i, r in enumerate(ROOTS):
        if r == DEFAULT_ROOT:
            default_id = i
            break
    return {"roots": roots, "default": default_id}


@app.get("/api/list")
def api_list(root: Optional[int] = None, path: str = ""):
    try:
        root_path = get_root(root)
    except RootNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    target = safe_path(root_path, path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Not found")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Not a directory")
    return {
        "root": str(root_path),
        "path": str(target.relative_to(root_path)),
        "items": iter_dir(root_path, target),
    }


@app.get("/api/search")
def api_search(q: str, root: Optional[int] = None):
    try:
        root_path = get_root(root)
    except RootNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    results, truncated = search(root_path, q)
    return {"results": results, "truncated": truncated}


@app.get("/api/recent")
def api_recent(root: Optional[int] = None):
    try:
        root_path = get_root(root)
    except RootNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"results": recent_files(root_path)}


@app.get("/api/usage")
def api_usage(root: Optional[int] = None):
    try:
        root_path = get_root(root)
    except RootNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    usage = shutil.disk_usage(root_path)
    return {
        "total": usage.total,
        "used": usage.used,
        "free": usage.free,
        "percent": round(usage.used / usage.total * 100, 2) if usage.total else 0,
    }


@app.get("/api/apps")
def api_apps():
    return {"apps": APPS}


@app.get("/api/stats")
def api_stats(root: Optional[int] = None, path: str = ""):
    try:
        root_path = get_root(root)
    except RootNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    target = safe_path(root_path, path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return file_info(root_path, target)


@app.get("/api/raw")
def api_raw(request: Request, root: Optional[int] = None, path: str = ""):
    try:
        root_path = get_root(root)
    except RootNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    target = safe_path(root_path, path)
    if not target.exists() or target.is_dir():
        raise HTTPException(status_code=404, detail="Not found")

    file_size = target.stat().st_size
    range_header = request.headers.get("range")
    byte_range = parse_range(range_header, file_size)

    if not byte_range:
        mime = guess_mime(target)
        headers = {"Content-Disposition": f"inline; filename=\"{target.name}\""}
        return FileResponse(target, media_type=mime, headers=headers)

    start, end = byte_range
    length = end - start + 1
    with open(target, "rb") as f:
        f.seek(start)
        data = f.read(length)
    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
    }
    mime = guess_mime(target)
    return Response(content=data, status_code=206, media_type=mime, headers=headers)


@app.get("/health")
def health():
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8765, reload=True)
