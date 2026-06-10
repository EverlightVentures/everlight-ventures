"""services_closeout -- Deal close-out tracker.

Closes the 13-step wholesale flow gaps #11 (title clears), #12 (close), and
#13 (wire received) into ONE observable + auto-reconciling system.

Trigger
-------
A Deal advances past `payment_handoff_approved` (DealEvent type). From that
point this module owns the rails:

  payment_handoff_approved
       -> psa_signed
       -> emd_received
       -> title_search_ordered
       -> title_clear
       -> closing_scheduled
       -> closed
       -> wired

Every transition is recorded as an immutable DealEvent. Stage advancement on
the Deal model rides the existing `stage` enum, with the new logical states
overlaid via DealEvent rows + boolean/timestamp fields already on Deal:

  emd_received_at         -> emd_received
  title_search_ordered_at -> title_search_ordered
  title_clear (bool)      -> title_clear
  Deal.stage = "closing"  -> closing_scheduled
  Deal.stage = "closed_won" + closed_at -> closed
  CommissionRecord(record_type="earned", deal=...) -> wired

Public surface
--------------
    advance_stage(deal, target, *, agent="Backend Hand", detail="", metadata=None)
    poll_title_status(deal)            -- stub, fail-soft, returns dict
    reconcile_wire(deal_id, amount, wire_date, *, agent, reference="", source="manual")
    walk_open_deals_and_progress()     -- timer entrypoint
    nudge_stale_deals(threshold_days=7) -- Slack ping for stuck stages

Branded Slack
-------------
On `wired` we fire a celebratory branded post to #ceo-brief in the same
gold-and-Playfair Block Kit style as the payment_handoff card. Stale-stage
nudges go to #ft-consult as ops pings (lower volume, ops audience).
"""

from __future__ import annotations

import logging
import os
import sys
import traceback
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.db import transaction
from django.utils import timezone

# Allow importing content_tools.* from /home/opc on Oracle
for d in ("/home/opc",):
    if d not in sys.path and Path(d).exists():
        sys.path.insert(0, d)

try:
    from content_tools.branded_slack import post_branded_slack  # type: ignore
except Exception:  # pragma: no cover -- branded_slack always present in prod
    post_branded_slack = None  # type: ignore

from broker_ops.models import CommissionRecord, Deal, DealEvent

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Logical close-out stages -- overlaid on top of Deal.stage + flag fields.
# ---------------------------------------------------------------------------

CLOSEOUT_STAGES = (
    "psa_signed",
    "emd_received",
    "title_search_ordered",
    "title_clear",
    "closing_scheduled",
    "closed",
    "wired",
)

# Map each logical close-out stage to (deal field setters, deal.stage update).
# A None deal_stage means we keep the existing Deal.stage; we only stamp the
# audit field + emit a DealEvent.
_STAGE_HANDLERS: dict[str, dict[str, Any]] = {
    "psa_signed": {
        "deal_stage": "signing",
        "field_sets": {},
    },
    "emd_received": {
        "deal_stage": "title_engaged",
        "field_sets": {"emd_status": "held"},
        "stamp_now": ("emd_received_at",),
    },
    "title_search_ordered": {
        "deal_stage": "title_engaged",
        "field_sets": {},
        "stamp_now": ("title_search_ordered_at",),
    },
    "title_clear": {
        "deal_stage": "closing",
        "field_sets": {"title_clear": True},
    },
    "closing_scheduled": {
        "deal_stage": "closing",
        "field_sets": {},
    },
    "closed": {
        "deal_stage": "closed_won",
        "field_sets": {},
        "stamp_now": ("closed_at",),
    },
    "wired": {
        # Stage stays closed_won; the DealEvent + CommissionRecord is the marker.
        "deal_stage": "closed_won",
        "field_sets": {},
    },
}


# ---------------------------------------------------------------------------
# Stage advancement
# ---------------------------------------------------------------------------

def advance_stage(
    deal: Deal,
    target: str,
    *,
    agent: str = "Backend Hand",
    detail: str = "",
    metadata: dict | None = None,
) -> DealEvent:
    """Advance a deal to a close-out stage. Idempotent per (deal, stage).

    Records a DealEvent of type `stage_change` with metadata.closeout_stage
    set to `target`. Updates Deal field flags + Deal.stage as appropriate.
    """
    if target not in CLOSEOUT_STAGES:
        raise ValueError(f"unknown close-out stage: {target}")

    md = dict(metadata or {})
    md["closeout_stage"] = target
    md["from_stage"] = deal.stage

    with transaction.atomic():
        # Idempotency: if the most recent stage_change for this deal is the
        # same target, skip the duplicate but return the existing event.
        existing = (DealEvent.objects
                    .filter(deal=deal, event_type="stage_change",
                            metadata__closeout_stage=target)
                    .order_by("-created_at")
                    .first())
        if existing:
            return existing

        handler = _STAGE_HANDLERS[target]
        for k, v in handler.get("field_sets", {}).items():
            setattr(deal, k, v)
        for f in handler.get("stamp_now", ()):
            if not getattr(deal, f, None):
                setattr(deal, f, timezone.now())
        new_stage = handler.get("deal_stage")
        if new_stage:
            deal.stage = new_stage
        deal.save()

        evt = DealEvent.objects.create(
            deal=deal,
            event_type="stage_change",
            title=f"Close-out stage advanced to {target}",
            detail=detail or f"{deal.stage} -- close-out checkpoint reached.",
            agent_name=agent,
            metadata=md,
        )
    return evt


# ---------------------------------------------------------------------------
# Title status polling -- STUB
# ---------------------------------------------------------------------------

def poll_title_status(deal: Deal) -> dict:
    """Stub. Returns {"ok": False, "configured": False, ...} when the title
    firm is not yet wired up. Real polling activates when we have an Ohio Real
    Title relationship (or equivalent).

    Fail-soft: never raises. Logs at INFO level when the firm isn't configured.
    """
    firm = (deal.title_company or "").strip()
    api_key = os.environ.get("TITLE_FIRM_API_KEY", "")
    if not firm or not api_key:
        log.info("title firm not yet configured for deal %s (firm=%r, api_key=%s)",
                 deal.id, firm, "set" if api_key else "unset")
        return {
            "ok": False,
            "configured": False,
            "reason": "title firm not yet configured.",
            "title_company": firm,
        }
    # When real polling is wired, dispatch by firm here:
    #   if firm.lower().startswith("ohio real"): return _poll_ohio_real(deal, api_key)
    log.info("title firm %s configured but no integration handler installed yet", firm)
    return {
        "ok": False,
        "configured": True,
        "reason": f"no handler for {firm} yet.",
        "title_company": firm,
    }


# ---------------------------------------------------------------------------
# Wire reconciliation
# ---------------------------------------------------------------------------

def reconcile_wire(
    deal_id: str,
    amount,
    wire_date,
    *,
    agent: str = "Backend Hand",
    reference: str = "",
    source: str = "manual",
) -> dict:
    """Match an inbound wire to a Deal, advance to `wired`, create a
    CommissionRecord row, and post the celebratory Slack card.

    `amount` and `wire_date` may be Decimal/str/datetime/str -- this fn
    coerces them. Returns a dict with the created records + Slack result.
    """
    try:
        deal = Deal.objects.select_related("lead").get(id=deal_id)
    except Deal.DoesNotExist:
        return {"ok": False, "error": "deal_not_found", "deal_id": str(deal_id)}

    try:
        amt = Decimal(str(amount))
    except Exception as exc:
        return {"ok": False, "error": f"bad_amount: {exc}"}

    expected = Decimal(str(deal.commission_due or 0))
    variance = amt - expected
    matched = abs(variance) <= Decimal("1.00")  # tolerate $1 fee/rounding

    # Advance through the closing rails so the event log tells the full story.
    if not deal.title_clear:
        advance_stage(deal, "title_clear", agent=agent,
                      detail="Auto-advanced via wire reconciliation.")
    advance_stage(deal, "closing_scheduled", agent=agent,
                  detail="Auto-advanced via wire reconciliation.")
    advance_stage(deal, "closed", agent=agent,
                  detail=f"Closed -- wire received {wire_date}.")
    wired_evt = advance_stage(
        deal, "wired", agent=agent,
        detail=(f"Wire received: ${amt} on {wire_date}. "
                f"Expected ${expected}. Variance ${variance}."),
        metadata={
            "amount": str(amt),
            "expected": str(expected),
            "variance": str(variance),
            "matched": matched,
            "wire_date": str(wire_date),
            "reference": reference,
            "source": source,
        },
    )

    # CommissionRecord -- the canonical "we got paid" row.
    rec = CommissionRecord.objects.create(
        deal=deal,
        record_type="earned",
        amount=amt,
        currency="USD",
        description=f"Wire received {wire_date}. Source: {source}.",
        reference=reference or f"wire-{deal.id}",
    )

    slack_res = _post_wired_slack(deal, amt, wire_date, expected, variance, matched)

    return {
        "ok": True,
        "deal_id": str(deal.id),
        "stage": deal.stage,
        "amount": str(amt),
        "expected": str(expected),
        "variance": str(variance),
        "matched": matched,
        "commission_id": str(rec.id),
        "event_id": str(wired_evt.id),
        "slack": getattr(slack_res, "__dict__", {"ok": False, "error": "no_branded_slack_module"}),
    }


def _post_wired_slack(deal, amt, wire_date, expected, variance, matched) -> Any:
    """Branded Block-Kit celebration to #ceo-brief. Gold theme, deal recap,
    variance flag if the wire didn't match expected to the dollar."""
    if post_branded_slack is None:
        return None

    lead = deal.lead
    addr = (getattr(lead, "address", "") or "address pending") if lead else "address pending"
    buyer = ((getattr(lead, "owner_name", "") or "buyer").strip() if lead else "buyer")

    headline = f"Wire received -- ${amt:,.2f}"
    summary = (f"Deal {str(deal.id)[:8]} closed. {addr}. "
               f"Buyer {buyer}. Commission earned and ledgered.")
    body_lines = [
        f"*Property:* {addr}",
        f"*Buyer:* {buyer}",
        f"*Wire amount:* ${amt:,.2f}",
        f"*Expected:* ${expected:,.2f}",
        f"*Variance:* ${variance:+,.2f}  ({'matched' if matched else 'CHECK'})",
        f"*Wire date:* {wire_date}",
        f"*Stage:* {deal.stage}",
    ]
    if not matched:
        body_lines.append("")
        body_lines.append(":warning: Variance exceeds $1.00 tolerance. Reconcile manually.")

    fields = {
        "Deal ID": str(deal.id)[:8],
        "Amount": f"${amt:,.2f}",
        "Expected": f"${expected:,.2f}",
        "Variance": f"${variance:+,.2f}",
        "Matched": "yes" if matched else "no",
    }

    try:
        return post_branded_slack(
            channel="#ceo-brief",
            title=headline,
            summary=summary,
            body="\n".join(body_lines),
            fields=fields,
            agent_name="Backend Hand",
            agent_title="Close-out Tracker",
            category="deal",
            fallback_text=f"Wire received ${amt:,.2f} on deal {str(deal.id)[:8]}",
        )
    except Exception as exc:  # pragma: no cover -- never block reconcile
        log.error("branded_slack post failed: %s\n%s", exc, traceback.format_exc())
        return None


# ---------------------------------------------------------------------------
# Timer entrypoint -- walks open deals, polls title, nudges stale stages
# ---------------------------------------------------------------------------

# Once a deal has crossed payment_handoff_approved, the close-out tracker owns it.
def _deals_in_closeout_window():
    """Open deals whose most recent DealEvent includes a handoff approval OR
    whose stage is already past `signing` (audit catch-all)."""
    candidate_stages = ("signing", "title_engaged", "closing", "closed_won")
    return (Deal.objects
            .filter(stage__in=candidate_stages)
            .exclude(stage="closed_lost")
            .select_related("lead"))


def walk_open_deals_and_progress(*, dry_run: bool = False) -> dict:
    """Hourly timer entry. Polls title firm for each open deal, records a
    DealEvent if anything moved, and triggers stale nudges.
    """
    walked = 0
    polled = 0
    title_clear_advances = 0
    nudges = 0
    errors: list[str] = []

    for deal in _deals_in_closeout_window():
        walked += 1
        try:
            res = poll_title_status(deal)
            polled += 1
            if res.get("ok") and res.get("title_clear") and not deal.title_clear:
                if not dry_run:
                    advance_stage(deal, "title_clear",
                                  agent="Backend Hand",
                                  detail="Title firm reported clear via poll.",
                                  metadata={"poll_result": res})
                title_clear_advances += 1
        except Exception as exc:  # pragma: no cover -- never crash the timer
            errors.append(f"{deal.id}: {exc}")
            log.error("walk_open_deals error on %s: %s\n%s",
                      deal.id, exc, traceback.format_exc())

    nudges = nudge_stale_deals(dry_run=dry_run)

    summary = {
        "walked": walked,
        "polled": polled,
        "title_clear_advances": title_clear_advances,
        "stale_nudges": nudges,
        "errors": errors,
        "dry_run": dry_run,
        "ts": timezone.now().isoformat(),
    }
    log.info("close-out walk complete: %s", summary)
    return summary


def nudge_stale_deals(threshold_days: int = 7, *, dry_run: bool = False) -> int:
    """Find deals stuck in title_search_ordered for > threshold_days and ping
    Slack so a human can chase the title firm.

    Returns count of nudges fired.
    """
    cutoff = timezone.now() - timedelta(days=threshold_days)
    fired = 0

    stuck = (Deal.objects
             .filter(stage__in=("title_engaged", "closing"))
             .filter(title_search_ordered_at__lte=cutoff)
             .filter(title_clear=False)
             .exclude(stage="closed_lost"))

    for deal in stuck:
        # Skip if a nudge for this stale window has already gone out today.
        already = (DealEvent.objects
                   .filter(deal=deal,
                           event_type="note",
                           metadata__nudge_kind="title_stale",
                           created_at__gte=timezone.now() - timedelta(hours=24))
                   .exists())
        if already:
            continue

        if dry_run:
            fired += 1
            continue

        days_in = (timezone.now() - deal.title_search_ordered_at).days
        DealEvent.objects.create(
            deal=deal,
            event_type="note",
            title=f"Title search stale ({days_in}d).",
            detail=("Title search ordered but not clear. "
                    "Title firm may need a chase."),
            agent_name="Backend Hand",
            metadata={"nudge_kind": "title_stale", "days_in": days_in},
        )

        if post_branded_slack is not None:
            try:
                post_branded_slack(
                    channel="#ft-consult",
                    title=f"Title search stale -- {days_in}d in",
                    summary=(f"Deal {str(deal.id)[:8]} has been in title search "
                             f"for {days_in} days with no movement."),
                    body=("Chase the title firm. If the firm is unresponsive, "
                          "consider reassigning to a backup."),
                    fields={
                        "Deal": str(deal.id)[:8],
                        "Stage": deal.stage,
                        "Days stale": str(days_in),
                        "Title firm": deal.title_company or "(unset)",
                    },
                    agent_name="Backend Hand",
                    agent_title="Close-out Tracker",
                    category="alert",
                    fallback_text=f"Title stale on deal {str(deal.id)[:8]}",
                )
            except Exception as exc:  # pragma: no cover
                log.error("nudge slack post failed: %s", exc)
        fired += 1
    return fired
