#!/usr/bin/env python3
"""
Moltbook -- Lucrex's personal AI notebook dashboard.

Stdlib HTTP server (no Flask/FastAPI -- proven Termux/proot pattern from
blinko_lite.py). Serves a single-page Everlight-themed dashboard that pulls
live data from the Hive's existing scripts (activity_feed.py, blinko_status.py)
and state files (AGENT_MAILBOX.md).

Default bind: 127.0.0.1:1112 (local only).
Set MOLTBOOK_BIND=0.0.0.0 to expose on tailnet (recommend only after tailnet
ACLs are tightened).

Routes:
  GET  /                  -> index.html
  GET  /static/*          -> CSS / JS / fonts
  GET  /api/memory        -> blinko_status.py JSON output
  GET  /api/activity      -> activity_feed.py JSON output (parsed)
  GET  /api/family        -> static device registry
  GET  /api/mailbox       -> last N AGENT_MAILBOX entries parsed
  GET  /api/notes         -> Blinko recent notes (remote or local fallback)
  GET  /api/health        -> server own health

Logging:
  Errors -> stderr (visible in nohup/journal).
  Access -> stdout if MOLTBOOK_VERBOSE=1.
"""
from __future__ import annotations
import html as _html
import json
import os
import re
import subprocess
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
SCRIPTS = WORKSPACE / "03_AUTOMATION_CORE" / "01_Scripts"
STATIC = HERE / "static"
INDEX = HERE / "index.html"
CONFIG = HERE / "moltbook.json"
MAILBOX = WORKSPACE / "_state" / "AGENT_MAILBOX.md"
AUDIT_DIR = WORKSPACE / "_state" / "audit_log"

BLINKO_URLS = [
    "http://e5-mother:1111",
    "http://100.125.115.95:1111",
]
LOCAL_DB = WORKSPACE / "_state" / "blinko_lite.db"

PORT = int(os.environ.get("MOLTBOOK_PORT", "2401"))  # 2400 band = Apps (per port band scheme)
BIND = os.environ.get("MOLTBOOK_BIND", "127.0.0.1")
VERBOSE = os.environ.get("MOLTBOOK_VERBOSE") == "1"


# ----- helpers -----
def _load_config() -> dict:
    if CONFIG.is_file():
        try:
            return json.loads(CONFIG.read_text())
        except json.JSONDecodeError:
            pass
    return {
        "title": "Moltbook",
        "subtitle": "Lucrex Notebook",
        "refresh_seconds": 30,
        "devices": [
            {"name": "e5-mother", "tailnet_ip": "100.125.115.95", "role": "Oracle hub · 24/7"},
            {"name": "acemagician-pc", "tailnet_ip": "100.93.253.49", "role": "Powerful #2"},
            {"name": "richards-z-fold7", "tailnet_ip": "100.112.180.29", "role": "Workstation"},
            {"name": "mgn-latitude-e7240", "tailnet_ip": "100.120.23.23", "role": "Spare"},
        ],
    }


def _run_script(args: list[str], timeout: int = 6) -> dict | None:
    """Run a script with timeout, capture stdout, parse as JSON."""
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        if r.returncode in (0, 1, 2):  # 1/2 are valid for status tools
            return json.loads(r.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    return None


def _parse_mailbox(n: int = 15) -> list[dict]:
    if not MAILBOX.is_file():
        return []
    pattern = re.compile(r"^\[(\d{4}-\d{2}-\d{2}[^\]]+)\]\s+FROM:(\S+)\s*\|\s*(.+)")
    items: list[dict] = []
    for line in MAILBOX.read_text().splitlines():
        m = pattern.match(line)
        if m:
            items.append({"ts": m.group(1), "from": m.group(2),
                          "msg": m.group(3)[:240].strip()})
    return items[-n:][::-1]  # most recent first


def _activity_feed(n: int) -> list[dict]:
    """Try the activity_feed.py script; if it lacks --mode=json, parse stdout."""
    script = SCRIPTS / "activity_feed.py"
    if not script.is_file():
        return []
    try:
        r = subprocess.run(
            [sys.executable, str(script), "-n", str(n)],
            capture_output=True, text=True, timeout=8
        )
        events = []
        for line in r.stdout.splitlines():
            line = line.strip()
            # parse "  2026-05-15 07:30:00  [mailbox:phone       ]  message"
            m = re.match(r"\s*(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}|\d{4}-\d{2}-\d{2}\s~\d{2}:\d{2}\s\w*)\s+\[([^\]]+)\]\s+(.+)", line)
            if m:
                events.append({"ts": m.group(1).strip(),
                               "src": m.group(2).strip(),
                               "summary": m.group(3).strip()[:240]})
        return events[:n]
    except (subprocess.TimeoutExpired, OSError):
        return []


def _memory_state() -> dict:
    script = SCRIPTS / "blinko_status.py"
    if script.is_file():
        out = _run_script([sys.executable, str(script), "-m", "json"], timeout=5)
        if out:
            return out
    # ultra-minimal fallback if script missing
    return {"state": "UNKNOWN", "probe_ms": 0}


def _parse_audit_frontmatter(text: str) -> tuple[dict, str]:
    """Parse simple YAML-style frontmatter (single-line key: value). Returns (meta, body)."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    fm_text = text[4:end]
    body = text[end + 5:]
    meta: dict = {}
    for line in fm_text.split("\n"):
        if ":" not in line or line.startswith("#"):
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip()
    return meta, body


def _render_markdown(text: str) -> str:
    """Minimal stdlib markdown -> HTML. Handles headers, bold, inline+block code,
    lists, tables, links, paragraphs. Escapes all user content via html.escape."""
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    in_code = False
    code_lang = ""
    code_buf: list[str] = []

    def inline(s: str) -> str:
        s = _html.escape(s)
        s = re.sub(r"`([^`]+)`", lambda m: f"<code>{m.group(1)}</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", lambda m: f"<strong>{m.group(1)}</strong>", s)
        # links [text](url) -- since we already escaped, the [ and ] are fine; URL is escaped
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                   lambda m: f'<a href="{m.group(2)}" target="_blank" rel="noopener">{m.group(1)}</a>',
                   s)
        return s

    while i < len(lines):
        line = lines[i]
        # Fenced code blocks
        if line.startswith("```"):
            if not in_code:
                in_code = True
                code_lang = line[3:].strip()
                code_buf = []
            else:
                in_code = False
                escaped = _html.escape("\n".join(code_buf))
                lang_attr = f' class="lang-{_html.escape(code_lang)}"' if code_lang else ""
                out.append(f"<pre><code{lang_attr}>{escaped}</code></pre>")
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue
        # Headers
        m = re.match(r"^(#{1,4})\s+(.+)$", line)
        if m:
            level = len(m.group(1))
            out.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
            i += 1
            continue
        # Tables: header line | followed by | --- |
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s\-:|]+\|\s*$", lines[i + 1]):
            headers = [c.strip() for c in line.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            parts = ["<table>", "<thead><tr>"]
            parts += [f"<th>{inline(h)}</th>" for h in headers]
            parts += ["</tr></thead><tbody>"]
            for r in rows:
                parts.append("<tr>")
                parts += [f"<td>{inline(c)}</td>" for c in r]
                parts.append("</tr>")
            parts.append("</tbody></table>")
            out.append("".join(parts))
            continue
        # Unordered lists
        if re.match(r"^[-*]\s+", line):
            items = []
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i]):
                items.append(re.sub(r"^[-*]\s+", "", lines[i]))
                i += 1
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>")
            continue
        # Ordered lists
        if re.match(r"^\d+\.\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i]):
                items.append(re.sub(r"^\d+\.\s+", "", lines[i]))
                i += 1
            out.append("<ol>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ol>")
            continue
        # Blockquotes
        if line.startswith("> "):
            quote_lines = []
            while i < len(lines) and lines[i].startswith("> "):
                quote_lines.append(lines[i][2:])
                i += 1
            out.append(f"<blockquote>{inline(' '.join(quote_lines))}</blockquote>")
            continue
        # Blank
        if not line.strip():
            i += 1
            continue
        # Paragraph
        para = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not (
            lines[i].startswith("#") or lines[i].startswith("```")
            or lines[i].startswith("|") or lines[i].startswith("> ")
            or re.match(r"^[-*]\s", lines[i]) or re.match(r"^\d+\.\s", lines[i])
        ):
            para.append(lines[i])
            i += 1
        out.append(f"<p>{inline(' '.join(para))}</p>")
    return "\n".join(out)


def _list_audit_entries() -> list[dict]:
    """Scan audit_log/ dir, parse frontmatter, return list sorted newest-first."""
    if not AUDIT_DIR.is_dir():
        return []
    entries = []
    for p in sorted(AUDIT_DIR.glob("*.md"), reverse=True):
        try:
            meta, _ = _parse_audit_frontmatter(p.read_text(encoding="utf-8"))
            if not meta:
                continue
            entries.append({
                "id": meta.get("id", p.stem),
                "title": meta.get("title", p.stem),
                "date": meta.get("date", ""),
                "agent": meta.get("agent", ""),
                "phase": meta.get("phase", ""),
                "category": meta.get("category", ""),
                "thread": meta.get("thread", ""),
                "session": meta.get("session", ""),
                "status": meta.get("status", ""),
                "tags": [t.strip() for t in (meta.get("tags", "") or "").split(",") if t.strip()],
                "summary": meta.get("summary", ""),
            })
        except (OSError, UnicodeDecodeError):
            continue
    return entries


def _get_audit_entry(entry_id: str) -> dict | None:
    """Return one audit entry by id with rendered HTML body. Defends against path traversal."""
    if not AUDIT_DIR.is_dir():
        return None
    if "/" in entry_id or ".." in entry_id or not entry_id:
        return None
    target = (AUDIT_DIR / f"{entry_id}.md").resolve()
    try:
        if not str(target).startswith(str(AUDIT_DIR.resolve())):
            return None
        if not target.is_file():
            # fall back: look for any file whose frontmatter id matches
            for p in AUDIT_DIR.glob("*.md"):
                meta, _ = _parse_audit_frontmatter(p.read_text(encoding="utf-8"))
                if meta.get("id") == entry_id:
                    target = p
                    break
            else:
                return None
        text = target.read_text(encoding="utf-8")
        meta, body = _parse_audit_frontmatter(text)
        return {
            "id": meta.get("id", target.stem),
            "title": meta.get("title", target.stem),
            "date": meta.get("date", ""),
            "agent": meta.get("agent", ""),
            "phase": meta.get("phase", ""),
            "category": meta.get("category", ""),
            "thread": meta.get("thread", ""),
            "session": meta.get("session", ""),
            "status": meta.get("status", ""),
            "tags": [t.strip() for t in (meta.get("tags", "") or "").split(",") if t.strip()],
            "summary": meta.get("summary", ""),
            "html": _render_markdown(body),
            "raw": body,
        }
    except (OSError, UnicodeDecodeError):
        return None


def _blinko_recent_notes(n: int = 5) -> list[dict]:
    """Try remote Blinko first; fall back to local SQLite."""
    payload = json.dumps({"query": "", "limit": n}).encode("utf-8")
    for url in BLINKO_URLS:
        try:
            req = urllib.request.Request(
                f"{url}/api/v1/note/list", data=payload, method="POST",
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3) as r:
                data = json.loads(r.read().decode("utf-8"))
                return [{"id": x.get("id", ""),
                         "created_at": x.get("created_at", ""),
                         "preview": (x.get("content", "")[:160]
                                     .replace("\n", " ").strip())}
                        for x in data.get("items", [])][:n]
        except Exception:
            continue
    # local fallback
    if LOCAL_DB.is_file():
        try:
            conn = sqlite3.connect(f"file:{LOCAL_DB}?mode=ro", uri=True, timeout=2)
            rows = conn.execute(
                "select id, created_at, substr(content,1,160) from notes "
                "order by created_at desc limit ?", (n,)
            ).fetchall()
            conn.close()
            return [{"id": r[0], "created_at": r[1],
                     "preview": r[2].replace("\n", " ").strip()} for r in rows]
        except sqlite3.DatabaseError:
            pass
    return []


# ----- HTTP handler -----
class MoltHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quiet by default
        if VERBOSE:
            super().log_message(fmt, *args)

    def _send(self, code: int, body: bytes, content_type: str,
              extra_headers: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data: dict | list, code: int = 200) -> None:
        self._send(code, json.dumps(data, indent=2).encode("utf-8"),
                   "application/json")

    def _file(self, path: Path, content_type: str) -> None:
        try:
            self._send(200, path.read_bytes(), content_type)
        except FileNotFoundError:
            self._json({"error": "not found"}, 404)

    def do_GET(self):
        path = self.path.split("?", 1)[0]

        if path == "/" or path == "/index.html":
            return self._file(INDEX, "text/html; charset=utf-8")

        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            target = (STATIC / rel).resolve()
            if not str(target).startswith(str(STATIC.resolve())):
                return self._json({"error": "forbidden"}, 403)
            content_type = (
                "text/css" if target.suffix == ".css"
                else "application/javascript" if target.suffix == ".js"
                else "application/octet-stream"
            )
            return self._file(target, content_type)

        if path == "/api/health":
            return self._json({"status": "ok", "pid": os.getpid(),
                               "uptime_s": int(time.time() - START_TS)})

        if path == "/api/memory":
            return self._json(_memory_state())

        if path == "/api/activity":
            return self._json({"events": _activity_feed(20)})

        if path == "/api/mailbox":
            return self._json({"entries": _parse_mailbox(15)})

        if path == "/api/family":
            return self._json({"devices": _load_config().get("devices", [])})

        if path == "/api/notes":
            return self._json({"items": _blinko_recent_notes(5)})

        if path == "/api/audit":
            return self._json({"entries": _list_audit_entries()})

        if path == "/api/audit/classification":
            class_file = AUDIT_DIR / "_classification.json"
            if class_file.is_file():
                try:
                    return self._json(json.loads(class_file.read_text(encoding="utf-8")))
                except json.JSONDecodeError:
                    return self._json({"error": "classification file malformed"}, 500)
            return self._json({"error": "no classification file"}, 404)

        if path.startswith("/api/audit/"):
            entry_id = path[len("/api/audit/"):]
            entry = _get_audit_entry(entry_id)
            if entry is None:
                return self._json({"error": "audit entry not found", "id": entry_id}, 404)
            return self._json(entry)

        if path == "/api/config":
            cfg = _load_config()
            return self._json({"title": cfg.get("title"),
                               "subtitle": cfg.get("subtitle"),
                               "refresh_seconds": cfg.get("refresh_seconds", 30)})

        return self._json({"error": "not found", "path": path}, 404)


START_TS = time.time()


def main() -> int:
    print(f"Moltbook starting on http://{BIND}:{PORT}  (workspace={WORKSPACE})",
          file=sys.stderr)
    server = HTTPServer((BIND, PORT), MoltHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Moltbook stopped", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
