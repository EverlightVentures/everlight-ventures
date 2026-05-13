"""hive_logger.py - Canonical log-line chokepoint for every Hive bot.

Purpose
-------
Every significant bot run produces one canonical log line that lands in THREE
sinks within 60s so (a) the `:8504` Django dashboard shows recent activity and
(b) artifacts a bot creates are searchable later.

The sinks
---------
  1. Local JSONL stream at `_logs/hive_runs/events.jsonl` (always written).
  2. Django endpoint `:8504/api/logger/ingest/` (graceful failure).
  3. Blinko upsert at `:1111/api/v1/note/upsert` (graceful failure).

Design
------
  * Stdlib only (urllib, json, uuid, re). No new deps.
  * Every sink is wrapped so a logging failure never aborts the bot.
  * Secrets are redacted before anything is written.
  * Per-process "current run" registry so `hive_3format.publish()` can emit
    an artifact without the caller threading the run object through.

Public API
----------
    run = hive_logger.start(agent="rex_wholesale", task="monday-run", inputs={"n":42})
    run.event("lead.ingested", {"id": 123})
    run.artifact("gdoc", url="https://...", title="Monday Pipeline")
    run.finish(status="done", summary="42 leads, 7 matches")

CLI selftest
------------
    python3 -m content_tools.hive_logger --selftest
    python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/hive_logger.py --selftest
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Tag vocabulary (sibling module)
try:
    from content_tools.hive_tags import validate_list as _validate_tags  # type: ignore
except Exception:
    try:
        from hive_tags import validate_list as _validate_tags  # type: ignore
    except Exception:
        def _validate_tags(tags: list[str]) -> list[str]:  # fallback
            return [t for t in (tags or []) if isinstance(t, str)]


# ── Config ──────────────────────────────────────────────────────────

WORKSPACE_CANDIDATES = [
    Path("/mnt/sdcard/AA_MY_DRIVE"),
    Path("/home/opc/AA_MY_DRIVE"),
    Path("/home/opc"),
]


def _workspace() -> Path:
    for p in WORKSPACE_CANDIDATES:
        if p.exists():
            return p
    return WORKSPACE_CANDIDATES[0]


_WS = _workspace()
RUNS_DIR = _WS / "_logs" / "hive_runs"
EVENTS_FILE = RUNS_DIR / "events.jsonl"
ERRORS_FILE = RUNS_DIR / "errors.jsonl"

DASHBOARD_URL = os.environ.get(
    "HIVE_DASHBOARD_URL",
    "http://127.0.0.1:2200",
)
DASHBOARD_TOKEN = os.environ.get("HIVE_LOGGER_TOKEN", "")
BLINKO_URL = os.environ.get("BLINKO_URL", "http://163.192.19.196:1111")
BLINKO_TOKEN = os.environ.get("BLINKO_TOKEN", "")

SINK_TIMEOUT = 10  # seconds per HTTP sink


# ── Redaction ───────────────────────────────────────────────────────

_REDACT_PATTERNS = [
    # API keys / tokens (highest specificity first)
    (re.compile(r"sk_live_[A-Za-z0-9]{20,}"), "<redacted-stripe>"),
    (re.compile(r"sk_test_[A-Za-z0-9]{20,}"), "<redacted-stripe>"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "<redacted-aws>"),
    (re.compile(r"sbp_[A-Za-z0-9]{20,}"), "<redacted-supabase>"),
    (re.compile(r"xox[bpoa]-[A-Za-z0-9\-]{20,}"), "<redacted-slack>"),
    (re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._\-]{16,})"), r"\1<redacted-token>"),
    (re.compile(r"(?i)(api[_-]?key[\"'\s:=]+)([A-Za-z0-9._\-]{16,})"), r"\1<redacted-key>"),
    (re.compile(r"(?i)(token[\"'\s:=]+)([A-Za-z0-9._\-]{20,})"), r"\1<redacted-token>"),
    # PII
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "<redacted-email>"),
    (re.compile(r"\+?\d[\d\s().\-]{9,}\d"), "<redacted-phone>"),
]


def _redact_str(s: str) -> tuple[str, int]:
    count = 0
    for pat, repl in _REDACT_PATTERNS:
        new, n = pat.subn(repl, s)
        count += n
        s = new
    return s, count


def _redact(value: Any) -> tuple[Any, int]:
    """Recursively redact strings inside dict/list structures."""
    if isinstance(value, str):
        return _redact_str(value)
    if isinstance(value, dict):
        total = 0
        out = {}
        for k, v in value.items():
            nv, n = _redact(v)
            out[k] = nv
            total += n
        return out, total
    if isinstance(value, list):
        total = 0
        out = []
        for item in value:
            ni, n = _redact(item)
            out.append(ni)
            total += n
        return out, total
    return value, 0


# ── IO helpers ──────────────────────────────────────────────────────

_IO_LOCK = threading.Lock()


def _append_jsonl(path: Path, obj: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with _IO_LOCK:
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
    except Exception as exc:  # pragma: no cover
        # Last resort: never raise from logger
        sys.stderr.write(f"[hive_logger] jsonl write failed: {exc}\n")


def _record_error(stage: str, exc: Exception, context: dict | None = None) -> None:
    _append_jsonl(
        ERRORS_FILE,
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "error": repr(exc)[:500],
            "context": context or {},
        },
    )


def _post_json(url: str, payload: dict, headers: dict, timeout: int = SINK_TIMEOUT) -> dict:
    body = json.dumps(payload, default=str).encode("utf-8")
    req = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {"ok": True}
    except (HTTPError, URLError, TimeoutError) as e:
        raise
    except Exception as e:  # pragma: no cover
        raise


# ── Sinks ───────────────────────────────────────────────────────────

def _sink_django(canonical: dict) -> bool:
    if not DASHBOARD_URL:
        return False
    headers = {"Content-Type": "application/json"}
    if DASHBOARD_TOKEN:
        headers["X-Hive-Token"] = DASHBOARD_TOKEN
    url = DASHBOARD_URL.rstrip("/") + "/api/logger/ingest/"
    try:
        _post_json(url, canonical, headers)
        return True
    except Exception as exc:
        _record_error("sink_django", exc, {"url": url, "session_id": canonical.get("session_id")})
        return False


def _sink_blinko(canonical: dict) -> bool:
    if not BLINKO_URL:
        return False
    agent = canonical.get("agent", "unknown")
    task = canonical.get("task", "run")
    status = canonical.get("status", "done")
    summary = canonical.get("summary") or "(no summary)"
    artifacts = canonical.get("artifacts") or []
    tags = canonical.get("tags") or ["#hive/session"]

    art_lines = []
    for a in artifacts:
        kind = a.get("kind", "file")
        title = a.get("title") or a.get("url") or a.get("path") or "artifact"
        link = a.get("url") or a.get("path") or ""
        if link:
            art_lines.append(f"- **{kind}**: [{title}]({link})")
        else:
            art_lines.append(f"- **{kind}**: {title}")

    body = (
        f"{' '.join(tags)}\n\n"
        f"# [{agent}] {task} -- {status}\n\n"
        f"**Session**: {canonical.get('session_id','')}\n"
        f"**When**: {canonical.get('finished_at','')}\n"
        f"**Duration**: {canonical.get('duration_seconds','?')}s\n\n"
        f"## Summary\n\n{summary}\n"
    )
    if art_lines:
        body += "\n## Artifacts\n\n" + "\n".join(art_lines) + "\n"

    headers = {"Content-Type": "application/json"}
    if BLINKO_TOKEN:
        headers["Authorization"] = f"Bearer {BLINKO_TOKEN}"
    url = BLINKO_URL.rstrip("/") + "/api/v1/note/upsert"
    try:
        _post_json(url, {"content": body, "type": 1}, headers)
        return True
    except Exception as exc:
        _record_error("sink_blinko", exc, {"url": url, "session_id": canonical.get("session_id")})
        return False


# ── Per-process current run registry ────────────────────────────────

_CURRENT_RUNS: list["Run"] = []
_CURRENT_LOCK = threading.Lock()


def current_run() -> "Run | None":
    """Return the most recently-started, unfinished Run, or None.

    Used by hive_3format.publish() to auto-register artifacts without the
    caller threading the Run through every function.
    """
    with _CURRENT_LOCK:
        for r in reversed(_CURRENT_RUNS):
            if not r._finished:
                return r
    return None


# ── Run object ──────────────────────────────────────────────────────

@dataclass
class Run:
    agent: str
    task: str
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    mode: str = "full"
    inputs: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    _events: list[dict] = field(default_factory=list)
    _artifacts: list[dict] = field(default_factory=list)
    _started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    _started_mono: float = field(default_factory=time.monotonic)
    _finished: bool = False
    _redactions: int = 0

    def event(self, type_: str, payload: dict | None = None) -> None:
        """Log one structured event. Written to jsonl immediately, non-blocking."""
        try:
            red_payload, n = _redact(payload or {})
            self._redactions += n
            ev = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "session_id": self.session_id,
                "agent": self.agent,
                "type": type_,
                "payload": red_payload,
            }
            self._events.append(ev)
            _append_jsonl(EVENTS_FILE, ev)
        except Exception as exc:
            _record_error("event", exc, {"type": type_, "session_id": self.session_id})

    def artifact(
        self,
        kind: str,
        url: str = "",
        path: str = "",
        title: str = "",
        tags: Iterable[str] | None = None,
    ) -> None:
        """Register an artifact this run created (gdoc, html, file, slack_post, blinko_note)."""
        try:
            art = {
                "kind": kind,
                "title": (title or "")[:255],
                "url": (url or "")[:1024],
                "path": (path or "")[:1024],
                "tags": _validate_tags(list(tags or [])),
            }
            self._artifacts.append(art)
            _append_jsonl(
                EVENTS_FILE,
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "session_id": self.session_id,
                    "agent": self.agent,
                    "type": "artifact.registered",
                    "payload": art,
                },
            )
        except Exception as exc:
            _record_error("artifact", exc, {"kind": kind, "session_id": self.session_id})

    def finish(self, status: str = "done", summary: str = "") -> dict:
        """End the run. Emits the canonical line to all three sinks.

        Always returns the canonical dict. Never raises.
        """
        if self._finished:
            return {"session_id": self.session_id, "already_finished": True}
        self._finished = True
        try:
            finished_at = datetime.now(timezone.utc).isoformat()
            duration = round(time.monotonic() - self._started_mono, 2)

            red_summary, ns = _redact_str(summary or "")
            red_inputs, ni = _redact(self.inputs)
            self._redactions += ns + ni

            canonical = {
                "session_id": self.session_id,
                "agent": self.agent,
                "task": self.task,
                "status": status if status in {"running", "done", "partial", "failed"} else "done",
                "mode": self.mode,
                "started_at": self._started_at,
                "finished_at": finished_at,
                "duration_seconds": duration,
                "summary": (red_summary or "")[:500],
                "routed_to": ["claude"],
                "events": self._events[-50:],  # cap payload size
                "artifacts": self._artifacts,
                "tags": _validate_tags(self.tags or ["#hive/session"]),
                "inputs_redacted": red_inputs,
                "redactions_applied": self._redactions,
            }

            # Local jsonl: always first, always written
            _append_jsonl(
                EVENTS_FILE,
                {**canonical, "type": "run.finish", "ts": finished_at},
            )

            # Remote sinks: graceful failure each
            _sink_django(canonical)
            _sink_blinko(canonical)
            return canonical
        except Exception as exc:
            _record_error("finish", exc, {"session_id": self.session_id})
            return {"session_id": self.session_id, "error": repr(exc)[:500]}


def start(
    agent: str,
    task: str,
    inputs: dict | None = None,
    tags: Iterable[str] | None = None,
    mode: str = "full",
) -> Run:
    """Begin a run. Returns a Run object the caller threads through their work."""
    run = Run(
        agent=str(agent)[:64],
        task=str(task)[:255],
        inputs=dict(inputs or {}),
        tags=_validate_tags(list(tags or [])),
        mode=mode,
    )
    _append_jsonl(
        EVENTS_FILE,
        {
            "ts": run._started_at,
            "session_id": run.session_id,
            "agent": run.agent,
            "task": run.task,
            "type": "run.start",
            "payload": {"inputs": _redact(run.inputs)[0]},
        },
    )
    with _CURRENT_LOCK:
        _CURRENT_RUNS.append(run)
    return run


# ── Selftest ────────────────────────────────────────────────────────

def _selftest() -> int:
    print("[hive_logger] selftest: starting")
    run = start(
        agent="smoke-test",
        task="hive-logger-selftest",
        inputs={"sample_email": "alice@example.com", "sample_token": "Bearer abc1234567890abcdef"},
        tags=["#hive/session"],
    )
    print(f"[hive_logger] session_id = {run.session_id}")
    run.event("selftest.started", {"n": 1})
    run.artifact("gdoc", url="https://docs.google.com/document/d/SMOKE_TEST_DOC", title="Smoke Test Doc")
    run.artifact("html", url=f"{DASHBOARD_URL}/reports/smoke.html", title="Smoke Test HTML")
    result = run.finish("done", "Selftest OK. Contact alice@example.com if broken.")
    print(f"[hive_logger] finished. redactions_applied={result.get('redactions_applied', 0)}")
    print(f"[hive_logger] jsonl tail: {EVENTS_FILE}")
    if ERRORS_FILE.exists():
        print(f"[hive_logger] errors log: {ERRORS_FILE}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
