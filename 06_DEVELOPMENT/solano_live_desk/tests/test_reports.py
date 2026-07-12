"""Community reports + gig-driver presence: TTL decay and presence upsert."""
from sld import reports


def test_add_report_sets_label_and_ttl(tmp_path):
    r = reports.add_report(str(tmp_path), "reckless_shoulder", 38.25, -122.04, "on my side", now=1000)
    assert r["severity"] == "HIGH"
    assert r["expires"] == 1000 + 900
    act = reports.active(str(tmp_path), now=1001)
    assert len(act) == 1 and act[0]["label"].startswith("Reckless: shoulder")


def test_unknown_kind_is_generic_hazard(tmp_path):
    r = reports.add_report(str(tmp_path), "mystery", 38.2, -122.0, now=0)
    assert r["label"] == "Driver-reported hazard" and r["severity"] == "MEDIUM"


def test_report_expires(tmp_path):
    reports.add_report(str(tmp_path), "reckless_weaving", 38.2, -122.0, now=0)  # ttl 900
    assert reports.active(str(tmp_path), now=500)      # still live
    assert reports.active(str(tmp_path), now=1000) == []  # decayed


def test_presence_upserts_one_row_per_client(tmp_path):
    reports.mark_presence(str(tmp_path), "driverA", 38.25, -122.04, now=0)
    reports.mark_presence(str(tmp_path), "driverA", 38.26, -122.05, now=60)  # moved
    act = [r for r in reports.active(str(tmp_path), now=61) if r["is_presence"]]
    assert len(act) == 1  # not two
    assert act[0]["lat"] == 38.26 and act[0]["label"].startswith("Delivery driver")


def test_presence_expires_and_clears(tmp_path):
    reports.mark_presence(str(tmp_path), "driverB", 38.2, -122.0, now=0)  # ttl 300
    assert reports.active(str(tmp_path), now=100)
    assert reports.active(str(tmp_path), now=400) == []  # auto-expired when they stop refreshing
    reports.mark_presence(str(tmp_path), "driverB", 38.2, -122.0, now=500)
    reports.clear_presence(str(tmp_path), "driverB")
    assert reports.active(str(tmp_path), now=501) == []


def test_reports_and_presence_coexist(tmp_path):
    reports.add_report(str(tmp_path), "hazard_flood", 38.2, -122.0, now=0)
    reports.mark_presence(str(tmp_path), "driverC", 38.3, -122.1, now=0)
    act = reports.active(str(tmp_path), now=10)
    kinds = {r["kind"] for r in act}
    assert "hazard_flood" in kinds and "presence_delivery" in kinds
