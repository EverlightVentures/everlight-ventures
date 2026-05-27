from inbound.sentinel_router import decide_action

def test_vendor_pitch_auto_replies():
    assert decide_action({"category": "sales_pitch", "high_stakes": False,
                          "opsec_flag": False}) == "auto_reply"

def test_opt_out_auto_replies():
    assert decide_action({"category": "opt_out", "high_stakes": False,
                          "opsec_flag": False}) == "auto_reply"

def test_recon_probe_drafts_never_replies():
    assert decide_action({"category": "recon_probe", "high_stakes": True,
                          "opsec_flag": True}) == "draft"

def test_investor_drafts():
    assert decide_action({"category": "investor", "high_stakes": True,
                          "opsec_flag": False}) == "draft"

def test_opsec_flag_forces_draft_even_if_low_stakes():
    assert decide_action({"category": "sales_pitch", "high_stakes": False,
                          "opsec_flag": True}) == "draft"
