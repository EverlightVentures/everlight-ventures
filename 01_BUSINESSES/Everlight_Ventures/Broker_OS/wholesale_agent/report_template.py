"""Everlight Report Template - generates styled HTML reports matching state_contract_matrix style.

Extracted from the gold-standard state_contract_matrix__8_markets report.
Style: Playfair Display headers, Inter body, #D4A843 gold, #0A0A0A black,
cards with left-border accents, badges, professional tables.

Usage:
    from report_template import render_report
    html = render_report(
        title="Pipeline Daily Report",
        content_html="<h2>Results</h2><p>12 leads scouted</p>",
        agent_name="Rex Blackwell",
        agent_title="Director of Acquisitions",
        agent_email="rex.b@everlightventures.io",
    )
"""
from __future__ import annotations

from datetime import datetime, timezone


def _now_pt() -> str:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%B %d, %Y %I:%M %p PT")
    except Exception:
        return datetime.now(timezone.utc).strftime("%B %d, %Y %H:%M UTC")


def _now_short() -> str:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y%m%d_%H%M")
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")


# The gold-standard CSS from state_contract_matrix
EVERLIGHT_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@400;600;700&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  background: #0A0A0A;
  color: #E8E8E8;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  line-height: 1.7;
  min-height: 100vh;
}

.header {
  background: linear-gradient(135deg, #0A0A0A 0%, #1A1A1A 100%);
  border-bottom: 2px solid #D4A843;
  padding: 40px 0;
  text-align: center;
}

.header-inner {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 24px;
}

.logo {
  font-family: 'Playfair Display', serif;
  font-size: 14px;
  letter-spacing: 4px;
  text-transform: uppercase;
  color: #D4A843;
  margin-bottom: 16px;
}

.header h1 {
  font-family: 'Playfair Display', serif;
  font-size: 28px;
  font-weight: 600;
  color: #E8E8E8;
  margin-bottom: 8px;
}

.header .meta {
  font-size: 13px;
  color: #999999;
}

.header .meta span {
  color: #D4A843;
}

.content {
  max-width: 800px;
  margin: 0 auto;
  padding: 40px 24px;
}

.content h2 {
  font-family: 'Playfair Display', serif;
  font-size: 22px;
  color: #D4A843;
  margin: 32px 0 16px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid #1A1A1A;
}

.content h3 {
  font-size: 16px;
  font-weight: 600;
  color: #E8E8E8;
  margin: 24px 0 12px 0;
}

.content p {
  margin-bottom: 16px;
  font-size: 15px;
}

.content ul, .content ol {
  margin: 0 0 16px 24px;
}

.content li {
  margin-bottom: 8px;
  font-size: 15px;
}

.content strong {
  color: #D4A843;
  font-weight: 600;
}

.card {
  background: #111111;
  border: 1px solid #222;
  border-left: 3px solid #D4A843;
  border-radius: 8px;
  padding: 20px 24px;
  margin: 16px 0;
}

.card.success { border-left-color: #4CAF50; }
.card.warning { border-left-color: #FF9800; }
.card.danger { border-left-color: #F44336; }

table {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  font-size: 14px;
}

th {
  background: #1A1A1A;
  color: #D4A843;
  text-align: left;
  padding: 12px 16px;
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

td {
  padding: 10px 16px;
  border-bottom: 1px solid #1a1a1a;
}

tr:hover td { background: #1A1A1A; }

code {
  background: #1A1A1A;
  color: #D4A843;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}

pre {
  background: #1A1A1A;
  border: 1px solid #222;
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
  margin: 16px 0;
  font-size: 13px;
  line-height: 1.5;
}

.footer {
  text-align: center;
  padding: 40px 24px;
  color: #999999;
  font-size: 12px;
  border-top: 1px solid #1a1a1a;
}

.footer .brand {
  color: #D4A843;
  font-family: 'Playfair Display', serif;
  font-size: 14px;
  letter-spacing: 2px;
}

.sig {
  margin-top: 40px;
  padding-top: 20px;
  border-top: 1px solid #222;
}

.sig .name {
  color: #D4A843;
  font-weight: 600;
  font-size: 15px;
}

.sig .role, .sig .contact {
  color: #999;
  font-size: 13px;
}

.badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
}
.badge-gold { background: #D4A843; color: #0A0A0A; }
.badge-green { background: #4CAF50; color: white; }
.badge-red { background: #F44336; color: white; }
.badge-orange { background: #FF9800; color: #0A0A0A; }

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
  margin: 20px 0;
}

.kpi {
  background: #111;
  border: 1px solid #222;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}

.kpi .value {
  font-size: 28px;
  font-weight: 700;
  color: #D4A843;
  font-family: 'Playfair Display', serif;
}

.kpi .label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #999;
  margin-top: 4px;
}
"""


def render_report(
    *,
    title: str,
    content_html: str,
    agent_name: str = "Everlight Ventures",
    agent_title: str = "Automated Intelligence",
    agent_email: str = "hello@everlightventures.io",
    confidential: bool = False,
) -> str:
    """Render a full branded HTML report.

    Args:
        title: Report title
        content_html: Inner HTML content (h2, p, table, cards, etc.)
        agent_name: Preparing agent's name
        agent_title: Agent's title
        agent_email: Agent's email
        confidential: Show CONFIDENTIAL badge

    Returns:
        Complete HTML string ready to save as .html file
    """
    ts = _now_pt()
    conf_badge = ' | <span>CONFIDENTIAL</span>' if confidential else ''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | Everlight Ventures</title>
<style>{EVERLIGHT_CSS}</style>
</head>
<body>

<div class="header">
  <div class="header-inner">
    <div class="logo">Everlight Ventures</div>
    <h1>{title}</h1>
    <div class="meta">
      Prepared by <span>{agent_name}</span> | {ts}{conf_badge}
    </div>
  </div>
</div>

<div class="content">
{content_html}

<div class="sig">
  <div class="name">{agent_name}</div>
  <div class="role">{agent_title}</div>
  <div class="contact">{agent_email} | everlightventures.io</div>
</div>
</div>

<div class="footer">
  <div class="brand">Everlight Ventures</div>
  <p style="margin-top: 8px;">Generated by the Everlight Hive Mind | Sacramento, CA</p>
  <p style="margin-top: 4px;">everlightventures.io</p>
</div>

</body>
</html>"""


def safe_filename(title: str) -> str:
    """Generate a safe filename from a title."""
    clean = title.lower().replace(" ", "_").replace("/", "_").replace("--", "_")
    clean = "".join(c for c in clean if c.isalnum() or c == "_")
    return f"{clean}_{_now_short()}.html"


# Convenience helpers for common content patterns

def kpi_grid(kpis: list[tuple[str, str]]) -> str:
    """Generate a KPI grid. kpis = [(value, label), ...]"""
    items = "\n".join(
        f'<div class="kpi"><div class="value">{v}</div><div class="label">{l}</div></div>'
        for v, l in kpis
    )
    return f'<div class="kpi-grid">{items}</div>'


def table(headers: list[str], rows: list[list[str]]) -> str:
    """Generate a styled table."""
    th = "".join(f"<th>{h}</th>" for h in headers)
    trs = "\n".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>"


def card(content: str, variant: str = "") -> str:
    """Generate a card. variant: success, warning, danger, or empty for gold."""
    cls = f"card {variant}" if variant else "card"
    return f'<div class="{cls}">{content}</div>'


def badge(text: str, color: str = "gold") -> str:
    """Generate a badge. color: gold, green, red, orange."""
    return f'<span class="badge badge-{color}">{text}</span>'
