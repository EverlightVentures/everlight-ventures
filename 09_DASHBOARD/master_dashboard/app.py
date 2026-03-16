import hashlib
import json
import mimetypes
import os
import shutil
import subprocess
import threading
import time
from PIL import Image
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException, Request, Response, UploadFile, File, Form
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
        "cache_dir": "/mnt/sdcard/AA_MY_DRIVE/.aa_dashboard_cache",
        "auto_build_index": True,
        "thumb_size": 320,
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
SERVICES = CONFIG.get("services", {})
SOFT_DELETE = bool(CONFIG.get("soft_delete", True))
REQUIRE_AUTH = bool(CONFIG.get("require_auth", False))
API_KEY = CONFIG.get("api_key", "")


async def check_auth(request: Request):
    if not REQUIRE_AUTH:
        return
    key = request.headers.get("X-API-Key", "")
    if not API_KEY or key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
CACHE_DIR = Path(CONFIG.get("cache_dir", "/mnt/sdcard/AA_MY_DRIVE/.aa_dashboard_cache"))
AUTO_BUILD_INDEX = bool(CONFIG.get("auto_build_index", True))
THUMB_SIZE = int(CONFIG.get("thumb_size", 320))
INDEX_REFRESH_SEC = int(CONFIG.get("index_refresh_sec", 60))

app = FastAPI(title="AA Dashboard", version="0.3.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if REQUIRE_AUTH:
        path = request.url.path
        if path.startswith("/api") or path.startswith("/edit") or path.startswith("/file"):
            key = request.headers.get("X-API-Key", "")
            if not API_KEY or key != API_KEY:
                return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)


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
    ".m4v": "video/mp4",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}

TEXT_EXT = {
    ".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
    ".html", ".css", ".toml", ".ini", ".cfg", ".sh",
}

EXT_GROUP = {
    "image": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"},
    "video": {".mp4", ".mkv", ".mov", ".webm"},
    "audio": {".mp3", ".m4a", ".wav", ".flac", ".ogg"},
    "doc": {".pdf", ".txt", ".md", ".rtf", ".doc", ".docx"},
    "code": {".py", ".js", ".ts", ".json", ".yaml", ".yml", ".html", ".css"},
}


def guess_mime(target: Path) -> str:
    mime, _ = mimetypes.guess_type(str(target))
    if mime:
        return mime
    return EXT_MIME.get(target.suffix.lower(), "application/octet-stream")








def version_path(root: Path, rel_path: str) -> Path:
    ts = time.strftime("%Y%m%d_%H%M%S")
    h = hashlib.sha1(f"{root}:{rel_path}:{ts}".encode("utf-8")).hexdigest()
    return CACHE_DIR / "versions" / f"{ts}_{h}"

def trash_path(root: Path, rel_path: str) -> Path:
    h = hashlib.sha1(f"{root}:{rel_path}:{time.time()}".encode("utf-8")).hexdigest()
    return CACHE_DIR / "trash" / h

def thumb_path(root: Path, rel_path: str) -> Path:
    h = hashlib.sha1(f"{root}:{rel_path}".encode("utf-8")).hexdigest()
    return CACHE_DIR / "thumbs" / f"{h}.jpg"


def build_thumbnail(root: Path, rel_path: str, target: Path) -> Path:
    out = thumb_path(root, rel_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(target) as img:
            img = img.convert("RGB")
            img.thumbnail((THUMB_SIZE, THUMB_SIZE))
            img.save(out, format="JPEG", quality=85)
    except Exception:
        if out.exists():
            out.unlink()
        raise
    return out


def file_group(target: Path) -> str:
    ext = target.suffix.lower()
    for group, exts in EXT_GROUP.items():
        if ext in exts:
            return group
    return "other"


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
        "group": "dir" if target.is_dir() else file_group(target),
        "ext": target.suffix.lower(),
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




MAX_INDEX_ITEMS = 5000  # Cap to prevent OOM on large drives

def index_refresher():
    # Delay first index build to let the server start up
    time.sleep(10)
    while True:
        if AUTO_BUILD_INDEX:
            for r in ROOTS:
                try:
                    build_index(r)
                except Exception:
                    pass
        time.sleep(INDEX_REFRESH_SEC)

if AUTO_BUILD_INDEX:
    threading.Thread(target=index_refresher, daemon=True).start()

def index_path(root: Path) -> Path:
    h = hashlib.sha1(str(root).encode("utf-8")).hexdigest()[:10]
    return CACHE_DIR / f"index_{h}.json"


def build_index(root: Path) -> Dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    capped = False
    for dirpath, dirnames, filenames in os.walk(root):
        dirpath = Path(dirpath)
        if not FOLLOW_SYMLINKS:
            dirnames[:] = [d for d in dirnames if not (dirpath / d).is_symlink()]
        if IGNORE_DIRS:
            dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        # Skip nested roots to avoid double-indexing
        dirnames[:] = [d for d in dirnames if (dirpath / d).resolve() not in ROOTS or (dirpath / d).resolve() == root]
        for name in filenames:
            p = dirpath / name
            try:
                items.append(file_info(root, p))
            except (FileNotFoundError, PermissionError):
                continue
            if len(items) >= MAX_INDEX_ITEMS:
                capped = True
                break
        if capped:
            break
    items.sort(key=lambda x: x["mtime"], reverse=True)
    payload = {
        "root": str(root),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "count": len(items),
        "capped": capped,
        "items": items,
    }
    index_path(root).write_text(json.dumps(payload))
    return payload


def load_index(root: Path) -> Optional[Dict]:
    path = index_path(root)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def ensure_index(root: Path) -> Optional[Dict]:
    index = load_index(root)
    if index is None and AUTO_BUILD_INDEX:
        return build_index(root)
    return index


def search_in_index(index: Dict, query: str) -> Tuple[List[Dict], bool]:
    query = query.lower().strip()
    results = []
    for item in index.get("items", []):
        if query in item.get("name", "").lower():
            results.append(item)
            if len(results) >= MAX_SEARCH:
                return results, True
    return results, False


def search(root: Path, query: str) -> Tuple[List[Dict], bool]:
    index = ensure_index(root)
    if index:
        return search_in_index(index, query)

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
    index = ensure_index(root)
    if index:
        return index.get("items", [])[:RECENT_LIMIT]

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


def media_files(root: Path, media_type: Optional[str] = None) -> List[Dict]:
    index = ensure_index(root)
    if index:
        items = index.get("items", [])
    else:
        items = recent_files(root)

    if media_type:
        return [i for i in items if i.get("group") == media_type]
    return [i for i in items if i.get("group") in {"image", "video", "audio"}]


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


@app.get("/api/media")
def api_media(root: Optional[int] = None, kind: Optional[str] = None):
    try:
        root_path = get_root(root)
    except RootNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"results": media_files(root_path, kind)}


@app.get("/api/index/build")
def api_index_build(root: Optional[int] = None):
    try:
        root_path = get_root(root)
    except RootNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    index = build_index(root_path)
    return {"ok": True, "count": index.get("count", 0), "generated_at": index.get("generated_at")}


@app.get("/api/index/status")
def api_index_status(root: Optional[int] = None):
    try:
        root_path = get_root(root)
    except RootNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    index = load_index(root_path)
    if not index:
        return {"ok": False}
    return {"ok": True, "count": index.get("count", 0), "generated_at": index.get("generated_at")}



@app.get("/api/thumb")
def api_thumb(root: Optional[int] = None, path: str = ""):
    try:
        root_path = get_root(root)
    except RootNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    target = safe_path(root_path, path)
    if not target.exists() or target.is_dir():
        raise HTTPException(status_code=404, detail="Not found")

    rel = str(target.relative_to(root_path))
    out = thumb_path(root_path, rel)
    if not out.exists():
        build_thumbnail(root_path, rel, target)
    return FileResponse(out, media_type="image/jpeg")


@app.post("/api/terminal/start")
async def api_terminal_start():
    # Optional: start ttyd + tmux if available
    if shutil.which("ttyd") is None:
        raise HTTPException(status_code=400, detail="ttyd not installed")
    # try to start if not running
    subprocess.Popen(["ttyd", "-p", "7681", "tmux", "new", "-A", "-s", "aa"])
    return {"ok": True, "url": "http://localhost:7681"}


@app.get("/api/search_content")
def api_search_content(root: Optional[int] = None, q: str = ""):
    if not q:
        return {"results": []}
    try:
        root_path = get_root(root)
    except RootNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    rg = shutil.which("rg")
    if not rg:
        raise HTTPException(status_code=400, detail="ripgrep not installed")

    # Build ignore globs
    globs = []
    for d in IGNORE_DIRS:
        globs.append(f"!{d}/**")
    cmd = [rg, "-n", "--no-messages", "--max-count", "200", q, str(root_path)]
    for g in globs:
        cmd.extend(["--glob", g])
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=False).stdout
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    results = [line for line in out.splitlines() if line.strip()][:200]
    return {"results": results}


@app.get("/api/smart")
def api_smart(root: Optional[int] = None, kind: str = ""):
    try:
        root_path = get_root(root)
    except RootNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    items = media_files(root_path)
    if kind:
        idx = ensure_index(root_path)
        if idx:
            items = [i for i in idx.get("items", []) if i.get("group") == kind]
        else:
            items = [i for i in items if i.get("group") == kind]
    return {"results": items}


@app.get("/api/services/list")
async def api_services_list(request: Request):
    await check_auth(request)
    return {"services": SERVICES}


@app.get("/api/services/status")
async def api_services_status(request: Request):
    await check_auth(request)
    status = {}
    for key, svc in SERVICES.items():
        status[key] = {"pid": None, "running": False}
        pid_path = Path(svc.get("pid", ""))
        if pid_path.exists():
            try:
                pid = int(pid_path.read_text().strip())
                status[key]["pid"] = pid
                os.kill(pid, 0)
                status[key]["running"] = True
            except Exception:
                status[key]["running"] = False
    return {"status": status}


@app.post("/api/services/start")
async def api_services_start(request: Request):
    await check_auth(request)
    body = await request.json()
    key = body.get("key")
    if key not in SERVICES:
        raise HTTPException(status_code=404, detail="Service not found")
    svc = SERVICES[key]
    log = svc.get("log")
    Path(log).parent.mkdir(parents=True, exist_ok=True)
    cmd = svc.get("start_cmd")
    proc = subprocess.Popen(cmd, shell=True, stdout=open(log, "a"), stderr=subprocess.STDOUT)
    Path(svc.get("pid")).write_text(str(proc.pid))
    return {"ok": True, "pid": proc.pid}


@app.post("/api/services/stop")
async def api_services_stop(request: Request):
    await check_auth(request)
    body = await request.json()
    key = body.get("key")
    if key not in SERVICES:
        raise HTTPException(status_code=404, detail="Service not found")
    svc = SERVICES[key]
    pid_path = Path(svc.get("pid"))
    if pid_path.exists():
        try:
            pid = int(pid_path.read_text().strip())
            os.kill(pid, 15)
        except Exception:
            pass
        pid_path.unlink(missing_ok=True)
    return {"ok": True}


@app.get("/api/services/logs")
async def api_services_logs(request: Request, key: str):
    await check_auth(request)
    if key not in SERVICES:
        raise HTTPException(status_code=404, detail="Service not found")
    log = SERVICES[key].get("log")
    if not log or not Path(log).exists():
        return {"logs": ""}
    data = Path(log).read_text(errors="ignore")
    return {"logs": "\n".join(data.splitlines()[-200:])}

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
    headers["Content-Disposition"] = f"inline; filename=\"{target.name}\""
    return Response(content=data, status_code=206, media_type=mime, headers=headers)


@app.get("/file", response_class=HTMLResponse)
def file_view(request: Request, root: Optional[int] = None, path: str = ""):
    try:
        root_path = get_root(root)
    except RootNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    target = safe_path(root_path, path)
    if not target.exists() or target.is_dir():
        raise HTTPException(status_code=404, detail="Not found")

    mime = guess_mime(target)
    url = f"/api/raw?root={root}&path={path}"
    kind = "other"
    text_body = ""
    if mime.startswith("image/"):
        kind = "image"
    elif mime.startswith("video/"):
        kind = "video"
    elif mime.startswith("audio/"):
        kind = "audio"
    elif mime == "application/pdf":
        kind = "pdf"
    elif mime.startswith("text/") or mime in {"application/json"} or target.suffix.lower() in TEXT_EXT:
        kind = "text"
        try:
            text_body = target.read_text(errors="ignore")
        except Exception:
            text_body = ""

    return templates.TemplateResponse(
        "file.html",
        {
            "request": request,
            "name": target.name,
            "url": url,
            "kind": kind,
            "text": text_body[:200000],
        },
    )



@app.get("/edit", response_class=HTMLResponse)
def edit_view(request: Request, root: Optional[int] = None, path: str = ""):
    try:
        root_path = get_root(root)
    except RootNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    target = safe_path(root_path, path)
    if not target.exists() or target.is_dir():
        raise HTTPException(status_code=404, detail="Not found")
    if target.suffix.lower() not in TEXT_EXT:
        raise HTTPException(status_code=415, detail="Not a text file")
    try:
        content = target.read_text(errors="ignore")
    except Exception:
        content = ""
    return templates.TemplateResponse(
        "edit.html",
        {"request": request, "name": target.name, "path": path, "root": root, "content": content},
    )


@app.post("/api/save")
async def api_save(request: Request):
    body = await request.json()
    root = body.get("root")
    path = body.get("path", "")
    content = body.get("content", "")
    try:
        root_path = get_root(root)
    except RootNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    target = safe_path(root_path, path)
    if target.is_dir():
        raise HTTPException(status_code=400, detail="Not a file")
    if target.suffix.lower() not in TEXT_EXT:
        raise HTTPException(status_code=415, detail="Not a text file")
    # version backup
    try:
        if target.exists():
            vp = version_path(root_path, str(target.relative_to(root_path)))
            vp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, vp)
    except Exception:
        pass
    target.write_text(content)
    return {"ok": True}


@app.post("/api/mkdir")
async def api_mkdir(request: Request):
    body = await request.json()
    root = body.get("root")
    path = body.get("path", "")
    name = body.get("name", "")
    if not name:
        raise HTTPException(status_code=400, detail="Missing name")
    try:
        root_path = get_root(root)
    except RootNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    parent = safe_path(root_path, path)
    if not parent.exists() or not parent.is_dir():
        raise HTTPException(status_code=400, detail="Invalid folder")
    target = (parent / name).resolve()
    if not is_within(root_path, target):
        raise HTTPException(status_code=403, detail="Path outside root")
    target.mkdir(parents=True, exist_ok=False)
    return {"ok": True}


@app.post("/api/touch")
async def api_touch(request: Request):
    body = await request.json()
    root = body.get("root")
    path = body.get("path", "")
    name = body.get("name", "")
    if not name:
        raise HTTPException(status_code=400, detail="Missing name")
    try:
        root_path = get_root(root)
    except RootNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    parent = safe_path(root_path, path)
    if not parent.exists() or not parent.is_dir():
        raise HTTPException(status_code=400, detail="Invalid folder")
    target = (parent / name).resolve()
    if not is_within(root_path, target):
        raise HTTPException(status_code=403, detail="Path outside root")
    target.write_text("")
    return {"ok": True}


@app.post("/api/delete")
async def api_delete(request: Request):
    body = await request.json()
    root = body.get("root")
    path = body.get("path", "")
    try:
        root_path = get_root(root)
    except RootNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    target = safe_path(root_path, path)
    if SOFT_DELETE:
        dest = trash_path(root_path, str(target.relative_to(root_path)))
        dest.parent.mkdir(parents=True, exist_ok=True)
        if target.is_dir():
            shutil.move(str(target), str(dest))
        else:
            shutil.move(str(target), str(dest))
    else:
        if target.is_dir():
            target.rmdir()
        else:
            target.unlink()
    return {"ok": True}


@app.post("/api/rename")
async def api_rename(request: Request):
    body = await request.json()
    root = body.get("root")
    path = body.get("path", "")
    name = body.get("name", "")
    if not name:
        raise HTTPException(status_code=400, detail="Missing name")
    try:
        root_path = get_root(root)
    except RootNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    target = safe_path(root_path, path)
    new_target = (target.parent / name).resolve()
    if not is_within(root_path, new_target):
        raise HTTPException(status_code=403, detail="Path outside root")
    target.rename(new_target)
    return {"ok": True}


@app.post("/api/move")
async def api_move(request: Request):
    body = await request.json()
    root = body.get("root")
    path = body.get("path", "")
    dest = body.get("dest", "")
    try:
        root_path = get_root(root)
    except RootNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    target = safe_path(root_path, path)
    dest_dir = safe_path(root_path, dest)
    if not dest_dir.exists() or not dest_dir.is_dir():
        raise HTTPException(status_code=400, detail="Invalid destination")
    new_target = (dest_dir / target.name).resolve()
    if not is_within(root_path, new_target):
        raise HTTPException(status_code=403, detail="Path outside root")
    target.rename(new_target)
    return {"ok": True}


@app.post("/api/upload")
async def api_upload(root: int = Form(...), path: str = Form(""), file: UploadFile = File(...)):
    try:
        root_path = get_root(root)
    except RootNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    dest_dir = safe_path(root_path, path)
    if not dest_dir.exists() or not dest_dir.is_dir():
        raise HTTPException(status_code=400, detail="Invalid destination")
    dest = (dest_dir / file.filename).resolve()
    if not is_within(root_path, dest):
        raise HTTPException(status_code=403, detail="Path outside root")
    with dest.open("wb") as f:
        f.write(await file.read())
    return {"ok": True}

@app.get("/health")
def health():
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8765, reload=True)
