"""
Gmail Label Router -- apply per-persona Gmail labels to real replies.

When inbound_reply_matcher detects a real reply for, say, piper_reeves,
this module applies the "Everlight/Piper" label to the corresponding Gmail
message via IMAP STORE +X-GM-LABELS. The user then sees replies grouped
by persona in the phone Gmail UI.

Requires:
  IMAP_USER       (default 1m.rich.gee@gmail.com)
  IMAP_PASS       (Gmail app password)
  IMAP_HOST       (default imap.gmail.com)

Uses Gmail's X-GM-LABELS IMAP extension (Gmail-specific). The label is
created automatically by Gmail if it doesn't exist.

Idempotent: applying a label that's already on the message is a no-op.
"""
from __future__ import annotations

import imaplib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("gmail_label_router")

_AUDIT = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/gmail_label_router.jsonl")

# Persona id -> Gmail label name (human-readable in Gmail UI)
# Nested labels (e.g. "Everlight/Frontline/Piper") create a tree view in Gmail.
PERSONA_LABEL_MAP: dict[str, str] = {
    # --- Frontline senders (counterparty-facing) ---
    "piper_reeves": "Everlight/Frontline/Piper",
    "henry_hammond": "Everlight/Frontline/Henry",
    "marvin_cohen": "Everlight/Frontline/Marvin",
    "vaughn_sterling": "Everlight/Frontline/Vaughn",
    # --- State designates ---
    "marvin_tn": "Everlight/States/TN-Marvin",
    "atlas_king": "Everlight/States/GA-Atlas",
    "daria_voss": "Everlight/States/TX-Daria",
    "cleo_vance": "Everlight/States/OH-Cleo",
    "jasper_reeves": "Everlight/States/FL-Jasper",
    "phin_reyes": "Everlight/States/AZ-Phin",
    "stella_marquez": "Everlight/States/MO-Stella",
    # --- Compliance buddies (internal) ---
    "lo_hines": "Everlight/Compliance/TN-Lo",
    "ellie_vaughn": "Everlight/Compliance/GA-Ellie",
    "mags_diaz": "Everlight/Compliance/TX-Mags",
    "bernie_kowalski": "Everlight/Compliance/OH-Bernie",
    "mona_castile": "Everlight/Compliance/FL-Mona",
    "lupe_salazar": "Everlight/Compliance/AZ-Lupe",
    "walt_henning": "Everlight/Compliance/MO-Walt",
    # --- Back-office wholesale intel ---
    "marquise_reed": "Everlight/Intel/Marquise",
    # --- Legal team ---
    "legal_theo_briggs": "Everlight/Legal/Theo",
    "legal_imani_calder": "Everlight/Legal/Imani",
    "legal_lia_knight": "Everlight/Legal/Lia",
    "legal_priya_bhattacharya": "Everlight/Legal/Priya",
    "legal_wen_marsh": "Everlight/Legal/Wen",
    "legal_heck_aurelio": "Everlight/Legal/Heck",
    # --- Legacy + catch-all ---
    "unknown_pre_gate": "Everlight/Replies-Legacy",
}


def label_for_persona(persona_id: str) -> str:
    return PERSONA_LABEL_MAP.get(persona_id, f"Everlight/{persona_id or 'unrouted'}")


def _audit(verdict: str, **fields) -> None:
    try:
        _AUDIT.parent.mkdir(parents=True, exist_ok=True)
        row = {"ts_utc": datetime.now(timezone.utc).isoformat(), "verdict": verdict, **fields}
        with open(_AUDIT, "a") as f:
            f.write(json.dumps(row, default=str) + "\n")
    except Exception as e:
        log.warning("audit write failed: %s", e)


def _imap_conn():
    user = os.environ.get("IMAP_USER") or os.environ.get("GMAIL_USER", "1m.rich.gee@gmail.com")
    pw = os.environ.get("IMAP_PASS") or os.environ.get("GMAIL_APP_PASSWORD", "")
    host = os.environ.get("IMAP_HOST", "imap.gmail.com")
    if not pw:
        raise RuntimeError("IMAP_PASS / GMAIL_APP_PASSWORD missing in env")
    m = imaplib.IMAP4_SSL(host)
    m.login(user, pw)
    return m


def apply_label(uid: str, persona_id: str, mailbox: str = "INBOX") -> dict:
    """Apply persona-derived Gmail label to message with given UID.

    Returns {ok: bool, label: str, error: str, uid: str}.
    """
    if not uid or not str(uid).strip():
        return {"ok": False, "error": "no_uid", "uid": uid, "label": ""}

    label = label_for_persona(persona_id)
    fields = {"uid": str(uid), "persona_id": persona_id, "label": label, "mailbox": mailbox}

    try:
        m = _imap_conn()
    except Exception as e:
        _audit("imap_login_failed", error=str(e), **fields)
        return {"ok": False, "error": f"imap_login_failed:{e}", **fields}

    try:
        m.select(mailbox)
        # Gmail X-GM-LABELS extension. Label is a UTF-8 string in quotes.
        # +X-GM-LABELS adds the label without removing existing ones.
        typ, data = m.uid("STORE", str(uid), "+X-GM-LABELS", f'"{label}"')
        if typ != "OK":
            _audit("store_failed", store_response=str(data)[:200], **fields)
            return {"ok": False, "error": f"store_failed:{typ}:{data}", **fields}
        _audit("labeled", **fields)
        return {"ok": True, "label": label, "uid": str(uid), "error": ""}
    except Exception as e:
        _audit("store_exception", error=str(e), **fields)
        return {"ok": False, "error": f"exception:{e}", **fields}
    finally:
        try:
            m.logout()
        except Exception:
            pass


# Persona -> ImprovMX alias mapping (operator must set up these aliases in ImprovMX dashboard).
# Each alias should route to 1m.rich.gee@gmail.com so Gmail filters can label by alias.
PERSONA_ALIAS_MAP: dict[str, str] = {
    # Frontline (counterparty-facing senders)
    "piper_reeves": "piper-inbox@everlightventures.io",
    "henry_hammond": "henry-inbox@everlightventures.io",
    "marvin_cohen": "marvin-inbox@everlightventures.io",
    "vaughn_sterling": "vaughn-inbox@everlightventures.io",
    # State designates
    "marvin_tn": "marvin-tn-inbox@everlightventures.io",
    "atlas_king": "atlas-inbox@everlightventures.io",
    "daria_voss": "daria-inbox@everlightventures.io",
    "cleo_vance": "cleo-inbox@everlightventures.io",
    "jasper_reeves": "jasper-inbox@everlightventures.io",
    "phin_reyes": "phin-inbox@everlightventures.io",
    "stella_marquez": "stella-inbox@everlightventures.io",
    # Compliance buddies (internal)
    "lo_hines": "lo-inbox@everlightventures.io",
    "ellie_vaughn": "ellie-inbox@everlightventures.io",
    "mags_diaz": "mags-inbox@everlightventures.io",
    "bernie_kowalski": "bernie-inbox@everlightventures.io",
    "mona_castile": "mona-inbox@everlightventures.io",
    "lupe_salazar": "lupe-inbox@everlightventures.io",
    "walt_henning": "walt-inbox@everlightventures.io",
    # Back-office wholesale intel
    "marquise_reed": "marquise-inbox@everlightventures.io",
    # Legal team
    "legal_theo_briggs": "theo-inbox@everlightventures.io",
    "legal_imani_calder": "imani-inbox@everlightventures.io",
    "legal_lia_knight": "lia-inbox@everlightventures.io",
    "legal_priya_bhattacharya": "priya-inbox@everlightventures.io",
    "legal_wen_marsh": "wen-inbox@everlightventures.io",
    "legal_heck_aurelio": "heck-inbox@everlightventures.io",
    # Legacy + catch-all
    "unknown_pre_gate": "replies-legacy-inbox@everlightventures.io",
}


def auto_forward_to_alias(
    persona_id: str,
    from_email: str,
    from_name: str,
    subject: str,
    body: str,
) -> dict:
    """Forward a real reply to the persona's ImprovMX alias inbox.

    Operator chose: dedicated ImprovMX aliases (2026-05-17).
    Aliases land at <persona>-inbox@everlightventures.io. The ImprovMX dashboard
    must be configured to route each alias to the desired Gmail label / inbox.

    Routes through branded_mailer with persona_id="system_router" (internal_only).
    The send_authority_gate confirms the recipient is @everlightventures.io.
    """
    alias = PERSONA_ALIAS_MAP.get(persona_id)
    fields = {"persona_id": persona_id, "alias": alias, "from_email": from_email}
    if not alias:
        _audit("forward_no_alias_mapped", **fields)
        return {"ok": False, "skipped": True, "reason": f"no alias for persona {persona_id}"}

    try:
        from branded_mailer import send_branded_email
    except ImportError as e:
        _audit("forward_branded_mailer_unavailable", error=str(e), **fields)
        return {"ok": False, "error": f"branded_mailer unavailable: {e}"}

    # Quote the original message as the forwarded body.
    quoted_body = (
        f"<p><em>Forwarded reply for {persona_id}:</em></p>"
        f"<p><strong>From:</strong> {from_name} &lt;{from_email}&gt;<br>"
        f"<strong>Original subject:</strong> {subject}</p>"
        f"<hr>"
        f"<pre style='white-space: pre-wrap; font-family: ui-monospace, monospace;'>"
        f"{(body or '')[:8000]}"
        f"</pre>"
    )

    res = send_branded_email(
        to=alias,
        subject=f"[FWD {persona_id}] {subject}"[:200],
        content_html=quoted_body,
        from_name="Everlight Routing",
        from_email="noreply@everlightventures.io",
        agent_name="System Router",
        agent_email="noreply@everlightventures.io",
        persona_id="system_router",
        budget_category="system",
        state_disclaimer=False,
        caller="gmail_label_router.auto_forward_to_alias",
    )
    _audit(
        "forwarded" if res.ok else "forward_failed",
        ok=res.ok,
        error=getattr(res, "error", ""),
        message_id=getattr(res, "message_id", ""),
        **fields,
    )
    return {"ok": res.ok, "alias": alias, "error": getattr(res, "error", ""), "message_id": getattr(res, "message_id", "")}


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Gmail label router self-test")
    p.add_argument("--uid", required=True)
    p.add_argument("--persona", required=True)
    p.add_argument("--mailbox", default="INBOX")
    args = p.parse_args()
    result = apply_label(args.uid, args.persona, args.mailbox)
    print(json.dumps(result, indent=2, default=str))
