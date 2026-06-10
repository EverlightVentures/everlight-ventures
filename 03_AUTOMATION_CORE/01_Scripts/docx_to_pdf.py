#!/usr/bin/env python3
"""Offline .docx -> .pdf converter for the phone (no LibreOffice/cloud needed).

The phone proot has no office suite, and Android's default .docx handler tries to
round-trip through Google Docs/Drive -- which fails when offline. This renders a
clean, plain professional PDF locally using python-docx (read) + reportlab (write)
so the document opens in any PDF viewer or browser with zero app/network dependency.

Usage:
    python3 docx_to_pdf.py <input.docx> [output.pdf]

Run-level bold/italic is preserved. Lines that read as headings (ALL-CAPS, or a
Roman-numeral section like "I.", "II.") render larger/bold. Intentionally NOT
Everlight-branded -- personal/legal documents stay neutral black-on-white.
"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import docx
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

ROMAN_PREFIXES = tuple(f"{r}." for r in
                       ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"))


def run_markup(paragraph) -> str:
    """Rebuild a paragraph as reportlab mini-markup, preserving bold/italic runs."""
    parts = []
    for run in paragraph.runs:
        text = escape(run.text)
        if not text:
            continue
        if run.bold:
            text = f"<b>{text}</b>"
        if run.italic:
            text = f"<i>{text}</i>"
        parts.append(text)
    return "".join(parts) or escape(paragraph.text)


def looks_like_heading(paragraph) -> bool:
    t = paragraph.text.strip()
    if not t or len(t) > 90:
        return False
    if t.startswith(ROMAN_PREFIXES):
        return True
    letters = [c for c in t if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters)


def convert(in_path: Path, out_path: Path) -> Path:
    doc = docx.Document(str(in_path))
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["Normal"],
                          fontName="Helvetica", fontSize=11, leading=15, spaceAfter=8)
    head = ParagraphStyle("head", parent=body, fontName="Helvetica-Bold",
                          fontSize=12.5, spaceBefore=10, spaceAfter=6)

    flow = []
    for p in doc.paragraphs:
        if not p.text.strip():
            flow.append(Spacer(1, 6))
            continue
        style = head if looks_like_heading(p) else body
        flow.append(Paragraph(run_markup(p), style))

    SimpleDocTemplate(str(out_path), pagesize=letter,
                      topMargin=inch, bottomMargin=inch,
                      leftMargin=inch, rightMargin=inch,
                      title=in_path.stem).build(flow)
    return out_path


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    in_path = Path(argv[1])
    out_path = Path(argv[2]) if len(argv) > 2 else in_path.with_suffix(".pdf")
    convert(in_path, out_path)
    print(f"wrote {out_path}  ({out_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
