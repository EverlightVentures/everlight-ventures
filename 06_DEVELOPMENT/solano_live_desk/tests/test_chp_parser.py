from pathlib import Path
from sld.chp_parser import parse_incidents, is_solano

FIX = Path(__file__).parent / "fixtures" / "sa_sample.xml"


def test_is_solano_by_area_label():
    assert is_solano("Solano") is True
    assert is_solano('"Solano"') is True  # quoted like the live feed


def test_is_solano_rejects_other_area_office():
    # I-680 runs through San Jose too; trust CHP's label, not the road name.
    assert is_solano("San Jose", 37.38, -121.85) is False
    assert is_solano("Contra Costa", 38.02, -122.11) is False


def test_is_solano_blank_area_falls_back_to_bbox():
    assert is_solano("", 38.25, -122.0) is True   # inside Solano box
    assert is_solano("", 37.38, -121.85) is False  # San Jose, outside box
    assert is_solano("", None, None) is False      # blank + no coords


def test_parse_keeps_only_ggcc_solano():
    events = parse_incidents(FIX.read_text())
    # GGCC 0043 is SF (filtered), SFCC 9001 is wrong dispatch (skipped),
    # only GGCC 0042 (Solano) survives.
    assert len(events) == 1
    ev = events[0]
    assert ev["id"] == "chp:GGCC:0042"
    assert ev["source"] == "chp"
    assert ev["type"] == "Trfc Collision-No Inj"
    assert ev["lat"] == 38.22374
    assert ev["lon"] == -122.12696
    assert ev["geo_label"] == "I80 E / SUISUN VALLEY RD"
    assert ev["body"] == "7:35AM  veh in center divide\n7:36AM  units en route"
    assert ev["details"] == [
        "7:35AM  veh in center divide",
        "7:36AM  units en route",
    ]


def test_parse_tolerates_truncated_tail_and_bare_amp():
    # The live CHP feed ends mid-tag and carries unescaped '&'. A complete
    # Solano log followed by a broken tail must still yield the good record.
    xml = (
        '<State><Center ID = "GGHB"><Dispatch ID = "GGCC">'
        '<Log ID = "1"><LogType>"Fire"</LogType>'
        '<Location>"I80 / PG&E ROAD"</Location><Area>"Solano"</Area>'
        '<LATLON>"38223740:122126960"</LATLON>'
        '<LogDetails><details><DetailTime>"1AM"</DetailTime>'
        '<IncidentDetail>"smoke"</IncidentDetail></details></LogDetails></Log>'
        '<Log ID = "2"><LogType>"Crash"</LogType><Location>"BROKEN'  # truncated
    )
    events = parse_incidents(xml)
    assert len(events) == 1
    assert events[0]["id"] == "chp:GGCC:1"
    assert events[0]["lat"] == 38.22374
    assert events[0]["body"] == "1AM  smoke"
