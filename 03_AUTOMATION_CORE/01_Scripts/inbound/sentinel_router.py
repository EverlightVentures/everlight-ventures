"""Turn a classified stranger email into actions.

decide_action(classification) -> "auto_reply" | "draft"  (pure, testable)
route(msg, classification, *, dry_run) -> dict             (side effects)

Safety: auto_reply ONLY for low-risk, non-opsec, non-high-stakes categories.
Everything else becomes a Gmail draft for one-tap human approval. Every send
goes through branded_mailer (which runs eradication_gate internally) and a
confidentiality scan that FAILS CLOSED -- if the gate cannot run we do NOT
send, we downgrade to alert-only. Mirrors the eradication-gate doctrine.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Put the Scripts dir (and the moltbook gate dir) on sys.path ONCE at import
# time so content_tools.* and the confidentiality gate resolve without
# per-call path mutation.
_SCRIPTS = Path(__file__).resolve().parents[1]  # .../01_Scripts
for _p in (str(_SCRIPTS), str(_SCRIPTS / "moltbook")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_LOG_DIR = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/inbound")
LOG = _LOG_DIR / "sentinel.jsonl"
DRAFTS = _LOG_DIR / "drafts.jsonl"

# Categories the classifier actually emits AND that are safe to auto-reply.
# (opt_out auto-reply is a planned classifier addition; until the classifier
#  emits "opt_out", an unsubscribe lands as "other" and safely drafts.)
_AUTO_REPLY_OK = {"sales_pitch"}

_PERSONA = {
    "sales_pitch": ("Vaughn Sterling", "Senior Partner", "vaughn@everlightventures.io"),
    "partnership": ("Vaughn Sterling", "Senior Partner", "vaughn@everlightventures.io"),
    "investor":    ("Vaughn Sterling", "Senior Partner", "vaughn@everlightventures.io"),
    "press":       ("Everlight Content", "Press Desk", "press@everlightventures.io"),
    "job":         ("Everlight Ops", "Operations", "ops@everlightventures.io"),
    "recon_probe": ("Vaughn Sterling", "Senior Partner", "vaughn@everlightventures.io"),
    "other":       ("Everlight Ventures", "Front Desk", "hello@everlightventures.io"),
}


def decide_action(classification: dict) -> str:
    if classification.get("opsec_flag"):
        return "draft"
    if classification.get("high_stakes"):
        return "draft"
    if classification.get("category") in _AUTO_REPLY_OK:
        return "auto_reply"
    return "draft"


def _log(record: dict) -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    record.setdefault("ts", datetime.now(timezone.utc).isoformat())
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, default=str) + "\n")


def _confidential_ok(body: str) -> bool:
    """True only if the reply body provably leaks no internal state.

    FAILS CLOSED: if the confidentiality gate cannot be imported or the scan
    raises, return False so route() downgrades to alert-only instead of
    sending. Mirrors the eradication_gate fail-closed doctrine.
    """
    try:
        from moltbook_confidentiality_gate import scan
        return len(scan(body)) == 0
    except Exception:
        return False


def _safe_reply_body(persona_name: str) -> str:
    """A content-free brush-off. Names nothing internal. auto_reply only."""
    return (
        "Hi,<br><br>Thanks for reaching out. We are heads-down right now and not "
        "evaluating new tools or partnerships. If that changes we will reach back out.<br><br>"
        f"Best,<br>{persona_name}<br>Everlight Ventures"
    )


def route(msg: dict, classification: dict, *, dry_run: bool = True) -> dict:
    action = decide_action(classification)
    category = classification.get("category", "other")
    persona_name, persona_title, persona_email = _PERSONA.get(category, _PERSONA["other"])
    result = {
        "from": msg.get("from_email"),
        "subject": msg.get("subject"),
        "category": category,
        "action": action,
        "opsec_flag": classification.get("opsec_flag"),
        "referenced_assets": classification.get("referenced_assets", []),
        "persona": persona_name,
        "dry_run": dry_run,
        "sent": False,
        "drafted": False,
        "alerted": False,
        "error": "",
    }
    if dry_run:
        _log(result)
        return result

    # 1. Always alert.
    result["alerted"] = _post_alert(msg, classification, action, persona_name)

    # 2. Reply path.
    if action == "auto_reply":
        body = _safe_reply_body(persona_name)
        if not _confidential_ok(body):
            result["action"] = "blocked_confidential"
        else:
            ok, err = _send_reply(msg, body, persona_name, persona_title, persona_email)
            result["sent"] = ok
            result["error"] = err
            if err.startswith("eradication"):
                # A blocked send is a security event, not a plain failure.
                _log({"event": "eradication_block_on_auto_reply",
                      "from": msg.get("from_email"), "error": err})
    else:
        result["drafted"] = _make_draft(msg, classification, persona_name, persona_email)

    _log(result)
    return result


def _post_alert(msg, classification, action, persona_name) -> bool:
    try:
        from content_tools.branded_slack import post_branded_slack
        cat = classification.get("category", "other")
        channel = "#ceo-brief" if cat in {"partnership", "investor", "press"} else "#hive-alerts"
        assets = classification.get("referenced_assets", [])
        if classification.get("opsec_flag"):
            opsec = "EXPOSED: " + ", ".join(assets) if assets else "EXPOSED"
        else:
            opsec = "clear"
        fields = {
            "From": msg.get("from_email", ""),
            "Category": cat,
            "Action": action,
            "Opsec": opsec,
            "Routed to": persona_name,
        }
        r = post_branded_slack(
            channel=channel,
            title="Inbound Sentinel: stranger reached out",
            summary=msg.get("subject", "")[:140],
            body=msg.get("body", "")[:600],
            fields=fields,
            category="intel",
            agent_name="Inbound Sentinel",
            agent_title="Everlight Ventures",
        )
        return bool(getattr(r, "ok", False))
    except Exception as exc:
        _log({"event": "alert_failed", "error": str(exc), "from": msg.get("from_email")})
        return False


def _send_reply(msg, body, name, title, from_email) -> tuple[bool, str]:
    try:
        from content_tools.branded_mailer import send_branded_email
        r = send_branded_email(
            to=msg.get("from_email"),
            subject="Re: " + msg.get("subject", ""),
            content_html=body,
            from_name="Everlight Ventures",
            from_email=from_email,
            agent_name=name, agent_title=title, agent_email=from_email,
            budget_category="vip_reply",
            persona_id="inbound_sentinel",
            caller="inbound_sentinel",
        )
        return bool(getattr(r, "ok", False)), str(getattr(r, "error", ""))
    except Exception as exc:
        _log({"event": "send_exception", "error": str(exc), "from": msg.get("from_email")})
        return False, f"send_exception:{exc}"


def _make_draft(msg, classification, name, from_email) -> bool:
    draft = {
        "to": msg.get("from_email"),
        "subject": "Re: " + msg.get("subject", ""),
        "suggested_persona": name,
        "from": from_email,
        "category": classification.get("category"),
        "note": "Review before sending. Opsec: " + (
            ", ".join(classification.get("referenced_assets", [])) or "clear"),
        "original_body": msg.get("body", "")[:1000],
    }
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    with DRAFTS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(draft, default=str) + "\n")
    return True
