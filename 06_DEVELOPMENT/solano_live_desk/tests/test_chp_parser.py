from pathlib import Path
from sld.chp_parser import parse_incidents, DEFAULT_CENTER

FIX = Path(__file__).parent / "fixtures" / "sa_sample.xml"


def test_parse_keeps_located_incidents_in_bubble():
    events = parse_incidents(FIX.read_text())  # default center = Fairfield, 75mi
    # Only GGCC 0042 has real coords (near Fairfield); the SF 0:0 logs are unlocated.
    assert len(events) == 1
    ev = events[0]
    assert ev["id"] == "chp:GGCC:0042"
    assert ev["source"] == "chp"
    assert ev["type"] == "Trfc Collision-No Inj"
    assert ev["lat"] == 38.22374
    assert ev["lon"] == -122.12696
    assert ev["body"] == "7:35AM  veh in center divide\n7:36AM  units en route"


def test_parse_reads_all_dispatches_not_just_ggcc():
    # A located incident under a NON-GGCC dispatch, inside the bubble, is kept.
    xml = (
        '<State><Center ID = "SAHB"><Dispatch ID = "SACC">'
        '<Log ID = "9"><LogType>"Fire"</LogType><Location>"I80 near Dixon"</Location>'
        '<Area>"Sacramento"</Area><LATLON>"38400000:121800000"</LATLON></Log>'
        "</Dispatch></Center></State>"
    )
    events = parse_incidents(xml)  # Dixon-ish point is ~15mi from Fairfield -> kept
    assert len(events) == 1
    assert events[0]["id"] == "chp:SACC:9"


def test_parse_radius_excludes_far_incident():
    # An LA point is ~380mi from Fairfield -> outside the 75mi bubble -> dropped.
    xml = (
        '<State><Center ID = "LAHB"><Dispatch ID = "LACC">'
        '<Log ID = "1"><LogType>"Crash"</LogType><Location>"I5 LA"</Location>'
        '<Area>"Los Angeles"</Area><LATLON>"34050000:118240000"</LATLON></Log>'
        "</Dispatch></Center></State>"
    )
    assert parse_incidents(xml) == []
    # ...but a wide radius keeps it.
    assert len(parse_incidents(xml, radius_mi=500)) == 1


def test_parse_recenters_bubble_on_given_center():
    # Same LA incident is kept when the bubble is centered on LA (follow-me).
    xml = (
        '<State><Center ID = "LAHB"><Dispatch ID = "LACC">'
        '<Log ID = "1"><LogType>"Crash"</LogType><Location>"I5 LA"</Location>'
        '<Area>"Los Angeles"</Area><LATLON>"34050000:118240000"</LATLON></Log>'
        "</Dispatch></Center></State>"
    )
    assert len(parse_incidents(xml, center=(34.05, -118.24))) == 1


def test_parse_tolerates_truncated_tail_and_bare_amp():
    # A complete located log followed by a broken tail still yields the good record.
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
    assert events[0]["body"] == "1AM  smoke"


def test_default_center_is_fairfield():
    assert abs(DEFAULT_CENTER[0] - 38.25) < 0.1
