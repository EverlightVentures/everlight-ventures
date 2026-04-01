from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(os.environ.get("CRYPTO_BOT_DIR", Path(__file__).resolve().parent))
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
RUNTIME_ENV_PATH = BASE_DIR / "secrets" / "runtime.env"
REPORT_HISTORY_PATH = LOGS_DIR / "report_history.jsonl"
REPORT_ARCHIVE_DIR = LOGS_DIR / "report_archive"
LATEST_REPORT_PATH = DATA_DIR / "report_latest.json"


def _safe_name(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(value))
    return safe.strip("_")[:96] or "report"


def _preview(content: str, limit: int = 1400) -> str:
    lines = [line.rstrip() for line in str(content or "").splitlines()]
    compact = []
    for line in lines:
        if line or (compact and compact[-1]):
            compact.append(line)
    preview = "\n".join(compact[:30]).strip()
    return preview[:limit]


def _history_link(report_id: str) -> str:
    base = (
        os.environ.get("XLM_REPORT_PUBLIC_BASE_URL", "").strip()
        or os.environ.get("REPORT_PUBLIC_BASE_URL", "").strip()
    )
    if not base and RUNTIME_ENV_PATH.exists():
        try:
            for raw in RUNTIME_ENV_PATH.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if line.startswith("XLM_REPORT_PUBLIC_BASE_URL="):
                    base = line.split("=", 1)[1].strip()
                    break
                if line.startswith("REPORT_PUBLIC_BASE_URL="):
                    base = line.split("=", 1)[1].strip()
                    break
        except Exception:
            base = ""
    if not base:
        return ""
    if "{report_id}" in base:
        return base.format(report_id=report_id)
    if base.endswith("="):
        return f"{base}{report_id}"
    return f"{base.rstrip('/')}/{report_id}"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str) + "\n")


def record_report(
    *,
    title: str,
    content: str,
    summary: str,
    app: str,
    folder: str,
    doc_link: str = "",
    local_path: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    created_at = datetime.now(timezone.utc).isoformat()
    metadata = metadata or {}
    report_kind = str(metadata.get("report_kind") or "report")
    report_id = hashlib.sha1(
        f"{created_at}|{app}|{report_kind}|{title}|{summary}".encode("utf-8")
    ).hexdigest()[:20]

    REPORT_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    stored_path = local_path
    if not stored_path:
        filename = f"{created_at[:19].replace(':', '-')}_{_safe_name(title)}_{report_id}.md"
        archive_path = REPORT_ARCHIVE_DIR / filename
        archive_path.write_text(str(content or ""), encoding="utf-8")
        stored_path = str(archive_path)

    payload = {
        "report_id": report_id,
        "created_at": created_at,
        "app": app,
        "report_kind": report_kind,
        "title": title,
        "summary": summary,
        "status": "doc_published" if doc_link else "fallback_saved",
        "folder_path": folder,
        "doc_link": doc_link,
        "history_link": _history_link(report_id),
        "stored_path": stored_path,
        "preview": _preview(content),
        "metadata": metadata,
    }
    _append_jsonl(REPORT_HISTORY_PATH, payload)
    _write_json(LATEST_REPORT_PATH, payload)
    return payload
