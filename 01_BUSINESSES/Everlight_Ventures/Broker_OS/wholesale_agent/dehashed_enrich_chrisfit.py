#!/usr/bin/env python3
"""
dehashed_enrich_chrisfit.py -- spend DeHashed credits to turn Chris-fit TN
properties into REAL, reachable, Deal-1 leads.

Reads the Chris-fit list (build_chris_fit_list.py output), runs each owner through
DeHashed (1 credit/owner), keeps the REAL emails, and writes a deal1_ready list of
Chris-fit owners we can legally CAN-SPAM email. Reports the hard hit-rate so the
purchase justifies itself with numbers, not hope.

Fast path: queries DeHashed directly (~1s/owner), NOT the 58s osint_api sweep.

Usage:
    python3 dehashed_enrich_chrisfit.py --limit 100     # spend ~100 credits, measure
    python3 dehashed_enrich_chrisfit.py --limit 25 --prefer-no-email
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
FIT_LIST = WH / "config/_generated/chris_fit_list.json"
OUT = WH / "config/_generated/deal1_ready.json"

import dehashed_client as dc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100, help="owners to query (= credits spent)")
    ap.add_argument("--prefer-no-email", action="store_true",
                    help="prioritize owners that have no email yet")
    args = ap.parse_args()

    if not dc.is_configured():
        print("DeHashed NOT configured -- set DEHASHED_API_KEY in secrets.env first "
              "(and `set -a; . /root/.config/everlight/secrets.env; set +a`).")
        return 1
    if not FIT_LIST.exists():
        print(f"No Chris-fit list at {FIT_LIST} -- run build_chris_fit_list.py first.")
        return 1

    fit = json.loads(FIT_LIST.read_text())["chris_fit"]

    def needs_email(l):
        return not (l.get("email") or l.get("owner_email") or "").strip()

    queue = sorted(fit, key=needs_email, reverse=True) if args.prefer_no_email else fit
    batch = queue[:args.limit]

    def _tokens(n):
        # assessor "JONES TOBY T" and breach "Toby Jones" -> {jones, toby} (drop 1-letter initials)
        return {t for t in re.sub(r"[^a-z ]", " ", (n or "").lower()).split() if len(t) > 1}

    def _owner_match(owner_name, entry_name):
        o, e = _tokens(owner_name), _tokens(entry_name)
        if not o or not e:
            return False
        # both surname-ish and given-ish overlap -> same person at this address
        return len(o & e) >= 2

    print("=" * 66)
    print(f"DeHashed enrich -- Chris-fit={len(fit)}  querying={len(batch)} (~{len(batch)} credits)")
    print("=" * 66)

    ready, queried, hits, total_emails, errors, owner_matched = [], 0, 0, 0, 0, 0
    last_balance = None
    for i, lead in enumerate(batch, 1):
        name = lead.get("owner_name", "")
        addr = lead.get("property_address") or lead.get("address", "")
        if not name:
            continue
        r = dc.search(name=name, address=addr,
                      city=lead.get("city", "Memphis"), state="TN")
        queried += 1
        if r.get("error"):
            errors += 1
        if r.get("balance") is not None:
            last_balance = r["balance"]
        emails = r.get("emails", [])
        # Address search returns everyone ever at the property -- tag which emails
        # belong to OUR owner (name match) vs co-residents/prior tenants.
        owner_emails = [e for e in emails if _owner_match(name, e.get("name", ""))]
        other_emails = [e for e in emails if e not in owner_emails]
        best = (owner_emails[0]["email"] if owner_emails
                else (emails[0]["email"] if emails else ""))
        if emails:
            hits += 1
            total_emails += len(emails)
            if owner_emails:
                owner_matched += 1
            ready.append({
                "owner_name": name, "address": addr,
                "zip": lead.get("zip") or lead.get("zip_code"),
                "lead_id": lead.get("lead_id") or lead.get("id"),
                "best_email": best,
                "owner_match": bool(owner_emails),
                "owner_emails": [e["email"] for e in owner_emails],
                "same_address_emails": [e["email"] for e in other_emails],
            })
        tag = "OWNER" if owner_emails else ("HIT*" if emails else ("ERR" if r.get("error") else "---"))
        print(f"  [{i}/{len(batch)}] {tag:5s} {name[:28]:28s} {best or (r.get('error') or '')}")
        time.sleep(0.4)  # be gentle on the API

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "queried": queried, "owners_with_real_email": hits,
        "owner_name_matched": owner_matched,
        "total_real_emails": total_emails, "errors": errors,
        "credits_balance_after": last_balance,
        "deal1_ready": ready,
    }, indent=2, default=str))

    rate = (hits / queried * 100) if queried else 0
    orate = (owner_matched / queried * 100) if queried else 0
    print("\n" + "=" * 66)
    print(f"RESULT: {hits}/{queried} addresses returned a real email ({rate:.0f}%)")
    print(f"        {owner_matched}/{queried} matched OUR OWNER by name ({orate:.0f}%) <- the reachable Deal-1 pool")
    print(f"        {total_emails} real emails | errors={errors} | credits left={last_balance}")
    print(f"        cost-per-owner-match = ~{(queried/owner_matched):.1f} credits" if owner_matched else "        no owner matches")
    print(f"wrote -> {OUT}")
    print("\nThese are REAL emails (breach-sourced) -> legal CAN-SPAM cold email after")
    print("Imani/Lo Hines one-line clear on breach-sourced marketing. No guessing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
