"""
pdf_certificate.py -- generates a PDF signature certificate for any signed document.

Uses reportlab (pre-installed). Produces a PDF/A-style document with:
  - Branded header (gold accent, Playfair-ish heading)
  - Document being certified (title + SHA-256)
  - Signer info (name, email, IP, user agent, timestamp)
  - Signature SHA-256 (the cryptographic seal)
  - Legal attestation block (UETA + E-SIGN Act citations)
  - QR code link back to verifiable record (optional)

The PDF is the artifact that gets emailed to all parties + saved to the deal dir.
"""
from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (Paragraph, Spacer, Table, TableStyle,
                                  SimpleDocTemplate, PageBreak)

GOLD = colors.HexColor("#d4a843")
GOLD_HOT = colors.HexColor("#ffcd3c")
GOLD_DEEP = colors.HexColor("#b8902f")
DARK = colors.HexColor("#0a0a0a")
PAPER = colors.HexColor("#15140d")
TEXT = colors.HexColor("#1a1a1a")  # dark text on white paper
MUTED = colors.HexColor("#6a6555")
BORDER = colors.HexColor("#322a14")


def render_signature_certificate_pdf(out_path: str | Path, sig: dict) -> Path:
    """
    sig dict expected fields (from esign_server.submit_signature):
      deal_key, doc_id, signer_name, signer_email, intent_affirmed,
      signed_at, ip, user_agent, document_sha256, signature_sha256
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.65 * inch, bottomMargin=0.65 * inch,
        title=f"Signature Certificate - {sig.get('doc_id', 'document')}",
        author="Everlight Ventures",
    )
    styles = getSampleStyleSheet()

    h1 = ParagraphStyle("h1", parent=styles["Heading1"],
                          fontName="Helvetica-Bold", fontSize=22, leading=26,
                          textColor=GOLD_DEEP, spaceAfter=4)
    label = ParagraphStyle("label", parent=styles["Normal"],
                              fontName="Courier-Bold", fontSize=8, leading=10,
                              textColor=GOLD, spaceAfter=2)
    body = ParagraphStyle("body", parent=styles["Normal"],
                            fontName="Helvetica", fontSize=10, leading=14,
                            textColor=TEXT, spaceAfter=6)
    mono = ParagraphStyle("mono", parent=styles["Normal"],
                            fontName="Courier", fontSize=8, leading=11,
                            textColor=MUTED)
    legal = ParagraphStyle("legal", parent=styles["Normal"],
                             fontName="Helvetica", fontSize=8, leading=11,
                             textColor=MUTED, spaceAfter=4)

    elements = []

    # Header
    elements.append(Paragraph(
        "EVERLIGHT VENTURES &nbsp;&nbsp;&#9670;&nbsp;&nbsp; SIGNATURE CERTIFICATE",
        label,
    ))
    elements.append(Paragraph(f"Signed: {sig.get('doc_id', '')}", h1))
    elements.append(Paragraph(
        f"Deal: <b>{sig.get('deal_key', '')}</b>", body))
    elements.append(Spacer(1, 14))

    # Signer block
    signer_data = [
        ["Signer name", sig.get("signer_name", "")],
        ["Signer email", sig.get("signer_email", "")],
        ["Signed at (UTC)", sig.get("signed_at", "")],
        ["From IP", sig.get("ip", "")],
        ["User agent", (sig.get("user_agent", "") or "")[:80]],
        ["Intent affirmed", "YES (checkbox required to submit)" if sig.get("intent_affirmed") else "NO"],
    ]
    t = Table(signer_data, colWidths=[1.6 * inch, 5.0 * inch])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (0, -1), "Courier-Bold", 8),
        ("FONT", (1, 0), (1, -1), "Helvetica", 9),
        ("TEXTCOLOR", (0, 0), (0, -1), GOLD_DEEP),
        ("TEXTCOLOR", (1, 0), (1, -1), TEXT),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(Paragraph("SIGNER", label))
    elements.append(t)
    elements.append(Spacer(1, 14))

    # Cryptographic seals
    crypto_data = [
        ["Document SHA-256", sig.get("document_sha256", "")],
        ["Signature SHA-256", sig.get("signature_sha256", "")],
    ]
    ct = Table(crypto_data, colWidths=[1.6 * inch, 5.0 * inch])
    ct.setStyle(TableStyle([
        ("FONT", (0, 0), (0, -1), "Courier-Bold", 8),
        ("FONT", (1, 0), (1, -1), "Courier", 7),
        ("TEXTCOLOR", (0, 0), (0, -1), GOLD_DEEP),
        ("TEXTCOLOR", (1, 0), (1, -1), TEXT),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(Paragraph("CRYPTOGRAPHIC SEALS", label))
    elements.append(ct)
    elements.append(Spacer(1, 14))

    # Legal block
    elements.append(Paragraph("LEGAL", label))
    elements.append(Paragraph(
        "This electronic signature is binding under the federal Electronic Signatures in "
        "Global and National Commerce Act (15 U.S.C. &#167; 7001) and the Tennessee Uniform "
        "Electronic Transactions Act (Tenn. Code Ann. &#167; 47-10-101 <i>et seq.</i>). The "
        "signer affirmed intent to sign by checking a required intent box prior to submission. "
        "The signer's typed legal name, IP address, user agent, and submission timestamp are "
        "captured above. The document being signed is cryptographically pinned to its content "
        "at the moment of signing via SHA-256 hash, making any subsequent alteration of the "
        "document detectable.",
        legal,
    ))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        "<b>Verification:</b> The signature record is also stored in the immutable, hash-chained "
        "deal_execution_log audit database. Any tampering with prior records breaks the chain "
        "and is detectable via the verify_chain() function.",
        legal,
    ))
    elements.append(Spacer(1, 14))

    # Footer line
    elements.append(Paragraph(
        f"Generated by Everlight E-Sign &nbsp;&#9670;&nbsp; "
        f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        ParagraphStyle("footer", parent=styles["Normal"],
                       fontName="Courier", fontSize=7, textColor=MUTED,
                       alignment=1),
    ))

    doc.build(elements, onFirstPage=_draw_brand_header, onLaterPages=_draw_brand_header)
    return out_path


def _draw_brand_header(canv: canvas.Canvas, doc):
    """Draw the gold accent line + brand chip on every page."""
    width, height = letter
    # Top hairline
    canv.setStrokeColor(GOLD)
    canv.setLineWidth(2)
    canv.line(0.75 * inch, height - 0.4 * inch, width - 0.75 * inch, height - 0.4 * inch)
    # Bottom hairline
    canv.setStrokeColor(GOLD_DEEP)
    canv.setLineWidth(0.5)
    canv.line(0.75 * inch, 0.5 * inch, width - 0.75 * inch, 0.5 * inch)
    # Page number
    canv.setFont("Courier", 7)
    canv.setFillColor(MUTED)
    canv.drawRightString(width - 0.75 * inch, 0.35 * inch, f"page {doc.page}")
    canv.drawString(0.75 * inch, 0.35 * inch, "EVERLIGHT VENTURES ◆ SIGNATURE CERTIFICATE")


if __name__ == "__main__":
    # Smoke test
    sample = {
        "deal_key": "2026-05-12_mikal_hakeem_1536_s_third",
        "doc_id": "01_PSA",
        "signer_name": "Mikal L. Hakeem",
        "signer_email": "mhakeem@timemphis.org",
        "intent_affirmed": True,
        "signed_at": "2026-05-12T18:55:00Z",
        "ip": "73.42.198.211",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)",
        "document_sha256": "a3f1c0b9d8e2c5a7f4b1e6d3c0a8f5b2e9d4c1a0f7b6e5d4c3a2b1f0e9d8c7a6",
        "signature_sha256": "e9d4c1a0f7b6e5d4c3a2b1f0e9d8c7a6a3f1c0b9d8e2c5a7f4b1e6d3c0a8f5b2",
    }
    out = render_signature_certificate_pdf(
        "/tmp/test_sig_cert.pdf", sample
    )
    print(f"  ✓ rendered {out}, size {out.stat().st_size:,} bytes")
