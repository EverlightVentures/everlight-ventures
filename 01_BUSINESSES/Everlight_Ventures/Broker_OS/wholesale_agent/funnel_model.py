"""
funnel_model.py -- reverse-engineer the wholesale email funnel.

Answers two questions:
  1. REVERSE: "To close N deals/month, how many emails/day + addresses/day?"
  2. FORWARD: "If I send E emails/day, how many deals/month should I expect?"

Built on conservative cold-email benchmarks NOW. As real outcomes accrue in
performance_metrics.json + leads_db, `actual_rates()` recomputes the live
conversion rates so the model calibrates itself off truth instead of guesses.
This is the metric brain: it tells the harvester how hard to run.

Free-first by design -- pure arithmetic, zero paid dependency.

Usage:
    python3 funnel_model.py --target-deals 1            # reverse: 1 deal/month
    python3 funnel_model.py --emails-per-day 50         # forward projection
    python3 funnel_model.py --target-deals 1 --preset distressed
    python3 funnel_model.py --actuals                   # use live rates if enough data
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
METRICS = HERE / "data" / "workbooks" / "performance_metrics.json"
LEADS = HERE / "leads_db.json"

# Minimum real events before we trust an actual rate over the benchmark.
_MIN_SAMPLE = 30


@dataclass
class FunnelRates:
    """Stage conversion rates. Defaults = conservative cold benchmarks."""
    email_found: float = 0.12     # address -> send-grade email (free OSINT, score >=75)
    deliverability: float = 0.92  # verified email -> actually delivered
    reply: float = 0.03           # delivered -> any reply (the big lever; targeting moves it)
    conversation: float = 0.40    # reply -> real seller conversation
    contract: float = 0.15        # conversation -> under contract
    close: float = 0.60           # under contract -> closed / assigned to buyer

    def per_email_close(self) -> float:
        """Probability one SENT email becomes a closed deal."""
        return (self.deliverability * self.reply * self.conversation
                * self.contract * self.close)

    def per_address_close(self) -> float:
        """Probability one HARVESTED address becomes a closed deal."""
        return self.email_found * self.per_email_close()


# Scenario presets -- only the reply rate really moves with targeting quality.
PRESETS = {
    "cold": FunnelRates(),                       # random homeowners
    "distressed": FunnelRates(reply=0.06),       # pre-foreclosure / code violations
    "tax_delinquent": FunnelRates(reply=0.10, email_found=0.15),  # highest motivation
}


def reverse(target_deals_per_month: float, rates: FunnelRates, days: int = 30) -> dict:
    """How many emails/day + addresses/day to hit the deal target."""
    pec = rates.per_email_close()
    pac = rates.per_address_close()
    emails_needed = (target_deals_per_month / pec) if pec else float("inf")
    addresses_needed = (target_deals_per_month / pac) if pac else float("inf")
    return {
        "target_deals_per_month": target_deals_per_month,
        "emails_per_deal": round(1 / pec) if pec else None,
        "addresses_per_deal": round(1 / pac) if pac else None,
        "emails_per_month": round(emails_needed),
        "emails_per_day": round(emails_needed / days),
        "addresses_per_month": round(addresses_needed),
        "addresses_per_day": round(addresses_needed / days),
    }


def forward(emails_per_day: float, rates: FunnelRates, days: int = 30) -> dict:
    """Given a daily send volume, expected monthly outcomes at each stage."""
    sent = emails_per_day * days
    delivered = sent * rates.deliverability
    replies = delivered * rates.reply
    conversations = replies * rates.conversation
    contracts = conversations * rates.contract
    closes = contracts * rates.close
    return {
        "emails_per_day": emails_per_day,
        "emails_per_month": round(sent),
        "delivered": round(delivered),
        "replies": round(replies, 1),
        "conversations": round(conversations, 1),
        "contracts_per_month": round(contracts, 2),
        "closes_per_month": round(closes, 2),
        "addresses_per_day_to_feed": round(emails_per_day / rates.email_found) if rates.email_found else None,
    }


def actual_rates(base: FunnelRates | None = None) -> tuple[FunnelRates, dict]:
    """Blend live data over the benchmark: each stage rate is replaced by the
    measured rate ONLY when we have >= _MIN_SAMPLE real events for it. Returns
    (rates, provenance) where provenance says benchmark-vs-measured per stage.
    The model gets more honest the more we run -- truth replaces guesses.
    """
    base = base or FunnelRates()
    prov = {k: "benchmark" for k in asdict(base)}
    try:
        leads = json.loads(LEADS.read_text())
        leads = leads if isinstance(leads, list) else list(leads.values())
        leads = [l for l in leads if isinstance(l, dict)]
    except Exception:
        return base, prov
    from collections import Counter
    st = Counter(str(l.get("status", "")).lower() for l in leads)
    sent = st.get("contacted", 0) + st.get("engaged", 0) + st.get("under_contract", 0) + st.get("closed", 0)
    replied = st.get("engaged", 0) + st.get("under_contract", 0) + st.get("closed", 0)
    contracted = st.get("under_contract", 0) + st.get("closed", 0)
    closed = st.get("closed", 0)
    out = FunnelRates(**asdict(base))
    if sent >= _MIN_SAMPLE and replied >= 0:
        out.reply = round(replied / sent, 4) if sent else base.reply
        prov["reply"] = f"measured(n={sent})"
    if replied >= _MIN_SAMPLE:
        out.contract = round(contracted / replied, 4) if replied else base.contract
        prov["contract"] = f"measured(n={replied})"
    if contracted >= _MIN_SAMPLE:
        out.close = round(closed / contracted, 4) if contracted else base.close
        prov["close"] = f"measured(n={contracted})"
    return out, prov


def main() -> None:
    ap = argparse.ArgumentParser(description="Wholesale email funnel calculator")
    ap.add_argument("--target-deals", type=float, help="deals/month to reverse-engineer")
    ap.add_argument("--emails-per-day", type=float, help="forward projection from a send volume")
    ap.add_argument("--preset", choices=list(PRESETS), default="cold")
    ap.add_argument("--actuals", action="store_true", help="use live measured rates where available")
    args = ap.parse_args()

    rates = PRESETS[args.preset]
    note = f"preset={args.preset}"
    if args.actuals:
        rates, prov = actual_rates(rates)
        note = f"actuals-blended ({', '.join(f'{k}:{v}' for k, v in prov.items() if 'measured' in v) or 'no stage had enough data yet -- all benchmark'})"

    print(json.dumps({"rates": asdict(rates), "basis": note}, indent=2))
    if args.target_deals:
        print("REVERSE:", json.dumps(reverse(args.target_deals, rates), indent=2))
    if args.emails_per_day:
        print("FORWARD:", json.dumps(forward(args.emails_per_day, rates), indent=2))
    if not args.target_deals and not args.emails_per_day:
        print("REVERSE (1 deal/mo):", json.dumps(reverse(1, rates), indent=2))


if __name__ == "__main__":
    main()
