"""
intel_enricher -- bridges Wholesale skip-trace output to the Intel Center OSINT desk,
with identity verification AND DNC short-circuit.

Two guards layered:
  1. DNC check (dnc_check.py)  -- if the owner is on the DNC, persist a record
     flagged dnc_blocked=true so NO downstream consumer drafts outreach. We still
     COLLECT the OSINT (for knowledge), but never use it for contact.
  2. Identity verification (identity_verifier.py) -- every finding is scored
     against the lead context. Only confidence >= threshold are "verified".

Per Operator Truth + DNC-permanent-eradication doctrine: verified != contactable.
DNC always wins.

Signature:
    enrich_after_trace(
        owner_name,
        phone=None, email=None, address=None,
        city=None, state=None, lead_id=None,
        triggered_by="wholesale_enricher",
    ) -> dict

Returns:
    {
      "raw":           {social_profiles_found, breach_flags, properties_owned, red_flags, ts},
      "verified":      same shape, only confidence >= threshold,
      "verification_summary": {total_findings, verified, rejected, avg_confidence, ...},
      "lead_context":  what we used to verify,
      "dnc_blocked":   bool,
      "dnc_reason":    str,
      "triggered_by":  str,
    }
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
INTEL_ROOT = WORKSPACE / "06_DEVELOPMENT/everlight_os/intel_center"
LEADS_DB = WORKSPACE / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale" / "leads_db.sqlite"
sys.path.insert(0, str(INTEL_ROOT))
sys.path.insert(0, str(WORKSPACE / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale"))


def _try_api(target: str, timeout: int = 25, triggered_by: str = "wholesale_enricher",
             lead_id: int | None = None,
             verify_for_state: str = "", verify_for_city: str = "") -> list[dict] | None:
    try:
        import httpx
        from urllib.parse import urlencode
        params = {"target": target, "triggered_by": triggered_by}
        if lead_id is not None:
            params["lead_id"] = str(lead_id)
        if verify_for_state:
            params["verify_for_state"] = verify_for_state
        if verify_for_city:
            params["verify_for_city"] = verify_for_city
        url = f"http://127.0.0.1:8677/events?{urlencode(params)}"
        results = []
        with httpx.Client(timeout=timeout) as http:
            with http.stream("GET", url) as resp:
                if resp.status_code != 200:
                    return None
                buf = ""
                for chunk in resp.iter_text():
                    buf += chunk
                    while "\n\n" in buf:
                        block, buf = buf.split("\n\n", 1)
                        for line in block.splitlines():
                            if line.startswith("data: "):
                                try:
                                    ev = json.loads(line[6:])
                                    if ev.get("type") == "result":
                                        results.append(ev["payload"])
                                    elif ev.get("type") == "done":
                                        return results
                                except json.JSONDecodeError:
                                    pass
        return results
    except Exception:
        return None


def _fallback_orchestrator(target: str, triggered_by: str = "wholesale_enricher",
                            lead_id: int | None = None) -> list[dict]:
    try:
        from osint_api.orchestrator import run_investigation_sync
        return run_investigation_sync(target)
    except Exception as e:
        print(f"[intel_enricher] orchestrator fallback failed: {e}", file=sys.stderr)
        return []


def _summarize(results: list[dict]) -> dict:
    """Distill investigator output into compact dict shape."""
    social = []; breaches = []; properties = []; red_flags = []
    seen_urls = set()
    for inv in results or []:
        iid = inv.get("investigator_id", "")
        for f in inv.get("findings", []):
            label = (f.get("label") or "").lower()
            value = f.get("value", ""); url = f.get("url", "")
            if iid == "social_recon" and label.startswith("✓"):
                platform = label.replace("✓", "").strip()
                if url and url not in seen_urls:
                    social.append({"platform": platform, "url": url,
                                   **({"verification": f.get("verification")} if f.get("verification") else {})})
                    seen_urls.add(url)
            elif iid == "leak_check" and ("breach" in label or "pwn" in label):
                breaches.append({"label": f.get("label"), "summary": value, "url": url,
                                 **({"verification": f.get("verification")} if f.get("verification") else {})})
            elif iid == "property_records":
                properties.append({"site": f.get("label"), "url": url, "status": value,
                                   **({"verification": f.get("verification")} if f.get("verification") else {})})
            elif iid == "domain_intel" and "threat" in label:
                if value and value != "0":
                    red_flags.append({"label": f.get("label"), "value": value, "url": url,
                                      **({"verification": f.get("verification")} if f.get("verification") else {})})
            elif iid in ("opencorporates", "sec_edgar"):
                red_flags.append({
                    "label": f"{inv.get('investigator')}: {f.get('label')}",
                    "value": (f.get("value") or "")[:120], "url": url,
                    **({"verification": f.get("verification")} if f.get("verification") else {}),
                })
    return {
        "social_profiles_found": social,
        "breach_flags": breaches,
        "properties_owned": properties,
        "red_flags": red_flags,
        "investigators_run": len(results or []),
        "ts": datetime.now().isoformat(),
    }


def _persist_to_lead(lead_id, payload: dict) -> None:
    if not lead_id or not LEADS_DB.exists():
        return
    try:
        con = sqlite3.connect(LEADS_DB)
        try:
            con.execute("ALTER TABLE leads ADD COLUMN intel_enrichment_json TEXT")
        except sqlite3.OperationalError:
            pass
        con.execute("UPDATE leads SET intel_enrichment_json = ? WHERE id = ?",
                    (json.dumps(payload), lead_id))
        con.commit(); con.close()
    except sqlite3.Error as e:
        print(f"[intel_enricher] lead persist failed: {e}", file=sys.stderr)


def enrich_after_trace(
    owner_name: str,
    *,
    phone: str | None = None,
    email: str | None = None,
    address: str | None = None,
    city: str | None = None,
    state: str | None = None,
    zip_code: str | None = None,
    lead_id: int | None = None,
    triggered_by: str = "wholesale_enricher",
) -> dict:
    """Main entry point. Called by cascade.py after a successful contact lookup."""
    lead_context = {
        "owner_name": (owner_name or "").strip(),
        "phone": phone, "owner_phone": phone,
        "email": email, "owner_email": email,
        "address": address, "city": city, "state": state, "zip": zip_code,
    }

    # ---- 1. DNC short-circuit: still collect OSINT, but flag the record ----
    dnc = {"is_dnc": False, "reason": "", "entry_id": None}
    try:
        from skip_trace.dnc_check import check as dnc_check
        dnc = dnc_check(owner_name=owner_name or "",
                       phone=phone or "", email=email or "",
                       address=address or "")
    except Exception as e:
        print(f"[intel_enricher] dnc lookup failed (non-fatal): {e}", file=sys.stderr)

    if not (owner_name and owner_name.strip()):
        return {
            "raw": _summarize([]),
            "verified": _summarize([]),
            "verification_summary": {"total_findings": 0, "verified": 0, "rejected": 0, "avg_confidence": 0},
            "lead_context": lead_context,
            "dnc_blocked": dnc["is_dnc"], "dnc_reason": dnc["reason"], "dnc_entry_id": dnc["entry_id"],
            "triggered_by": triggered_by,
        }

    target = owner_name.strip()

    # ---- 2. Run OSINT (API first, fallback to in-process) ----
    results = _try_api(target, triggered_by=triggered_by, lead_id=lead_id,
                        verify_for_state=state or "", verify_for_city=city or "")
    if not results:
        results = _fallback_orchestrator(target, triggered_by=triggered_by, lead_id=lead_id)

    # ---- 3. Address-as-separate-investigation merge (property records lane) ----
    if address:
        addr_results = _try_api(address, triggered_by=triggered_by, lead_id=lead_id,
                                  verify_for_state=state or "", verify_for_city=city or "")
        if not addr_results:
            addr_results = _fallback_orchestrator(address, triggered_by=triggered_by, lead_id=lead_id)
        results = (results or []) + (addr_results or [])

    # ---- 4. Identity verification ----
    verification_summary = {"total_findings": 0, "verified": 0, "rejected": 0, "avg_confidence": 0}
    verified_results = results
    try:
        from skip_trace.identity_verifier import verify_investigation
        v = verify_investigation(lead_context, results or [])
        verification_summary = v["summary"]
        # Reshape so verified_results contains ONLY findings that survived
        verified_results = [{
            **inv,
            "findings": inv.get("findings_verified", []),
        } for inv in v["results"]]
        # And keep the rejected-too as raw_results (with verification attached)
        raw_results = [{
            **inv,
            "findings": inv.get("findings_verified", []) + inv.get("findings_rejected", []),
        } for inv in v["results"]]
    except Exception as e:
        print(f"[intel_enricher] verifier failed (non-fatal): {e}", file=sys.stderr)
        raw_results = results or []

    # ---- 5. Summarize raw + verified separately ----
    summary_raw = _summarize(raw_results)
    summary_verified = _summarize(verified_results)

    payload = {
        "raw": summary_raw,
        "verified": summary_verified,
        "verification_summary": verification_summary,
        "lead_context": {k: v for k, v in lead_context.items() if v},
        "dnc_blocked": dnc["is_dnc"], "dnc_reason": dnc["reason"], "dnc_entry_id": dnc["entry_id"],
        "triggered_by": triggered_by,
    }
    _persist_to_lead(lead_id, payload)
    return payload


def main():
    ap = argparse.ArgumentParser(description="Smoke test intel_enricher with verification + DNC")
    ap.add_argument("name", help="Owner name to investigate")
    ap.add_argument("--phone", default=None)
    ap.add_argument("--email", default=None)
    ap.add_argument("--address", default=None)
    ap.add_argument("--city", default=None)
    ap.add_argument("--state", default=None)
    ap.add_argument("--zip", default=None, dest="zip_code")
    ap.add_argument("--lead-id", default=None, type=int)
    ap.add_argument("--triggered-by", default="cli_user")
    args = ap.parse_args()
    out = enrich_after_trace(
        args.name, phone=args.phone, email=args.email, address=args.address,
        city=args.city, state=args.state, zip_code=args.zip_code,
        lead_id=args.lead_id, triggered_by=args.triggered_by,
    )
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
