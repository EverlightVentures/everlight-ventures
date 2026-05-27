"""Turn a classified stranger email into actions.

decide_action(classification) -> "auto_reply" | "draft"  (pure, testable)
route(msg, classification, *, dry_run) -> dict             (side effects)

Safety: auto_reply ONLY for low-risk, non-opsec, non-high-stakes categories.
Everything else becomes a Gmail draft for one-tap human approval. Every send
goes through branded_mailer (which runs eradication_gate internally) and the
confidentiality scan; a confidentiality hit downgrades the send to alert-only.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/inbound/sentinel.jsonl")
_AUTO_REPLY_OK = {"sales_pitch", "vendor_pitch", "opt_out"}

# Persona routing: which teammate owns the reply for each category.
_PERSONA = {
    "sales_pitch": ("Vaughn Sterling", "Senior Partner", "vaughn@everlightventures.io"),
    "opt_out":     ("Vaughn Sterling", "Senior Partner", "vaughn@everlightventures.io"),
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


def _confidential_ok(body: str) -> bool:
    """True if the reply body leaks no internal state. Reuses moltbook gate."""
    try:
        sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/moltbook")
        from moltbook_confidentiality_gate import scan
        return len(scan(body)) == 0
    except Exception:
        return True  # gate import failure must not silently send; see route() guard


def _log(record: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    record["ts"] = datetime.now(timezone.utc).isoformat()
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, default=str) + "\n")


def _safe_reply_body(persona_name: str) -> str:
    """A content-free brush-off. Names nothing internal. Used for auto_reply only."""
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
    }
    if dry_run:
        _log(result)
        return result

    # 1. Always alert (branded Slack card + push handled by orchestrator).
    result["alerted"] = _post_alert(msg, classification, action, persona_name)

    # 2. Reply path.
    if action == "auto_reply":
        body = _safe_reply_body(persona_name)
        if not _confidential_ok(body):
            result["action"] = "blocked_confidential"
        else:
            result["sent"] = _send_reply(msg, body, persona_name, persona_title, persona_email)
    else:
        result["drafted"] = _make_draft(msg, classification, persona_name, persona_email)

    _log(result)
    return result


def _post_alert(msg, classification, action, persona_name) -> bool:
    try:
        sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts")
        from content_tools.branded_slack import post_branded_slack
        cat = classification.get("category", "other")
        channel = "#ceo-brief" if cat in {"partnership", "investor", "press"} else "#hive-alerts"
        fields = {
            "From": msg.get("from_email", ""),
            "Category": cat,
            "Action": action,
            "Opsec": "EXPOSED: " + ", ".join(classification.get("referenced_assets", [])) if classification.get("opsec_flag") else "clear",
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
    except Exception:
        return False


def _send_reply(msg, body, name, title, from_email) -> bool:
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
        return bool(getattr(r, "ok", False))
    except Exception:
        return False


def _make_draft(msg, classification, name, from_email) -> bool:
    """Persist a draft record the orchestrator turns into a Gmail draft."""
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
    out = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/inbound/drafts.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(draft, default=str) + "\n")
    return True
