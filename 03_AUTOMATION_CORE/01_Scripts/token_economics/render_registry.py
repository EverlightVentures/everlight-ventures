"""Render the key registry as a branded HTML view (gold Everlight theme).

Reads the JSON catalog, groups by project, surfaces a "needs attention" block
(leaked / unconfirmed / expiring), and writes KEY_REGISTRY.html. Brand theme is
applied by content_tools.report_template (single source of truth for the palette).
"""
from __future__ import annotations

import html
from pathlib import Path

from content_tools import report_template
from token_economics import key_registry as kr

OUT_PATH = str(Path(__file__).parent / "KEY_REGISTRY.html")
TODAY = "2026-06-25"


def _row(e: kr.KeyEntry) -> str:
    cost = f"${e.monthly_cost_usd:.2f}" if e.monthly_cost_usd else "-"
    exp = e.expires or "no expiry"
    status_label = e.status.upper()
    return (
        "<tr>"
        f"<td><strong>{html.escape(e.key_name)}</strong></td>"
        f"<td>{html.escape(e.sub_avenue)}</td>"
        f"<td>{html.escape(e.provider)}</td>"
        f"<td>{html.escape(e.owner)}</td>"
        f"<td>{html.escape(exp)}</td>"
        f"<td>{cost}</td>"
        f"<td>{html.escape(status_label)}</td>"
        f"<td>{html.escape(e.value_location)}</td>"
        "</tr>"
    )


def _table(entries: list[kr.KeyEntry]) -> str:
    head = (
        "<table><thead><tr>"
        "<th>Key</th><th>Sub-avenue</th><th>Provider</th><th>Owner</th>"
        "<th>Expires</th><th>Monthly cost</th><th>Status</th><th>Stored in</th>"
        "</tr></thead><tbody>"
    )
    body = "".join(_row(e) for e in sorted(entries, key=lambda x: x.key_name))
    return head + body + "</tbody></table>"


def build_content(entries: list[kr.KeyEntry]) -> str:
    parts: list[str] = []
    costs = kr.monthly_cost_by_project(entries)
    total = sum(costs.values())
    projects = kr.by_project(entries)

    parts.append(
        f"<p><strong>{len(entries)}</strong> keys across "
        f"<strong>{len(projects)}</strong> projects. "
        f"Tracked monthly cost: <strong>${total:.2f}</strong> "
        "(per-key costs land in Phase 2).</p>"
    )

    leaked = [e for e in entries if e.status == "leaked"]
    unconfirmed = [e for e in entries if e.project == "UNCONFIRMED"]
    expiring = kr.expiring_within(entries, 30, today=TODAY)

    if leaked or unconfirmed or expiring:
        parts.append("<h2>Needs attention</h2>")
        if leaked:
            parts.append("<h3>Hardcoded secrets to move + rotate</h3>")
            parts.append(_table(leaked))
        if expiring:
            parts.append("<h3>Expiring within 30 days</h3>")
            parts.append(_table(expiring))
        if unconfirmed:
            parts.append("<h3>Unconfirmed project tag (please confirm)</h3>")
            parts.append(_table(unconfirmed))

    parts.append("<h2>By project</h2>")
    for proj in sorted(projects):
        sub = costs.get(proj, 0.0)
        parts.append(f"<h3>{html.escape(proj)} (${sub:.2f}/mo, {len(projects[proj])} keys)</h3>")
        parts.append(_table(projects[proj]))

    return "\n".join(parts)


def main() -> int:
    entries = kr.load_registry()
    violations = kr.validate_registry(entries)
    if violations:
        print("Refusing to render: registry has violations:")
        for v in violations:
            print("  -", v)
        return 1
    content = build_content(entries)
    doc = report_template.render_report(
        title="API Key Registry",
        content_html=content,
        agent_name="Token Economics OS",
        agent_title="Key Registry (Phase 1)",
        confidential=True,
    )
    Path(OUT_PATH).write_text(doc)
    print(f"Wrote {OUT_PATH} ({len(entries)} keys)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
