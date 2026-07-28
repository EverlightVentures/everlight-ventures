#!/usr/bin/env python3
"""
enrich_tracker_dehashed.py -- turn the 42 TN deal-tracker leads into REAL,
owner-matched, reachable Deal-1 emails using DeHashed.

This is the FOCUSED sibling of dehashed_enrich_chrisfit.py. That script enriches
the broad 1,213-row chris_fit_list. This one targets ONLY the curated
tn_deal_tracker.json (the Chris @ Mid-South buy-box list Rich actually works),
and writes the email back INTO the tracker so the sender picks it up.

Owner-match discipline (the lesson from the 5/30 run -- 64 address hits but only
2 owner matches): an address search returns everyone ever tied to the street
(prior tenants, adult kids, roommates). We only mark a lead send-ready when a
breach record's NAME overlaps the assessor owner name by >=2 tokens. Co-resident
emails are kept as candidates but NOT auto-sent.

Usage:
    set -a; . /root/.config/everlight/secrets.env; set +a
    python3 enrich_tracker_dehashed.py --check      # 0 credits, validate key
    python3 enrich_tracker_dehashed.py --limit 42   # spend ~42 credits, write back
    python3 enrich_tracker_dehashed.py --dry-run --limit 3   # no write, just show
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
WH = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale")
TRACKER = WH / "tn_deal_tracker.json"
ASSESSOR_DIR = WH / "owner_downloads" / "parsed"

import dehashed_client as dc


def _norm_parcel(pid: str) -> str:
    return re.sub(r"\s+", "", pid or "")


def _load_assessor() -> dict:
    """parcel_id -> parsed Shelby assessor record. Carries owner_mailing_street +
    owner_mailing_city_state_zip -- the owner/tenant separator: for absentee owners
    the property address houses a TENANT, the mailing address is where the OWNER lives."""
    out = {}
    if not ASSESSOR_DIR.exists():
        return out
    for f in ASSESSOR_DIR.glob("*.json"):
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        if isinstance(d, dict) and d.get("parcel_id"):
            out[_norm_parcel(d["parcel_id"])] = d
    return out


def _mailing_street(rec: dict) -> str:
    """Clean the assessor's run-together mailing street ('9411FORREST WINDDR')
    into something DeHashed can match ('9411 FORREST WIND DR'). Best-effort:
    split the leading house number off, the rest is the street."""
    raw = (rec.get("owner_mailing_street") or "").strip()
    if not raw:
        return ""
    m = re.match(r"(\d+)\s*(.*)", raw)
    if not m:
        return raw
    num, rest = m.group(1), m.group(2)
    rest = re.sub(r"([a-z])([A-Z])", r"\1 \2", rest)   # FORRESTWind -> FORREST Wind
    rest = re.sub(r"\s+", " ", rest).strip()
    return f"{num} {rest}".strip()


def _is_absentee(rec: dict, property_address: str) -> bool:
    ms = (rec.get("owner_mailing_street") or "").strip()
    if not ms:
        return False
    house = (property_address or "").split()[:1]
    return bool(house) and house[0] not in ms


def _tokens(n: str) -> set[str]:
    # assessor "JONES TOBY T" and breach "Toby Jones" -> {jones, toby} (drop 1-letter initials)
    return {t for t in re.sub(r"[^a-z ]", " ", (n or "").lower()).split() if len(t) > 1}


def _owner_match(owner_name: str, entry_name: str) -> bool:
    o, e = _tokens(owner_name), _tokens(entry_name)
    if not o or not e:
        return False
    return len(o & e) >= 2


def _is_llc(name: str) -> bool:
    return bool(re.search(r"\b(llc|inc|corp|company|co|trust|church|properties|ministries)\b",
                          (name or "").lower()))


def _load_suppressed() -> set:
    """Bounced/complained addresses we must never re-propose -- don't waste a
    DeHashed credit resolving a dead address (see bounce_sweeper.py)."""
    p = HERE / "bounce_suppression.json"
    if not p.exists():
        return set()
    try:
        return {e.lower() for e in json.loads(p.read_text()).get("addresses", {})}
    except Exception:
        return set()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=42, help="owners to query (= credits spent)")
    ap.add_argument("--check", action="store_true", help="validate key + show credits (0 credits)")
    ap.add_argument("--dry-run", action="store_true", help="query but do NOT write back to tracker")
    args = ap.parse_args()

    if not dc.is_configured():
        print("DeHashed NOT configured -- set DEHASHED_API_KEY in secrets.env first\n"
              "  set -a; . /root/.config/everlight/secrets.env; set +a")
        return 1

    if args.check:
        print(json.dumps(dc.account_info(), indent=2))
        return 0

    if not TRACKER.exists():
        print(f"No tracker at {TRACKER}")
        return 1

    tracker = json.loads(TRACKER.read_text())
    assessor = _load_assessor()
    suppressed = _load_suppressed()  # never re-propose a bounced address

    # Build the work queue: leads with an owner_name and no email yet.
    # De-dupe on parcel (the tracker has a few double-spaced parcel-id twins).
    seen_addr = set()
    queue = []
    for pid, lead in tracker.items():
        name = (lead.get("owner_name") or "").strip()
        addr = (lead.get("property_address") or "").strip()
        has_email = bool((lead.get("email") or "").strip())
        if not name or has_email:
            continue
        norm = re.sub(r"\s+", " ", addr.upper())
        if norm in seen_addr:
            continue
        seen_addr.add(norm)
        queue.append((pid, lead))

    batch = queue[:args.limit]
    print("=" * 70)
    print(f"DeHashed tracker enrich -- {len(tracker)} parcels | "
          f"{len(queue)} need email | querying {len(batch)} (~{len(batch)} credits)")
    print("=" * 70)

    queried = hits = owner_matched = total_emails = errors = 0
    last_balance = None

    def _flush():
        if not args.dry_run:
            TRACKER.write_text(json.dumps(tracker, indent=1))

    for i, (pid, lead) in enumerate(batch, 1):
        name = lead["owner_name"].strip()
        addr = (lead.get("property_address") or "").strip()
        rec = assessor.get(_norm_parcel(pid), {})
        absentee = _is_absentee(rec, addr)
        mail_street = _mailing_street(rec)

        emails = []
        owner_emails = []

        # PASS 1 -- absentee owner: search the OWNER'S MAILING address (where the
        # owner lives), NOT the property (where the tenant lives). This is the
        # owner/tenant separator. Owner-occupied: property addr IS the owner's home.
        if absentee and mail_street:
            mcity = ""
            mcsz = (rec.get("owner_mailing_city_state_zip") or "")
            mst = "TN" if "TN" in mcsz.upper() else ""
            cm = re.match(r"([A-Za-z .'-]+?)([A-Z]{2})\d", mcsz)
            if cm:
                mcity = cm.group(1).strip()
            r0 = dc.search(address=mail_street, city=mcity, state=mst or "")
            queried += 1
            if r0.get("balance") is not None:
                last_balance = r0["balance"]
            for e in r0.get("emails", []):
                emails.append(e)
                if _owner_match(name, e.get("name", "")):
                    owner_emails.append(e)

        # PASS 2 -- property-address search (owner-occupied -> owner; absentee -> tenant/co-resident).
        r = dc.search(name=name, address=addr, city="Memphis", state="TN")
        queried += 1
        if r.get("error"):
            errors += 1
        if r.get("balance") is not None:
            last_balance = r["balance"]
        seen0 = {e["email"] for e in emails}
        for e in r.get("emails", []):
            if e["email"] in seen0:
                continue
            emails.append(e)
            if _owner_match(name, e.get("name", "")):
                owner_emails.append(e)

        # Name-fallback: absentee/vacant property -> address search finds tenants,
        # not the owner who lives elsewhere. If address gave NO owner match, query
        # by name and keep only entries that overlap the owner name AND corroborate
        # on TN/Memphis (so a same-name person in another state doesn't slip in).
        if not owner_emails and not _is_llc(name):
            r2 = dc.search(name=name, state="TN")
            if r2.get("balance") is not None:
                last_balance = r2["balance"]
            for e in r2.get("emails", []):
                ent_addr = (e.get("address") or "").upper()
                tn_ok = ("TN" in ent_addr or "MEMPHIS" in ent_addr or not ent_addr)
                if _owner_match(name, e.get("name", "")) and tn_ok:
                    owner_emails.append(e)
            # merge new emails into the candidate pool
            seen_e = {x["email"] for x in emails}
            emails += [e for e in r2.get("emails", []) if e["email"] not in seen_e]
            queried += 1  # the fallback spent a 2nd credit

        # Drop any address we've already seen bounce -- never re-propose a dead one.
        emails = [e for e in emails if e["email"].lower() not in suppressed]
        owner_emails = [e for e in owner_emails if e["email"].lower() not in suppressed]

        best = (owner_emails[0]["email"] if owner_emails
                else (emails[0]["email"] if emails else ""))

        if emails:
            hits += 1
            total_emails += len(emails)

        # Write back. Only an OWNER-matched email becomes send-ready; co-resident
        # hits are stored as candidates for human review, NOT auto-sent.
        lead["email_candidates"] = [
            {"email": e["email"], "name": e.get("name", ""),
             "owner_match": _owner_match(name, e.get("name", ""))}
            for e in emails
        ]
        lead["email_checked_at"] = datetime.now(timezone.utc).isoformat()
        if owner_emails:
            owner_matched += 1
            lead["email"] = owner_emails[0]["email"]
            lead["email_confidence"] = 0.85
            lead["status"] = "email_ready"
        elif emails:
            # address-level hit, owner not confirmed -> hold for review
            lead["email_confidence"] = 0.40
            lead["status"] = "email_review"
        else:
            lead["email_confidence"] = 0.0
            lead["status"] = "email_not_found" if not r.get("error") else "email_error"

        tag = ("OWNER" if owner_emails else
               ("LLC*" if (_is_llc(name) and emails) else
                ("HIT*" if emails else ("ERR" if r.get("error") else "---"))))
        print(f"  [{i:2d}/{len(batch)}] {tag:5s} {name[:26]:26s} "
              f"{best or (r.get('error') or 'no email')}", flush=True)

        if i % 10 == 0:
            _flush()
        time.sleep(0.4)

    _flush()

    rate = (hits / queried * 100) if queried else 0
    orate = (owner_matched / queried * 100) if queried else 0
    print("\n" + "=" * 70)
    print(f"RESULT ({'DRY-RUN, not written' if args.dry_run else 'written to tracker'}):")
    print(f"  {hits}/{queried} addresses returned a real email ({rate:.0f}%)")
    print(f"  {owner_matched}/{queried} OWNER-matched -> SEND-READY pool ({orate:.0f}%)")
    print(f"  {total_emails} real emails | errors={errors} | credits left={last_balance}")
    print("\n  status=email_ready  -> owner confirmed, safe to CAN-SPAM cold email")
    print("  status=email_review -> address hit, owner unconfirmed, human-eyeball first")
    print("  Breach-sourced marketing: keep Imani/Lo Hines one-line clear on file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
