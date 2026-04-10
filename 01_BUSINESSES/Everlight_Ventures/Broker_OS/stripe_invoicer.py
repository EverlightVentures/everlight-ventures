"""
Broker OS -- Stripe Auto-Invoicing
When a deal closes, auto-create a Stripe invoice for the finder fee,
email it to the client, and track payment status.

Usage:
    from stripe_invoicer import invoice_deal, check_invoice_status
    result = invoice_deal(deal_data)
    status = check_invoice_status(invoice_id)
"""
from __future__ import annotations
import os
import json
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Load credentials
_env_path = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")
if not _env_path.exists():
    _env_path = Path("/home/opc/.env")
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_API = "https://api.stripe.com/v1"

# Where to log invoice records
INVOICE_LOG = Path(os.getenv(
    "INVOICE_LOG_DIR",
    "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/invoices"
))
INVOICE_LOG.mkdir(parents=True, exist_ok=True)

COMPANY_NAME = "Everlight Ventures"


def _stripe_headers():
    return {"Authorization": "Bearer %s" % STRIPE_SECRET_KEY}


def _stripe_post(endpoint: str, data: dict) -> dict:
    """Make a POST to Stripe API."""
    resp = requests.post(
        "%s/%s" % (STRIPE_API, endpoint),
        headers=_stripe_headers(),
        data=data,
        timeout=15,
    )
    return resp.json()


def _stripe_get(endpoint: str, params: dict = None) -> dict:
    """Make a GET to Stripe API."""
    resp = requests.get(
        "%s/%s" % (STRIPE_API, endpoint),
        headers=_stripe_headers(),
        params=params or {},
        timeout=15,
    )
    return resp.json()


def _find_or_create_customer(email: str, name: str) -> str | None:
    """Find existing Stripe customer by email or create one."""
    # Search first
    result = _stripe_get("customers", {"email": email, "limit": 1})
    customers = result.get("data", [])
    if customers:
        return customers[0]["id"]

    # Create new
    customer = _stripe_post("customers", {
        "email": email,
        "name": name,
        "metadata[source]": "broker_os",
        "metadata[created_by]": "auto_invoicer",
    })
    return customer.get("id")


def invoice_deal(deal: dict) -> dict:
    """
    Create and send a Stripe invoice for a closed deal.

    deal dict should contain:
        client_name: str        - company/person name
        client_email: str       - email for invoice
        deal_type: str          - 'finder_fee' or 'wholesale_assignment'
        scope: str              - description of the deal
        deal_value: float       - total deal value
        commission_pct: float   - e.g. 0.20 for 20%
        commission_amount: float - override (if set, ignores pct calc)
        due_days: int           - days until due (default 30)
        auto_send: bool         - send immediately (default True)

    Returns dict with:
        success: bool
        invoice_id: str
        invoice_url: str (hosted payment page)
        amount: int (cents)
        error: str (if failed)
    """
    if not STRIPE_SECRET_KEY:
        return {"success": False, "error": "STRIPE_SECRET_KEY not configured"}

    client_name = deal.get("client_name", "Unknown")
    client_email = deal.get("client_email", "")
    deal_type = deal.get("deal_type", "finder_fee")
    scope = deal.get("scope", "Brokered introduction")
    deal_value = deal.get("deal_value", 0)
    pct = deal.get("commission_pct", 0.20)
    due_days = deal.get("due_days", 30)
    auto_send = deal.get("auto_send", True)

    # Calculate commission
    if deal.get("commission_amount"):
        commission = deal["commission_amount"]
    else:
        commission = deal_value * pct

    amount_cents = int(commission * 100)
    if amount_cents < 50:
        return {"success": False, "error": "Invoice amount too small (min $0.50)"}

    if not client_email:
        return {"success": False, "error": "Client email required for invoicing"}

    # Find or create customer
    customer_id = _find_or_create_customer(client_email, client_name)
    if not customer_id:
        return {"success": False, "error": "Failed to create Stripe customer"}

    # Build description based on deal type
    if deal_type == "wholesale_assignment":
        description = "Assignment Fee - %s" % scope
        memo = (
            "Wholesale real estate assignment fee per executed purchase agreement. "
            "Property: %s. "
            "This fee is collected by the title company at closing and disbursed to Everlight Logistics LLC."
        ) % scope
    else:
        pct_str = "%.0f%%" % (pct * 100)
        description = "Finder Fee (%s) - %s" % (pct_str, scope)
        memo = (
            "Finder fee per Finder Fee Agreement between Everlight Logistics LLC (d/b/a Everlight Ventures) "
            "and %s. Fee of %s on deal value of $%s for: %s. "
            "Payment due Net %d from close date."
        ) % (client_name, pct_str, "{:,.0f}".format(deal_value), scope, due_days)

    # Create invoice with proper branding
    invoice = _stripe_post("invoices", {
        "customer": customer_id,
        "collection_method": "send_invoice",
        "days_until_due": due_days,
        "description": memo[:500],
        "footer": "Everlight Logistics LLC (d/b/a Everlight Ventures) | deals@everlightventures.io | everlightventures.io",
        "metadata[deal_type]": deal_type,
        "metadata[deal_value]": str(deal_value),
        "metadata[commission_pct]": str(pct),
        "metadata[source]": "broker_os_auto",
        "metadata[scope]": scope[:200],
    })

    if invoice.get("error"):
        return {"success": False, "error": invoice["error"].get("message", "Invoice creation failed")}

    invoice_id = invoice.get("id")
    if not invoice_id:
        return {"success": False, "error": "No invoice ID returned"}

    # Add line item
    line = _stripe_post("invoiceitems", {
        "customer": customer_id,
        "invoice": invoice_id,
        "amount": amount_cents,
        "currency": "usd",
        "description": description,
    })

    if line.get("error"):
        return {"success": False, "error": "Failed to add line item: %s" % line["error"].get("message", "")}

    # Finalize invoice
    finalized = _stripe_post("invoices/%s/finalize" % invoice_id, {})

    # Send invoice
    hosted_url = ""
    if auto_send and not finalized.get("error"):
        sent = _stripe_post("invoices/%s/send" % invoice_id, {})
        hosted_url = sent.get("hosted_invoice_url", finalized.get("hosted_invoice_url", ""))
    else:
        hosted_url = finalized.get("hosted_invoice_url", "")

    # Log locally
    record = {
        "invoice_id": invoice_id,
        "customer_id": customer_id,
        "client_name": client_name,
        "client_email": client_email,
        "deal_type": deal_type,
        "scope": scope,
        "deal_value": deal_value,
        "commission_pct": pct,
        "amount_cents": amount_cents,
        "amount_usd": commission,
        "hosted_url": hosted_url,
        "status": "sent" if auto_send else "finalized",
        "created_at": datetime.now(timezone(timedelta(hours=-7))).isoformat(),
    }
    log_path = INVOICE_LOG / ("%s.json" % invoice_id)
    log_path.write_text(json.dumps(record, indent=2))

    return {
        "success": True,
        "invoice_id": invoice_id,
        "invoice_url": hosted_url,
        "amount": amount_cents,
        "amount_usd": commission,
        "customer_id": customer_id,
    }


def check_invoice_status(invoice_id: str) -> dict:
    """Check current status of a Stripe invoice."""
    if not STRIPE_SECRET_KEY:
        return {"error": "STRIPE_SECRET_KEY not configured"}

    result = _stripe_get("invoices/%s" % invoice_id)
    if result.get("error"):
        return {"error": result["error"].get("message", "Lookup failed")}

    return {
        "invoice_id": invoice_id,
        "status": result.get("status"),
        "amount_due": result.get("amount_due", 0),
        "amount_paid": result.get("amount_paid", 0),
        "hosted_url": result.get("hosted_invoice_url", ""),
        "customer_email": result.get("customer_email", ""),
        "due_date": result.get("due_date"),
        "paid": result.get("paid", False),
    }


def list_pending_invoices() -> list[dict]:
    """List all open/unpaid Broker OS invoices."""
    if not STRIPE_SECRET_KEY:
        return []

    result = _stripe_get("invoices", {
        "status": "open",
        "limit": 50,
    })

    invoices = []
    for inv in result.get("data", []):
        meta = inv.get("metadata", {})
        if meta.get("source") == "broker_os_auto":
            invoices.append({
                "invoice_id": inv["id"],
                "customer_email": inv.get("customer_email", ""),
                "amount_due": inv.get("amount_due", 0),
                "deal_type": meta.get("deal_type", ""),
                "scope": meta.get("scope", ""),
                "status": inv.get("status"),
                "due_date": inv.get("due_date"),
                "hosted_url": inv.get("hosted_invoice_url", ""),
            })

    return invoices


if __name__ == "__main__":
    print("Stripe Auto-Invoicer - Test Mode")
    print("Checking Stripe connection...")

    if not STRIPE_SECRET_KEY:
        print("ERROR: No STRIPE_SECRET_KEY found")
    else:
        # Test API connection
        result = _stripe_get("balance")
        if result.get("available"):
            avail = sum(b.get("amount", 0) for b in result["available"]) / 100
            pending = sum(b.get("amount", 0) for b in result.get("pending", [])) / 100
            print("  Stripe connected. Balance: $%.2f available, $%.2f pending" % (avail, pending))
        elif result.get("error"):
            print("  Stripe error: %s" % result["error"].get("message", "unknown"))

        # List pending invoices
        pending = list_pending_invoices()
        print("  Open broker invoices: %d" % len(pending))
        for inv in pending[:5]:
            print("    - %s | $%.2f | %s" % (inv["invoice_id"], inv["amount_due"] / 100, inv["scope"][:50]))
