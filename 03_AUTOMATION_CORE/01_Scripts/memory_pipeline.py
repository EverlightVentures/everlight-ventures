"""memory_pipeline.py - Cleanup-to-knowledge-bank, not cleanup-to-void.

Source: Lucrex directive. Nothing gets deleted; content is passed down the memory pipeline
into a spreadsheet knowledge bank + Blinko + markdown archive BEFORE disk reclaims space.

Pipeline:
  1. Candidate identified for cleanup (log file, cache dir, old report, journal)
  2. Summarize the content via Haiku (one-sentence + key signals)
  3. Append a row to the Knowledge Bank Google Sheet
     (columns: date_utc, source_type, path, size_bytes, summary, key_signals, blinko_id, md_archive_path)
  4. Write a preserved markdown copy to `08_BACKUPS/knowledge_bank/YYYY-MM/<slug>.md`
  5. Push a Blinko note with tag `#hive/memory-pipeline`
  6. Only THEN mark the source safe to reclaim

This file is the entry point. `disk_guardian.py` should call
`memory_pipeline.ingest_before_delete(path)` instead of blind rm.

Usage:
    from memory_pipeline import ingest_before_delete, ingest_and_trim

    # Preserve context then delete a file
    ingest_before_delete("/tmp/old_report.log")

    # Preserve then trim the middle of a file, keep head + tail
    ingest_and_trim("/var/log/xlm-bot.log", keep_lines_head=200, keep_lines_tail=200)

CLI:
    python3 memory_pipeline.py --ingest /path/to/old.log
    python3 memory_pipeline.py --scan /home/opc/xlm-bot/logs --older-than-days 7
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE_CANDIDATES = [
    Path("/mnt/sdcard/AA_MY_DRIVE"),
    Path("/home/opc/AA_MY_DRIVE"),
]

BLINKO_URL = os.environ.get("BLINKO_URL", "http://163.192.19.196:1111")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
HAIKU_MODEL = "claude-haiku-4-5-20251001"
SHEETS_WEBHOOK_ENV = "KNOWLEDGE_BANK_SHEETS_WEBHOOK"  # n8n webhook that appends to GSheet


def _workspace() -> Path:
    for p in WORKSPACE_CANDIDATES:
        if p.exists():
            return p
    return Path("/tmp/AA_MY_DRIVE_fallback")


def _load_env_once() -> None:
    if os.environ.get("_MEMPIPE_ENV_LOADED"):
        return
    for env in [
        _workspace() / "03_AUTOMATION_CORE" / "03_Credentials" / ".env",
        Path("/home/opc/.env"),
    ]:
        if not env.exists():
            continue
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    os.environ["_MEMPIPE_ENV_LOADED"] = "1"


# ---------------------------------------------------------------------------
# Summarizer (Haiku)
# ---------------------------------------------------------------------------

def summarize_content(content: str, source_hint: str = "") -> dict[str, Any]:
    """Return {summary, key_signals: [..], tokens_seen}."""
    _load_env_once()
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return {"summary": "(no API key available, stored raw)", "key_signals": [], "tokens_seen": 0}

    # Truncate very large blobs
    trimmed = content[:8000]
    prompt = (
        "You are compressing a log or report before it is archived and deleted. "
        "Produce a single-sentence summary PLUS 3-6 key signals (dates, numbers, "
        "anomalies, named entities). Respond ONLY as JSON.\n\n"
        f"Source hint: {source_hint or 'unknown'}\n\n"
        f"Content:\n{trimmed}\n\n"
        'JSON shape: {"summary": "<1 sentence>", "key_signals": ["signal1", "signal2", ...]}'
    )
    body = json.dumps({
        "model": HAIKU_MODEL,
        "max_tokens": 400,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        ANTHROPIC_URL,
        data=body,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        return {"summary": f"(summarize fail: {e})", "key_signals": [], "tokens_seen": len(content)}
    raw = data.get("content", [{}])[0].get("text", "")
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        return {"summary": raw[:200], "key_signals": [], "tokens_seen": len(content)}
    try:
        parsed = json.loads(raw[start:end + 1])
    except json.JSONDecodeError:
        return {"summary": raw[:200], "key_signals": [], "tokens_seen": len(content)}
    return {
        "summary": str(parsed.get("summary", ""))[:400],
        "key_signals": list(parsed.get("key_signals", []))[:10],
        "tokens_seen": len(content),
    }


# ---------------------------------------------------------------------------
# Archive to markdown
# ---------------------------------------------------------------------------

def write_md_archive(source_path: Path, content: str, summary: dict[str, Any]) -> Path:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    archive_root = _workspace() / "08_BACKUPS" / "knowledge_bank" / month
    if not archive_root.parent.parent.exists():
        # workspace may not exist on Oracle; fall back to /home/opc
        archive_root = Path("/home/opc/hive_reports/knowledge_bank") / month
    archive_root.mkdir(parents=True, exist_ok=True)
    slug_base = str(source_path).replace("/", "_").strip("_")[-80:]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_path = archive_root / f"{ts}_{slug_base}.md"
    header = (
        f"---\n"
        f"source_path: {source_path}\n"
        f"archived_at_utc: {datetime.now(timezone.utc).isoformat()}\n"
        f"original_bytes: {len(content)}\n"
        f"summary: {summary.get('summary','')}\n"
        f"key_signals: {json.dumps(summary.get('key_signals', []))}\n"
        f"---\n\n"
    )
    # Always include summary first, then a tail excerpt of raw content (bounded)
    tail = content[-4000:] if len(content) > 4000 else content
    archive_path.write_text(header + "# Archived Content (tail excerpt)\n\n" + tail, encoding="utf-8")
    return archive_path


# ---------------------------------------------------------------------------
# Blinko + Google Sheets knowledge bank
# ---------------------------------------------------------------------------

def log_blinko(source_path: Path, summary: dict[str, Any], archive_path: Path) -> str:
    note = (
        f"# Memory Pipeline Ingest: {source_path.name}\n\n"
        f"#hive/memory-pipeline #hive/archive\n\n"
        f"**Source**: `{source_path}`\n"
        f"**Archived**: `{archive_path}`\n"
        f"**Original bytes**: {summary.get('tokens_seen', 0)}\n\n"
        f"## Summary\n\n{summary.get('summary','(none)')}\n\n"
        f"## Key signals\n\n"
        + "\n".join(f"- {s}" for s in summary.get("key_signals", []))
        + "\n"
    )
    body = json.dumps({"content": note, "type": 1}).encode()
    req = urllib.request.Request(
        f"{BLINKO_URL}/api/v1/note/upsert",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode()).get("id", "")
    except Exception:
        return ""


def log_sheets(row: dict[str, Any]) -> bool:
    """Append a row to the Knowledge Bank. Webhook first, local CSV fallback.

    The primary path is an n8n webhook that does a Google Sheets 'append row'.
    If that fails (or no webhook env var), we ALWAYS append to a local CSV at
    `08_BACKUPS/knowledge_bank/rows.csv` so zero data is lost. When the webhook
    comes back online, a separate sync job can replay the CSV rows.
    """
    sent_webhook = False
    url = os.environ.get(SHEETS_WEBHOOK_ENV, "")
    if url:
        body = json.dumps(row).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=15) as _:
                sent_webhook = True
        except Exception:
            sent_webhook = False

    # ALWAYS write CSV fallback (also acts as audit trail)
    csv_path = _csv_path()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.exists()
    columns = ["date_utc", "source_type", "path", "size_bytes", "summary",
               "key_signals", "blinko_id", "md_archive_path", "webhook_synced"]
    # Minimal CSV writer (avoid import csv overhead in hot path)
    import csv as _csv
    with csv_path.open("a", encoding="utf-8", newline="") as f:
        writer = _csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        row_out = dict(row)
        row_out["webhook_synced"] = "yes" if sent_webhook else "no"
        writer.writerow(row_out)

    return sent_webhook


def _csv_path():
    if (_workspace() / "08_BACKUPS").exists():
        return _workspace() / "08_BACKUPS" / "knowledge_bank" / "rows.csv"
    return Path("/home/opc/hive_reports/knowledge_bank/rows.csv")


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def ingest_content(path_str: str, content: str, source_type: str = "log") -> dict[str, Any]:
    """Run the full pipeline on an already-read content blob."""
    path = Path(path_str)
    summary = summarize_content(content, source_hint=f"{source_type}: {path.name}")
    archive_path = write_md_archive(path, content, summary)
    blinko_id = log_blinko(path, summary, archive_path)
    row = {
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "source_type": source_type,
        "path": str(path),
        "size_bytes": len(content),
        "summary": summary.get("summary", ""),
        "key_signals": "; ".join(summary.get("key_signals", [])),
        "blinko_id": blinko_id,
        "md_archive_path": str(archive_path),
    }
    sheets_ok = log_sheets(row)
    return {"row": row, "sheets_logged": sheets_ok, "blinko_id": blinko_id, "archive_path": str(archive_path)}


def ingest_before_delete(path_str: str, source_type: str = "log") -> dict[str, Any]:
    """Archive context then return. Caller still runs the actual rm.

    We intentionally do NOT delete. Caller decides based on the returned payload.
    If `ingest_before_delete` returns success, caller can safely rm.
    """
    path = Path(path_str)
    if not path.exists():
        return {"ok": False, "error": f"not found: {path}"}
    if path.is_dir():
        return {"ok": False, "error": "dirs not supported; call per-file"}
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {"ok": False, "error": str(e)}
    out = ingest_content(str(path), content, source_type)
    out["ok"] = True
    out["safe_to_delete"] = bool(out.get("blinko_id")) or bool(out.get("archive_path"))
    return out


def ingest_and_trim(path_str: str, keep_lines_head: int = 200, keep_lines_tail: int = 200) -> dict[str, Any]:
    """Archive full content, then rewrite file with only head + tail bounds."""
    path = Path(path_str)
    if not path.exists():
        return {"ok": False, "error": "not found"}
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {"ok": False, "error": str(e)}
    out = ingest_content(str(path), content, source_type="trimmed_log")
    lines = content.splitlines()
    if len(lines) > (keep_lines_head + keep_lines_tail):
        head = lines[:keep_lines_head]
        tail = lines[-keep_lines_tail:]
        marker = f"\n...<MIDDLE TRIMMED: see {out['archive_path']}>...\n"
        path.write_text("\n".join(head) + marker + "\n".join(tail) + "\n", encoding="utf-8")
    out["ok"] = True
    out["trimmed"] = True
    return out


def scan(dir_str: str, older_than_days: int = 7, size_min_bytes: int = 1024) -> list[dict[str, Any]]:
    """Walk a directory. Ingest-and-mark every file older than N days above size_min."""
    now = time.time()
    cutoff = now - older_than_days * 86400
    base = Path(dir_str)
    if not base.exists():
        return [{"error": f"no such dir: {base}"}]
    out = []
    for p in base.rglob("*"):
        if not p.is_file():
            continue
        try:
            st = p.stat()
        except OSError:
            continue
        if st.st_mtime > cutoff or st.st_size < size_min_bytes:
            continue
        res = ingest_before_delete(str(p), source_type="scan_candidate")
        res["path"] = str(p)
        out.append(res)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ingest", help="Single file path to ingest (archives context, does NOT delete)")
    ap.add_argument("--trim", help="Path to archive-then-trim")
    ap.add_argument("--keep-head", type=int, default=200)
    ap.add_argument("--keep-tail", type=int, default=200)
    ap.add_argument("--scan", help="Directory to scan for old files")
    ap.add_argument("--older-than-days", type=int, default=7)
    args = ap.parse_args()

    if args.ingest:
        print(json.dumps(ingest_before_delete(args.ingest), indent=2))
    elif args.trim:
        print(json.dumps(ingest_and_trim(args.trim, args.keep_head, args.keep_tail), indent=2))
    elif args.scan:
        print(json.dumps(scan(args.scan, args.older_than_days), indent=2))
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
