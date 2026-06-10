"""marcus_contract_handoff -- triggered when a seller verbally agrees.

When a lead transitions to `verbal_agreement`, Marcus Cole:
  1. Looks up the state-specific title company (with fallback chain).
  2. Generates the Purchase Contract PDF (14-day inspection period included).
  3. Posts the contract PDF into the lead's Slack thread in #wholesale-deals.
  4. DMs Rich (owner) with a summary: what to sign, what the title wire is for,
     next steps after signature.
  5. Marks the lead's status = 'contract_sent' and awaits Rich's approval.

Owner's job after receiving the DM: sign the PDF (or click approve), then
reply with their signed copy. The next cron sweep flips the lead to 'signed'
and triggers the buyer blast + optional outbound confirmation call.

Runs via cron every 5 min -- idempotent (only acts on verbal_agreement leads
that haven't been processed yet).
"""
from __future__ import annotations

import json
import logging
import os
import pathlib
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="[marcus %(asctime)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("marcus_contract_handoff")

ROOT = pathlib.Path("/mnt/sdcard/AA_MY_DRIVE")
LEADS_DB = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Broker_OS" / "wholesale_agent" / "leads_db.json"
CONTRACTS_DIR = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Broker_OS" / "wholesale_agent" / "contracts_sent"
CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)
MARCUS_CURSOR = ROOT / "_logs" / "marcus_handoff_cursor.json"
CREDS = ROOT / "03_AUTOMATION_CORE" / "03_Credentials" / ".env"

CHANNEL_DEALS = os.environ.get("WHOLESALE_DEALS_CHANNEL", "C0ANLLV8JAC")  # #wholesale-deals
OWNER_SLACK_USER = os.environ.get("OWNER_SLACK_USER_ID", "")  # optional: DM id (Rich)

sys.path.insert(0, str(ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Broker_OS" / "wholesale_agent"))
try:
    from rex_closer import get_title_company, get_title_companies_ranked
    from deal_slack import post_touch, post_stage
except Exception as _e:
    log.error("imports failed: %s", _e)
    raise


def _slack_token() -> str:
    t = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    if t:
        return t
    if CREDS.exists():
        m = re.search(r"^SLACK_BOT_TOKEN\s*=\s*['\"]?(xoxb-[A-Za-z0-9\-]+)['\"]?",
                      CREDS.read_text(), re.M)
        if m:
            return m.group(1)
    return ""


def _slack_upload_file(path: pathlib.Path, channel: str, thread_ts: str, title: str) -> bool:
    """Upload a file to Slack via files.upload (v1 API still supported for bots)."""
    token = _slack_token()
    if not token:
        return False
    boundary = "----FormBoundaryMarcus"
    body = bytearray()
    for field, value in (("channels", channel), ("thread_ts", thread_ts),
                         ("title", title), ("filename", path.name),
                         ("filetype", "pdf")):
        body.extend(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{field}"\r\n\r\n'
            f"{value}\r\n".encode()
        )
    body.extend(
        f"--{boundary}\r\n".encode()
        + f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode()
        + b"Content-Type: application/pdf\r\n\r\n"
    )
    body.extend(path.read_bytes())
    body.extend(f"\r\n--{boundary}--\r\n".encode())
    req = urllib.request.Request(
        "https://slack.com/api/files.upload",
        data=bytes(body),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    try:
        r = urllib.request.urlopen(req, timeout=20).read()
        resp = json.loads(r)
        return bool(resp.get("ok"))
    except Exception as e:
        log.warning("slack upload err: %s", e)
        return False


def _slack_dm_owner(text: str) -> bool:
    """DM Rich if OWNER_SLACK_USER_ID is set; else post to #hive-alerts as a
    mention fallback."""
    token = _slack_token()
    if not token:
        return False
    target = OWNER_SLACK_USER or "C0ANPRCA4AD"  # #hive-alerts fallback
    prefix = "" if OWNER_SLACK_USER else ":bust_in_silhouette: *For Rich* -- "
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps({"channel": target, "text": prefix + text, "mrkdwn": True}).encode(),
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json; charset=utf-8"},
    )
    try:
        urllib.request.urlopen(req, timeout=8).read()
        return True
    except Exception:
        return False


def _load_cursor() -> dict:
    try:
        return json.loads(MARCUS_CURSOR.read_text())
    except Exception:
        return {"handed_off": []}


def _save_cursor(c: dict) -> None:
    MARCUS_CURSOR.write_text(json.dumps(c))


def _fetch_thread_ts(lead_id: str) -> str | None:
    # Read the shared deal_thread_cursor to find the thread_ts
    p = ROOT / "_logs" / "deal_thread_cursor.json"
    try:
        d = json.loads(p.read_text())
        entry = d.get("leads", {}).get(str(lead_id))
        return entry.get("thread_ts") if entry else None
    except Exception:
        return None


def _generate_contract(lead: dict, title_co: dict, offer: int,
                       assignment_fee: int = 5000,
                       inspection_days: int = 14) -> pathlib.Path | None:
    """Generate the purchase contract PDF by calling contract_generator."""
    try:
        from contract_generator import generate_contract_pdf  # may exist
    except ImportError:
        log.warning("contract_generator.generate_contract_pdf not importable -- skipping PDF")
        return None

    deal = {
        "address": lead.get("address", ""),
        "city": lead.get("city", ""),
        "state": lead.get("state", ""),
        "owner_name": lead.get("owner_name", ""),
        "owner_email": lead.get("email") or lead.get("owner_email", ""),
        "offer": offer,
        "assignment_fee": assignment_fee,
        "inspection_days": inspection_days,
        "title_company": title_co.get("name", "TBD"),
        "closing_date": (datetime.now(timezone.utc).strftime("%B %d, %Y")),
    }
    out = CONTRACTS_DIR / f"contract_{lead.get('id','x')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    try:
        generate_contract_pdf(deal, str(out))
    except Exception as e:
        log.warning("contract generation failed: %s", e)
        return None
    return out if out.exists() else None


def _estimate_offer(lead: dict) -> int:
    """Rough offer math: ARV * 0.70 - 15% repair estimate."""
    try:
        arv = float(lead.get("estimated_arv") or lead.get("arv") or 0)
    except Exception:
        arv = 0.0
    repair = round(arv * 0.15, -2)
    return max(int(round((arv * 0.70) - repair, -2)), 0)


def handoff(lead: dict) -> bool:
    """Do the full Marcus handoff for one lead."""
    lid = str(lead.get("id") or lead.get("lead_id") or "")
    state = (lead.get("state") or "").upper()
    addr = lead.get("address", "")
    city = lead.get("city", "")
    owner = lead.get("owner_name", "Unknown").title()
    email = lead.get("email") or lead.get("owner_email", "")

    ranked = get_title_companies_ranked(state)
    primary = ranked[0] if ranked else {"name": "TBD", "phone": "", "email": ""}
    offer = _estimate_offer(lead)
    contract_pdf = _generate_contract(lead, primary, offer=offer)

    # Post rich summary into deal thread
    thread_ts = _fetch_thread_ts(lid)
    summary = (
        f":pencil2: *MARCUS: Contract ready for signature*\n"
        f"Seller: *{owner}*  ({email})\n"
        f"Property: `{addr}`, {city}, {state}\n"
        f"Offer: *${offer:,}*  (14-day inspection period + QA review clause included)\n"
        f"Assignment fee: $5,000\n"
        f"Title company: *{primary.get('name','TBD')}*  {primary.get('phone','')}\n"
        f"Backup title co's on deck: "
        + ", ".join(c.get("name", "?") for c in ranked[1:4])
        + "\n\n"
        f":point_right: Rich: sign the attached PDF or approve here; I'll route to title once signed."
    )
    if thread_ts:
        post_touch(lead=lead, agent="Marcus Cole", channel="email",
                   subject="Contract ready for signature",
                   body=summary, outcome="contract drafted")

    # Upload PDF
    if contract_pdf and thread_ts:
        _slack_upload_file(contract_pdf, CHANNEL_DEALS, thread_ts,
                           f"Contract -- {addr}")

    # DM Rich with actionable summary
    dm = (
        f":rotating_light: *Deal ready for your signature*\n\n"
        f"Seller *{owner}* agreed to our cash offer on `{addr}, {city}, {state}`.\n"
        f"Offer: *${offer:,}*. Assignment fee: $5,000. Title: *{primary.get('name','TBD')}* "
        f"({primary.get('phone','')}).\n\n"
        f":black_nib: Sign the contract PDF (in the thread above this alert).\n"
        f":bank: Expected wire sequence:\n"
        f"  1. Buyer wires $1,000 earnest to {primary.get('name','TBD')} within 3 days.\n"
        f"  2. Closing happens within 14 days.\n"
        f"  3. Your $5,000 assignment fee wires to your bank on close.\n\n"
        f":warning: The title company will *call you* to verify wire instructions. "
        f"Pick up. Never share wire details over email.\n\n"
        f":hash: Deal thread: <#{CHANNEL_DEALS}>  lead_id: `{lid}`"
    )
    _slack_dm_owner(dm)

    # Flip status
    lead["status"] = "contract_sent"
    lead["offer_amount"] = offer
    lead["assigned_title_company"] = primary.get("name", "")
    lead["contract_pdf"] = str(contract_pdf) if contract_pdf else ""
    if thread_ts:
        post_stage(lead, "contract_sent",
                   detail=f":arrow_right: Waiting on Rich's signature. Title: *{primary.get('name','TBD')}*")
    return True


def scan() -> dict:
    if not LEADS_DB.exists():
        return {"processed": 0, "handed_off": 0}
    leads = json.loads(LEADS_DB.read_text())
    cursor = _load_cursor()
    already = set(cursor.get("handed_off", []))
    count = 0
    for lead in leads:
        if lead.get("status") != "verbal_agreement":
            continue
        lid = str(lead.get("id") or lead.get("lead_id") or "")
        if not lid or lid in already:
            continue
        log.info("handing off: %s @ %s", lead.get("owner_name", "?"), lead.get("address", "?"))
        ok = handoff(lead)
        if ok:
            already.add(lid); count += 1
    # Persist both cursor and lead_db (we updated statuses)
    cursor["handed_off"] = sorted(already)
    _save_cursor(cursor)
    LEADS_DB.write_text(json.dumps(leads, indent=2, default=str))
    return {"processed": len(leads), "handed_off": count}


def main():
    s = scan()
    print(json.dumps(s))


if __name__ == "__main__":
    main()
