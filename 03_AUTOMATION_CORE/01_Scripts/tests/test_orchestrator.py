from pathlib import Path
from content_tools.imap_fetch import parse_message
import inbound_sentinel as s

FIX = Path(__file__).parent / "fixtures"

def test_process_one_anyip_keeps_and_drafts():
    msg = parse_message((FIX / "anyip.eml").read_bytes())
    out = s.process_one(msg, dry_run=True)
    assert out is not None
    assert out["action"] == "draft"        # opsec flag forces draft
    assert out["category"] in {"recon_probe", "sales_pitch"}

def test_process_one_newsletter_dropped():
    msg = parse_message((FIX / "newsletter.eml").read_bytes())
    assert s.process_one(msg, dry_run=True) is None  # filtered out


def _vendor_msg(mid):
    return {"message_id": mid, "from_email": "x@vendor.com", "subject": "demo",
            "body": "book a call", "list_unsubscribe": "", "precedence": ""}

def test_scan_once_empty_inbox(monkeypatch, tmp_path):
    monkeypatch.setattr(s, "SEEN", tmp_path / "seen.json")
    monkeypatch.setattr(s, "fetch_recent", lambda **k: [])
    assert s.scan_once() == {"kept": 0, "actions": {}, "dry_run": True}

def test_scan_once_dedup_within_run(monkeypatch, tmp_path):
    monkeypatch.setattr(s, "SEEN", tmp_path / "seen.json")
    m = _vendor_msg("<dup@x>")
    monkeypatch.setattr(s, "fetch_recent", lambda **k: [m, m])  # same id twice
    out = s.scan_once(dry_run=True)
    assert out["kept"] == 1

def test_scan_once_persists_across_runs(monkeypatch, tmp_path):
    monkeypatch.setattr(s, "SEEN", tmp_path / "seen.json")
    monkeypatch.setattr(s, "fetch_recent", lambda **k: [_vendor_msg("<a@x>")])
    assert s.scan_once(dry_run=True)["kept"] == 1   # first run processes it
    assert s.scan_once(dry_run=True)["kept"] == 0   # second run: already seen, skipped
