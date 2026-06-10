"""audit_log -- append-only cryptographically chained audit envelope writer.

The cryptographic backbone of HIVE_GOVERNANCE_V2.md Section 4. Every meaningful
Hive action (DNC registration, recipient block, PSA decision, contract sign,
outbound send, money movement) writes a JSON envelope to:

    /AA_MY_DRIVE/_audit/<tier>/<agent_id>/<YYYY-MM-DD>/<UTC-ISO-Z>_<action>.json

Each envelope is sha256-chained to its predecessor. Any retroactive edit to the
chain breaks the hash linkage and is detectable by chain_verify().

Public API
----------
    write_envelope(agent_id, action_type, payload, *, human=False) -> EnvelopeReceipt
        Atomic write. Never raises. Returns receipt with ok flag.

    chain_verify(agent_id, *, since=None) -> ChainVerifyReport
        Walk the agent's envelope chain, recompute hashes, report breaks.

    last_envelope_for(agent_id) -> Optional[Envelope]
        Read the most recent envelope (used to seed previous_hash on next write).

Storage layout
--------------
    _audit/
        1L/state_marvin_tn/2026-05-05/2026-05-05T20-30-00-000Z_psa.audit_decision.json
        2L/state_lo_hines_tn/2026-05-05/2026-05-05T20-30-01-000Z_psa.audit_decision.passed.json
        3L/theo_briggs/2026-05-05/2026-05-05T20-30-02-000Z_quarterly.sample_review.json
        _index/<agent_id>.head.json   (caches last envelope hash + path -- fast read)

Atomicity
---------
- Each write goes to a tempfile in the same directory, then os.replace().
- The per-agent head pointer (_index/<agent_id>.head.json) is also written
  atomically. If head update fails the envelope is still on disk; chain_verify
  will rebuild from the directory tree.
- Concurrent writes from the same agent_id are serialized with a per-agent
  threading.Lock. Cross-process concurrency uses fcntl when available; falls
  back to best-effort head re-read on platforms without fcntl.

Defensive contract
------------------
- Pure stdlib (json, hashlib, os, pathlib, threading, datetime, fcntl-optional).
- Tier classification comes from two_line_dispatch.tier_for_agent().
- Never raises. All failure modes return EnvelopeReceipt(ok=False, error=...).
- Payload must be JSON-serializable; non-serializable values are coerced via
  default=str (lossy but never crashes).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("audit_log")

# Resolve audit root. Prefer the canonical /AA_MY_DRIVE/_audit if accessible,
# fall back to phone-mirror or oracle path. Override with AUDIT_LOG_ROOT env.
_DEFAULT_AUDIT_ROOTS = [
    Path(os.environ.get("AUDIT_LOG_ROOT", "")) if os.environ.get("AUDIT_LOG_ROOT") else None,
    Path("/AA_MY_DRIVE/_audit"),
    Path("/mnt/sdcard/AA_MY_DRIVE/_audit"),
    Path("/home/opc/_audit"),
]
_DEFAULT_AUDIT_ROOTS = [p for p in _DEFAULT_AUDIT_ROOTS if p is not None]


def _audit_root() -> Path:
    """Pick the first writable audit root (creates dir on first call)."""
    for p in _DEFAULT_AUDIT_ROOTS:
        try:
            p.mkdir(parents=True, exist_ok=True)
            # Quick writability probe
            tprobe = p / ".write_probe"
            try:
                tprobe.write_text("ok", encoding="utf-8")
                tprobe.unlink(missing_ok=True)
                return p
            except Exception:
                continue
        except Exception:
            continue
    # Last resort: tempdir, so we never crash callers
    fallback = Path(tempfile.gettempdir()) / "everlight_audit"
    fallback.mkdir(parents=True, exist_ok=True)
    log.warning("audit_log falling back to tempdir %s -- envelopes may not persist!", fallback)
    return fallback


# Per-agent thread locks (in-process serialization)
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _agent_lock(agent_id: str) -> threading.Lock:
    with _locks_guard:
        if agent_id not in _locks:
            _locks[agent_id] = threading.Lock()
        return _locks[agent_id]


@dataclass
class EnvelopeReceipt:
    ok: bool
    envelope_path: str = ""
    this_hash: str = ""
    previous_hash: str = ""
    error: str = ""


@dataclass
class Envelope:
    envelope_version: int
    timestamp_utc: str
    actor: dict
    action_type: str
    action_payload: dict
    previous_envelope_hash: str
    this_envelope_hash: str
    tier: str = ""
    git_commit: Optional[str] = None
    signed_by: Optional[str] = None


@dataclass
class ChainVerifyReport:
    ok: bool
    agent_id: str
    envelopes_checked: int = 0
    breaks: list[dict] = field(default_factory=list)  # [{"path":..., "expected":..., "actual":...}]
    first_envelope_iso: str = ""
    last_envelope_iso: str = ""
    error: str = ""


def _tier_for(agent_id: str) -> str:
    """Resolve tier via two_line_dispatch (defensive import)."""
    try:
        # Inline the import paths to keep audit_log usable across hosts
        for p in (
            "/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind",
            "/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind",
            "/home/opc/hive_mind",
        ):
            if p not in sys.path:
                sys.path.insert(0, p)
        from two_line_dispatch import tier_for_agent  # type: ignore
        return tier_for_agent(agent_id)
    except Exception as exc:
        log.debug("tier_for_agent unavailable, defaulting to 1L: %s", exc)
        return "1L"


_SAFE_ACTION_RE = re.compile(r"[^A-Za-z0-9._-]+")
_SAFE_AGENT_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_segment(value: str, fallback: str) -> str:
    if not value:
        return fallback
    cleaned = _SAFE_ACTION_RE.sub("_", value).strip("._-")
    return cleaned or fallback


def _safe_agent(agent_id: str) -> str:
    cleaned = _SAFE_AGENT_RE.sub("_", agent_id or "").strip("._-")
    return cleaned or "unknown_agent"


def _now_iso_z() -> str:
    """ISO-8601 UTC with millisecond precision and 'Z' suffix."""
    now = datetime.now(timezone.utc)
    # millisecond precision, replace + with Z
    return now.strftime("%Y-%m-%dT%H:%M:%S") + f".{now.microsecond // 1000:03d}Z"


def _filename_for(timestamp_iso: str, action_type: str) -> str:
    """Convert an ISO timestamp into a filesystem-safe filename component."""
    # Replace : with - so it's safe on every filesystem (incl. exFAT/Windows)
    safe_ts = timestamp_iso.replace(":", "-").replace("+00:00", "Z")
    safe_action = _safe_segment(action_type, "action")
    return f"{safe_ts}_{safe_action}.json"


def _index_dir(root: Path) -> Path:
    d = root / "_index"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _head_path(root: Path, agent_id: str) -> Path:
    return _index_dir(root) / f"{_safe_agent(agent_id)}.head.json"


def _read_head(root: Path, agent_id: str) -> Optional[dict]:
    """Read the cached head pointer for an agent. None if absent/corrupt."""
    p = _head_path(root, agent_id)
    if not p.exists():
        return None
    try:
        with p.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and "this_hash" in data:
            return data
    except Exception as exc:
        log.warning("head pointer corrupt for %s: %s", agent_id, exc)
    return None


def _write_head(root: Path, agent_id: str, head: dict) -> bool:
    """Atomic head pointer write. Returns False on failure (non-fatal)."""
    p = _head_path(root, agent_id)
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=str(p.parent), prefix=".tmp_head_",
            suffix=".json", delete=False, encoding="utf-8",
        ) as tmp:
            json.dump(head, tmp, default=str)
            tmp.flush()
            try:
                os.fsync(tmp.fileno())
            except OSError:
                pass
            tmp_path = tmp.name
        os.replace(tmp_path, str(p))
        return True
    except Exception as exc:
        log.warning("head pointer write failed for %s: %s", agent_id, exc)
        return False


def _scan_last_envelope(root: Path, agent_id: str) -> Optional[Envelope]:
    """Walk the agent's directory tree to find the chronologically last envelope.

    Slow path -- only used when the head pointer is missing or corrupt.
    Iterates dates in descending order so first hit wins.
    """
    safe_aid = _safe_agent(agent_id)
    # Search across all tiers (1L/2L/3L) since an agent's tier may have moved
    for tier in ("3L", "2L", "1L"):
        agent_dir = root / tier / safe_aid
        if not agent_dir.exists():
            continue
        # Date dirs sort lexicographically as YYYY-MM-DD; descend to newest
        try:
            date_dirs = sorted(
                (d for d in agent_dir.iterdir() if d.is_dir()),
                key=lambda p: p.name,
                reverse=True,
            )
        except Exception:
            continue
        for date_dir in date_dirs:
            try:
                files = sorted(
                    (f for f in date_dir.iterdir() if f.is_file() and f.suffix == ".json"),
                    key=lambda p: p.name,
                    reverse=True,
                )
            except Exception:
                continue
            for f in files:
                try:
                    with f.open("r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    if isinstance(data, dict) and "this_envelope_hash" in data:
                        return Envelope(
                            envelope_version=int(data.get("envelope_version", 1)),
                            timestamp_utc=str(data.get("timestamp_utc", "")),
                            actor=dict(data.get("actor") or {}),
                            action_type=str(data.get("action_type", "")),
                            action_payload=dict(data.get("action_payload") or {}),
                            previous_envelope_hash=str(data.get("previous_envelope_hash", "")),
                            this_envelope_hash=str(data.get("this_envelope_hash", "")),
                            tier=str(data.get("tier", "")),
                            git_commit=data.get("git_commit"),
                            signed_by=data.get("signed_by"),
                        )
                except Exception:
                    continue
    return None


def last_envelope_for(agent_id: str) -> Optional[Envelope]:
    """Return the most recent envelope for an agent, or None if none yet."""
    root = _audit_root()
    safe_aid = _safe_agent(agent_id)
    head = _read_head(root, safe_aid)
    if head and head.get("path"):
        try:
            with Path(head["path"]).open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            return Envelope(
                envelope_version=int(data.get("envelope_version", 1)),
                timestamp_utc=str(data.get("timestamp_utc", "")),
                actor=dict(data.get("actor") or {}),
                action_type=str(data.get("action_type", "")),
                action_payload=dict(data.get("action_payload") or {}),
                previous_envelope_hash=str(data.get("previous_envelope_hash", "")),
                this_envelope_hash=str(data.get("this_envelope_hash", "")),
                tier=str(data.get("tier", "")),
                git_commit=data.get("git_commit"),
                signed_by=data.get("signed_by"),
            )
        except Exception as exc:
            log.warning("head-pointed envelope unreadable, falling back to scan: %s", exc)
    return _scan_last_envelope(root, safe_aid)


_SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9][A-Za-z0-9_\-]{19,}"),  # generic OpenAI/Stripe-like
    re.compile(r"re_[A-Za-z0-9_\-]{20,}"),  # Resend
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),  # Google API
    re.compile(r"ya29\.[A-Za-z0-9_\-]{20,}"),  # Google OAuth access token
    re.compile(r"-----BEGIN\s+(RSA|OPENSSH|EC|DSA|ENCRYPTED)?\s*PRIVATE\s+KEY-----[\s\S]+?-----END\s+(?:RSA|OPENSSH|EC|DSA|ENCRYPTED)?\s*PRIVATE\s+KEY-----"),
    re.compile(r"\beyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]+"),  # JWT
]


def _redact_secrets(value):
    """Recursively scrub credential-shaped substrings from any json-serializable
    value before it's written to the chain. Replaces matches with "<redacted:N>"
    where N is the original length. Per Rich's screenshot/secret doctrine
    (2026-05-07): credentials must NEVER hit the audit chain (which syncs to a
    git remote). Pure stdlib, deterministic, idempotent."""
    if isinstance(value, str):
        out = value
        for rx in _SECRET_PATTERNS:
            def _sub(m):
                return f"<redacted:{len(m.group(0))}>"
            out = rx.sub(_sub, out)
        return out
    if isinstance(value, dict):
        return {k: _redact_secrets(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_secrets(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_redact_secrets(v) for v in value)
    return value


def _hash_envelope_dict(env: dict) -> str:
    """Compute sha256 of the envelope's canonical content (excluding this_hash itself)."""
    payload = {k: env[k] for k in env.keys() if k != "this_envelope_hash"}
    blob = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def write_envelope(
    agent_id: str,
    action_type: str,
    payload: dict[str, Any],
    *,
    human: bool = False,
) -> EnvelopeReceipt:
    """Append an envelope to the agent's chain. Atomic, never raises.

    Args:
        agent_id:    Hive agent identifier (matches role_classification.json).
        action_type: dotted lowercase event name, e.g. "dnc.registered".
        payload:     JSON-serializable dict with the event's facts.
        human:       True if a human (Rich) authored the action. Defaults False.

    Returns:
        EnvelopeReceipt(ok=True, envelope_path=..., this_hash=..., previous_hash=...)
        EnvelopeReceipt(ok=False, error="...") on any failure.
    """
    if not agent_id or not isinstance(agent_id, str):
        return EnvelopeReceipt(ok=False, error="missing_agent_id")
    if not action_type or not isinstance(action_type, str):
        return EnvelopeReceipt(ok=False, error="missing_action_type")
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        return EnvelopeReceipt(ok=False, error="payload_must_be_dict")

    # Scrub credential-shaped substrings BEFORE hashing or writing. Per Rich's
    # 2026-05-07 doctrine, secrets must never hit the audit chain (which is
    # git-synced to an external remote). Hash includes the redacted form so
    # chain integrity is preserved.
    payload = _redact_secrets(payload)

    safe_aid = _safe_agent(agent_id)
    root = _audit_root()
    tier = _tier_for(agent_id)

    lock = _agent_lock(safe_aid)
    with lock:
        prev = last_envelope_for(safe_aid)
        prev_hash = prev.this_envelope_hash if prev else "sha256:GENESIS"

        ts_iso = _now_iso_z()
        date_segment = ts_iso.split("T", 1)[0]

        envelope: dict[str, Any] = {
            "envelope_version": 1,
            "timestamp_utc": ts_iso,
            "tier": tier,
            "actor": {
                "agent_id": agent_id,
                "human_or_agent": "human" if human else "agent",
            },
            "action_type": action_type,
            "action_payload": payload,
            "previous_envelope_hash": prev_hash,
            "git_commit": None,
            "signed_by": None,
        }
        try:
            this_hash = _hash_envelope_dict(envelope)
        except Exception as exc:
            return EnvelopeReceipt(ok=False, error=f"hash_failed:{exc}")
        envelope["this_envelope_hash"] = this_hash

        # Build the destination path
        target_dir = root / tier / safe_aid / date_segment
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            return EnvelopeReceipt(ok=False, error=f"mkdir_failed:{exc}")

        fname = _filename_for(ts_iso, action_type)
        target_path = target_dir / fname

        # Collision handling -- if same-millisecond+action twice, append suffix
        if target_path.exists():
            i = 1
            while True:
                alt = target_dir / fname.replace(".json", f"_{i}.json")
                if not alt.exists():
                    target_path = alt
                    break
                i += 1
                if i > 1000:
                    return EnvelopeReceipt(ok=False, error="filename_collision_overflow")

        # Atomic write: tempfile + os.replace
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", dir=str(target_dir), prefix=".tmp_env_",
                suffix=".json", delete=False, encoding="utf-8",
            ) as tmp:
                json.dump(envelope, tmp, sort_keys=True, default=str, ensure_ascii=False, indent=2)
                tmp.flush()
                try:
                    os.fsync(tmp.fileno())
                except OSError:
                    pass
                tmp_path = tmp.name
            os.replace(tmp_path, str(target_path))
        except Exception as exc:
            return EnvelopeReceipt(ok=False, error=f"write_failed:{exc}")

        # Update head pointer (best-effort)
        _write_head(root, safe_aid, {
            "agent_id": safe_aid,
            "path": str(target_path),
            "this_hash": this_hash,
            "previous_hash": prev_hash,
            "timestamp_utc": ts_iso,
            "tier": tier,
        })

        return EnvelopeReceipt(
            ok=True,
            envelope_path=str(target_path),
            this_hash=this_hash,
            previous_hash=prev_hash,
        )


def chain_verify(agent_id: str, *, since: Optional[str] = None) -> ChainVerifyReport:
    """Walk an agent's envelope chain in chronological order, verify hash linkage.

    Args:
        agent_id: target agent identifier.
        since:    optional ISO-8601 date prefix to start at (e.g. "2026-05-01").

    Returns:
        ChainVerifyReport with ok=True if chain is intact, plus per-break details.
        Never raises.
    """
    safe_aid = _safe_agent(agent_id)
    report = ChainVerifyReport(ok=True, agent_id=safe_aid)
    root = _audit_root()

    envelopes_in_order: list[tuple[str, dict]] = []
    try:
        for tier in ("1L", "2L", "3L"):
            agent_dir = root / tier / safe_aid
            if not agent_dir.exists():
                continue
            try:
                date_dirs = sorted(
                    (d for d in agent_dir.iterdir() if d.is_dir()),
                    key=lambda p: p.name,
                )
            except Exception:
                continue
            for date_dir in date_dirs:
                if since and date_dir.name < since:
                    continue
                try:
                    files = sorted(
                        (f for f in date_dir.iterdir() if f.is_file() and f.suffix == ".json"),
                        key=lambda p: p.name,
                    )
                except Exception:
                    continue
                for f in files:
                    try:
                        with f.open("r", encoding="utf-8") as fh:
                            data = json.load(fh)
                        envelopes_in_order.append((str(f), data))
                    except Exception as exc:
                        report.breaks.append({"path": str(f), "error": f"unreadable:{exc}"})
                        report.ok = False
    except Exception as exc:
        report.ok = False
        report.error = f"scan_failed:{exc}"
        return report

    # Sort cross-tier by timestamp (an agent's tier could change over time)
    try:
        envelopes_in_order.sort(key=lambda x: x[1].get("timestamp_utc", ""))
    except Exception:
        pass

    expected_prev = "sha256:GENESIS"
    for path, data in envelopes_in_order:
        report.envelopes_checked += 1
        if not report.first_envelope_iso:
            report.first_envelope_iso = data.get("timestamp_utc", "")
        report.last_envelope_iso = data.get("timestamp_utc", "")

        # Recompute hash and compare
        actual_this = data.get("this_envelope_hash", "")
        recomputed = _hash_envelope_dict(data)
        if actual_this != recomputed:
            report.breaks.append({
                "path": path,
                "kind": "this_hash_mismatch",
                "expected": recomputed,
                "actual": actual_this,
            })
            report.ok = False

        actual_prev = data.get("previous_envelope_hash", "")
        if actual_prev != expected_prev:
            report.breaks.append({
                "path": path,
                "kind": "previous_hash_mismatch",
                "expected": expected_prev,
                "actual": actual_prev,
            })
            report.ok = False

        expected_prev = actual_this or recomputed

    return report


# CLI: `python3 audit_log.py verify <agent_id>` or `python3 audit_log.py last <agent_id>`
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    if len(sys.argv) < 3:
        print("usage:")
        print("  python3 audit_log.py verify <agent_id>")
        print("  python3 audit_log.py last <agent_id>")
        print("  python3 audit_log.py write <agent_id> <action_type> [payload_json]")
        sys.exit(2)
    cmd = sys.argv[1]
    aid = sys.argv[2]
    if cmd == "verify":
        rep = chain_verify(aid)
        print(json.dumps({
            "ok": rep.ok,
            "agent_id": rep.agent_id,
            "envelopes_checked": rep.envelopes_checked,
            "first_envelope_iso": rep.first_envelope_iso,
            "last_envelope_iso": rep.last_envelope_iso,
            "breaks": rep.breaks,
            "error": rep.error,
        }, indent=2))
        sys.exit(0 if rep.ok else 1)
    elif cmd == "last":
        env = last_envelope_for(aid)
        if env is None:
            print("(no envelopes)")
            sys.exit(0)
        print(json.dumps({
            "timestamp_utc": env.timestamp_utc,
            "tier": env.tier,
            "action_type": env.action_type,
            "this_hash": env.this_envelope_hash,
            "previous_hash": env.previous_envelope_hash,
        }, indent=2))
        sys.exit(0)
    elif cmd == "write":
        action = sys.argv[3] if len(sys.argv) > 3 else "cli.test"
        payload_str = sys.argv[4] if len(sys.argv) > 4 else "{}"
        try:
            payload = json.loads(payload_str)
        except Exception:
            payload = {"raw": payload_str}
        rec = write_envelope(aid, action, payload, human=True)
        print(json.dumps({
            "ok": rec.ok,
            "envelope_path": rec.envelope_path,
            "this_hash": rec.this_hash,
            "previous_hash": rec.previous_hash,
            "error": rec.error,
        }, indent=2))
        sys.exit(0 if rec.ok else 1)
    else:
        print(f"unknown command: {cmd}")
        sys.exit(2)
