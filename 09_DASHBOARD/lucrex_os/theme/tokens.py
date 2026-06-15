"""Single source of truth for LUCREX OS colors + fonts.
The gold value has never changed in git history, so this is a flat dict,
not a DTCG/Style-Dictionary pipeline (see design spec section 3.2)."""

TOKENS = {
    # chrome (brand)
    "gold": "#D4AF37",
    "dark": "#0A0A0A",
    "text": "#E8E8E8",
    "text_dim": "#A8A8A8",
    # data-surface elevation ramp (off pure black for readability)
    "canvas": "#141414",
    "card": "#1E1E1E",
    "gridline": "#2E2E2E",
    # status (desaturated, gold is NEVER a status color)
    "pos": "#5BA46A",
    "neg": "#C25B5B",
}

FONTS = {
    "display": "'Playfair Display', serif",
    "body": "'Inter', -apple-system, sans-serif",
    "mono": "'JetBrains Mono', monospace",
    "ui": "'DM Sans', sans-serif",
}

def emit_css_vars() -> str:
    lines = [":root {"]
    for k, v in TOKENS.items():
        lines.append(f"  --{k.replace('_','-')}: {v};")
    for k, v in FONTS.items():
        lines.append(f"  --font-{k}: {v};")
    lines.append("}")
    return "\n".join(lines)
