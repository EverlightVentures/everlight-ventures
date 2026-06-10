"""branded_calendar -- branded Google/Apple Calendar event description renderer.

Why this exists
---------------
Calendar invites are a high-touch surface. The prospect sees a notification,
they tap to view details, and the brand impression sticks. If the description
is plain text or generic boilerplate, you look like every other vendor.

This module produces a single canonical HTML body for every Hive-created
calendar event. Google Calendar and Apple Calendar both render the HTML
description (Google fully, Apple partially). The output uses the Everlight
gold palette and Playfair Display where supported.

Public API
----------
    from content_tools.branded_calendar import render_event_description

    html = render_event_description(
        title="Discovery Call: Everlight Ventures + Acme Corp",
        prospect_name="Alexandra",
        agent_name="Marcus Cole",
        agent_title="Chief Operator",
        agent_email="marcus@everlightventures.io",
        agenda=[
            "Review your current SaaS sourcing pipeline",
            "Walk through Everlight's broker model",
            "Decide on next 7-day action plan",
        ],
        meeting_link="https://meet.google.com/abc-defg-hij",
        notes="Bring any vendor lists you'd like sourced.",
    )

The HTML output drops directly into the `description` field of a Google
Calendar `events.insert` call.
"""
from __future__ import annotations

from html import escape
from typing import Iterable

BRAND_GOLD = "#D4AF37"
BRAND_BG = "#0A0A0A"
BRAND_FG = "#E8E8E8"
BRAND_MUTED = "#999999"


def render_event_description(
    *,
    title: str,
    prospect_name: str,
    agent_name: str,
    agent_title: str = "Everlight Ventures",
    agent_email: str = "",
    agenda: Iterable[str] | None = None,
    meeting_link: str = "",
    notes: str = "",
    confidential: bool = False,
) -> str:
    """Return a self-contained HTML body for a calendar event description.

    Inline-styled (no external CSS or fonts) because most calendar clients
    strip <style> blocks and external assets. Uses system fonts for max
    rendering compatibility.
    """
    title_safe = escape(title or "Everlight Ventures Meeting")
    prospect_safe = escape(prospect_name or "there")
    agent_safe = escape(agent_name)
    agent_title_safe = escape(agent_title)
    notes_safe = escape(notes).replace("\n", "<br>") if notes else ""

    parts: list[str] = []

    # Header band
    parts.append(
        f'<div style="background:{BRAND_BG};color:{BRAND_FG};padding:18px 20px;'
        f'border-left:4px solid {BRAND_GOLD};font-family:Georgia,Cambria,serif;">'
    )
    parts.append(
        f'<div style="font-size:11px;letter-spacing:3px;color:{BRAND_GOLD};'
        f'text-transform:uppercase;margin-bottom:6px;">EVERLIGHT VENTURES</div>'
    )
    parts.append(
        f'<div style="font-size:18px;color:{BRAND_FG};font-weight:600;">{title_safe}</div>'
    )
    if confidential:
        parts.append(
            f'<div style="font-size:10px;color:#EF4444;margin-top:6px;'
            f'letter-spacing:2px;text-transform:uppercase;">CONFIDENTIAL</div>'
        )
    parts.append("</div>")

    # Body
    parts.append(
        f'<div style="padding:18px 20px;color:#222;font-family:Georgia,Cambria,serif;'
        f'font-size:14px;line-height:1.7;background:#fafafa;">'
    )
    parts.append(f"<p>Hi {prospect_safe},</p>")
    parts.append(
        f"<p>Looking forward to connecting. Below is the agenda and meeting "
        f"details. If anything needs to shift, just reply to the calendar "
        f"invite or email me directly.</p>"
    )

    # Agenda
    items = [a for a in (agenda or []) if a and isinstance(a, str)]
    if items:
        parts.append(
            f'<div style="font-weight:600;color:{BRAND_GOLD};margin-top:14px;'
            f'margin-bottom:6px;letter-spacing:1px;text-transform:uppercase;'
            f'font-size:12px;">Agenda</div>'
        )
        parts.append('<ul style="margin:0 0 12px 22px;padding:0;">')
        for it in items[:12]:
            parts.append(f'<li style="margin-bottom:4px;">{escape(it)}</li>')
        parts.append("</ul>")

    # Meeting link CTA
    if meeting_link:
        parts.append(
            f'<div style="margin:18px 0;text-align:center;">'
            f'<a href="{escape(meeting_link)}" '
            f'style="background:linear-gradient(135deg,{BRAND_GOLD},#B8860B);'
            f'color:#000;padding:10px 26px;border-radius:6px;text-decoration:none;'
            f'font-weight:600;font-size:14px;display:inline-block;">'
            f'Join the Meeting</a></div>'
        )

    # Notes
    if notes_safe:
        parts.append(
            f'<div style="font-weight:600;color:{BRAND_GOLD};margin-top:14px;'
            f'margin-bottom:6px;letter-spacing:1px;text-transform:uppercase;'
            f'font-size:12px;">Notes</div>'
        )
        parts.append(f'<div style="color:#444;">{notes_safe}</div>')

    # Signature
    parts.append('<div style="margin-top:22px;padding-top:14px;border-top:1px solid #e0e0e0;">')
    parts.append(f'<div style="color:{BRAND_GOLD};font-weight:600;font-size:14px;">{agent_safe}</div>')
    parts.append(f'<div style="color:{BRAND_MUTED};font-size:12px;">{agent_title_safe}</div>')
    if agent_email:
        parts.append(
            f'<div style="color:{BRAND_MUTED};font-size:12px;">'
            f'<a href="mailto:{escape(agent_email)}" style="color:{BRAND_GOLD};'
            f'text-decoration:none;">{escape(agent_email)}</a> · '
            f'<a href="https://everlightventures.io" style="color:{BRAND_GOLD};'
            f'text-decoration:none;">everlightventures.io</a></div>'
        )
    parts.append("</div>")
    parts.append("</div>")  # body

    # Footer
    parts.append(
        f'<div style="text-align:center;padding:12px;color:{BRAND_MUTED};'
        f'font-size:10px;font-family:Georgia,serif;letter-spacing:2px;'
        f'background:{BRAND_BG};">EVERLIGHT VENTURES · The Mind Behind the Money</div>'
    )

    return "".join(parts)


def _cli() -> int:
    """Print a sample HTML body for local preview."""
    sample = render_event_description(
        title="Discovery Call: Everlight + Sample Co",
        prospect_name="Alex",
        agent_name="Marcus Cole",
        agent_title="Chief Operator",
        agent_email="marcus@everlightventures.io",
        agenda=[
            "Review your current SaaS sourcing pipeline",
            "Walk through Everlight's broker model",
            "Decide on next 7-day action plan",
        ],
        meeting_link="https://meet.google.com/sample",
        notes="Bring any vendor lists you'd like sourced.\nWe will share NDA on request.",
    )
    print(sample)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_cli())
