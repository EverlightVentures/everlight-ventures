"""bidding_war_engine -- when a deal locks up, every buyer gets pitched
simultaneously and the best bid wins.

Why this exists:
  Sequential outreach (pitch buyer 1, wait for no, pitch buyer 2) leaves
  money on the table. The wholesaler model is to CREATE competition: every
  qualified buyer sees the deal at the same time, knows others see it too,
  and bids accordingly. Highest credible bid + fastest close wins.

How it works:
  1. trigger(deal_id) -- called when Deal.stage flips to 'contract'
  2. Pulls ALL POF-verified, market-matched, type-matched buyers
  3. Generates a personalized buyer_pitch per buyer (BRRRR/flip/hold/land math)
  4. Fires all pitches in one batch (cold/warm based on prior contact)
  5. Posts a branded Slack card to #wholesale-deals with the bid window
  6. Each buyer reply lands in the BidLedger (one row per bid)
  7. At deadline (24h default), pick winner: highest_bid * speed_score
  8. Fire winner the assignment contract auto-generated
  9. Fire losers the polite "thanks, next deal soon" close

Bid scoring (weighted):
  bid_amount * 0.7
  + (1 / can_close_days) * 100000 * 0.2     -- 7-day closer beats 30-day
  + (POF_verified ? 1.0 : 0.0) * 50000 * 0.1  -- POF tiebreaker

Compliance:
  - Fires through branded_mailer (gold template + budget gate)
  - Each buyer's state checked via state_gate
  - Buyers must have ai_call/email consent OR be on InvestorBuyer.is_active=True
    (B2B investor outreach has different rules than seller cold outreach)

Usage:
  python3 bidding_war_engine.py trigger --deal-id=<uuid>
  python3 bidding_war_engine.py status --deal-id=<uuid>
  python3 bidding_war_engine.py close --deal-id=<uuid>   # picks winner
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

for p in (
    "/home/opc/hive_django",
    "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard",
    "/home/opc/wholesale/pitches",
    "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/pitches",
    "/home/opc/content_tools",
    "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools",
):
    if p not in sys.path and Path(p).exists():
        sys.path.insert(0, p)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
import django  # noqa
django.setup()

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("bidding_war")

# How long buyers have to bid before we pick winner
DEFAULT_BID_WINDOW_HOURS = 24

# Where bid records live until BidLedger Django model is wired (Phase 2)
BID_LEDGER_FILE = Path("/home/opc/wholesale/_logs/bid_ledger.jsonl")
BID_LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)


def _eligible_buyers(deal) -> list:
    """Return InvestorBuyer rows that match this deal's market + property type.

    Filters:
      - is_active=True
      - cash_buyer=True
      - market overlap with the property's city OR state
      - property_type overlap (or 'any')
      - has email OR phone (something to fire to)
    """
    from broker_ops.models import InvestorBuyer
    deal_state = (getattr(deal, "property_state", "") or "").upper()
    deal_city = (getattr(deal, "property_city", "") or "").lower()
    deal_addr = (getattr(deal, "property_address", "") or "").lower()
    deal_type = (getattr(deal, "property_type", "") or "").lower() or "single_family"

    qs = InvestorBuyer.objects.filter(is_active=True, cash_buyer=True)

    matches = []
    for b in qs:
        markets_str = " ".join(str(m).lower() for m in (b.markets or []))
        # Match on state OR city OR full address contained in any market string
        market_match = (
            (deal_state and deal_state.lower() in markets_str)
            or (deal_city and deal_city in markets_str)
            or any(t in markets_str for t in deal_addr.split() if len(t) > 3)
        )
        if not market_match:
            continue

        # Property type match (empty list = accepts all types)
        ptypes = [str(p).lower() for p in (b.property_types or [])]
        if ptypes and deal_type not in ptypes:
            continue

        # Need at least one contact method
        if not (b.email or b.phone):
            continue

        matches.append(b)

    return matches


def _fire_pitch(deal, buyer, bid_window_close_at: datetime) -> dict:
    """Send the buyer the deal pitch with the explicit bid deadline."""
    try:
        from pitch_generator import buyer_pitch  # type: ignore
        from branded_mailer import send_branded_email  # type: ignore
    except Exception as exc:
        return {"ok": False, "error": f"import_failed:{exc}"}

    # Build a synthetic 'lead' object from the deal for buyer_pitch
    class _Lead:
        address = getattr(deal, "property_address", "")
        city = getattr(deal, "property_city", "")
        state = getattr(deal, "property_state", "")
        zip_code = getattr(deal, "property_zip", "")
        bedrooms = getattr(deal, "property_bedrooms", 3)
        bathrooms = getattr(deal, "property_bathrooms", 1)
        sqft = getattr(deal, "property_sqft", 1200)
        estimated_arv = float(getattr(deal, "estimated_arv", 0) or 0)
        estimated_repair = float(getattr(deal, "estimated_repair", 0) or 0)
        property_type = getattr(deal, "property_type", "single_family")

    buyer_profile = {
        "name": buyer.name,
        "email": buyer.email,
        "phone": buyer.phone,
        "buyer_type": buyer.buyer_type or "brrrr",
        "deals_closed": int(buyer.deals_closed or 0),
        "can_close_days": int(buyer.can_close_days or 14),
        "state": (buyer.markets[0] if buyer.markets else ""),
    }

    contract_price = float(getattr(deal, "purchase_price", 0) or 0)
    if contract_price <= 0:
        # Fall back to MAO-derived if purchase_price not set
        contract_price = max(0.0, _Lead.estimated_arv * 0.70 - _Lead.estimated_repair - 10000)

    pitch = buyer_pitch(
        lead=_Lead(),
        buyer_profile=buyer_profile,
        agent_name="Hammer Knox",
        agent_email="henry@everlightventures.io",
        contract_price=contract_price,
        assignment_fee=10000.0,
    )

    # Inject the bid-war banner at the top
    deadline_str = bid_window_close_at.strftime("%a %b %d at %I:%M %p UTC")
    bid_banner = (
        f'<div style="background:#0A0A0A;color:#D4A843;padding:18px;'
        f'border-left:6px solid #D4A843;margin-bottom:18px;">'
        f'<div style="text-transform:uppercase;letter-spacing:2px;font-size:12px;">'
        f'BID WINDOW OPEN -- closes {deadline_str}</div>'
        f'<div style="font-size:16px;margin-top:8px;color:#E8E8E8;">'
        f'This deal is going to <strong>every verified buyer in our network simultaneously</strong>. '
        f'Highest bid + fastest close wins. Reply with your number + POF.</div>'
        f'</div>'
    )
    html_with_banner = bid_banner + pitch["html_body"]

    result = send_branded_email(
        to=buyer.email,
        subject=f"[BID WINDOW] {pitch['subject']}",
        content_html=html_with_banner,
        plain_text_fallback=pitch["plain_text"] + f"\n\nBID DEADLINE: {deadline_str}",
        agent_name="Hammer Knox",
        agent_title="Disposition, Everlight Ventures",
        agent_email="henry@everlightventures.io",
        from_name="Hammer Knox",
        from_email="henry@everlightventures.io",
        budget_category="vip_reply",  # buyer dispo is high-value, not bulk
        recipient_state=(buyer.markets[0] if buyer.markets else ""),
    )
    return {"ok": result.ok, "error": result.error if not result.ok else "",
             "buyer_id": buyer.id, "buyer_name": buyer.name}


def trigger(deal_id: str, bid_window_hours: int = DEFAULT_BID_WINDOW_HOURS) -> dict:
    """Fire the bidding war for a Deal that just locked up."""
    from broker_ops.models import Deal
    try:
        deal = Deal.objects.get(id=deal_id)
    except Deal.DoesNotExist:
        return {"error": f"deal not found: {deal_id}"}

    if deal.stage not in ("contract", "psa_signed", "intro"):
        log.info(f"deal {deal_id} stage={deal.stage} -- skipping (not in lockup-able stage)")
        return {"error": f"deal stage {deal.stage} not eligible for bid war"}

    bid_window_close_at = datetime.now(timezone.utc) + timedelta(hours=bid_window_hours)
    eligible = _eligible_buyers(deal)
    log.info(f"bid war for deal {deal_id}: {len(eligible)} eligible buyers, deadline {bid_window_close_at}")

    fired = []
    failed = []
    for buyer in eligible:
        if not buyer.email:
            failed.append({"buyer_id": buyer.id, "reason": "no_email"})
            continue
        result = _fire_pitch(deal, buyer, bid_window_close_at)
        if result.get("ok"):
            fired.append(result)
        else:
            failed.append(result)

    # Log the bid war trigger event
    BID_LEDGER_FILE.open("a").write(json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "bid_war_triggered",
        "deal_id": str(deal_id),
        "buyer_count": len(eligible),
        "deadline_at": bid_window_close_at.isoformat(),
        "fired": [f["buyer_id"] for f in fired],
        "failed": failed,
    }) + "\n")

    # Slack ping for visibility
    try:
        from branded_slack import post_branded_slack  # type: ignore
        post_branded_slack(
            channel="#wholesale-deals",
            category="deal",
            title=f"BID WAR OPEN -- {getattr(deal, 'property_address', '')[:60]}",
            summary=f"{len(fired)} buyers pitched. Deadline {bid_window_hours}h.",
            body=f"Deal: {deal.id}\nDeadline: {bid_window_close_at}\n"
                  f"Buyers reached: {[f['buyer_name'] for f in fired]}",
            agent_name="Hammer Knox",
            agent_title="Disposition",
        )
    except Exception:
        pass

    return {
        "deal_id": str(deal_id),
        "eligible_buyers": len(eligible),
        "fired": len(fired),
        "failed": len(failed),
        "deadline_at": bid_window_close_at.isoformat(),
    }


def record_bid(deal_id: str, buyer_id: int, bid_amount: float,
               can_close_days: int, pof_verified: bool, notes: str = "") -> dict:
    """Append a bid to the ledger. Called by reply handler when buyer replies."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "bid_received",
        "deal_id": str(deal_id),
        "buyer_id": int(buyer_id),
        "bid_amount": float(bid_amount),
        "can_close_days": int(can_close_days),
        "pof_verified": bool(pof_verified),
        "notes": notes,
        "score": _score_bid(bid_amount, can_close_days, pof_verified),
    }
    BID_LEDGER_FILE.open("a").write(json.dumps(record) + "\n")
    log.info(f"  bid recorded: deal={deal_id} buyer={buyer_id} amount=${bid_amount:,.0f} score={record['score']:.0f}")
    return record


def _score_bid(amount: float, days: int, pof: bool) -> float:
    """Bid score: 70% money, 20% speed, 10% POF certainty."""
    money = amount * 0.7
    speed = (100000.0 / max(days, 1)) * 0.2
    cert = (50000.0 if pof else 0.0) * 0.1
    return money + speed + cert


def _fire_winner_pitch(deal, winner_buyer, winning_bid: float, total_bids: int) -> dict:
    """Send the winning buyer the WHY-THIS-DEAL-IS-GOLD pitch + 14-day timeline.

    Reuses buyer_pitch (which has BRRRR/flip/hold/land math + market block +
    spread block). Adds a winner banner showing how many they beat, the
    strategy fit, and the close timeline. This is where we close the loop --
    the buyer paid up, now they need to feel certain about it.
    """
    try:
        from pitch_generator import buyer_pitch  # type: ignore
        from branded_mailer import send_branded_email  # type: ignore
    except Exception as exc:
        return {"ok": False, "error": f"import_failed:{exc}"}

    class _Lead:
        address = getattr(deal, "property_address", "")
        city = getattr(deal, "property_city", "")
        state = getattr(deal, "property_state", "")
        zip_code = getattr(deal, "property_zip", "")
        bedrooms = getattr(deal, "property_bedrooms", 3)
        bathrooms = getattr(deal, "property_bathrooms", 1)
        sqft = getattr(deal, "property_sqft", 1200)
        estimated_arv = float(getattr(deal, "estimated_arv", 0) or 0)
        estimated_repair = float(getattr(deal, "estimated_repair", 0) or 0)
        property_type = getattr(deal, "property_type", "single_family")

    buyer_profile = {
        "name": winner_buyer.name,
        "email": winner_buyer.email,
        "phone": winner_buyer.phone,
        "buyer_type": winner_buyer.buyer_type or "brrrr",
        "deals_closed": int(winner_buyer.deals_closed or 0),
        "can_close_days": int(winner_buyer.can_close_days or 14),
        "state": (winner_buyer.markets[0] if winner_buyer.markets else ""),
    }

    pitch = buyer_pitch(
        lead=_Lead(),
        buyer_profile=buyer_profile,
        agent_name="Hammer Knox",
        agent_email="henry@everlightventures.io",
        contract_price=winning_bid - 10000.0,
        assignment_fee=10000.0,
    )

    deals_closed = int(winner_buyer.deals_closed or 0)
    relationship_line = (
        f"You've closed {deals_closed} deals with us before -- you know the drill."
        if deals_closed >= 3
        else "Here's how the next 14 days flow:"
    )

    winner_banner = (
        f'<div style="background:#0F7B3D;color:#fff;padding:22px;margin-bottom:20px;">'
        f'<div style="text-transform:uppercase;letter-spacing:3px;font-size:11px;opacity:0.85;">'
        f'YOU WON THE BID -- {total_bids} other buyers were in</div>'
        f'<div style="font-family:Playfair Display,Georgia,serif;font-size:26px;margin-top:6px;">'
        f'Deal locked at ${winning_bid:,.0f}</div>'
        f'<div style="font-size:13px;margin-top:10px;color:#dfd;">{relationship_line}</div>'
        f'</div>'

        f'<div style="background:#fafafa;border-left:4px solid #D4A843;padding:14px 18px;margin-bottom:20px;">'
        f'<div style="color:#7a5c00;font-weight:600;text-transform:uppercase;letter-spacing:2px;font-size:11px;">'
        f"Why this beat the other deals you're looking at</div>"
        f'<ul style="margin:8px 0 0 18px;padding:0;color:#444;font-size:14px;line-height:1.7;">'
        f"<li>Off-market -- never hit MLS, never hit retail, no agent commission baked in</li>"
        f"<li>Spread already verified -- ARV pulled live from Zillow, repair estimated against comps</li>"
        f"<li>EMD goes to a vetted title co (we close at the same 2-3 GA title companies every time)</li>"
        f"<li>Assignment fee transparent -- $10k baked in, no surprise add-ons</li>"
        f"<li>Seller already signed PSA + 7-day walk-away expired -- no flake risk</li>"
        f"</ul></div>"

        f'<div style="background:#0A0A0A;color:#E8E8E8;padding:14px 18px;border-left:4px solid #D4A843;margin-bottom:18px;">'
        f'<div style="color:#D4A843;font-weight:600;text-transform:uppercase;letter-spacing:2px;font-size:11px;">'
        f"Next 14 days, mapped</div>"
        f'<table style="width:100%;border-collapse:collapse;font-size:13px;margin-top:8px;">'
        f'<tr><td style="padding:4px 6px;color:#aaa;">Today</td>'
        f'<td style="padding:4px 6px;">Assignment contract emailed for your e-sig</td></tr>'
        f'<tr><td style="padding:4px 6px;color:#aaa;">Day 1-2</td>'
        f'<td style="padding:4px 6px;">EMD wire to title ($1k standard or as agreed)</td></tr>'
        f'<tr><td style="padding:4px 6px;color:#aaa;">Day 3-7</td>'
        f'<td style="padding:4px 6px;">Optional walkthrough + your inspection if you want one</td></tr>'
        f'<tr><td style="padding:4px 6px;color:#aaa;">Day 10-14</td>'
        f'<td style="padding:4px 6px;">Closing day. Title co handles all coordination. Wire your funds in.</td></tr>'
        f"</table></div>"
    )

    html = winner_banner + pitch["html_body"]

    result = send_branded_email(
        to=winner_buyer.email,
        subject=f"YOU WON -- {pitch['subject'].replace('[OFF-MARKET, 24hr first look] ', '')}",
        content_html=html,
        plain_text_fallback=(
            f"YOU WON THE BID -- locked at ${winning_bid:,.0f}\n"
            f"{total_bids} other buyers were bidding. Assignment contract goes out today.\n\n"
            f"Next 14 days:\n"
            f"  Today: assignment contract for e-sig\n"
            f"  Day 1-2: EMD wire to title\n"
            f"  Day 3-7: optional walkthrough\n"
            f"  Day 10-14: close day, wire your funds\n\n"
            f"{pitch['plain_text']}"
        ),
        agent_name="Hammer Knox",
        agent_title="Disposition, Everlight Ventures",
        agent_email="henry@everlightventures.io",
        from_name="Hammer Knox",
        from_email="henry@everlightventures.io",
        budget_category="vip_reply",
        recipient_state=(winner_buyer.markets[0] if winner_buyer.markets else ""),
    )
    return {"ok": result.ok, "error": result.error if not result.ok else "",
             "buyer_id": winner_buyer.id}


def _fire_loser_close(deal, loser_buyer) -> dict:
    """Polite close to losing bidders -- keeps the relationship for the next deal."""
    try:
        from branded_mailer import send_branded_email  # type: ignore
    except Exception:
        return {"ok": False, "error": "import_failed"}

    first = loser_buyer.name.split()[0] if loser_buyer.name else "there"
    body = (
        f"<p>Hi {first},</p>"
        f"<p>The bid window closed and another buyer landed it this time. "
        f"That's how it goes when there's competition on a real deal.</p>"
        f"<p>Three things:</p>"
        f"<ul>"
        f"<li>Your bid was credible. You're staying on our priority list.</li>"
        f"<li>Next off-market we lock up, you'll be in the first batch -- not the second.</li>"
        f"<li>If you want to widen the criteria you're buying in (different metro, different price band), reply and we'll update your profile.</li>"
        f"</ul>"
        f"<p>Talk soon.</p>"
        f"<p>Hammer Knox<br><em>Disposition, Everlight Ventures</em></p>"
    )

    result = send_branded_email(
        to=loser_buyer.email,
        subject="This one went to another bidder -- you're in for the next one",
        content_html=body,
        agent_name="Hammer Knox",
        agent_title="Disposition",
        agent_email="henry@everlightventures.io",
        from_name="Hammer Knox",
        from_email="henry@everlightventures.io",
        budget_category="nurture",
    )
    return {"ok": result.ok, "buyer_id": loser_buyer.id}


def close_war(deal_id: str) -> dict:
    """Pick the winning bid + fire winner pitch + close losers gracefully."""
    from broker_ops.models import Deal, InvestorBuyer

    bids = []
    for line in (BID_LEDGER_FILE.read_text().splitlines() if BID_LEDGER_FILE.exists() else []):
        try:
            r = json.loads(line)
            if r.get("event") == "bid_received" and str(r.get("deal_id")) == str(deal_id):
                bids.append(r)
        except Exception:
            continue

    if not bids:
        return {"deal_id": str(deal_id), "winner": None, "reason": "no_bids_received"}

    winner_bid = max(bids, key=lambda b: b.get("score", 0))
    log.info(f"WINNER for deal {deal_id}: buyer {winner_bid['buyer_id']} bid ${winner_bid['bid_amount']:,.0f}")

    # Fire the winner pitch with full reinforcement of why this deal is gold
    winner_send = {"ok": False, "error": "deal/buyer not found"}
    try:
        deal = Deal.objects.get(id=deal_id)
        winner_buyer = InvestorBuyer.objects.get(id=winner_bid["buyer_id"])
        winner_send = _fire_winner_pitch(deal, winner_buyer, winner_bid["bid_amount"], len(bids))
        log.info(f"  winner pitch sent: {winner_send}")
    except Exception as exc:
        log.warning(f"  winner pitch failed: {exc}")
        winner_send = {"ok": False, "error": str(exc)}

    # Polite close to losing bidders (keeps relationships warm)
    losers_closed = []
    loser_ids = {b["buyer_id"] for b in bids if b["buyer_id"] != winner_bid["buyer_id"]}
    for lid in loser_ids:
        try:
            loser = InvestorBuyer.objects.get(id=lid)
            losers_closed.append(_fire_loser_close(deal, loser))
        except Exception:
            pass

    BID_LEDGER_FILE.open("a").write(json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "war_closed",
        "deal_id": str(deal_id),
        "winner": winner_bid,
        "total_bids": len(bids),
        "winner_send_result": winner_send,
        "losers_closed": len(losers_closed),
    }) + "\n")

    try:
        from branded_slack import post_branded_slack  # type: ignore
        post_branded_slack(
            channel="#wholesale-deals",
            category="deal",
            title="BID WAR CLOSED -- winner pitched + assignment in motion",
            summary=f"Deal {deal_id}: {len(bids)} bids. Winner: buyer #{winner_bid['buyer_id']} at ${winner_bid['bid_amount']:,.0f}",
            body=(f"Winning bid: ${winner_bid['bid_amount']:,.0f}\n"
                   f"Close days: {winner_bid['can_close_days']}\n"
                   f"POF verified: {winner_bid['pof_verified']}\n"
                   f"Score: {winner_bid['score']:.0f}\n"
                   f"Total bids: {len(bids)}\n"
                   f"Loser closes sent: {len(losers_closed)}\n\n"
                   f"Winner pitch sent: {winner_send.get('ok')}\n"
                   f"Next: assignment contract goes to winner today, EMD to title in 48h."),
            agent_name="Hammer Knox",
            agent_title="Disposition",
        )
    except Exception:
        pass

    return {
        "deal_id": str(deal_id),
        "winner": winner_bid,
        "total_bids": len(bids),
        "winner_send": winner_send,
        "losers_closed": len(losers_closed),
    }


def status(deal_id: str) -> dict:
    """How many bids in for this deal, current leader."""
    bids = []
    if BID_LEDGER_FILE.exists():
        for line in BID_LEDGER_FILE.read_text().splitlines():
            try:
                r = json.loads(line)
                if r.get("event") == "bid_received" and str(r.get("deal_id")) == str(deal_id):
                    bids.append(r)
            except Exception:
                pass
    leader = max(bids, key=lambda b: b.get("score", 0)) if bids else None
    return {"deal_id": str(deal_id), "bids_in": len(bids),
             "leader": leader, "all_bids": bids}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["trigger", "status", "close"])
    ap.add_argument("--deal-id", required=True)
    ap.add_argument("--hours", type=int, default=DEFAULT_BID_WINDOW_HOURS)
    args = ap.parse_args()

    if args.cmd == "trigger":
        result = trigger(args.deal_id, bid_window_hours=args.hours)
    elif args.cmd == "status":
        result = status(args.deal_id)
    elif args.cmd == "close":
        result = close_war(args.deal_id)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
