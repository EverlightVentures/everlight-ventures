from pathlib import Path
from content_tools.imap_fetch import parse_message
from inbound.sentinel_filter import triage_keep

FIX = Path(__file__).parent / "fixtures"

def _msg(name):
    return parse_message((FIX / name).read_bytes())

def test_stranger_is_kept():
    keep, reason = triage_keep(_msg("anyip.eml"))
    assert keep is True
    assert reason == "stranger_inbound"

def test_bulk_marketing_dropped():
    keep, reason = triage_keep(_msg("newsletter.eml"))
    assert keep is False
    assert reason == "bulk_marketing"

def test_known_contact_dropped():
    keep, reason = triage_keep(_msg("seller_reply.eml"))
    assert keep is False
    assert reason == "known_contact"

def test_billing_alert_deferred():
    keep, reason = triage_keep(_msg("stripe_alert.eml"))
    assert keep is False
    assert reason == "critical_service_defer"
