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


def test_fetch_recent_returns_empty_without_creds(monkeypatch):
    import content_tools.imap_fetch as mod
    monkeypatch.delenv("GMAIL_IMAP_USER", raising=False)
    monkeypatch.delenv("GMAIL_IMAP_PASS", raising=False)
    # neutralize the .env loader so it cannot supply real creds during the test
    monkeypatch.setattr(mod, "load_env", lambda *a, **k: 0)
    assert mod.fetch_recent(days=1) == []


def test_parse_message_handles_garbage_without_raising():
    msg = parse_message(b"not a real email at all")
    assert isinstance(msg, dict)
    assert set(msg) == {"message_id", "from_name", "from_email", "subject", "body",
                        "delivered_to", "list_unsubscribe", "precedence", "date"}
