"""
signature_burner.py -- Burn a signature into a contract HTML to produce an executed copy.

Why this exists:
  The original contract HTML (e.g. 01_PSA.html) is a TEMPLATE with empty signature
  block lines. When someone signs via the e-sign service, we need a separate executed
  copy (01_PSA_signed.html) with their signature image, typed name, and date burned
  into the right block. Original template stays untouched (so the doc SHA-256 in the
  audit chain stays valid forever -- it's a fingerprint of what the signer SAW).

Approach:
  1. Read the original HTML
  2. Find the signature block matching the signer's name (Seller or Buyer side)
  3. Replace the empty <div class="sig-line"></div> with:
       - Drawn signature image (base64-embedded so file is self-contained)
       - Typed legal name (rendered in script-style font for visual signature)
       - Date stamp
  4. Add a "✓ SIGNED" banner at top
  5. Add an audit footer with SHA-256 of original + signature
  6. Save as <doc_id>_signed.html in same dir

Public API:
  burn_signature(deal_key, doc_id, sig_payload) -> Path of signed file
"""
from __future__ import annotations

import base64
import re
from datetime import datetime
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
DEALS_DIR = ROOT / "09_DASHBOARD" / "reports" / "deals"


def _embed_image_b64(image_path: Path) -> str:
    """Read PNG and return data URL for inline embedding."""
    if not image_path.exists():
        return ""
    raw = image_path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _signed_signature_block_html(signer_name: str, signed_at_iso: str,
                                  sig_image_data_url: str, role_label: str) -> str:
    """Build the HTML that replaces the empty sig-line for a signed party."""
    # Format date as "Month DD, YYYY at HH:MM UTC"
    try:
        dt = datetime.fromisoformat(signed_at_iso.rstrip("Z"))
        date_str = dt.strftime("%B %d, %Y at %H:%M UTC")
    except Exception:
        date_str = signed_at_iso

    # Image vs typed-only
    if sig_image_data_url:
        sig_visual = (
            f'<div style="position:relative; border-bottom:2px solid #d4a843; '
            f'height:3.5rem; padding:.25rem 0; background: linear-gradient(180deg, transparent 0%, rgba(0,229,255,0.04) 100%);">'
            f'  <img src="{sig_image_data_url}" alt="signature" '
            f'       style="max-height:3.2rem; max-width:100%; display:block; '
            f'              filter: brightness(0.85) contrast(1.4);"/>'
            f'</div>'
        )
    else:
        # Typed-only fallback: render the name in a script-style font
        sig_visual = (
            f'<div style="position:relative; border-bottom:2px solid #d4a843; '
            f'height:3.5rem; display:flex; align-items:center; padding-left:.5rem;">'
            f'  <span style="font-family: \'Brush Script MT\', \'Snell Roundhand\', cursive; '
            f'               font-size: 2.1rem; color: #1a1308; '
            f'               text-shadow: 0 1px 0 rgba(0,0,0,0.1);">{signer_name}</span>'
            f'</div>'
        )

    return (
        f'{sig_visual}'
        f'<div class="sig-label" style="margin-top:.4rem;">'
        f'  <strong style="color:#5cffb1; display:inline; margin-right:.5em;">✓ SIGNED</strong>'
        f'  by <strong style="color:#d4a843;">{signer_name}</strong>'
        f'  on <strong style="color:#d4a843;">{date_str}</strong>'
        f'</div>'
    )


def _signed_banner_html(signer_name: str, signed_at_iso: str,
                          doc_sha: str, sig_sha: str) -> str:
    """Top-of-document banner replacing 'DRAFT for e-signature'."""
    try:
        dt = datetime.fromisoformat(signed_at_iso.rstrip("Z"))
        date_str = dt.strftime("%B %d, %Y at %H:%M UTC")
    except Exception:
        date_str = signed_at_iso
    return (
        '<div class="banner" style="background: linear-gradient(90deg, rgba(92,255,177,.18) 0%, rgba(92,255,177,.04) 100%); '
        'border-color: rgba(92,255,177,.5); color: #5cffb1;">'
        f'<strong>✓ EXECUTED</strong> ◆ Signed by <strong>{signer_name}</strong> '
        f'on <strong>{date_str}</strong> ◆ '
        f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:.75rem;">'
        f'doc-sha: {doc_sha[:16]}… ◆ sig-sha: {sig_sha[:16]}…</span>'
        '</div>'
    )


def _signed_footer_html(sig_payload: dict) -> str:
    """Audit footer with full crypto + signing context."""
    return f'''
<div style="margin-top:2rem; padding:1.25rem; background:#0f0f0a;
            border:1px dashed #d4a843; border-radius:10px;
            font-family:'JetBrains Mono', monospace; font-size:.72rem;
            color:#b5af9b; line-height:1.7;">
  <div style="color:#d4a843; font-weight:700; letter-spacing:.15em; text-transform:uppercase; margin-bottom:.5rem;">
    Signature Certificate
  </div>
  <div><strong style="color:#d4a843;">Signer:</strong> {sig_payload.get("signer_name","")} &lt;{sig_payload.get("signer_email","")}&gt;</div>
  <div><strong style="color:#d4a843;">Signed at (UTC):</strong> {sig_payload.get("signed_at","")}</div>
  <div><strong style="color:#d4a843;">From IP:</strong> {sig_payload.get("ip","")}</div>
  <div><strong style="color:#d4a843;">User agent:</strong> {(sig_payload.get("user_agent","") or "")[:120]}</div>
  <div><strong style="color:#d4a843;">Intent affirmed:</strong> {"YES (intent checkbox required)" if sig_payload.get("intent_affirmed") else "NO"}</div>
  <div><strong style="color:#d4a843;">Document SHA-256:</strong> <span style="color:#7a7560;">{sig_payload.get("document_sha256","")}</span></div>
  <div><strong style="color:#d4a843;">Signature SHA-256:</strong> <span style="color:#7a7560;">{sig_payload.get("signature_sha256","")}</span></div>
  {f'<div><strong style="color:#d4a843;">Signature image SHA-256:</strong> <span style="color:#7a7560;">{sig_payload.get("signature_image_sha256")}</span></div>' if sig_payload.get("signature_image_sha256") else ""}
  <div style="margin-top:.75rem; color:#7a7560; font-size:.68rem;">
    This electronic signature is binding under the federal E-Sign Act (15 USC § 7001) and the
    Tennessee Uniform Electronic Transactions Act (Tenn. Code Ann. § 47-10-101 et seq).
    Cryptographic verification: this document's SHA-256 is pinned in the immutable hash-chained
    deal_execution_log audit database. Any tampering with the document or audit log is detectable
    via verify_chain().
  </div>
</div>
'''


def _replace_block_for_signer(html: str, signer_name: str,
                                replacement_html: str) -> tuple[str, bool]:
    """Find the empty <div class="sig-line"></div> that's followed by a sig-label
    containing this signer's name, and replace it with the executed signature block.

    Returns (modified_html, replaced: bool).
    """
    # The pattern: <div><div class="sig-line"></div><div class="sig-label">SignerName<br><strong>Date</strong></div></div>
    # We want to match the sig-line + sig-label pair where the label contains this signer's name.
    # Use re.escape for the name in case it has special regex chars.
    safe_name = re.escape(signer_name)
    pattern = re.compile(
        r'(<div class="sig-line"></div>)'  # group 1: the empty sig-line we'll replace
        r'(\s*<div class="sig-label">'
        rf'[^<]*?{safe_name}'
        r'.*?</div>)',
        re.DOTALL,
    )
    new_html, n = pattern.subn(replacement_html, html, count=1)
    return new_html, n > 0


def burn_signature(deal_key: str, doc_id: str, sig_payload: dict) -> Path | None:
    """Generate <doc_id>_signed.html with the signature burned in.
    Returns the path of the signed copy, or None on failure.
    """
    deal_dir = DEALS_DIR / deal_key
    src = deal_dir / f"{doc_id}.html"
    if not src.exists():
        print(f"[burn] source doc not found: {src}")
        return None

    html = src.read_text(encoding="utf-8")
    signer_name = sig_payload.get("signer_name", "")
    signed_at = sig_payload.get("signed_at", datetime.utcnow().isoformat() + "Z")
    doc_sha = sig_payload.get("document_sha256", "")
    sig_sha = sig_payload.get("signature_sha256", "")

    # Embed the drawn image (if any) as a data URL
    img_path_str = sig_payload.get("signature_image_path")
    img_data_url = _embed_image_b64(Path(img_path_str)) if img_path_str else ""

    # Build replacement for the signer's empty sig-line block
    role_label = "SELLER" if "seller" in (sig_payload.get("role", "") or "").lower() or signer_name else "PARTY"
    replacement = _signed_signature_block_html(signer_name, signed_at, img_data_url, role_label)
    # The pattern keeps the sig-label intact (group 2), so we wrap the replacement to produce
    # the same outer structure: the visual sig + a new label below.
    # Actually we WANT to replace BOTH the empty sig-line AND the original "name + Date" label.
    # The replacement_html already contains its own label. So just replace both.
    full_replacement = replacement

    new_html, replaced = _replace_block_for_signer(html, signer_name, full_replacement)
    if not replaced:
        print(f"[burn] couldn't find sig block for {signer_name} in {doc_id}")
        # Still produce a signed copy with a banner + footer, just no in-block burn-in
        new_html = html

    # Replace the DRAFT banner with EXECUTED (or insert at top if no banner)
    signed_banner = _signed_banner_html(signer_name, signed_at, doc_sha, sig_sha)
    draft_banner_re = re.compile(
        r'<div class="banner">DRAFT for e-signature[^<]*?</div>', re.DOTALL)
    if draft_banner_re.search(new_html):
        new_html = draft_banner_re.sub(signed_banner, new_html, count=1)
    else:
        # Inject after first <main class="doc-body"> opening
        main_re = re.compile(r'(<main class="doc-body">)', re.DOTALL)
        if main_re.search(new_html):
            new_html = main_re.sub(r"\1\n" + signed_banner, new_html, count=1)

    # Append signature certificate footer just before </main>
    footer_html = _signed_footer_html(sig_payload)
    new_html = new_html.replace("</main>", footer_html + "\n</main>", 1)

    # Save as <doc_id>_signed.html
    out = deal_dir / f"{doc_id}_signed.html"
    out.write_text(new_html, encoding="utf-8")
    return out


if __name__ == "__main__":
    import json, sys
    if len(sys.argv) < 4:
        print("usage: signature_burner.py <deal_key> <doc_id> <sig_json_path>")
        sys.exit(1)
    sig = json.loads(Path(sys.argv[3]).read_text())
    out = burn_signature(sys.argv[1], sys.argv[2], sig)
    print(f"  ✓ wrote {out}" if out else "  ✗ failed")
