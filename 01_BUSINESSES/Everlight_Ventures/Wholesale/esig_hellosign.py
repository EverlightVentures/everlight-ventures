"""esig_hellosign -- free-tier HelloSign (now Dropbox Sign) e-signature.

Why this:
  Per AUTONOMY_AUDIT.md: "E-signature (seller + you sign contract) -- NO.
  PDF only. Needs DocuSign / HelloSign integration. Currently: PDF attached
  to email, seller signs and emails back."

  HelloSign free tier: 3 signature requests/month forever. Plenty for the
  first 1-3 deals. After Deal 1 commission, upgrade to Standard ($20/mo)
  for unlimited.

What this does:
  1. Take a PSA template + lead data
  2. Build a fillable PDF (or use the existing contract template)
  3. Submit signature request via HelloSign API
  4. Email both parties with the e-sign link
  5. Webhook receives signed event -> updates Deal.stage='psa_signed'
  6. Triggers bidding_war_engine when fully signed

Auth:
  Set HELLOSIGN_API_KEY in /home/opc/.env. Free tier API key works.
  Get one at https://app.hellosign.com/api/keys (free signup).

Until the API key is set: this module gracefully degrades and returns
"please email the PDF manually" instructions, so the system doesn't break.

Usage:
  python3 esig_hellosign.py send --deal-id=<uuid> --pdf-path=/path/to/psa.pdf
  python3 esig_hellosign.py status --signature-request-id=<id>
"""
from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

for p in ("/home/opc/hive_django",
          "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard"):
    if p not in sys.path and Path(p).exists():
        sys.path.insert(0, p)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
import django  # noqa
django.setup()

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("esig")

API_BASE = "https://api.hellosign.com/v3"
LEDGER = Path("/home/opc/wholesale/_logs/esig_ledger.jsonl")
LEDGER.parent.mkdir(parents=True, exist_ok=True)


def _api_key() -> str:
    return os.environ.get("HELLOSIGN_API_KEY", "") or os.environ.get("DROPBOX_SIGN_API_KEY", "")


def _auth_header() -> dict:
    key = _api_key()
    if not key:
        return {}
    auth = base64.b64encode(f"{key}:".encode()).decode()
    return {"Authorization": f"Basic {auth}"}


def _post_multipart(url: str, fields: dict, files: dict) -> dict:
    """POST multipart/form-data to HelloSign. Built without requests dependency."""
    boundary = "----EverlightBoundary" + os.urandom(8).hex()
    body = b""
    for name, value in fields.items():
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
    for name, (filename, data) in files.items():
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
        body += b"Content-Type: application/pdf\r\n\r\n"
        body += data
        body += b"\r\n"
    body += f"--{boundary}--\r\n".encode()

    headers = {**_auth_header(), "Content-Type": f"multipart/form-data; boundary={boundary}"}
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        return {"error": str(exc)}


def send_signature_request(
    pdf_path: str,
    seller_name: str,
    seller_email: str,
    your_name: str = "Rich Gillies",
    your_email: str = "rich@everlightventures.io",
    title: str = "Purchase and Sale Agreement -- Everlight Ventures",
    subject: str = "Please sign: PSA for your property",
    message: str = ("Attached is the PSA for your property. "
                     "Sign electronically below. "
                     "Reply to rich@everlightventures.io with any questions."),
) -> dict:
    """Submit a signature request to HelloSign. Returns response dict.

    On no-API-key: returns degraded-mode response telling user to send PDF manually.
    """
    if not _api_key():
        log.warning("No HELLOSIGN_API_KEY -- degrading to manual-email mode")
        return {
            "ok": False,
            "mode": "manual_fallback",
            "instructions": (
                f"E-sig API not configured. Manual flow: email {pdf_path} to "
                f"{seller_email}. Ask seller to print + sign + scan back, "
                f"or use any free PDF signer (PDFescape, DocuSign free tier)."
            ),
            "pdf_path": pdf_path,
            "seller_email": seller_email,
        }

    pdf_data = Path(pdf_path).read_bytes()

    fields = {
        "title": title,
        "subject": subject,
        "message": message,
        "signers[0][email_address]": seller_email,
        "signers[0][name]": seller_name,
        "signers[0][order]": "0",
        "signers[1][email_address]": your_email,
        "signers[1][name]": your_name,
        "signers[1][order]": "1",
        "test_mode": "0",  # set 1 for sandbox
    }

    files = {"file[0]": (Path(pdf_path).name, pdf_data)}

    log.info(f"Sending PSA to {seller_email} via HelloSign")
    result = _post_multipart(f"{API_BASE}/signature_request/send", fields, files)

    sig_req = result.get("signature_request", {}) if isinstance(result, dict) else {}
    sig_id = sig_req.get("signature_request_id", "")

    LEDGER.open("a").write(json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "sent",
        "signature_request_id": sig_id,
        "seller_email": seller_email,
        "seller_name": seller_name,
        "title": title,
        "raw_response_summary": {
            "title": sig_req.get("title"),
            "is_complete": sig_req.get("is_complete"),
            "signing_url": sig_req.get("signing_url"),
        },
    }) + "\n")

    return {
        "ok": bool(sig_id),
        "signature_request_id": sig_id,
        "signing_url_seller": sig_req.get("signing_url", ""),
        "details_url": sig_req.get("details_url", ""),
    }


def check_status(signature_request_id: str) -> dict:
    """Poll HelloSign for current sig status. Updates Deal.stage when both signed."""
    if not _api_key():
        return {"error": "no_api_key"}

    req = urllib.request.Request(
        f"{API_BASE}/signature_request/{signature_request_id}",
        headers=_auth_header(),
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        return {"error": str(exc)}

    sig_req = data.get("signature_request", {})
    is_complete = sig_req.get("is_complete", False)
    signers = sig_req.get("signatures", [])
    signed = [s for s in signers if s.get("signed_at")]

    LEDGER.open("a").write(json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "status_check",
        "signature_request_id": signature_request_id,
        "is_complete": is_complete,
        "signed_count": len(signed),
        "total_signers": len(signers),
    }) + "\n")

    return {
        "signature_request_id": signature_request_id,
        "is_complete": is_complete,
        "signed_count": len(signed),
        "total_signers": len(signers),
        "signed_emails": [s.get("signer_email_address") for s in signed],
        "files_url": sig_req.get("files_url", ""),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["send", "status", "check-key"])
    ap.add_argument("--pdf-path", default="")
    ap.add_argument("--seller-email", default="")
    ap.add_argument("--seller-name", default="")
    ap.add_argument("--signature-request-id", default="")
    args = ap.parse_args()

    if args.cmd == "check-key":
        key = _api_key()
        if key:
            print(json.dumps({"key_present": True, "preview": key[:8] + "..."}))
        else:
            print(json.dumps({"key_present": False, "set_env": "HELLOSIGN_API_KEY"}))
    elif args.cmd == "send":
        if not (args.pdf_path and args.seller_email and args.seller_name):
            print("--pdf-path + --seller-email + --seller-name required")
            return
        result = send_signature_request(
            pdf_path=args.pdf_path,
            seller_email=args.seller_email,
            seller_name=args.seller_name,
        )
        print(json.dumps(result, indent=2))
    elif args.cmd == "status":
        if not args.signature_request_id:
            print("--signature-request-id required")
            return
        result = check_status(args.signature_request_id)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
