from pathlib import Path
from content_tools.imap_fetch import parse_message
from inbound.sentinel_classifier import classify

FIX = Path(__file__).parent / "fixtures"

def test_anyip_is_recon_probe_with_opsec_flag():
    msg = parse_message((FIX / "anyip.eml").read_bytes())
    result = classify(msg)
    # asks "how important is that layer" about a named public repo => recon probe
    assert result["category"] in {"recon_probe", "sales_pitch"}
    assert "everlight-ventures" in result["referenced_assets"]
    assert result["opsec_flag"] is True
    assert result["high_stakes"] is True   # recon/sales both route to draft, never auto-reply-leak

def test_referenced_assets_extracts_repo_path():
    from inbound.sentinel_classifier import referenced_assets
    assets = referenced_assets("look at EverlightVentures/everlight-ventures repo")
    assert "everlight-ventures" in assets
