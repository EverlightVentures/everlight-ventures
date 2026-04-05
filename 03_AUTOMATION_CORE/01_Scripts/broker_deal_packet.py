#!/usr/bin/env python3
"""
Broker Deal Packet Generator
Creates branded gold/black PDF deal packets for buyers.

Generates:
  - Property overview with key metrics
  - Profit projections (ARV, repair costs, wholesale fee)
  - Comparable sales data
  - Investment summary for cash buyers

Usage:
    python3 broker_deal_packet.py                    # Generate for all pending deals
    python3 broker_deal_packet.py --deal-id 123      # Specific deal
"""
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Django setup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '09_DASHBOARD', 'hive_dashboard'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hive_dashboard.settings')

try:
    import django
    django.setup()
    from broker_ops.models import Deal, BrokerMatch, LeadProfile, OfferListing
    DJANGO_AVAILABLE = True
except Exception:
    DJANGO_AVAILABLE = False

sys.path.insert(0, os.path.dirname(__file__))

log = logging.getLogger("deal-packet")
logging.basicConfig(level=logging.INFO, format="[DealPacket %(asctime)s] %(message)s")

OUTPUT_DIR = Path(os.environ.get("DEAL_PACKETS_DIR", "/tmp/hive_deliverables/deal_packets"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_deal_packet(deal_id: int = None) -> list[str]:
    """Generate PDF deal packets for pending deals."""
    if not DJANGO_AVAILABLE:
        log.error("Django not available. Run from hive_dashboard context.")
        return []

    if deal_id:
        deals = Deal.objects.filter(id=deal_id)
    else:
        deals = Deal.objects.filter(stage__in=["intro", "negotiating", "contracted"])

    if not deals.exists():
        log.info("No deals found to generate packets for.")
        return []

    paths = []
    for deal in deals:
        path = _generate_single_packet(deal)
        if path:
            paths.append(path)
            log.info(f"Generated deal packet: {path}")

    return paths


def _generate_single_packet(deal) -> str:
    """Generate a single deal packet PDF."""
    # Gather deal data
    offer = deal.offer if hasattr(deal, 'offer') else None
    lead = deal.lead if hasattr(deal, 'lead') else None

    deal_data = {
        "id": deal.id,
        "title": getattr(offer, 'title', 'Untitled Deal') if offer else str(deal),
        "stage": deal.stage,
        "seller_name": getattr(offer, 'seller_name', 'Unknown') if offer else 'Unknown',
        "buyer_name": getattr(lead, 'name', 'Unknown') if lead else 'Unknown',
        "buyer_company": getattr(lead, 'company', '') if lead else '',
        "buyer_email": getattr(lead, 'email', '') if lead else '',
        "match_score": getattr(deal, 'match_score', 0) or 0,
        "commission_pct": getattr(deal, 'commission_pct', 15) or 15,
        "notes": getattr(deal, 'notes', '') or '',
        "created": deal.created_at.strftime('%Y-%m-%d') if hasattr(deal, 'created_at') and deal.created_at else '',
    }

    # Build sections for PDF
    sections = [
        {
            "heading": "Deal Overview",
            "body": (
                f"Product/Service: {deal_data['title']}\n"
                f"Stage: {deal_data['stage'].title()}\n"
                f"Match Score: {deal_data['match_score']}/100\n"
                f"Date Created: {deal_data['created']}\n"
            ),
        },
        {
            "heading": "Seller Information",
            "body": f"Seller: {deal_data['seller_name']}\n",
        },
        {
            "heading": "Buyer Information",
            "body": (
                f"Name: {deal_data['buyer_name']}\n"
                f"Company: {deal_data['buyer_company']}\n"
                f"Email: {deal_data['buyer_email']}\n"
            ),
        },
        {
            "heading": "Commission Structure",
            "body": (
                f"Finder's Fee: {deal_data['commission_pct']}%\n"
                f"Payment Terms: Net 30 from close\n"
                f"Everlight Ventures acts as finder only -- no ownership stake.\n"
            ),
        },
    ]

    if deal_data['notes']:
        sections.append({
            "heading": "Deal Notes",
            "body": deal_data['notes'],
        })

    sections.append({
        "heading": "Next Steps",
        "body": (
            "1. Review deal terms with buyer\n"
            "2. Execute finder's agreement\n"
            "3. Facilitate introduction\n"
            "4. Monitor deal progression\n"
            "5. Invoice commission on close\n"
        ),
    })

    # Generate PDF
    try:
        from hive_deliverables import generate_pdf
        filepath = generate_pdf(
            title=f"Deal Packet: {deal_data['title'][:40]}",
            subtitle=f"Everlight Ventures | Prepared {datetime.now().strftime('%B %d, %Y')}",
            sections=sections,
        )
        # Copy to deal packets dir
        import shutil
        dest = OUTPUT_DIR / Path(filepath).name
        shutil.copy2(filepath, dest)
        return str(dest)

    except ImportError:
        # Fallback to text
        filepath = OUTPUT_DIR / f"deal_{deal_data['id']}_{datetime.now().strftime('%Y%m%d')}.txt"
        with open(filepath, "w") as f:
            f.write(f"DEAL PACKET: {deal_data['title']}\n{'=' * 50}\n\n")
            for s in sections:
                f.write(f"\n## {s['heading']}\n{s['body']}\n")
        return str(filepath)


def generate_lead_export() -> str:
    """Export all leads to branded Excel spreadsheet."""
    if not DJANGO_AVAILABLE:
        return ""

    leads = LeadProfile.objects.filter(unsubscribed=False).exclude(
        email__contains="@placeholder.io"
    ).exclude(email="").values(
        "name", "email", "company", "intent", "source", "created_at"
    )[:500]

    rows = [
        {
            "name": l["name"],
            "email": l["email"],
            "company": l["company"] or "",
            "intent": l["intent"] or "",
            "source": l["source"] or "",
            "created": l["created_at"].strftime("%Y-%m-%d") if l["created_at"] else "",
        }
        for l in leads
    ]

    try:
        from hive_deliverables import generate_excel
        return generate_excel(
            title="Broker OS Lead Export",
            sheets={"Active Leads": rows or [{"note": "No leads yet"}]},
        )
    except ImportError:
        return ""


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--deal-id", type=int, help="Specific deal ID")
    parser.add_argument("--export-leads", action="store_true", help="Export leads to Excel")
    args = parser.parse_args()

    if args.export_leads:
        path = generate_lead_export()
        print(f"Lead export: {path}")
    else:
        paths = generate_deal_packet(args.deal_id)
        for p in paths:
            print(f"Deal packet: {p}")
