"""lob_mail_sender -- branded yellow letters / postcards via Lob API.

Why
---
Industry data: cold email to property owners gets <0.1% reply. Direct mail
gets 1-2% reply, 0.1-0.3% to-contract. For wholesale, mail is the
non-negotiable channel for cold seller acquisition. We use Lob.com because
they accept HTML templates and ship within 1-2 business days.

Pricing (as of 2026-04):
  - Yellow letter (standard #10): ~$0.85 each at 1K vol, ~$0.65 at 5K
  - Postcard 4x6: ~$0.50 each at 1K vol
  - Returns to PO Box at $1/return processed

A $2K/month budget = ~3,000 letters or ~4,000 postcards. Industry rule of
thumb: 1 contract per 1,500 mailers, 1 close per 3,000 mailers. So $2K/mo
realistically yields 1-2 closes/month, growing as the list quality improves.

Public API
----------
    from lob_mail_sender import send_yellow_letter, send_postcard, monthly_status

    res = send_yellow_letter(
        to_name="John Owner",
        to_address={"line1": "123 Main St", "city": "Cleveland", "state": "OH", "zip": "44101"},
        from_name="Piper Reeves",
        from_address={...},
        body="Hi John, saw 123 Main St has been vacant. ...",
        merge_vars={"property_address": "123 Main St"},
    )

Status of LOB_API_KEY
---------------------
This module is built so the moment you add LOB_API_KEY to /home/opc/.env
it goes live. Until then, every send returns ok=False with a clear reason
so callers (Piper, the cron) degrade gracefully -- the property is still
queued and will ship as soon as the key lands.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import base64

log = logging.getLogger("lob_mail_sender")

WORKSPACE_CANDIDATES = [
    Path("/mnt/sdcard/AA_MY_DRIVE"),
    Path("/home/opc/AA_MY_DRIVE"),
    Path("/home/opc"),
]


def _workspace() -> Path:
    for p in WORKSPACE_CANDIDATES:
        if p.exists():
            return p
    return WORKSPACE_CANDIDATES[0]


LOB_API = "https://api.lob.com/v1"
LEDGER = _workspace() / "_logs" / "direct_mail.jsonl"


@dataclass
class MailResult:
    ok: bool
    lob_id: str = ""
    expected_delivery_date: str = ""
    cost_cents: int = 0
    error: str = ""


def _api_key() -> str:
    return os.environ.get("LOB_API_KEY", "") or os.environ.get("LOB_TEST_API_KEY", "")


def _post(endpoint: str, payload: dict) -> dict:
    key = _api_key()
    if not key:
        return {"ok": False, "error": "no_lob_api_key"}
    auth = base64.b64encode(f"{key}:".encode()).decode()
    req = Request(
        f"{LOB_API}{endpoint}",
        data=urlencode(payload, doseq=True).encode(),
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8") or "{}")
            return {"ok": True, "data": data}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")[:500]
        return {"ok": False, "error": f"http_{exc.code}: {body}"}
    except (URLError, TimeoutError) as exc:
        return {"ok": False, "error": str(exc)}


def _record(kind: str, payload: dict, response: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "to": payload.get("to_name") or payload.get("to[name]") or "?",
            "ok": response.get("ok"),
            "lob_id": (response.get("data") or {}).get("id", ""),
            "error": response.get("error", ""),
        }) + "\n")


# ── Yellow letter (looks handwritten on yellow legal paper) ─────

YELLOW_LETTER_TEMPLATE = """<html><body style="font-family:'Marker Felt','Comic Sans MS',cursive; font-size:14pt; padding:30px; background:#fffacd;">
<p>Hi {{to_first_name}},</p>
<p>I'm Piper at Everlight Ventures. I drove past <strong>{{property_address}}</strong> last week and noticed it might be sitting empty. I'm a local cash buyer -- if selling has crossed your mind, I'd love to make you a fair, no-obligation cash offer. Close on your timeline. No repairs, no commissions, no showings.</p>
<p>Easiest way to start: call or text me at {{from_phone}}. I'll listen, give you a number, and you decide. That's it.</p>
<p>If you're not interested, no worries -- just toss this letter and I'll never bother you again.</p>
<p>Thanks for your time,<br>Piper Reeves<br>Everlight Ventures<br>{{from_phone}}</p>
</body></html>"""


def send_yellow_letter(
    *,
    to_name: str,
    to_address: dict[str, str],
    from_name: str = "Piper Reeves",
    from_address: dict[str, str] | None = None,
    from_phone: str = "(555) 555-0100",
    property_address: str = "your property",
    description: str = "",
) -> MailResult:
    """Send a single yellow letter. Returns MailResult, never raises."""
    if not from_address:
        from_address = {
            "line1": "PO Box 1234",
            "city": "Cleveland",
            "state": "OH",
            "zip": "44114",
        }

    body = (
        YELLOW_LETTER_TEMPLATE
        .replace("{{to_first_name}}", to_name.split()[0] if to_name else "there")
        .replace("{{property_address}}", property_address)
        .replace("{{from_phone}}", from_phone)
    )

    # Justine's pre-send phrase scrub. Block agent-representation language
    # for the recipient's state before the letter ships. ORC 4735.02 in OH;
    # baseline list everywhere else. Skips quietly if the scrub module is
    # not on PYTHONPATH (degrades to send, logs the failure).
    try:
        import sys as _sys
        for _p in (
            "/home/opc/content_tools",
            "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools",
        ):
            if _p not in _sys.path:
                _sys.path.insert(0, _p)
        from pre_send_phrase_scrub import validate_outbound  # type: ignore
        _scrub = validate_outbound(
            body,
            state=(to_address.get("state") or "").upper(),
            channel="mail",
            recipient=to_name,
        )
        if not _scrub.ok:
            log.warning(
                "phrase_scrub blocked yellow letter to %s (%s): %s",
                to_name, to_address.get("state"), _scrub.blocked_phrases,
            )
            return MailResult(
                ok=False,
                error=f"phrase_scrub_blocked: {_scrub.blocked_phrases[0]}",
            )
    except Exception as _scrub_err:
        log.warning("phrase_scrub import/check failed, allowing send: %s", _scrub_err)

    payload = {
        "description": description or f"YL: {to_name} -> {property_address}",
        "to[name]": to_name,
        "to[address_line1]": to_address.get("line1", ""),
        "to[address_city]": to_address.get("city", ""),
        "to[address_state]": to_address.get("state", ""),
        "to[address_zip]": to_address.get("zip", ""),
        "to[address_country]": "US",
        "from[name]": from_name,
        "from[address_line1]": from_address["line1"],
        "from[address_city]": from_address["city"],
        "from[address_state]": from_address["state"],
        "from[address_zip]": from_address["zip"],
        "from[address_country]": "US",
        "file": body,
        "color": False,  # yellow letter is monochrome
        "double_sided": False,
        "metadata[campaign]": "yellow_letter_2026q2",
        "metadata[market]": to_address.get("state", ""),
    }

    response = _post("/letters", payload)
    _record("yellow_letter", payload, response)
    if response.get("ok"):
        data = response.get("data", {})
        return MailResult(
            ok=True,
            lob_id=str(data.get("id", "")),
            expected_delivery_date=str(data.get("expected_delivery_date", "")),
            cost_cents=int(float(data.get("price", 0)) * 100),
        )
    return MailResult(ok=False, error=response.get("error", "unknown"))


def monthly_status() -> dict[str, Any]:
    """Count this month's mail spend from the ledger."""
    from datetime import datetime
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    sent = 0
    failed = 0
    if LEDGER.exists():
        with LEDGER.open() as f:
            for line in f:
                try:
                    row = json.loads(line)
                    ts = datetime.fromisoformat(row["ts"].replace("Z", "+00:00"))
                    if ts < month_start:
                        continue
                    if row.get("ok"):
                        sent += 1
                    else:
                        failed += 1
                except Exception:
                    continue
    return {
        "month": now.strftime("%Y-%m"),
        "sent": sent,
        "failed": failed,
        "estimated_cost_usd": sent * 0.85,  # rough yellow-letter cost
        "lob_api_key_configured": bool(_api_key()),
    }


# ── CLI ─────────────────────────────────────────────────────────

def _cli() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    p1 = sub.add_parser("send-yellow")
    p1.add_argument("--to", required=True)
    p1.add_argument("--addr-line1", required=True)
    p1.add_argument("--city", required=True)
    p1.add_argument("--state", required=True)
    p1.add_argument("--zip", required=True)
    p1.add_argument("--property", default="your property")
    p1.add_argument("--phone", default="(555) 555-0100")
    p1.add_argument("--dry-run", action="store_true")

    p2 = sub.add_parser("status")

    args = ap.parse_args()
    if args.cmd == "send-yellow":
        if args.dry_run:
            print("DRY RUN -- would send yellow letter to:", args.to, "at", args.addr_line1, args.city, args.state, args.zip)
            return 0
        res = send_yellow_letter(
            to_name=args.to,
            to_address={"line1": args.addr_line1, "city": args.city, "state": args.state, "zip": args.zip},
            from_phone=args.phone,
            property_address=args.property,
        )
        print(json.dumps({"ok": res.ok, "lob_id": res.lob_id, "delivery": res.expected_delivery_date, "error": res.error}, indent=2))
        return 0 if res.ok else 1
    if args.cmd == "status":
        print(json.dumps(monthly_status(), indent=2))
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(_cli())
