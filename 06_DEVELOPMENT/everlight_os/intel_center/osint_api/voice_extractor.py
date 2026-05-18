"""
voice_extractor -- read an agent's firmware and extract their voice/persona.

The pitch pipeline was using GENERIC templates and ignoring the actual agent
firmware. That's why every email sounded the same. This module fixes that:
given an agent slug like "31_outreach_agent" or "marquise_reed_acquisitions",
pull the markdown file at `.claude/agents/<slug>.md` and parse:

  - name
  - email + signature line
  - speech style (intro patterns, catchphrases, verbal tics)
  - tone keywords (warm/direct/etc.)
  - opener templates (their actual voice)
  - sign-off patterns

Returns a dict the pitch builder can interpolate into instead of using
hardcoded "Hey {first}" templates.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

AGENTS_DIR = Path("/mnt/sdcard/AA_MY_DRIVE/.claude/agents")


@lru_cache(maxsize=64)
def load_agent(slug_or_name: str) -> dict:
    """
    Find an agent file by slug, name, or partial match.
    Returns a parsed dict with the persona fields.
    """
    if not slug_or_name:
        return _default_voice()

    candidates = [
        AGENTS_DIR / f"{slug_or_name}.md",
        AGENTS_DIR / f"{slug_or_name.lower()}.md",
    ]
    # Try exact match first
    for p in candidates:
        if p.exists():
            return _parse_firmware(p.read_text())

    # Try fuzzy: any file whose basename contains the slug
    needle = slug_or_name.lower().replace(" ", "_").replace("-", "_")
    for p in sorted(AGENTS_DIR.glob("*.md")):
        if needle in p.stem.lower().replace("-", "_"):
            return _parse_firmware(p.read_text())

    return _default_voice()


def _default_voice() -> dict:
    return {
        "name": "Everlight Ventures",
        "email": "team@everlightventures.io",
        "title": "Acquisitions",
        "speech_style": "professional, warm, concise",
        "tone": "neutral",
        "openers": ["Hi {first},"],
        "signoff": "Best,",
        "signature_block": "Everlight Ventures",
        "verbal_tics": [],
        "catchphrase": "",
        "uses_names": False,
        "uses_exclamations": False,
        "regional_dialect": None,
    }


def _grab(md: str, *labels: str) -> str:
    """Pull a value from `**Label:** value` lines."""
    for label in labels:
        m = re.search(rf"\*\*{re.escape(label)}:\*\*\s*([^\n]+)", md, re.I)
        if m:
            return m.group(1).strip()
    return ""


def _parse_firmware(md: str) -> dict:
    """Parse an agent .md file into a voice dict."""
    voice = _default_voice()

    # Frontmatter name
    fm = re.match(r"---\s*\n(.+?)\n---", md, re.S)
    if fm:
        for line in fm.group(1).splitlines():
            if line.startswith("name:"):
                voice["frontmatter_name"] = line.split(":", 1)[1].strip()

    # Identity block
    name = _grab(md, "Name")
    if name:
        voice["name"] = name
    email = _grab(md, "Email")
    if email:
        voice["email"] = email
    dept = _grab(md, "Department")
    if dept:
        voice["department"] = dept
    personality = _grab(md, "Personality")
    if personality:
        voice["personality"] = personality
    tone = _grab(md, "Tone")
    if tone:
        voice["tone"] = tone
    catch = _grab(md, "Catchphrase")
    if catch:
        voice["catchphrase"] = catch.strip('"').strip("'")

    # Speech style block (the gold)
    m = re.search(r"\*\*Speech style:\*\*\s*(.+?)(?=\n\s*-\s+\*\*|$)", md, re.S | re.I)
    if m:
        voice["speech_style"] = re.sub(r"\s+", " ", m.group(1)).strip()

    # Detect dialectal cues
    style_text = voice.get("speech_style", "").lower()
    if any(c in style_text for c in ("y'all", "honey", "bless", "drawl", "nashville",
                                        "memphis", "southern", "tennessee", "texas")):
        voice["regional_dialect"] = "southern"
    if "uses people's names" in style_text or "generous with names" in style_text:
        voice["uses_names"] = True
    if "exclamation" in style_text or "!" in style_text:
        voice["uses_exclamations"] = True
    if "concise" in style_text or "direct" in style_text:
        voice["concise"] = True

    # Openers from "Says yes:" / catchphrase
    yes_line = _grab(md, "Says yes")
    if yes_line:
        voice["affirmative"] = yes_line.strip('"').strip("'")[:80]

    # Signature block (look for ``` block with signature)
    m = re.search(r"```\n(.+?)\n```", md, re.S)
    if m and "@everlightventures" in m.group(1):
        voice["signature_block"] = m.group(1).strip()

    # Title from signature block second line
    if voice.get("signature_block"):
        lines = voice["signature_block"].split("\n")
        if len(lines) >= 2:
            voice["title"] = lines[1].strip()

    # Build openers from voice cues
    voice["openers"] = _build_openers(voice)
    voice["signoff"] = _build_signoff(voice)

    return voice


def _build_openers(voice: dict) -> list[str]:
    """Construct opener templates from the agent's voice cues."""
    openers = []
    name = voice.get("name", "Friend")
    first = name.split()[0] if name else "Friend"
    use_names = voice.get("uses_names")
    excl = voice.get("uses_exclamations")
    dialect = voice.get("regional_dialect")
    tone_lc = voice.get("tone", "").lower()

    if dialect == "southern":
        openers.append("Hey {first}, hope y'all are doing well.")
        if excl:
            openers.append("{first}! Quick note from down the road --")
        openers.append("{first}, real quick from Memphis --")
    elif "warm" in tone_lc:
        if use_names:
            openers.append("Hey {first} -- Piper here.")
            openers.append("Hi {first}!")
        else:
            openers.append("Hi {first} --")
    elif "concise" in tone_lc or "direct" in tone_lc:
        openers.append("{first} --")
        openers.append("Hi {first},")
    else:
        openers.append("Hi {first},")
        openers.append("{first} --")

    return openers


def _build_signoff(voice: dict) -> str:
    """Construct sign-off appropriate to voice."""
    dialect = voice.get("regional_dialect")
    tone_lc = voice.get("tone", "").lower()
    if dialect == "southern":
        return "Talk soon,"
    if "warm" in tone_lc and voice.get("uses_exclamations"):
        return "Talk soon!"
    if "warm" in tone_lc:
        return "Best,"
    if "concise" in tone_lc:
        return "Best,"
    return "Best,"


def render_signature(voice: dict) -> str:
    """HTML signature block for an email."""
    name = voice.get("name", "Everlight Ventures")
    title = voice.get("title", "")
    email = voice.get("email", "")
    sig = voice.get("signature_block")
    if sig:
        return sig.replace("\n", "<br>")
    return f"<strong>{name}</strong><br>{title}<br>Everlight Ventures<br><a href='mailto:{email}'>{email}</a>"


# CLI smoke test
if __name__ == "__main__":
    import json, sys
    slug = sys.argv[1] if len(sys.argv) > 1 else "marquise_reed_acquisitions"
    v = load_agent(slug)
    print(json.dumps(v, indent=2))
