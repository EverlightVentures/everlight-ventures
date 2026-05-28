"""
enrich_batch.py -- manual assessor folder -> osint -> tiered send-ready leads.

Deal-1 path: reads Marquise's manually-saved MHTML files, runs OSINT to find
emails, gates them by confidence tier, and writes send-ready output for the
branded outbound pipeline.

Pipeline
--------
  .mht/.mhtml in inbox/
      |
      v
  parse_assessor_mhtml.extract_lead()  -> owner_name, mailing_address, property fields
      |
      v
  homeowner_osint.resolve()            -> candidate_emails, identity_score, verdict
      |
      v
  email_confidence_gate.categorize()   -> tier, best_email, score
      |
      v
  leads_db.json updated                -> best_email, confidence_score, confidence_tier, osint_at
  _logs/enrichment/enrich_batch.jsonl  -> per-file audit trail
  _logs/enrichment/send_ready_<UTC>.jsonl -> auto_email tier only (for outbound pickup)

Usage
-----
    # process up to 10 MHTMLs from default inbox:
    python3 enrich_batch.py

    # dry-run (parse only, no OSINT, no writes):
    python3 enrich_batch.py --dry-run

    # use stub OSINT for testing:
    python3 enrich_batch.py --mock-osint --dry-run

    # custom inbox and limit:
    python3 enrich_batch.py --inbox /path/to/inbox --limit 5
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Workspace paths
# ---------------------------------------------------------------------------
_WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")

_SCRIPTS_DIR = _WORKSPACE / "03_AUTOMATION_CORE/01_Scripts"
_WHOLESALE_ROOT = _WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale"
_AGENT_ROOT = _WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent"

DEFAULT_INBOX = _WHOLESALE_ROOT / "owner_downloads/inbox"
LEADS_DB_PATH = _AGENT_ROOT / "leads_db.json"
LOG_DIR = _WORKSPACE / "_logs/enrichment"
BATCH_LOG = LOG_DIR / "enrich_batch.jsonl"

# Inject parse_assessor_mhtml from its canonical location
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
# Also ensure agent root is on path for homeowner_osint + email_confidence_gate
if str(_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_AGENT_ROOT))


# ---------------------------------------------------------------------------
# Module imports (soft -- so --mock-osint tests don't need the live libs)
# ---------------------------------------------------------------------------

def _load_modules():
    """Return (extract_lead, osint_resolve, gate_categorize) or raise ImportError."""
    import parse_assessor_mhtml as _pam
    import homeowner_osint as _osint
    import email_confidence_gate as _gate
    return _pam.extract_lead, _osint.resolve, _gate.categorize


# ---------------------------------------------------------------------------
# Stub used by --mock-osint
# ---------------------------------------------------------------------------

_MOCK_OSINT_RESULT = {
    "candidate_emails": [
        {
            "email": "mock.owner@example.com",
            "confidence": 80,
            "verified": True,
            "sources": ["mock"],
        }
    ],
    "identity_score": 85,
    "verdict": "mock_strong_match",
    "raw_investigation_id": "mock-001",
}


def _mock_osint_resolve(name, address="", city="", state="", mailing_address="", lead_id=None):
    return dict(_MOCK_OSINT_RESULT)


# ---------------------------------------------------------------------------
# Leads DB helpers
# ---------------------------------------------------------------------------

def load_leads() -> list[dict]:
    if not LEADS_DB_PATH.exists():
        return []
    return json.loads(LEADS_DB_PATH.read_text())


def save_leads(leads: list[dict]) -> None:
    LEADS_DB_PATH.write_text(json.dumps(leads, indent=2, default=str))


def find_lead_for_record(leads: list[dict], parcel_id: str, property_address: str) -> Optional[dict]:
    """Match by parcel_id first, then by normalized street address."""
    parcel = (parcel_id or "").strip()
    if parcel:
        for lead in leads:
            if (lead.get("parcel_id") or "").strip() == parcel:
                return lead
    addr_norm = re.sub(r"\s+", " ", (property_address or "").upper().strip())
    if addr_norm:
        for lead in leads:
            e_addr = re.sub(r"\s+", " ", (lead.get("address") or "").upper().strip())
            e_street = e_addr.split(",")[0].strip()
            if e_street and e_street == addr_norm:
                return lead
    return None


# ---------------------------------------------------------------------------
# Ledger writer
# ---------------------------------------------------------------------------

def write_ledger(entry: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(BATCH_LOG, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def write_send_ready(records: list[dict]) -> Optional[Path]:
    if not records:
        return None
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts_tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = LOG_DIR / f"send_ready_{ts_tag}.jsonl"
    with open(out_path, "w") as f:
        for rec in records:
            f.write(json.dumps(rec, default=str) + "\n")
    return out_path


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def _default_extract_html(mht_path: Path) -> tuple[str, str]:
    """
    Extract HTML string from an MHTML file using parse_assessor_mhtml helper.
    Falls back to raw read if the helper is unavailable.
    Returns (html, source_url).
    """
    try:
        import parse_assessor_mhtml as _pam
        return _pam.extract_html_from_mht(mht_path)
    except Exception:
        pass
    # Raw fallback
    try:
        return mht_path.read_bytes().decode("utf-8", errors="replace"), ""
    except Exception:
        return "", ""


def process_file(
    mht_path: Path,
    leads: list[dict],
    extract_lead_fn,
    osint_resolve_fn,
    gate_categorize_fn,
    dry_run: bool = False,
    extract_html_fn=None,
) -> dict:
    """
    Process one MHTML file through the full pipeline.

    Parameters
    ----------
    extract_html_fn : callable(Path) -> (html_str, source_url_str) | None
        Override the MHTML-to-HTML extraction step.  When None, uses the
        default (parse_assessor_mhtml.extract_html_from_mht).  Tests inject
        this to bypass MHTML parsing entirely.
    extract_lead_fn : callable(html, source_url, source_file) -> dict
        Convert raw HTML into a structured lead record.  Tests inject this
        to return synthetic owner data without needing real HTML or BeautifulSoup.

    Returns a result dict with keys: file, ok, tier, best_email, score,
    owner_name, property_address, error.
    """
    ts = datetime.now(timezone.utc).isoformat()
    result = {
        "file": mht_path.name,
        "ts": ts,
        "ok": False,
        "tier": None,
        "best_email": None,
        "score": 0,
        "owner_name": None,
        "property_address": None,
        "parcel_id": None,
        "error": None,
    }

    # Step 1: extract HTML from MHTML container
    _html_extractor = extract_html_fn or _default_extract_html
    try:
        html, source_url = _html_extractor(mht_path)
        if not html:
            result["error"] = "no_html_in_file"
            return result
    except Exception as e:
        result["error"] = f"html_extract_error: {e}"
        return result

    # Step 2: parse HTML into structured lead record
    try:
        parsed = extract_lead_fn(html, source_url=source_url, source_file=str(mht_path))
    except Exception as e:
        result["error"] = f"parse_error: {e}"
        return result

    owner_name = (parsed.get("owner_name") or "").strip()
    property_address = (parsed.get("property_address") or "").strip()
    parcel_id = (parsed.get("parcel_id") or "").strip()
    mailing_address = (parsed.get("owner_mailing_full") or parsed.get("owner_mailing_street") or "").strip()
    city = (parsed.get("property_address_full") or "MEMPHIS").split(",")[1].strip() if "," in (parsed.get("property_address_full") or "") else "MEMPHIS"
    state = "TN"

    result["owner_name"] = owner_name
    result["property_address"] = property_address
    result["parcel_id"] = parcel_id

    if not owner_name:
        result["error"] = "no_owner_name_extracted"
        return result

    # Step 2: OSINT
    try:
        osint_result = osint_resolve_fn(
            name=owner_name,
            address=property_address,
            city=city,
            state=state,
            mailing_address=mailing_address,
            lead_id=parcel_id or property_address,
        )
    except Exception as e:
        result["error"] = f"osint_error: {e}"
        return result

    candidates = osint_result.get("candidate_emails") or []
    identity_score = int(osint_result.get("identity_score") or 0)

    # Step 3: gate
    try:
        gate_result = gate_categorize_fn(candidates, identity_score)
    except Exception as e:
        result["error"] = f"gate_error: {e}"
        return result

    tier = gate_result.get("tier", "directmail")
    best_email = gate_result.get("best_email")
    score = gate_result.get("score", 0)

    result.update({
        "ok": True,
        "tier": tier,
        "best_email": best_email,
        "score": score,
        "identity_score": identity_score,
        "verdict": osint_result.get("verdict"),
        "ranked": gate_result.get("ranked", []),
        "reason": gate_result.get("reason", ""),
    })

    # Step 4: write back to leads_db (unless dry-run)
    if not dry_run:
        matched = find_lead_for_record(leads, parcel_id, property_address)
        enrich_ts = ts
        if matched is not None:
            matched["best_email"] = best_email
            matched["confidence_score"] = score
            matched["confidence_tier"] = tier
            matched["osint_at"] = enrich_ts
            matched["identity_score"] = identity_score
            if best_email:
                matched.setdefault("email", best_email)
        # If no match, we skip DB write (file not yet in leads_db -- ok for manual batch)

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(args: argparse.Namespace) -> int:
    inbox = Path(args.inbox)
    if not inbox.exists():
        print(f"[enrich_batch] Inbox not found: {inbox}")
        print("[enrich_batch] Creating inbox directory.")
        inbox.mkdir(parents=True, exist_ok=True)

    mht_files = sorted(
        list(inbox.glob("*.mht")) + list(inbox.glob("*.mhtml"))
    )[: args.limit]

    if not mht_files:
        print(f"[enrich_batch] No .mht/.mhtml files found in {inbox}")
        return 0

    print(f"[enrich_batch] Found {len(mht_files)} file(s) in {inbox}")

    # Load function pointers
    if args.mock_osint:
        try:
            extract_lead_fn, _, gate_categorize_fn = _load_modules()
            osint_resolve_fn = _mock_osint_resolve
        except ImportError as e:
            # If parse_assessor_mhtml is missing too, we still need it for real files.
            # Only happens in tests where monkeypatching handles it anyway.
            print(f"[enrich_batch] WARNING: could not load modules: {e}")
            extract_lead_fn = None
            osint_resolve_fn = _mock_osint_resolve
            gate_categorize_fn = None
    else:
        try:
            extract_lead_fn, osint_resolve_fn, gate_categorize_fn = _load_modules()
        except ImportError as e:
            print(f"[enrich_batch] ERROR: required module not found: {e}")
            print("[enrich_batch] Run with --mock-osint for testing, or install deps on E5.")
            return 1

    leads = load_leads() if not args.dry_run else []

    results = []
    tier_counts = {"auto_email": 0, "review": 0, "directmail": 0, "error": 0}
    send_ready = []

    for mht_path in mht_files:
        print(f"[enrich_batch] Processing: {mht_path.name}")
        res = process_file(
            mht_path=mht_path,
            leads=leads,
            extract_lead_fn=extract_lead_fn,
            osint_resolve_fn=osint_resolve_fn,
            gate_categorize_fn=gate_categorize_fn,
            dry_run=args.dry_run,
        )
        results.append(res)

        if not args.dry_run:
            write_ledger(res)

        if res.get("ok"):
            t = res.get("tier") or "directmail"
            tier_counts[t] = tier_counts.get(t, 0) + 1
            print(
                f"  -> {t.upper()} | score={res.get('score',0)} | "
                f"email={res.get('best_email') or 'none'} | "
                f"owner={res.get('owner_name','?')}"
            )
            if t == "auto_email":
                send_ready.append({
                    "owner_name": res.get("owner_name"),
                    "property_address": res.get("property_address"),
                    "parcel_id": res.get("parcel_id"),
                    "best_email": res.get("best_email"),
                    "score": res.get("score"),
                    "tier": t,
                    "identity_score": res.get("identity_score"),
                    "verdict": res.get("verdict"),
                    "source_file": res.get("file"),
                    "ts": res.get("ts"),
                })
        else:
            tier_counts["error"] += 1
            print(f"  -> ERROR: {res.get('error','unknown')}")

    # Save leads_db if not dry-run
    if not args.dry_run and leads:
        save_leads(leads)

    # Write send-ready file
    send_ready_path = None
    if not args.dry_run and send_ready:
        send_ready_path = write_send_ready(send_ready)

    # Summary
    print("\n[enrich_batch] ========== SUMMARY ==========")
    print(f"  Files processed : {len(mht_files)}")
    print(f"  auto_email      : {tier_counts['auto_email']}")
    print(f"  review          : {tier_counts['review']}")
    print(f"  directmail      : {tier_counts['directmail']}")
    print(f"  errors          : {tier_counts['error']}")
    if send_ready_path:
        print(f"  Send-ready file : {send_ready_path}")
    elif args.dry_run:
        print(f"  (dry-run -- no writes, no send-ready file)")
    else:
        print(f"  (no auto_email leads this batch)")
    print("[enrich_batch] ================================\n")

    if send_ready:
        print("[enrich_batch] AUTO-EMAIL leads:")
        for r in send_ready:
            print(f"  {r['owner_name']} | {r['property_address']} | {r['best_email']} | score={r['score']}")

    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Manual assessor folder -> OSINT -> tiered send-ready leads (Deal-1 path)."
    )
    p.add_argument("--limit", type=int, default=10,
                   help="Max MHTML files to process (default 10)")
    p.add_argument("--inbox", default=str(DEFAULT_INBOX),
                   help="Path to inbox folder containing .mht/.mhtml files")
    p.add_argument("--dry-run", action="store_true",
                   help="Parse + categorize but make no writes")
    p.add_argument("--mock-osint", action="store_true",
                   help="Use stub OSINT instead of live API (for testing)")
    return p


if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()
    sys.exit(run(args))
