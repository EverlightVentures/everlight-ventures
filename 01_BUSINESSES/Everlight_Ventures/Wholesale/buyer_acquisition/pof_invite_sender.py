"""pof_invite_sender -- send branded POF request emails to all active buyers
that don't have a current proof-of-funds on file.

Why
---
Buyers without verified POF cannot reliably close. Industry best practice:
require POF (bank letter, lender pre-approval, or transactional funder
commitment) less than 90 days old before sending them deal dispo.

Run after every buyer-list expansion sweep, and quarterly to refresh.
"""
from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

for sub in (
    "/home/opc/hive_django",
    "/home/opc/content_tools",
):
    if sub not in sys.path and Path(sub).exists():
        sys.path.insert(0, sub)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
import django  # noqa: E402
django.setup()

from broker_ops.models import InvestorBuyer, POFRequest  # noqa: E402
from branded_mailer import send_branded_email  # noqa: E402


PUBLIC_BASE = os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:2200")


POF_EMAIL_HTML = """
<p>Hi {first_name},</p>

<p>Hammer here at Everlight Ventures. Quick housekeeping note.</p>

<p>We're tightening up our buyer list this quarter so when an off-market
deal lands, we know we're sending it to operators who can actually close.
That means we need a current proof-of-funds letter on file for every
buyer -- yours included.</p>

<p><strong>What we need:</strong></p>
<ul>
<li>Bank letter, brokerage statement, or lender pre-approval</li>
<li>Dated within the last 90 days</li>
<li>Showing access to at least your typical purchase price range</li>
</ul>

<p>Easiest way: <a href="{upload_url}">click here to upload</a>.
Takes about 60 seconds.</p>

<p>Once you're verified, you stay on the priority list -- first look on
every off-market deal in your criteria with a 24-hour exclusive window
before it goes wider.</p>

<p>If you don't have a fresh letter handy, ask your lender or banker for
"a proof-of-funds for real estate purchases" -- they get this request all
the time and can usually email one over the same day.</p>

<p>Thanks for keeping things clean on your end.</p>

<p>Hammer Knox<br>
<em>Disposition, Everlight Ventures</em></p>
"""


def main(limit: int = 50, dry_run: bool = False) -> int:
    # Buyers who are active+cash but proof_of_funds is False
    qs = InvestorBuyer.objects.filter(
        is_active=True, cash_buyer=True, proof_of_funds=False,
    ).exclude(email="").order_by("-deals_closed", "name")[:limit]

    sent = 0
    skipped = 0
    for buyer in qs:
        # Skip if a recent POFRequest already exists in invited / submitted
        existing = POFRequest.objects.filter(
            buyer=buyer, status__in=["invited", "submitted"],
        ).first()
        if existing and not dry_run:
            skipped += 1
            continue

        token = secrets.token_urlsafe(24)
        first_name = (buyer.name or "").split()[0] or "there"
        upload_url = f"{PUBLIC_BASE}/pof/upload/{token}/"

        if dry_run:
            print(f"[DRY] Would invite {buyer.name} <{buyer.email}> -> {upload_url}")
            sent += 1
            continue

        # Create the request row first so the upload page can lookup the token
        POFRequest.objects.create(
            buyer=buyer, token=token, status="invited",
        )

        body = POF_EMAIL_HTML.format(first_name=first_name, upload_url=upload_url)
        result = send_branded_email(
            to=buyer.email,
            subject="Quick proof-of-funds note -- 60 seconds",
            content_html=body,
            title="Proof of Funds -- Everlight Ventures Buyer List",
            from_name="Hammer Knox",
            from_email="henry@everlightventures.io",
            agent_name="Hammer Knox",
            agent_title="Disposition Lead",
            agent_email="henry@everlightventures.io",
            budget_category="vip_reply",  # warm B2B comms, not bulk
        )
        if result.ok:
            sent += 1
        else:
            print(f"  send failed for {buyer.email}: {result.error}")

    print(f"sent={sent} skipped={skipped} dry_run={dry_run}")
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.exit(main(args.limit, args.dry_run))
