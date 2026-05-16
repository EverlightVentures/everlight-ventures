"""Ad-hoc guest persona builder for the Hive Roundtable.

Generates a structured dossier for a public-domain figure (e.g., "Charlie Munger",
"Seth Godin", "Warren Buffett") that the roundtable can load alongside real Hive
members. Output matches the .claude/agents/*.md format so Solomon's engine can
treat guests and natives interchangeably.

Strict rules:
  - Public-domain figures ONLY. No prospects, no operators, no real clients.
  - Eradication-gate scan on the name before any generation begins.
  - Output is clearly marked as GENERATED so it can never be mistaken for a
    real Hive member's dossier.
  - Caches to roundtable/guests/{slug}.md -- re-runs are no-ops unless --force.

Usage:
    python persona_builder.py "Charlie Munger" --focus "mental models, inversion"
    python persona_builder.py "Seth Godin" --voice "warm, contrarian, marketing"

Public API:
    from hive_mind.roundtable.persona_builder import build_guest
    path = build_guest("Charlie Munger", focus="mental models")
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

# Workspace + path setup -----------------------------------------------------
WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
for candidate in (Path("/mnt/sdcard/AA_MY_DRIVE"), Path("/home/opc/AA_MY_DRIVE"), Path("/home/opc")):
    if candidate.exists():
        WORKSPACE = candidate
        break

GUESTS_DIR = WORKSPACE / "06_DEVELOPMENT" / "everlight_os" / "hive_mind" / "roundtable" / "guests"
CONTENT_TOOLS = WORKSPACE / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"
if str(CONTENT_TOOLS) not in sys.path:
    sys.path.insert(0, str(CONTENT_TOOLS))

try:
    import eradication_gate  # type: ignore
    from eradication_gate import EradicationViolation  # type: ignore
except Exception as e:
    print(f"[persona_builder] CRITICAL: eradication_gate unavailable ({e}).", file=sys.stderr)
    raise


CLAUDE_MODEL = "claude-opus-4-7"


class PersonaBuilderError(Exception):
    """Raised when a guest persona cannot be generated."""


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s or "untitled"


def _gate(name: str) -> None:
    """Refuse to generate a persona for an eradicated subject."""
    if eradication_gate.outbound_halted():
        raise PersonaBuilderError("WHOLESALE_OUTBOUND_HALT=1 is active. Guest generation refused.")
    eradication_gate.assert_safe(name=name, caller="persona_builder")


def _build_prompt(name: str, focus: str, voice: str) -> str:
    return f"""You are generating a structured persona dossier for a Hive Roundtable guest.

GUEST: {name}
{f'FOCUS AREA: {focus}' if focus else ''}
{f'VOICE NOTES: {voice}' if voice else ''}

Produce a markdown dossier in EXACTLY the format below. Use only public-domain
information about this figure -- their known body of work, public writings,
interviews, and publicly-documented frameworks. NEVER invent private opinions
or insert speculation about living individuals' undisclosed views.

If the named figure is:
  - Living, public, and well-documented (e.g., Charlie Munger, Seth Godin, Naval Ravikant): use their documented frameworks and public voice.
  - Historical (e.g., Cleopatra, Shakespeare, Lincoln): use scholarly consensus about their voice and perspective.
  - Fictional or unknown: refuse, and respond ONLY with: "REFUSED: {name} is not a public-domain figure with documented frameworks."

Otherwise, output the dossier verbatim in this structure:

---
name: {_slug(name)}
description: GUEST PERSONA -- {{one-sentence description of their lane and what they bring to a Hive roundtable}}
tools: Read, Grep, Glob
generated: true
generated_at: {datetime.now().isoformat()}
---

# {name} (Generated Guest Persona)

> **GENERATED PERSONA** -- this is a roundtable guest, not a Hive employee. Sourced from public-domain documentation only.

## Identity
- **Name:** {name}
- **Role:** {{their public role / what they're known for}}
- **Personality:** {{2-3 adjectives based on public record}}
- **Tone:** {{how they sound in interviews / writings}}
- **Catchphrase:** {{a phrase they're publicly known for, or "n/a" if none}}

## Firmware
- **Speech style:** {{documented patterns -- vocabulary, cadence, common analogies}}
- **Frameworks they're known for:** {{numbered list of their 2-4 most-cited public frameworks}}
- **How they push back:** {{their documented disagreement style}}
- **Known weak points / blind spots:** {{publicly-acknowledged or widely-noted limitations}}

## Mission in this Roundtable
{{One paragraph: what kind of question is this figure especially useful for? Where will their voice be most valuable in the cross-fire?}}

## Rules
- This is a GENERATED guest. Their words here are an interpretation of their public corpus, not actual statements.
- Never attribute private opinions or undisclosed personal views.
- If asked about a topic clearly outside their public domain, they should say so directly.

## Dossier
- **Background:** {{1-2 sentences of public bio}}
- **Documented voice:** {{1 sentence on what makes their voice distinctive}}
- **Best used for:** {{1 sentence -- what kind of roundtable question}}

---

Generate the dossier now. Output ONLY the markdown -- no preamble, no commentary."""


def _generate_via_anthropic(prompt: str) -> str:
    try:
        import anthropic  # type: ignore
    except ImportError:
        raise PersonaBuilderError(
            "anthropic SDK not installed. Run: pip install anthropic"
        )
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2000,
        system="You generate clean, structured persona dossiers for an internal roundtable engine. You use ONLY public-domain information. You refuse to invent private opinions.",
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def build_guest(
    name: str,
    focus: str = "",
    voice: str = "",
    force: bool = False,
    mock: bool = False,
) -> Path:
    """Generate (or load cached) guest persona dossier.

    Returns the Path to the dossier file. Raises PersonaBuilderError on refusal
    or compliance gate failure.
    """
    _gate(name)

    GUESTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = GUESTS_DIR / f"{_slug(name)}.md"

    if out_path.exists() and not force:
        return out_path

    if mock:
        # Canned dossier for orchestration validation only
        content = f"""---
name: {_slug(name)}
description: GUEST PERSONA (MOCK) -- canned dossier for smoke testing only.
tools: Read, Grep, Glob
generated: true
generated_at: {datetime.now().isoformat()}
mock: true
---

# {name} (Generated Guest Persona, MOCK)

> **GENERATED PERSONA -- MOCK BUILD** -- not for real decisions.

## Identity
- **Name:** {name}
- **Role:** Public-figure roundtable guest (mock)
- **Personality:** Sharp, contrarian, principled.
- **Tone:** Direct, dry, occasional analogies.
- **Catchphrase:** "Invert. Always invert."

## Firmware
- **Speech style:** Short declarative sentences. Frequent appeals to first-principles thinking.
- **Frameworks:** {focus or "first-principles reasoning, inversion, second-order effects"}
- **How they push back:** Names the assumption, inverts it, asks what falls.
- **Known weak points:** Mock persona -- treat with skepticism.

## Mission in this Roundtable
Bring a contrarian, first-principles read. {voice or "Probe assumptions the room is treating as settled."}

## Rules
- MOCK persona for smoke testing only. Do not treat as real generation.
"""
    else:
        prompt = _build_prompt(name, focus, voice)
        content = _generate_via_anthropic(prompt)

        if content.strip().startswith("REFUSED:"):
            raise PersonaBuilderError(content.strip())

    out_path.write_text(content)
    return out_path


def _cli() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a guest persona dossier for the Hive Roundtable",
    )
    parser.add_argument("name", help="Public-domain figure (e.g., 'Charlie Munger')")
    parser.add_argument("--focus", default="", help="Focus area (e.g., 'mental models, inversion')")
    parser.add_argument("--voice", default="", help="Voice notes (e.g., 'warm, contrarian')")
    parser.add_argument("--force", action="store_true", help="Regenerate even if cached")
    parser.add_argument("--mock", action="store_true", help="Generate a mock dossier (no API)")
    args = parser.parse_args()

    try:
        path = build_guest(
            name=args.name,
            focus=args.focus,
            voice=args.voice,
            force=args.force,
            mock=args.mock,
        )
    except PersonaBuilderError as e:
        print(f"[persona_builder] {e}", file=sys.stderr)
        return 2
    except EradicationViolation as e:
        print(f"[persona_builder] ERADICATION VIOLATION: {e}", file=sys.stderr)
        return 3

    print(f"Guest persona written: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
