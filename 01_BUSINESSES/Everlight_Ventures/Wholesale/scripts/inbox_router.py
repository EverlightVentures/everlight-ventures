#!/usr/bin/env python3
"""
inbox_router.py -- organize the personal Gmail into a BUSINESS inbox by the one true
signifier: "did WE email this address via Resend?" If an incoming message is FROM an
address on our contacted list, it's a real seller/buyer reply -> label it into the owning
AGENT's folder so that agent watches + responds. Everything else (Carnival, Groupon) is
left alone. Newsletters never become leads (that was the pollution bug).

KEY SIGNIFIER (Rich, 2026-05-24): business = FROM in the contacted registry AND inbound to
Gmail. The contacted registry = every address we actually sent to via Resend:
  - leads_db leads with outreach_count > 0  (the real property contacts)
  - resend_budget.jsonl `to` addresses, excluding our own/internal addresses

AGENT FOLDERS (created idempotently via Gmail IMAP X-GM-LABELS -- no MCP write scope needed):
  Everlight/Broker_OS/Piper_Outreach     -- new + early seller replies
  Everlight/Broker_OS/Henry_Negotiation  -- engaged/negotiating
  Everlight/Broker_OS/Marvin_Closing     -- under_contract / assigning
  Everlight/Broker_OS/Vaughn_Signoff     -- closing
  Everlight/Broker_OS/Seller_Replies     -- (existing) catch-all matched reply
The owning agent is computed from the lead's PHASE via pipeline_phase_manager (one brain).

Usage:
  python3 inbox_router.py --registry         # show the contacted registry
  python3 inbox_router.py --classify EMAIL    # is this sender business? which agent?
  python3 inbox_router.py --route --dry-run   # scan inbox, show routing, no changes (default)
  python3 inbox_router.py --route             # live: create labels + tag matched messages
"""
from __future__ import annotations

import imaplib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
WH = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale"
LEADS_DB = ROOT / "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/leads_db.json"
RESEND_LEDGER = ROOT / "_logs" / "resend_budget.jsonl"
sys.path.insert(0, str(WH / "scripts"))

# Our own / internal addresses -- a send TO these is not a "contact", it's a SIM/alert.
OWN = {"1m.rich.gee@gmail.com", "admin@everlightventures.io"}
OWN_DOMAINS = {"everlightventures.io"}

AGENT_LABEL = {
    "piper_reeves":    "Everlight/Broker_OS/Piper_Outreach",
    "henry_hammond":   "Everlight/Broker_OS/Henry_Negotiation",
    "marvin_cohen":    "Everlight/Broker_OS/Marvin_Closing",
    "vaughn_sterling": "Everlight/Broker_OS/Vaughn_Signoff",
}
SELLER_REPLIES_LABEL = "Everlight/Broker_OS/Seller_Replies"
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def _load(p, default):
    try:
        return json.loads(p.read_text())
    except Exception:
        return default


def contacted_registry() -> dict:
    """address -> {who, state}. The set of people WE actually emailed (the signifier)."""
    reg: dict[str, dict] = {}
    for ld in _load(LEADS_DB, []):
        if not isinstance(ld, dict) or not ld.get("outreach_count"):
            continue
        em = (ld.get("email") or ld.get("owner_email") or "").strip().lower()
        if em and em not in OWN:
            reg[em] = {"who": ld.get("owner_name"), "state": ld.get("state"), "lead_id": ld.get("id")}
    # resend ledger recipients (exclude our own/internal + SIM sends to self)
    if RESEND_LEDGER.exists():
        for line in RESEND_LEDGER.read_text().splitlines():
            try:
                row = json.loads(line)
            except Exception:
                continue
            to = (row.get("to") or "").strip().lower()
            dom = to.split("@")[-1] if "@" in to else ""
            if to and to not in OWN and dom not in OWN_DOMAINS:
                reg.setdefault(to, {"who": None, "state": None, "via": "resend_ledger"})
    return reg


def agent_for(from_addr: str, reg: dict) -> str:
    """Owning agent = the lead's current phase owner (one brain: the conductor).
    Falls back to Piper (first-touch owner) for a matched address with no phase yet."""
    try:
        import pipeline_phase_manager as ppm
        info = reg.get(from_addr.lower(), {})
        lid = info.get("lead_id")
        for row in ppm.reconcile():
            if lid and str(row.get("key")) == str(lid):
                return ppm.PHASES.get(row["phase"], (0, "piper_reeves"))[1]
    except Exception:
        pass
    return "piper_reeves"


def classify_incoming(from_addr: str) -> dict:
    reg = contacted_registry()
    addr = (from_addr or "").strip().lower()
    if addr not in reg:
        return {"business": False, "reason": "not_on_contacted_list", "label": None, "agent": None}
    agent = agent_for(addr, reg)
    return {"business": True, "agent": agent,
            "label": AGENT_LABEL.get(agent, SELLER_REPLIES_LABEL),
            "who": reg[addr].get("who")}


# --- Gmail IMAP label ops (X-GM-LABELS) -- works with the poller's existing creds ---
def _imap():
    user = os.environ.get("IMAP_USER") or os.environ.get("GMAIL_USER") or "1m.rich.gee@gmail.com"
    pw = os.environ.get("GMAIL_APP_PASSWORD") or os.environ.get("IMAP_PASS", "")
    if not pw:
        return None, "no_imap_password"
    try:
        m = imaplib.IMAP4_SSL("imap.gmail.com")
        m.login(user, pw)
        return m, "ok"
    except Exception as e:
        return None, f"imap_login_failed_{type(e).__name__}"


def route(dry_run: bool = True, since_days: int = 3) -> dict:
    reg = contacted_registry()
    summary = {"registry_size": len(reg), "dry_run": dry_run, "scanned": 0,
               "business_matched": 0, "routed": [], "labels_ensured": list(AGENT_LABEL.values())}
    m, status = _imap()
    if not m:
        summary["imap"] = status
        summary["note"] = "matcher logic ready; live labeling runs on the poller cron with creds"
        return summary
    try:
        if not dry_run:
            for lbl in list(AGENT_LABEL.values()) + [SELLER_REPLIES_LABEL]:
                try:
                    m.create(f'"{lbl}"')  # idempotent: errors if exists, harmless
                except Exception:
                    pass
        m.select("INBOX")
        typ, data = m.search(None, f'(NEWER {since_days*86400})') if False else m.search(None, "ALL")
        uids = (data[0].split() if data and data[0] else [])[-100:]
        for uid in uids:
            typ, msg = m.fetch(uid, "(BODY[HEADER.FIELDS (FROM SUBJECT)])")
            if typ != "OK" or not msg or not msg[0]:
                continue
            hdr = msg[0][1].decode(errors="replace")
            found = EMAIL_RE.findall(hdr)
            subj = ""
            for ln in hdr.splitlines():
                if ln.lower().startswith("subject:"):
                    subj = ln.split(":", 1)[1].strip()
            summary["scanned"] += 1
            frm = found[0].lower() if found else ""
            if frm in reg:
                summary["business_matched"] += 1
                agent = agent_for(frm, reg)
                lbl = AGENT_LABEL.get(agent, SELLER_REPLIES_LABEL)
                summary["routed"].append({"from": frm, "who": reg[frm].get("who"), "agent": agent, "label": lbl})
                if not dry_run:
                    m.store(uid, "+X-GM-LABELS", f'"{lbl}"')
                    # REACTIVE AUTO-ARM: generate the agent's response + stage it as a gated
                    # draft. No asking -- the draft fires the instant the system unblocks.
                    try:
                        import auto_responder
                        auto_responder.stage_draft(frm, reg[frm].get("who"), subj, subj, agent)
                    except Exception:
                        pass
        m.logout()
    except Exception as e:
        summary["error"] = f"{type(e).__name__}: {str(e)[:80]}"
    return summary


if __name__ == "__main__":
    if "--registry" in sys.argv:
        reg = contacted_registry()
        print(f"contacted registry: {len(reg)} addresses we emailed")
        for a, v in list(reg.items())[:15]:
            print(f"  {a}  ({v.get('who')})")
    elif "--classify" in sys.argv:
        i = sys.argv.index("--classify")
        addr = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
        print(json.dumps(classify_incoming(addr), indent=2))
    elif "--route" in sys.argv:
        print(json.dumps(route(dry_run="--run" not in sys.argv), indent=2))
    else:
        print(__doc__)
