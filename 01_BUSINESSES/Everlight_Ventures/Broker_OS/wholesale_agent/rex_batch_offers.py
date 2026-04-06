"""
Rex Batch Offers -- Reads pipeline leads, underwrites them, generates offer
letters, and sends via Resend API from piper@everlightventures.io.

Part of the Everlight Ventures wholesale pipeline.
Agents: Rex Blackwell (scouting), Penny Voss (underwriting), Piper Reeves (outreach).

Rate limits: max 50 offers/day. Deduplication by address. Full logging.

Usage:
    python rex_batch_offers.py                    # Process all available leads
    python rex_batch_offers.py --dry-run          # Preview without sending
    python rex_batch_offers.py --max 10           # Send at most 10
    python rex_batch_offers.py --file data/apify_leads.json
"""

import os
import json
import sys
import time
import logging
import argparse
import hashlib
from pathlib import Path
from datetime import datetime, timezone

import requests

from creative_finance_engine import underwrite_property

log = logging.getLogger("rex_batch_offers")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_URL = "https://api.resend.com/emails"
FROM_EMAIL = "piper@everlightventures.io"
FROM_NAME = "Piper Reeves | Everlight Ventures"
REPLY_TO = "acquisitions@everlightventures.io"

DATA_DIR = Path(__file__).parent / "data"
OFFERS_SENT_FILE = DATA_DIR / "offers_sent.json"

MAX_OFFERS_PER_DAY = 50
SEND_DELAY_SECONDS = 3  # Delay between sends to avoid rate limits

# Lead file search order
LEAD_FILES = [
    DATA_DIR / "apify_leads.json",
    DATA_DIR / "surplus_leads.json",
    Path(__file__).parent / "pipeline" / "surplus_leads.json",
]


# ---------------------------------------------------------------------------
# Tracking / deduplication
# ---------------------------------------------------------------------------

def load_sent_offers() -> dict:
    """Load the offers_sent.json tracking file."""
    if OFFERS_SENT_FILE.exists():
        try:
            with open(OFFERS_SENT_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            log.warning("Corrupt offers_sent.json -- starting fresh")
    return {"sent": [], "addresses_sent": [], "daily_counts": {}}


def save_sent_offers(tracker: dict):
    """Save the offers_sent.json tracking file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OFFERS_SENT_FILE, "w") as f:
        json.dump(tracker, f, indent=2, default=str)


def address_hash(address: str) -> str:
    """Normalize and hash an address for deduplication."""
    normalized = address.lower().strip().replace(",", "").replace(".", "")
    return hashlib.md5(normalized.encode()).hexdigest()


def get_today_key() -> str:
    """Return today's date string for daily count tracking."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def daily_sends_remaining(tracker: dict) -> int:
    """How many more offers can we send today."""
    today = get_today_key()
    sent_today = tracker.get("daily_counts", {}).get(today, 0)
    return max(0, MAX_OFFERS_PER_DAY - sent_today)


# ---------------------------------------------------------------------------
# Email sending via Resend
# ---------------------------------------------------------------------------

def send_offer_email(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
) -> dict:
    """Send an offer email via Resend API.

    Returns dict with send status and message_id.
    """
    if not RESEND_API_KEY:
        log.error("No RESEND_API_KEY set -- cannot send emails")
        return {"success": False, "error": "No API key"}

    payload = {
        "from": f"{FROM_NAME} <{FROM_EMAIL}>",
        "to": [to_email],
        "reply_to": REPLY_TO,
        "subject": subject,
        "text": body_text,
    }
    if body_html:
        payload["html"] = body_html

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        r = requests.post(RESEND_URL, headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        data = r.json()
        return {"success": True, "message_id": data.get("id", ""), "status_code": r.status_code}
    except requests.RequestException as exc:
        log.error("Failed to send email to %s: %s", to_email, exc)
        return {"success": False, "error": str(exc)}


def text_to_html(text: str) -> str:
    """Convert plain text offer letter to basic HTML."""
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    paragraphs = escaped.split("\n\n")
    html_parts = []
    for p in paragraphs:
        lines = p.replace("\n", "<br>\n")
        html_parts.append(f"<p>{lines}</p>")
    return f"""<!DOCTYPE html>
<html>
<head><style>
body {{ font-family: Georgia, serif; max-width: 700px; margin: 40px auto; padding: 20px; color: #333; line-height: 1.6; }}
p {{ margin-bottom: 1em; }}
</style></head>
<body>
{''.join(html_parts)}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Lead loading
# ---------------------------------------------------------------------------

def find_leads_file(override: str | None = None) -> Path | None:
    """Find the first available leads file."""
    if override:
        p = Path(override)
        if p.exists():
            return p
        log.error("Specified leads file not found: %s", p)
        return None

    for f in LEAD_FILES:
        if f.exists():
            log.info("Found leads file: %s", f)
            return f

    log.error("No leads file found. Run apify_lead_wrapper.py first or provide --file")
    return None


def load_leads(leads_path: Path) -> list[dict]:
    """Load and parse leads from a JSON file."""
    with open(leads_path) as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "leads" in data:
        return data["leads"]

    log.error("Unexpected format in %s", leads_path)
    return []


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_batch(
    leads_file: str | None = None,
    max_offers: int | None = None,
    dry_run: bool = False,
    offer_type: str = "subject_to",
) -> dict:
    """Run the full batch offer pipeline.

    Args:
        leads_file: Path to leads JSON (auto-detected if None)
        max_offers: Override max offers to send
        dry_run: If True, generate but don't send
        offer_type: Which offer to send: subject_to, owner_finance, lease_option

    Returns:
        Summary dict with counts and errors.
    """
    tracker = load_sent_offers()
    remaining = daily_sends_remaining(tracker)

    if remaining <= 0 and not dry_run:
        log.warning("Daily send limit reached (%d). Try again tomorrow.", MAX_OFFERS_PER_DAY)
        return {"sent": 0, "error": "daily_limit_reached"}

    leads_path = find_leads_file(leads_file)
    if not leads_path:
        return {"sent": 0, "error": "no_leads_file"}

    leads = load_leads(leads_path)
    if not leads:
        log.warning("No leads found in %s", leads_path)
        return {"sent": 0, "error": "no_leads"}

    log.info("Loaded %d leads from %s", len(leads), leads_path)

    # Determine send cap
    cap = min(
        max_offers or MAX_OFFERS_PER_DAY,
        remaining if not dry_run else 9999,
        len(leads),
    )

    sent_count = 0
    skipped_count = 0
    error_count = 0
    results = []

    for lead in leads:
        if sent_count >= cap:
            break

        address = lead.get("address", "")
        if not address:
            skipped_count += 1
            continue

        # Deduplication
        ahash = address_hash(address)
        if ahash in tracker.get("addresses_sent", []):
            log.debug("Skipping (already sent): %s", address)
            skipped_count += 1
            continue

        # Underwrite
        price = lead.get("price", 0)
        if not price or price <= 0:
            skipped_count += 1
            continue

        arv = lead.get("arv", round(price * 1.30, 2))
        rental = lead.get("rental_estimate", 0)

        underwrites = underwrite_property(
            address=address,
            assessed_value=price,
            arv=arv,
            rental_estimate=rental,
            city=lead.get("city", ""),
            state=lead.get("state", ""),
        )

        if "error" in underwrites:
            error_count += 1
            continue

        # Get the selected offer
        offer = underwrites["offers"].get(offer_type)
        if not offer:
            offer = underwrites["offers"].get(underwrites["best_offer"])

        letter = offer.get("letter", "")
        if not letter:
            error_count += 1
            continue

        subject = f"Cash Offer for {address}"

        # Determine recipient email (from lead data or skip)
        to_email = lead.get("email", lead.get("owner_email", ""))

        if dry_run:
            log.info("[DRY RUN] Would send %s offer to %s for %s", offer_type, to_email or "NO_EMAIL", address)
            results.append({
                "address": address,
                "offer_type": offer_type,
                "to_email": to_email,
                "status": "dry_run",
                "terms": offer["terms"],
            })
            sent_count += 1
            continue

        if not to_email:
            log.debug("No email for %s -- skipping send (offer still generated)", address)
            # Still track the underwriting
            results.append({
                "address": address,
                "offer_type": offer_type,
                "to_email": "",
                "status": "no_email",
                "terms": offer["terms"],
            })
            skipped_count += 1
            continue

        # Send
        html_body = text_to_html(letter)
        send_result = send_offer_email(to_email, subject, letter, html_body)

        record = {
            "address": address,
            "address_hash": ahash,
            "offer_type": offer_type,
            "to_email": to_email,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "send_result": send_result,
            "terms": offer["terms"],
        }
        results.append(record)

        if send_result.get("success"):
            sent_count += 1
            tracker.setdefault("sent", []).append(record)
            tracker.setdefault("addresses_sent", []).append(ahash)
            today = get_today_key()
            tracker.setdefault("daily_counts", {})[today] = tracker["daily_counts"].get(today, 0) + 1
            log.info("Sent %s offer to %s for %s", offer_type, to_email, address)
            time.sleep(SEND_DELAY_SECONDS)
        else:
            error_count += 1
            log.error("Failed to send to %s: %s", to_email, send_result.get("error"))

    # Save tracker
    save_sent_offers(tracker)

    # Save batch results
    batch_output = DATA_DIR / f"batch_results_{get_today_key()}.json"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(batch_output, "w") as f:
        json.dump({
            "results": results,
            "summary": {
                "total_leads": len(leads),
                "sent": sent_count,
                "skipped": skipped_count,
                "errors": error_count,
                "dry_run": dry_run,
                "offer_type": offer_type,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, f, indent=2, default=str)

    summary = {
        "sent": sent_count,
        "skipped": skipped_count,
        "errors": error_count,
        "total_leads": len(leads),
        "batch_file": str(batch_output),
    }

    log.info("Batch complete: %d sent, %d skipped, %d errors", sent_count, skipped_count, error_count)
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Rex Batch Offers -- Send creative finance offers at scale")
    parser.add_argument("--file", type=str, help="Path to leads JSON file")
    parser.add_argument("--max", type=int, default=None, help="Max offers to send (default: 50/day)")
    parser.add_argument("--dry-run", action="store_true", help="Preview offers without sending")
    parser.add_argument(
        "--offer-type",
        type=str,
        default="subject_to",
        choices=["subject_to", "owner_finance", "lease_option"],
        help="Offer type to send (default: subject_to)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    result = run_batch(
        leads_file=args.file,
        max_offers=args.max,
        dry_run=args.dry_run,
        offer_type=args.offer_type,
    )

    print(f"\n=== BATCH RESULTS ===")
    print(f"Sent:    {result.get('sent', 0)}")
    print(f"Skipped: {result.get('skipped', 0)}")
    print(f"Errors:  {result.get('errors', 0)}")
    if result.get("batch_file"):
        print(f"Details: {result['batch_file']}")


if __name__ == "__main__":
    main()
