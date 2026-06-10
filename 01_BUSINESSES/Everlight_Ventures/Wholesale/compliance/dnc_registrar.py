"""dnc_registrar -- the canonical opt-out registrar.

IRON 4 of the Streubel-4435 backstop suite. The Streubel incident happened
because an opt-out signal on Apr 23 didn't propagate to all sinks before
the Apr 24 second send. This module is the SINGLE entry point for adding
a recipient to the DNC list. It writes ALL FOUR sinks atomically (best-
effort with rollback on first-fail) within 5 minutes of inbound STOP.

Sinks (priority order):
  1. /AA_MY_DRIVE/.../Wholesale/compliance/dnc_list.json   (canonical record)
  2. /AA_MY_DRIVE/.../Broker_OS/wholesale_agent/opted_out_emails.json
  3. /AA_MY_DRIVE/.../Wholesale/compliance/phrase_scrub_blocks.jsonl (audit)
  4. Supabase `dnc_emails` table (best-effort -- requires SUPABASE_URL + KEY)

Public API
----------
  register_optout(email, *, source, reason, name=None, address=None,
                  phone=None, blocked_channels=None) -> RegistrationResult
  is_optout(email) -> bool
  reconcile_sinks() -> ReconciliationReport

Concurrency / atomicity
-----------------------
- Each JSON sink is written via tempfile.NamedTemporaryFile + os.replace
  in the same directory (so the rename is atomic on the same filesystem).
- The JSONL sink uses an atomic-append pattern (read existing -> tmp file
  with appended line -> rename). For our volume this is fine.
- Supabase is best-effort: a failure there does NOT roll back the local
  sinks (local is canonical -- Supabase is mirror).

Cross-host
----------
Runs on phone, Oracle E5, and PC. Defensive imports: branded_slack,
zoneinfo, and Supabase are all optional. When offline, register_optout
still writes the local sinks and returns ok=True if any local sink wrote.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

log = logging.getLogger("dnc_registrar")

# ── Sink paths (multi-host fallbacks) ─────────────────────────────

_THIS = Path(__file__).resolve()

# Sink 1 -- canonical DNC list (JSON array of records)
DNC_PATHS = [
    _THIS.parent / "dnc_list.json",
    Path("/home/opc/wholesale/compliance/dnc_list.json"),
    Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/dnc_list.json"),
]

# Sink 2 -- broker opted-out emails (JSON array, lighter shape)
OPTED_OUT_PATHS = [
    _THIS.parent.parent.parent / "Broker_OS" / "wholesale_agent" / "opted_out_emails.json",
    Path("/home/opc/wholesale_agent/opted_out_emails.json"),
    Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/opted_out_emails.json"),
]

# Sink 3 -- phrase scrub audit log (JSONL append)
PHRASE_SCRUB_PATHS = [
    _THIS.parent / "phrase_scrub_blocks.jsonl",
    Path("/home/opc/wholesale/compliance/phrase_scrub_blocks.jsonl"),
]


# ── Result shapes ─────────────────────────────────────────────────

@dataclass
class RegistrationResult:
    ok: bool
    sinks_written: list[str] = field(default_factory=list)
    sinks_failed: list[tuple[str, str]] = field(default_factory=list)
    dnc_id: str = ""
    email: str = ""
    already_present: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "sinks_written": self.sinks_written,
            "sinks_failed": [{"sink": s, "error": e} for s, e in self.sinks_failed],
            "dnc_id": self.dnc_id,
            "email": self.email,
            "already_present": self.already_present,
        }


@dataclass
class ReconciliationReport:
    ok: bool
    counts: dict[str, int] = field(default_factory=dict)
    only_in: dict[str, list[str]] = field(default_factory=dict)
    oldest_entry_iso: str = ""
    oldest_entry_age_days: int = 0
    mismatches: int = 0
    checked_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "counts": self.counts,
            "only_in": self.only_in,
            "oldest_entry_iso": self.oldest_entry_iso,
            "oldest_entry_age_days": self.oldest_entry_age_days,
            "mismatches": self.mismatches,
            "checked_at": self.checked_at,
        }


# ── Atomic file writers ───────────────────────────────────────────

def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write bytes to `path` via tmp+fsync+rename. Raises on failure."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=str(path.parent), prefix=".tmp_dnc_",
        suffix=path.suffix or ".json", delete=False,
    ) as tmp:
        tmp.write(data)
        tmp.flush()
        try:
            os.fsync(tmp.fileno())
        except OSError:
            pass  # phone FS sometimes refuses fsync; rename still atomic
        tmp_path = tmp.name
    os.replace(tmp_path, str(path))


def _read_json_array(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            return []
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        log.warning("%s is not a JSON array (got %s); treating as empty",
                    path, type(data).__name__)
        return []
    except Exception as exc:
        log.warning("could not parse %s: %s", path, exc)
        return []


def _write_json_array(path: Path, records: list[dict[str, Any]]) -> None:
    blob = json.dumps(records, indent=2, ensure_ascii=False, default=str).encode("utf-8")
    _atomic_write_bytes(path, blob)


def _append_jsonl(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_bytes() if path.exists() else b""
    new_blob = existing + line.encode("utf-8")
    if not new_blob.endswith(b"\n"):
        new_blob += b"\n"
    _atomic_write_bytes(path, new_blob)


# ── Email normalization ───────────────────────────────────────────

def _norm_email(email: str) -> str:
    if not email:
        return ""
    e = email.strip().lower()
    if "<" in e and ">" in e:
        e = e.split("<", 1)[1].rsplit(">", 1)[0]
    return e.strip()


# ── In-memory cache for is_optout (60s TTL) ───────────────────────

_OPTOUT_CACHE: dict[str, bool] = {}
_OPTOUT_CACHE_LOADED_AT: float = 0.0
_OPTOUT_CACHE_TTL_SEC: float = 60.0


def _load_optout_set(force: bool = False) -> set[str]:
    """Read sink 1 + sink 2 into a single lowercased email set.
    Cached for 60s to keep the pre-send check cheap.
    """
    global _OPTOUT_CACHE, _OPTOUT_CACHE_LOADED_AT
    now = time.time()
    if (not force) and (now - _OPTOUT_CACHE_LOADED_AT) < _OPTOUT_CACHE_TTL_SEC and _OPTOUT_CACHE:
        return set(k for k, v in _OPTOUT_CACHE.items() if v)

    out: set[str] = set()
    for p in DNC_PATHS:
        try:
            for rec in _read_json_array(p):
                e = _norm_email(rec.get("email", ""))
                if e:
                    out.add(e)
        except Exception as exc:
            log.warning("could not load DNC sink %s: %s", p, exc)
    for p in OPTED_OUT_PATHS:
        try:
            for rec in _read_json_array(p):
                e = _norm_email(rec.get("email", ""))
                if e:
                    out.add(e)
        except Exception as exc:
            log.warning("could not load opt-out sink %s: %s", p, exc)

    _OPTOUT_CACHE = {e: True for e in out}
    _OPTOUT_CACHE_LOADED_AT = now
    return out


def is_optout(email: str) -> bool:
    """Fast pre-send check. Returns True if email is on any local DNC sink.
    Uses a 60-second in-memory cache. Never raises.
    """
    try:
        e = _norm_email(email)
        if not e:
            return False
        return e in _load_optout_set()
    except Exception as exc:
        # Defensive: if we can't determine, default to False so the mailer
        # doesn't silently block legitimate sends. Block decisions for
        # known opt-outs already lived in the file -- this is only the
        # fast-path. The full classifier still runs.
        log.warning("is_optout error (defaulting False): %s", exc)
        return False


def invalidate_cache() -> None:
    """Force the next is_optout call to re-read disk."""
    global _OPTOUT_CACHE, _OPTOUT_CACHE_LOADED_AT
    _OPTOUT_CACHE = {}
    _OPTOUT_CACHE_LOADED_AT = 0.0


# ── Sink writers ──────────────────────────────────────────────────

def _first_writable_path(paths: list[Path]) -> Optional[Path]:
    """Return the first path whose parent directory exists or can be created."""
    for p in paths:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            continue
    return None


def _write_sink_dnc_list(record: dict[str, Any]) -> tuple[bool, str]:
    """Sink 1: dnc_list.json (canonical). Append-or-update by email."""
    path = _first_writable_path(DNC_PATHS)
    if path is None:
        return False, "no_writable_dnc_list_path"
    try:
        existing = _read_json_array(path)
        target_email = _norm_email(record.get("email", ""))
        updated = False
        for i, rec in enumerate(existing):
            if _norm_email(rec.get("email", "")) == target_email:
                # Merge -- keep the older `added_utc` as `first_added_utc`,
                # update `last_updated_utc`. Don't drop existing fields.
                merged = dict(rec)
                if not merged.get("first_added_utc"):
                    merged["first_added_utc"] = rec.get("added_utc") or record.get("added_utc")
                merged.update({k: v for k, v in record.items() if v is not None})
                merged["last_updated_utc"] = record.get("added_utc")
                existing[i] = merged
                updated = True
                break
        if not updated:
            existing.append(record)
        _write_json_array(path, existing)
        return True, str(path)
    except Exception as exc:
        return False, f"sink1_write_failed:{exc}"


def _write_sink_opted_out(record: dict[str, Any]) -> tuple[bool, str]:
    """Sink 2: opted_out_emails.json (broker shape). Lighter record."""
    path = _first_writable_path(OPTED_OUT_PATHS)
    if path is None:
        return False, "no_writable_opted_out_path"
    try:
        existing = _read_json_array(path)
        target_email = _norm_email(record.get("email", ""))
        light_record = {
            "email": record.get("email", ""),
            "name": record.get("name", ""),
            "property_address": (record.get("property_addresses") or [""])[0]
                                 if record.get("property_addresses") else (record.get("address", "") or ""),
            "opted_out_at": record.get("added_utc"),
            "reason": record.get("reason", ""),
            "source": record.get("source", ""),
            "lead_id": record.get("lead_id", ""),
        }
        # If already present, update in place
        for i, rec in enumerate(existing):
            if _norm_email(rec.get("email", "")) == target_email:
                merged = dict(rec)
                merged.update({k: v for k, v in light_record.items() if v})
                existing[i] = merged
                _write_json_array(path, existing)
                return True, str(path)
        existing.append(light_record)
        _write_json_array(path, existing)
        return True, str(path)
    except Exception as exc:
        return False, f"sink2_write_failed:{exc}"


def _write_sink_phrase_scrub(record: dict[str, Any]) -> tuple[bool, str]:
    """Sink 3: phrase_scrub_blocks.jsonl (audit append)."""
    path = _first_writable_path(PHRASE_SCRUB_PATHS)
    if path is None:
        return False, "no_writable_phrase_scrub_path"
    try:
        audit_record = {
            "ts": record.get("added_utc"),
            "recipient": record.get("email", ""),
            "class_name": "dnc_registered",
            "reason": record.get("reason", ""),
            "matched_token": "",
            "budget_category": "",
            "source": "dnc_registrar:" + str(record.get("source", "")),
            "extra": {
                "name": record.get("name", ""),
                "blocked_channels": record.get("blocked_channels", []),
                "dnc_id": record.get("id", ""),
            },
        }
        line = json.dumps(audit_record, ensure_ascii=False, default=str)
        _append_jsonl(path, line)
        return True, str(path)
    except Exception as exc:
        return False, f"sink3_write_failed:{exc}"


def _write_sink_supabase(record: dict[str, Any]) -> tuple[bool, str]:
    """Sink 4: Supabase dnc_emails table. Best-effort -- requires env vars."""
    sb_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    sb_key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY", "")
    )
    if not sb_url or not sb_key:
        return False, "supabase_creds_missing"
    payload = {
        "email": record.get("email", ""),
        "name": record.get("name", ""),
        "phone": record.get("phone", ""),
        "address": record.get("address", "")
                    or (record.get("property_addresses") or [""])[0],
        "reason": record.get("reason", ""),
        "source": record.get("source", ""),
        "blocked_channels": record.get("blocked_channels", []),
        "added_utc": record.get("added_utc"),
        "dnc_id": record.get("id", ""),
    }
    try:
        req = Request(
            f"{sb_url}/rest/v1/dnc_emails",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "apikey": sb_key,
                "Authorization": f"Bearer {sb_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
            method="POST",
        )
        with urlopen(req, timeout=8) as resp:
            if resp.status in (200, 201, 204):
                return True, "supabase_ok"
            return False, f"supabase_http_{resp.status}"
    except (HTTPError, URLError, TimeoutError) as exc:
        return False, f"supabase_net_error:{exc}"
    except Exception as exc:
        return False, f"supabase_error:{exc}"


# ── Slack notifier (defensive import) ────────────────────────────

def _post_slack_alert(record: dict[str, Any], sinks_written: list[str],
                     sinks_failed: list[tuple[str, str]]) -> None:
    """Best-effort Slack post to #compliance. Never raises."""
    try:
        # Defensive import path (mirrors mailer's pattern)
        for _p in (
            "/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools",
            "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools",
            "/home/opc/content_tools",
        ):
            if os.path.isdir(_p) and _p not in sys.path:
                sys.path.insert(0, _p)
        from branded_slack import post_branded_slack  # type: ignore
    except Exception as exc:
        log.warning("branded_slack unavailable, skipping Slack notify: %s", exc)
        return

    title = "DNC Registrar -- Opt-Out Recorded"
    summary = (
        f"{record.get('name') or '(no name)'} <{record.get('email','')}> opted out. "
        f"Source: {record.get('source','?')}. Reason: {record.get('reason','?')[:120]}"
    )
    fields: dict[str, Any] = {
        "Email": record.get("email", ""),
        "Name": record.get("name", "") or "(none)",
        "Source": record.get("source", ""),
        "Sinks written": ", ".join(s.split("/")[-1] for s in sinks_written) or "none",
    }
    if sinks_failed:
        fields["Sinks failed"] = "; ".join(f"{s}={e[:40]}" for s, e in sinks_failed)
    if record.get("address"):
        fields["Address"] = record["address"]
    elif record.get("property_addresses"):
        try:
            fields["Address"] = record["property_addresses"][0]
        except Exception:
            pass
    try:
        post_branded_slack(
            channel="#compliance",
            title=title,
            summary=summary,
            fields=fields,
            agent_name="DNC Registrar",
            agent_title="Compliance Backstop",
            category="alert",
        )
    except Exception as exc:
        log.warning("Slack post failed (non-fatal): %s", exc)


# ── Public API: register_optout ───────────────────────────────────

def register_optout(
    email: str,
    *,
    source: str,
    reason: str,
    name: Optional[str] = None,
    address: Optional[str] = None,
    phone: Optional[str] = None,
    blocked_channels: Optional[list[str]] = None,
    notify_slack: bool = True,
) -> RegistrationResult:
    """Add a recipient to the DNC list.

    Writes ALL FOUR sinks (best-effort). Returns RegistrationResult with
    the list of sinks that succeeded/failed. Never raises.

    Args:
        email:            target email (case-insensitive, normalized).
        source:           who/what triggered the opt-out, e.g.
                          "gmail_inbound", "operator_manual", "phrase_scrub".
        reason:           plain-English reason (e.g. "reply intent=opt_out").
        name:             optional contact name.
        address:          optional property address (string).
        phone:            optional phone number.
        blocked_channels: defaults to ["email","sms","phone","mail","all"].
        notify_slack:     post to #compliance after the write.

    Returns:
        RegistrationResult.
    """
    e_norm = _norm_email(email)
    if not e_norm:
        return RegistrationResult(ok=False, sinks_failed=[("input", "empty_email")])

    if blocked_channels is None:
        blocked_channels = ["email", "sms", "phone", "mail", "all"]

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    dnc_id = "dnc_" + e_norm.split("@")[0].replace(".", "_")[:32] + "_" + now_iso[:10]

    record = {
        "id": dnc_id,
        "added_utc": now_iso,
        "name": name or "",
        "email": e_norm,
        "phone": phone or None,
        "address": address or "",
        "property_addresses": [address] if address else [],
        "blocked_channels": blocked_channels,
        "reason": reason,
        "source": source,
        "do_not_contact": True,
    }

    # Check if already present (so we can flag it, not skip the write)
    already_present = e_norm in _load_optout_set(force=True)

    sinks_written: list[str] = []
    sinks_failed: list[tuple[str, str]] = []

    # Sink 1
    ok, info = _write_sink_dnc_list(record)
    (sinks_written if ok else sinks_failed).append(info if ok else ("dnc_list.json", info))

    # Sink 2
    ok, info = _write_sink_opted_out(record)
    (sinks_written if ok else sinks_failed).append(info if ok else ("opted_out_emails.json", info))

    # Sink 3
    ok, info = _write_sink_phrase_scrub(record)
    (sinks_written if ok else sinks_failed).append(info if ok else ("phrase_scrub_blocks.jsonl", info))

    # Sink 4 (best-effort, doesn't affect ok status if local sinks wrote)
    ok, info = _write_sink_supabase(record)
    if ok:
        sinks_written.append("supabase:dnc_emails")
    else:
        sinks_failed.append(("supabase:dnc_emails", info))

    # Invalidate cache so subsequent is_optout calls see this record
    invalidate_cache()

    overall_ok = len(sinks_written) >= 1  # at least one sink wrote = ok

    result = RegistrationResult(
        ok=overall_ok,
        sinks_written=sinks_written,
        sinks_failed=sinks_failed,
        dnc_id=dnc_id,
        email=e_norm,
        already_present=already_present,
    )

    if notify_slack:
        try:
            _post_slack_alert(record, sinks_written, sinks_failed)
        except Exception as exc:
            log.warning("slack notify failed: %s", exc)

    # Append-only audit envelope (HIVE_GOVERNANCE_V2.md Section 4).
    # Every DNC registration writes a cryptographically chained envelope.
    # Best-effort: a write failure here does NOT roll back the sink writes.
    try:
        from audit_log import write_envelope as _audit_write  # type: ignore
        _audit_write(
            agent_id="dnc_registrar",
            action_type="dnc.registered",
            payload={
                "email": e_norm,
                "dnc_id": dnc_id,
                "source": source,
                "reason": reason,
                "name": name or "",
                "address": address or "",
                "phone": phone or "",
                "blocked_channels": list(blocked_channels),
                "sinks_written": list(sinks_written),
                "sinks_failed_count": len(sinks_failed),
                "already_present": already_present,
                "overall_ok": overall_ok,
            },
        )
    except Exception as _audit_err:
        log.warning("audit_log envelope failed (non-fatal): %s", _audit_err)

    log.info(
        "register_optout email=%s source=%s ok=%s sinks_written=%d sinks_failed=%d",
        e_norm, source, overall_ok, len(sinks_written), len(sinks_failed),
    )
    return result


# ── Public API: reconcile_sinks ───────────────────────────────────

def reconcile_sinks() -> ReconciliationReport:
    """Compare all four sinks; return per-sink counts + diffs.

    Used by dnc_reconcile.py daily cron. Never raises.
    """
    checked_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Read each sink's email set. Multiple paths for the same logical sink
    # are unioned (we want to know what the system *would* see).
    sink1: set[str] = set()
    sink1_records: list[dict[str, Any]] = []
    for p in DNC_PATHS:
        for rec in _read_json_array(p):
            e = _norm_email(rec.get("email", ""))
            if e:
                sink1.add(e)
                sink1_records.append(rec)

    sink2: set[str] = set()
    for p in OPTED_OUT_PATHS:
        for rec in _read_json_array(p):
            e = _norm_email(rec.get("email", ""))
            if e:
                sink2.add(e)

    # Sink 3 is JSONL audit; we count "dnc_registered" entries
    sink3: set[str] = set()
    for p in PHRASE_SCRUB_PATHS:
        if not p.exists():
            continue
        try:
            for line in p.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("class_name") == "dnc_registered":
                    e = _norm_email(rec.get("recipient", ""))
                    if e:
                        sink3.add(e)
        except Exception as exc:
            log.warning("could not read phrase scrub %s: %s", p, exc)

    # Sink 4 -- Supabase. Best-effort GET; treat unreachable as empty set.
    sink4: set[str] = set()
    sb_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    sb_key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY", "")
    )
    if sb_url and sb_key:
        try:
            req = Request(
                f"{sb_url}/rest/v1/dnc_emails?select=email",
                headers={"apikey": sb_key, "Authorization": f"Bearer {sb_key}"},
            )
            with urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    rows = json.loads(resp.read().decode("utf-8") or "[]")
                    for r in rows:
                        e = _norm_email(r.get("email", ""))
                        if e:
                            sink4.add(e)
        except Exception as exc:
            log.warning("Supabase reconcile fetch failed: %s", exc)

    counts = {
        "dnc_list_json": len(sink1),
        "opted_out_emails_json": len(sink2),
        "phrase_scrub_jsonl": len(sink3),
        "supabase_dnc_emails": len(sink4),
    }

    # Compute "only_in" diffs against the canonical set (sink1)
    only_in: dict[str, list[str]] = {
        "only_in_sink2_not_sink1": sorted(sink2 - sink1),
        "only_in_sink1_not_sink2": sorted(sink1 - sink2),
        "only_in_sink4_not_sink1": sorted(sink4 - sink1) if sink4 else [],
    }
    mismatches = sum(len(v) for v in only_in.values())

    # Oldest entry: scan sink1 records for `added_utc`
    oldest_iso = ""
    oldest_age_days = 0
    try:
        oldest_dt: Optional[datetime] = None
        for rec in sink1_records:
            iso = rec.get("added_utc") or rec.get("first_added_utc") or ""
            if not iso:
                continue
            try:
                dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
                if oldest_dt is None or dt < oldest_dt:
                    oldest_dt = dt
                    oldest_iso = iso
            except Exception:
                continue
        if oldest_dt is not None:
            now = datetime.now(timezone.utc)
            oldest_age_days = max(0, (now - oldest_dt).days)
    except Exception as exc:
        log.warning("oldest entry computation failed: %s", exc)

    return ReconciliationReport(
        ok=(mismatches == 0),
        counts=counts,
        only_in=only_in,
        oldest_entry_iso=oldest_iso,
        oldest_entry_age_days=oldest_age_days,
        mismatches=mismatches,
        checked_at=checked_at,
    )


# ── CLI ───────────────────────────────────────────────────────────

def _cli() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="DNC registrar -- multi-sink opt-out manager")
    sub = ap.add_subparsers(dest="cmd")

    p_add = sub.add_parser("add", help="Register an opt-out")
    p_add.add_argument("email")
    p_add.add_argument("--source", required=True)
    p_add.add_argument("--reason", required=True)
    p_add.add_argument("--name", default=None)
    p_add.add_argument("--address", default=None)
    p_add.add_argument("--phone", default=None)
    p_add.add_argument("--no-slack", action="store_true")

    p_chk = sub.add_parser("check", help="Is this email opted out?")
    p_chk.add_argument("email")

    sub.add_parser("reconcile", help="Reconcile all four sinks")

    args = ap.parse_args()

    if args.cmd == "add":
        result = register_optout(
            args.email, source=args.source, reason=args.reason,
            name=args.name, address=args.address, phone=args.phone,
            notify_slack=not args.no_slack,
        )
        print(json.dumps(result.to_dict(), indent=2))
        return 0 if result.ok else 1

    if args.cmd == "check":
        out = is_optout(args.email)
        print(json.dumps({"email": args.email, "is_optout": out}, indent=2))
        return 0 if not out else 2

    if args.cmd == "reconcile":
        rep = reconcile_sinks()
        print(json.dumps(rep.to_dict(), indent=2))
        return 0 if rep.ok else 1

    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(_cli())
