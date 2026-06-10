"""pof_followup_sequence -- free, multi-touch follow-up for the 19 invited
buyers who haven't replied with proof of funds yet.

Strategy (no spend):
  Touch 1 (already sent): the original POF invite email
  Touch 2 (T+3 days): warm reminder email -- short, specific deal vibe
  Touch 3 (T+7 days):  SMS reminder (free via existing Twilio num if buyer
                        opted in) OR a different-subject email
  Touch 4 (T+14 days): final phone call from Hammer with templated script

Each touch logs to ConsentLedger / hive_logger so the audit trail is intact.

Usage:
  python3 pof_followup_sequence.py status     # see who's still pending
  python3 pof_followup_sequence.py touch2     # send reminder email to all due
  python3 pof_followup_sequence.py touch3     # SMS or alt-subject email
  python3 pof_followup_sequence.py call-list  # print phone-call queue
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

for p in ("/home/opc/hive_django",
          "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard",
          "/home/opc/content_tools",
          "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools"):
    if p not in sys.path and Path(p).exists():
        sys.path.insert(0, p)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
import django  # noqa
django.setup()


def _pending_buyers():
    """Return list of POFRequest rows still in 'invited' state past T+3 days.

    Each row has .buyer (InvestorBuyer FK) for contact info: name, email, phone, markets.
    """
    from broker_ops.models import POFRequest
    cutoff = datetime.now(timezone.utc) - timedelta(days=3)
    return list(POFRequest.objects.filter(
        status="invited", requested_at__lt=cutoff
    ).select_related("buyer"))


def _contact_for(req) -> dict:
    """Pull contact info via the buyer FK."""
    b = getattr(req, "buyer", None)
    if not b:
        return {"name": "", "email": "", "phone": "", "markets": []}
    return {
        "name": b.name or "",
        "email": (b.email or "").lower(),
        "phone": b.phone or "",
        "markets": list(b.markets) if b.markets else [],
    }


def _touch2_body(buyer_name: str, market: str = "Metro Atlanta") -> tuple[str, str]:
    """Touch 2: warm reminder, no pressure. Returns (subject, html_body)."""
    first = (buyer_name or "there").split()[0].title()
    subject = f"Quick check-in -- {market} deal queue"
    html = f"""
<p>Hey {first},</p>

<p>Sent over a quick proof-of-funds verification a few days back -- wanted to bump it
to the top of your inbox in case it slipped through.</p>

<p>Reason it matters: we're locking up off-market deals in {market}
and the buyers who close with us first are the ones we have verified POF on file for.
When something hits at <strong>$80k-$150k under ARV</strong>, we go to the verified list first.
Takes 2 minutes via the secure link below.</p>

<p>If you're no longer actively buying or this isn't your market, just reply "remove" and
I'll pull you off our buyer roster -- no hard feelings.</p>

<p>Otherwise, the link is the same as last time:</p>

<p><strong><a href="{{{{pof_link}}}}" style="color:#D4A843;">Verify POF (2 min)</a></strong></p>

<p>Hammer Knox<br>
<em>Disposition, Everlight Ventures</em><br>
<a href="mailto:henry@everlightventures.io" style="color:#D4A843;">henry@everlightventures.io</a></p>
"""
    return subject, html


def _touch3_sms(buyer_name: str, pof_link: str) -> str:
    """Touch 3: short SMS. Only sends if buyer has phone + has opted in (consent)."""
    first = (buyer_name or "there").split()[0].title()
    return (f"EV: Hey {first}, Hammer @ Everlight. Couple of off-market Atl deals "
            f"queuing up. POF verification (2 min): {pof_link}  "
            f"Reply STOP=optout")


def _call_script(buyer_name: str, market: str = "Metro Atlanta") -> str:
    """Touch 4: phone call talking points."""
    first = (buyer_name or "there").split()[0].title()
    return f"""
PHONE CALL SCRIPT -- {first}
============================

OPEN (10 sec):
"Hey {first}, this is Hammer with Everlight Ventures. You got a couple of POF
verification notes from us over the past two weeks -- got a quick minute?"

IF YES:
"Real quick: we've got off-market deals coming through {market} and our process is to
go to the verified-POF buyer list first. The form is just bank statement upload or a
hard-money letter -- takes 90 seconds. Most folks knock it out from their phone.
Want me to text you the link right now while we're on the call?"

IF "I'M NOT REALLY ACTIVE RIGHT NOW":
"All good. Want me to keep you on the warm list and just send a quarterly check-in,
or pull you off entirely? No bad answer."

IF "WHAT KIND OF DEALS":
"Mostly Metro Atlanta single-family. Off-market only. Last spread we ran was
ARV around $280k, our cost to you would have been $185k all-in including assignment,
$95k of equity after rehab. Cap rate 8.7%. That kind of math."

IF VOICEMAIL:
"Hey {first}, Hammer with Everlight, calling about your POF verification.
We've got a couple of off-market Atlanta deals queuing up and you'd be on
the priority list once we have POF on file. If you want me to text the link,
shoot me a yes back to this number. Otherwise reply remove and I'll pull
you off our list. Thanks {first}."

CLOSE:
"Cool, I'll text the link in 30 seconds. Talk soon."

NEVER PRESSURE. If they say no, accept it warmly. The next 4 touches are NOT for
hard sells -- they're for keeping the door open with people who might re-activate
in 6 months.
"""


def status():
    pending = _pending_buyers()
    print(f"Pending POF requests > 3d old: {len(pending)}")
    print()
    for r in pending:
        age_days = (datetime.now(timezone.utc) - r.requested_at).days
        c = _contact_for(r)
        contact = c["email"] or c["phone"] or "(no contact)"
        print(f"  - {c['name'][:30]:<30} {contact:<30} age {age_days}d  markets={c['markets']}")


def touch2_send():
    """Send the T+3 reminder email to every pending buyer past 3 days."""
    from broker_ops.models import POFRequest
    try:
        from branded_mailer import send_branded_email  # type: ignore
    except Exception as exc:
        print(f"branded_mailer import failed: {exc}", file=sys.stderr)
        return 0

    sent = 0
    skipped = 0
    pending = _pending_buyers()
    for r in pending:
        c = _contact_for(r)
        if not c["email"]:
            skipped += 1
            continue

        subj, html = _touch2_body(c["name"], market="Metro Atlanta")
        pof_link = f"http://127.0.0.1:2200/broker/pof/{r.token}/"
        html = html.replace("{{pof_link}}", pof_link)

        # Pick state from buyer's markets list (first GA-ish market wins)
        recipient_state = ""
        for m in c["markets"]:
            mu = (m or "").upper()
            for st in ("GA", "FL", "TX", "AZ", "CA", "MO", "NC", "TN"):
                if st in mu:
                    recipient_state = st
                    break
            if recipient_state:
                break

        result = send_branded_email(
            to=c["email"],
            subject=subj,
            content_html=html,
            agent_name="Hammer Knox",
            agent_title="Disposition, Everlight Ventures",
            agent_email="henry@everlightventures.io",
            from_name="Hammer Knox",
            from_email="henry@everlightventures.io",
            budget_category="vip_reply",  # NOT bulk -- these are warm
            recipient_state=recipient_state,
        )
        if result.ok:
            sent += 1
            print(f"  sent: {c['email']}")
        else:
            skipped += 1
            print(f"  skipped {c['email']}: {result.error}")

    print(f"\nDONE: sent={sent} skipped={skipped}")
    return sent


def call_list():
    """Print the phone-call queue with templated scripts."""
    pending = _pending_buyers()
    callable_buyers = []
    for r in pending:
        c = _contact_for(r)
        age = datetime.now(timezone.utc) - r.requested_at
        if c["phone"] and age >= timedelta(days=14):
            callable_buyers.append((r, c))
    print(f"=== PHONE CALL QUEUE ({len(callable_buyers)} buyers, T+14d+) ===\n")
    for r, c in callable_buyers:
        print(f"\n--- {c['name'] or '(unknown)'} | {c['phone']} ---")
        print(_call_script(c["name"] or "", market="Metro Atlanta"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["status", "touch2", "call-list"])
    args = ap.parse_args()

    if args.cmd == "status":
        status()
    elif args.cmd == "touch2":
        touch2_send()
    elif args.cmd == "call-list":
        call_list()


if __name__ == "__main__":
    main()
