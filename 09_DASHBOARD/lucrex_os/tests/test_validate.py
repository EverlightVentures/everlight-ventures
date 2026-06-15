import dataclasses
from registry import load_registry, validate

def test_valid_registry_has_no_errors(fixture_path):
    assert validate(load_registry(fixture_path)) == []

def test_bad_hex_token_is_flagged(fixture_path):
    reg = load_registry(fixture_path)
    reg.tokens["gold"] = "D4AF37"  # missing '#'
    errs = validate(reg)
    assert any("gold" in e and "hex" in e for e in errs)

def test_duplicate_dashboard_id_is_flagged(fixture_path):
    reg = load_registry(fixture_path)
    dup = dataclasses.replace(reg.dashboards[0])
    reg.dashboards.append(dup)
    errs = validate(reg)
    assert any("duplicate id" in e for e in errs)

def test_bad_enum_is_flagged(fixture_path):
    reg = load_registry(fixture_path)
    reg.dashboards[0].access = "world"  # not in enum
    errs = validate(reg)
    assert any("access" in e for e in errs)
