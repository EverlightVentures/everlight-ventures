from sld.alerts import plan, dispatch


def test_plan_by_level():
    channels = [c for c, _ in plan("EXTREME")]
    assert "push" in channels and "email" in channels
    assert plan("EXTREME")[0] == ("push", 5)
    assert plan("HIGH")[0] == ("push", 4)
    assert [c for c, _ in plan("LOW")] == ["dashboard"]


def test_dispatch_calls_senders_and_records_receipts():
    calls = []
    senders = {
        "push": lambda e, p: calls.append(("push", p)) or True,
        "email": lambda e, p: True,
        "dashboard": lambda e, p: True,
    }
    receipts = dispatch({"threat_level": "EXTREME", "type": "Shots Fired"}, senders)
    assert ("push", 5) in calls
    assert all(r["ok"] for r in receipts)
    assert {r["channel"] for r in receipts} == {"push", "email", "dashboard"}


def test_dispatch_skips_missing_channel_and_survives_sender_error():
    def boom(e, p):
        raise RuntimeError("ntfy down")

    receipts = dispatch({"threat_level": "EXTREME"}, {"push": boom})
    # email + dashboard have no sender -> skipped; push captured its error, no crash.
    assert len(receipts) == 1
    assert receipts[0]["channel"] == "push"
    assert receipts[0]["ok"] is False
    assert "ntfy down" in receipts[0]["error"]
