from pathlib import Path
from content_tools.imap_fetch import parse_message

FIX = Path(__file__).parent / "fixtures"

def test_parse_extracts_core_fields():
    raw = (FIX / "anyip.eml").read_bytes()
    msg = parse_message(raw)
    assert msg["from_email"] == "ben@anyipit.com"
    assert msg["from_name"] == "Ben"
    assert "everlight-ventures" in msg["subject"]
    assert "proxy-broker" in msg["body"]
    assert msg["message_id"] == "<anyip-0001@anyipit.com>"
    assert msg["delivered_to"] == "1m.rich.gee@gmail.com"
    assert msg["list_unsubscribe"] == ""        # not a bulk email
    assert msg["precedence"] == ""
