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
    assert result["high_stakes"] is True   # recon_probe is high-stakes -> always drafts, never auto-reply

def test_referenced_assets_extracts_repo_path():
    from inbound.sentinel_classifier import referenced_assets
    assets = referenced_assets("look at EverlightVentures/everlight-ventures repo")
    assert "everlight-ventures" in assets


def _m(subject="", body=""):
    return {"subject": subject, "body": body}

def test_investor_email():
    r = classify(_m("Funding interest", "we'd love to invest and discuss check size"))
    assert r["category"] == "investor"
    assert r["high_stakes"] is True

def test_partnership_email():
    r = classify(_m("Partnership", "want to explore a reseller partnership and integrate"))
    assert r["category"] == "partnership"

def test_press_email():
    r = classify(_m("Quick one", "I'm a journalist writing a story, can we do an interview"))
    assert r["category"] == "press"

def test_job_email():
    r = classify(_m("Application", "attaching my resume, applying for a role"))
    assert r["category"] == "job"

def test_other_low_stakes_no_opsec():
    r = classify(_m("hello", "just saying hi"))
    assert r["category"] == "other"
    assert r["high_stakes"] is False
    assert r["opsec_flag"] is False

def test_sales_pitch_is_not_high_stakes():
    r = classify(_m("Our platform", "check out our platform, book a call for a demo"))
    assert r["category"] == "sales_pitch"
    assert r["high_stakes"] is False

def test_your_service_not_misread_as_sales():
    r = classify(_m("question", "your services look interesting, how do you handle billing"))
    assert r["category"] != "sales_pitch"

def test_raise_awareness_not_investor():
    r = classify(_m("collab", "we want to raise awareness and work together on a campaign"))
    assert r["category"] != "investor"

def test_recon_override_beats_partnership():
    r = classify(_m("partnership", "love to partner -- how important is that proxy-broker layer to you?"))
    assert r["category"] == "recon_probe"
    assert r["opsec_flag"] is True

def test_intent_is_float():
    assert isinstance(classify(_m("hi", "hello"))["intent"], float)
