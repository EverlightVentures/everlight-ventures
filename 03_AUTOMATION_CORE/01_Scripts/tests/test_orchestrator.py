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
