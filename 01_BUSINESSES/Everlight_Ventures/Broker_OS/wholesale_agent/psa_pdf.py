#!/usr/bin/env python3
"""
psa_pdf.py -- Convert the TN SB 909 PSA (render_psa_contract) to PDF and send
to Documenso for e-signature.

WHY a separate module instead of extending pdf_autofill.py:
  - pdf_autofill.py boots Django and requires broker_ops models. The new PSA
    pipeline runs from the wholesale_agent dir with plain dicts (lead, deal_terms)
    and must work standalone -- no Django required.
  - Keeping the modules separate means neither can break the other's callers.
  - pdf_autofill.main() stays intact for the old assignment.pdf path.

PDF library: fpdf2 (pure-Python, proot-safe, same lib pdf_autofill uses).
  reportlab is also installed but fpdf2 is lighter, already in use here, and
  does not require native extensions.

Entry points:
  psa_to_pdf(lead, deal_terms) -> Path
      Renders the 8-block PSA and writes a PDF to contracts_out/.
      Returns the Path to the .pdf file.

  send_psa_for_signature(deal, lead, deal_terms) -> str | None
      psa_to_pdf -> maybe_send_to_documenso.
      Returns the Documenso signing URL or None if key is unset / send fails.
      'deal' may be None when running outside Django (skips agreement_url save).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import textwrap
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Avoid hard Django import at module level -- see note above.
    pass

log = logging.getLogger("psa_pdf")
if not log.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s psa_pdf: %(message)s",
        datefmt="%H:%M:%S",
    )

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_WORKSPACE_ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
_AGENT_DIR = Path(__file__).parent
_CONTRACTS_OUT = _AGENT_DIR / "contracts_out"

# Fallback: Oracle prod path
_ORACLE_CONTRACTS_OUT = Path("/home/opc/wholesale_agent/contracts_out")


def _resolve_out_dir(deal_token: str) -> Path:
    base = _ORACLE_CONTRACTS_OUT if _ORACLE_CONTRACTS_OUT.parent.exists() else _CONTRACTS_OUT
    out = base / deal_token
    out.mkdir(parents=True, exist_ok=True)
    return out


# ---------------------------------------------------------------------------
# PDF generation -- fpdf2
# ---------------------------------------------------------------------------

def _wrap_lines(text: str, width: int = 95) -> list[str]:
    """Wrap plain text to width, preserving blank-line paragraph breaks."""
    result: list[str] = []
    for para in text.split("\n"):
        if para.strip() == "":
            result.append("")
        else:
            result.extend(textwrap.wrap(para, width=width) or [""])
    return result


def blocks_to_pdf(blocks: list[dict], out_path: Path, title: str = "", subtitle: str = "") -> Path:
    """Render a list of {title, body} blocks to a clean PDF.

    Uses fpdf2 (pure-Python). Output is title-company-readable: Helvetica
    throughout, section headers bold, body in 10pt. A narrow gold accent rule
    (#D4AF37) appears under the document title only -- the rest is clean black
    on white for court/legal readability.

    Returns the out_path.
    """
    try:
        from fpdf import FPDF
    except ImportError as exc:
        raise RuntimeError(
            "fpdf2 is required for psa_pdf. "
            "Install with: pip install fpdf2 --break-system-packages"
        ) from exc

    class _PSA(FPDF):
        def header(self):
            pass  # Custom title drawn once in body

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(120, 120, 120)
            self.cell(
                0, 10,
                f"Page {self.page_no()} -- CONFIDENTIAL PURCHASE AND SALE AGREEMENT -- Everlight Ventures",
                align="C",
            )
            self.set_text_color(0, 0, 0)

    pdf = _PSA(orientation="P", unit="mm", format="Letter")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_left_margin(20)
    pdf.set_right_margin(20)

    # -- Document title block -------------------------------------------------
    if title:
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT", align="C")
        # Gold accent rule (RGB #D4AF37)
        x0 = pdf.get_x()
        y0 = pdf.get_y()
        pdf.set_draw_color(212, 175, 55)
        pdf.set_line_width(0.8)
        pdf.line(20, y0, 195, y0)
        pdf.set_draw_color(0, 0, 0)
        pdf.set_line_width(0.2)
        pdf.ln(3)

    if subtitle:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(60, 60, 60)
        for line in subtitle.split("\n"):
            pdf.cell(0, 5, line, new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(4)

    # -- Blocks ---------------------------------------------------------------
    for blk in blocks:
        blk_title = blk.get("title", "")
        blk_body = blk.get("body", "")

        # Section header
        pdf.set_font("Helvetica", "B", 11)
        try:
            safe_title = blk_title.encode("latin-1", "replace").decode("latin-1")
        except Exception:
            safe_title = blk_title
        pdf.cell(0, 7, safe_title, new_x="LMARGIN", new_y="NEXT")

        # Light grey rule under section header
        y_rule = pdf.get_y()
        pdf.set_draw_color(180, 180, 180)
        pdf.line(20, y_rule, 195, y_rule)
        pdf.set_draw_color(0, 0, 0)
        pdf.ln(2)

        # Body text -- pass the whole block body to multi_cell with CHAR wrapmode
        # so long tokens (parcel IDs, URLs, legal phrases) never cause
        # "Not enough horizontal space" errors.
        pdf.set_font("Helvetica", "", 10)
        try:
            safe_body = blk_body.encode("latin-1", "replace").decode("latin-1")
        except Exception:
            safe_body = blk_body
        # fpdf2 2.x: multi_cell accepts the full text including embedded \n.
        # wrapmode="CHAR" ensures hard-to-break tokens wrap at character level.
        pdf.multi_cell(
            0, 5, safe_body,
            new_x="LMARGIN", new_y="NEXT",
            wrapmode="CHAR",
        )
        pdf.ln(5)

    pdf.output(str(out_path))
    return out_path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def psa_to_pdf(lead: dict, deal_terms: dict) -> Path:
    """Render the TN SB 909 PSA and write a PDF.

    Calls render_psa_contract from outreach_templates, then renders the
    blocks to a clean PDF via fpdf2.

    Returns the Path to the written .pdf file.
    """
    # Import render_psa_contract here so psa_pdf.py remains importable even if
    # outreach_templates is not on the path (tests monkeypatch it).
    _agent_dir = str(Path(__file__).parent)
    if _agent_dir not in sys.path:
        sys.path.insert(0, _agent_dir)

    from outreach_templates import render_psa_contract  # noqa: PLC0415

    psa = render_psa_contract(lead, deal_terms)
    blocks = psa["blocks"]

    addr = lead.get("property_address") or lead.get("address") or "PROPERTY ADDRESS"
    effective_date = deal_terms.get("effective_date") or datetime.now().strftime("%B %d, %Y")
    purchase_price = int(deal_terms.get("purchase_price") or 0)
    emd_amount = int(deal_terms.get("emd_amount") or 500)

    title = "PURCHASE AND SALE AGREEMENT"
    subtitle = (
        f"Property: {addr}\n"
        f"Effective Date: {effective_date}  |  "
        f"Purchase Price: ${purchase_price:,}  |  EMD: ${emd_amount:,}\n"
        f"Governed by Tennessee Law -- TN SB 909 / Public Chapter 911 (2022)"
    )

    # Resolve output directory
    seller_slug = (lead.get("owner_name") or "seller").lower()
    seller_slug = "".join(c if c.isalnum() else "_" for c in seller_slug)[:30]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    deal_token = f"psa_{seller_slug}_{ts}"

    out_dir = _resolve_out_dir(deal_token)
    pdf_path = out_dir / "psa_contract.pdf"

    log.info(f"Rendering PSA PDF for {addr} -> {pdf_path}")
    blocks_to_pdf(blocks, pdf_path, title=title, subtitle=subtitle)

    size = pdf_path.stat().st_size
    log.info(f"PDF written: {pdf_path} ({size:,} bytes)")
    return pdf_path


def send_psa_for_signature(
    deal,
    lead: dict,
    deal_terms: dict,
) -> str | None:
    """Generate the PSA PDF and send it to Documenso for e-signature.

    Args:
        deal: Django Deal instance (may be None -- skips agreement_url save).
        lead: plain dict (owner_name, property_address, owner_email, ...).
        deal_terms: plain dict (purchase_price, emd_amount, ...).

    Returns:
        Documenso signing URL string on success, None if key unset or send fails.
    """
    try:
        pdf_path = psa_to_pdf(lead, deal_terms)
    except Exception as exc:
        log.error(f"psa_to_pdf failed: {exc}")
        return None

    signing_url = _documenso_send_psa(deal, lead, deal_terms, pdf_path)
    return signing_url


# ---------------------------------------------------------------------------
# Documenso integration (PSA-specific)
# ---------------------------------------------------------------------------

def _documenso_send_psa(
    deal,
    lead: dict,
    deal_terms: dict,
    pdf_path: Path,
) -> str | None:
    """POST the PSA PDF to Documenso and return the signing URL.

    Mirrors the logic in pdf_autofill.maybe_send_to_documenso but:
    - Works with plain dicts (no Django ORM required for lead/deal_terms).
    - Uses PSA-specific title and subject lines.
    - deal may be None (skips agreement_url save).
    """
    api_url = os.environ.get(
        "DOCUMENSO_API_URL",
        "https://sign.everlightventures.io/api/v1",
    ).rstrip("/")
    api_key = os.environ.get("DOCUMENSO_API_KEY", "").strip()

    if not api_key:
        log.info(
            "DOCUMENSO_API_KEY not set -- PSA PDF saved locally but NOT sent for e-sign. "
            "See wholesale_agent/DOCUMENSO_SETUP.md to wire the key."
        )
        return None

    if not pdf_path.exists():
        log.warning(f"PDF not found at {pdf_path}; cannot send to Documenso")
        return None

    addr = lead.get("property_address") or lead.get("address") or "property"
    seller_name = (lead.get("owner_name") or "Seller").strip()
    seller_email = (
        lead.get("owner_email") or lead.get("email") or ""
    ).strip()

    if not seller_email:
        log.warning(
            f"No owner_email on lead for {addr}; cannot send PSA for signature. "
            "Add owner_email to the lead dict or skip-trace first."
        )
        return None

    effective_date = deal_terms.get("effective_date") or datetime.now().strftime("%B %d, %Y")
    purchase_price = int(deal_terms.get("purchase_price") or 0)
    title_str = f"Purchase and Sale Agreement -- {addr}"

    create_payload = {
        "title": title_str,
        "recipients": [
            {
                "email": seller_email,
                "name": seller_name,
                "role": "SIGNER",
            },
        ],
        "meta": {
            "subject": f"Your purchase contract for {addr} -- please review and sign",
            "message": (
                f"Hi {seller_name.split()[0] if seller_name else 'there'},\n\n"
                f"Attached is the Purchase and Sale Agreement for {addr}, "
                f"effective {effective_date}. The agreed purchase price is "
                f"${purchase_price:,}. "
                f"Please review and sign at your convenience. "
                f"Questions? Reply to this email or call us directly. "
                f"We look forward to working with you."
            ),
        },
    }

    try:
        req = urllib.request.Request(
            f"{api_url}/documents",
            data=json.dumps(create_payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            doc = json.loads(resp.read().decode("utf-8"))

        doc_id = doc.get("id") or (doc.get("document") or {}).get("id")
        upload_url = doc.get("uploadUrl") or doc.get("upload_url")
        if not doc_id or not upload_url:
            log.warning(f"Documenso create: missing id/uploadUrl -- response: {doc}")
            return None

        # PUT the PDF bytes to the presigned upload URL
        with pdf_path.open("rb") as f:
            put_req = urllib.request.Request(
                upload_url,
                data=f.read(),
                headers={"Content-Type": "application/pdf"},
                method="PUT",
            )
            urllib.request.urlopen(put_req, timeout=60).read()

        # Send for signing
        send_req = urllib.request.Request(
            f"{api_url}/documents/{doc_id}/send-for-signing",
            data=b"{}",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        urllib.request.urlopen(send_req, timeout=30).read()

        signing_url = f"https://sign.everlightventures.io/sign/{doc_id}"
        log.info(f"PSA sent to Documenso: doc_id={doc_id}, signer={seller_email}")

        # Update Deal.agreement_url if a real ORM instance was passed
        if deal is not None:
            try:
                if hasattr(deal, "agreement_url"):
                    deal.agreement_url = signing_url
                    deal.save(update_fields=["agreement_url"])
            except Exception as exc:
                log.warning(f"could not save agreement_url to Deal: {exc}")

        return signing_url

    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", "replace")[:400]
        except Exception:
            pass
        log.warning(f"Documenso HTTP {exc.code}: {body}")
        return None
    except Exception as exc:
        log.warning(f"Documenso send error: {exc}")
        return None
