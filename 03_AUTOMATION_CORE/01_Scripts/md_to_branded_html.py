#!/usr/bin/env python3
"""
md_to_branded_html.py -- Convert a markdown file to branded gold-on-dark HTML.

Per memory rule: feedback_html_not_md HARD LAW (2026-04-30 + reinforced 2026-05-13).

Usage:
    python3 md_to_branded_html.py <input.md> [output.html] [--title "Custom Title"]
                                              [--agent "Author Name"]
                                              [--keep-md]   # default: deletes the .md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
sys.path.insert(0, str(ROOT / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"))

from report_template import render_report  # noqa: E402


def md_to_html(md: str) -> str:
    """Lightweight markdown → HTML for our docs (no full md parser dependency)."""
    lines = md.splitlines()
    out: list[str] = []
    in_code = False
    in_list = False
    in_table = False
    table_rows: list[str] = []

    def flush_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    def flush_table():
        nonlocal in_table, table_rows
        if in_table and table_rows:
            out.append("<table style='width:100%;border-collapse:collapse;font-size:14px;margin:16px 0;'>")
            for i, row in enumerate(table_rows):
                cells = [c.strip() for c in row.strip().strip("|").split("|")]
                tag = "th" if i == 0 else "td"
                style = "padding:8px;border-bottom:1px solid #2a2a2a;text-align:left;"
                if i == 0:
                    style += "border-bottom:2px solid #D4A843;background:#1a1a1a;color:#D4A843;"
                cell_html = "".join(f"<{tag} style='{style}'>{inline_md(c)}</{tag}>" for c in cells)
                out.append(f"<tr>{cell_html}</tr>")
            out.append("</table>")
            table_rows = []
            in_table = False

    def inline_md(text: str) -> str:
        # Code spans first (so other replacements don't break them)
        text = re.sub(r"`([^`]+)`",
                      r"<code style='background:#1a1a1a;color:#D4A843;padding:2px 6px;border-radius:3px;font-family:JetBrains Mono,monospace;font-size:13px;'>\1</code>",
                      text)
        # Bold
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong style='color:#E8E8E8;'>\1</strong>", text)
        # Italic (single *)
        text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
        # Links
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                      r"<a href='\2' style='color:#D4A843;text-decoration:underline;'>\1</a>",
                      text)
        return text

    for raw in lines:
        line = raw.rstrip()

        # Code fence
        if line.startswith("```"):
            flush_list()
            flush_table()
            if not in_code:
                lang = line[3:].strip()
                out.append(f"<pre style='background:#0d0d0d;color:#E8E8E8;padding:16px;border-left:3px solid #D4A843;overflow-x:auto;font-family:JetBrains Mono,monospace;font-size:13px;line-height:1.5;margin:16px 0;'><code class='{lang}'>")
                in_code = True
            else:
                out.append("</code></pre>")
                in_code = False
            continue

        if in_code:
            esc = (line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
            out.append(esc)
            continue

        # Headings
        if line.startswith("# "):
            flush_list()
            flush_table()
            out.append(f"<h1 style='font-family:Playfair Display,serif;color:#D4A843;font-size:28px;margin:24px 0 12px;border-bottom:2px solid #2a2a2a;padding-bottom:8px;'>{inline_md(line[2:])}</h1>")
            continue
        if line.startswith("## "):
            flush_list()
            flush_table()
            out.append(f"<h2 style='font-family:Playfair Display,serif;color:#D4A843;font-size:22px;margin:20px 0 10px;'>{inline_md(line[3:])}</h2>")
            continue
        if line.startswith("### "):
            flush_list()
            flush_table()
            out.append(f"<h3 style='font-family:Playfair Display,serif;color:#E8E8E8;font-size:18px;margin:16px 0 8px;border-left:3px solid #D4A843;padding-left:10px;'>{inline_md(line[4:])}</h3>")
            continue
        if line.startswith("#### "):
            flush_list()
            flush_table()
            out.append(f"<h4 style='color:#E8E8E8;font-size:16px;margin:12px 0 6px;'>{inline_md(line[5:])}</h4>")
            continue

        # Tables (markdown pipe-style)
        if "|" in line and line.count("|") >= 2:
            stripped = line.strip()
            if stripped.startswith("|"):
                flush_list()
                # Skip the separator row (---|---|...)
                if re.match(r"^[\s|:\-]+$", stripped):
                    in_table = True
                    continue
                in_table = True
                table_rows.append(stripped)
                continue
        flush_table()

        # Lists
        if re.match(r"^\s*[-*]\s+", line):
            if not in_list:
                out.append("<ul style='margin:8px 0 16px 0;padding-left:24px;'>")
                in_list = True
            content = re.sub(r"^\s*[-*]\s+", "", line)
            out.append(f"<li style='margin:4px 0;'>{inline_md(content)}</li>")
            continue
        if re.match(r"^\s*\d+\.\s+", line):
            flush_list()
            content = re.sub(r"^\s*\d+\.\s+", "", line)
            out.append(f"<p style='margin:6px 0 6px 24px;'>{inline_md(content)}</p>")
            continue
        flush_list()

        # Horizontal rule
        if line.strip() == "---":
            out.append("<hr style='border:none;border-top:1px solid #2a2a2a;margin:24px 0;'>")
            continue

        # Blank line
        if not line.strip():
            out.append("")
            continue

        # Paragraph
        out.append(f"<p style='margin:8px 0;'>{inline_md(line)}</p>")

    flush_list()
    flush_table()
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_md", type=Path)
    ap.add_argument("output_html", type=Path, nargs="?", default=None)
    ap.add_argument("--title", default=None)
    ap.add_argument("--agent", default="Hive Mind")
    ap.add_argument("--agent-title", default="Operations Intelligence")
    ap.add_argument("--keep-md", action="store_true")
    args = ap.parse_args()

    if not args.input_md.exists():
        print(f"missing: {args.input_md}", file=sys.stderr)
        return 2

    md = args.input_md.read_text(encoding="utf-8")
    body_html = md_to_html(md)

    title = args.title or args.input_md.stem.replace("_", " ").title()
    html = render_report(
        title=title,
        content_html=body_html,
        agent_name=args.agent,
        agent_title=args.agent_title,
    )
    out_path = args.output_html or args.input_md.with_suffix(".html")
    out_path.write_text(html, encoding="utf-8")
    print(f"wrote {out_path}  ({len(html)} bytes)")

    if not args.keep_md:
        args.input_md.unlink()
        print(f"deleted {args.input_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
