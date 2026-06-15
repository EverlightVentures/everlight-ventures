import re, pathlib
from theme.tokens import TOKENS, FONTS

CSS = pathlib.Path("theme/lucrex.css")
FX = pathlib.Path("theme/lucrex.fx.css")

def _defined():
    names = {f"--{k.replace('_','-')}" for k in TOKENS}
    names |= {f"--font-{k}" for k in FONTS}
    return names

def test_lucrex_css_only_uses_defined_tokens():
    used = set(re.findall(r"var\((--[a-z0-9-]+)\)", CSS.read_text()))
    undefined = used - _defined()
    assert not undefined, f"undefined tokens: {undefined}"

def test_fx_is_reduced_motion_gated():
    assert "prefers-reduced-motion: reduce" in FX.read_text()
