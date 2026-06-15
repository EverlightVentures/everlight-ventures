from theme.tokens import TOKENS, emit_css_vars

def test_canonical_gold():
    assert TOKENS["gold"] == "#D4AF37"
    assert TOKENS["dark"] == "#0A0A0A"

def test_emit_css_vars_block():
    css = emit_css_vars()
    assert ":root" in css
    assert "--gold: #D4AF37;" in css
    assert "--canvas:" in css   # data-surface ramp token exists
