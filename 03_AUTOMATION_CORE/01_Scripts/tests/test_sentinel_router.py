from inbound.sentinel_router import decide_action, route, _confidential_ok

def test_sales_pitch_auto_replies():
    assert decide_action({"category": "sales_pitch", "high_stakes": False,
                          "opsec_flag": False}) == "auto_reply"

def test_unknown_category_drafts():
    assert decide_action({"category": "other", "high_stakes": False,
                          "opsec_flag": False}) == "draft"

def test_recon_probe_drafts_never_replies():
    assert decide_action({"category": "recon_probe", "high_stakes": True,
                          "opsec_flag": True}) == "draft"

def test_investor_drafts():
    assert decide_action({"category": "investor", "high_stakes": True,
                          "opsec_flag": False}) == "draft"

def test_opsec_flag_forces_draft_even_if_low_stakes():
    assert decide_action({"category": "sales_pitch", "high_stakes": False,
                          "opsec_flag": True}) == "draft"

def test_route_dry_run_drafts_and_sends_nothing():
    msg = {"from_email": "ben@anyipit.com", "subject": "hi", "body": "hello"}
    cls = {"category": "recon_probe", "high_stakes": True, "opsec_flag": True,
           "referenced_assets": ["everlight-ventures"]}
    out = route(msg, cls, dry_run=True)
    assert out["action"] == "draft"
    assert out["sent"] is False
    assert out["drafted"] is False   # dry_run does not even write the draft
    assert out["alerted"] is False
    assert "everlight-ventures" in out["referenced_assets"]

def test_route_dry_run_sales_pitch_decision_only():
    msg = {"from_email": "x@vendor.com", "subject": "demo", "body": "book a call"}
    cls = {"category": "sales_pitch", "high_stakes": False, "opsec_flag": False,
           "referenced_assets": []}
    out = route(msg, cls, dry_run=True)
    assert out["action"] == "auto_reply"
    assert out["sent"] is False   # dry_run never sends

def test_confidential_fails_closed_when_gate_unavailable(monkeypatch):
    import sys
    # Force the in-function import to fail -> _confidential_ok must return False.
    monkeypatch.setitem(sys.modules, "moltbook_confidentiality_gate", None)
    assert _confidential_ok("any body text") is False
