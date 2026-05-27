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

def test_known_by_domain_dropped():
    # a NEW person at a known domain (not the listed email) still drops as known;
    # mixed-case sender also verifies domain normalization.
    msg = {"from_email": "newperson@MidSouthHomebuyers.com",
           "list_unsubscribe": "", "precedence": ""}
    keep, reason = triage_keep(msg)
    assert keep is False
    assert reason == "known_contact"

def test_no_signal_when_no_sender():
    keep, reason = triage_keep({"from_email": "", "list_unsubscribe": "", "precedence": ""})
    assert keep is False
    assert reason == "no_signal"
