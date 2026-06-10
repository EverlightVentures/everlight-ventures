"""triage_daemon -- runs every POLL_INTERVAL seconds. Pulls new emails,
classifies them, drafts responses, auto-DNCs opt-outs, queues high-stakes
items for Rich's approval via Slack.

This is the orchestrator. Modules:
  inbox_poller -> classifier -> dnc_writer + responder -> Resend send

Per Rich's halt-policy v2 (2026-05-07):
  - opt_out -> immediate auto-reply confirmation + DNC add (no human approval)
  - legal_threat -> DNC add + queue Rich + auto-draft a defensible reply
  - positive_reply -> queue Rich (with draft)
  - question -> queue Rich (with draft)
  - bounce -> log only
  - spam -> archive
  - other -> queue Rich

Every action writes an audit envelope to /AA_MY_DRIVE/_audit/email_triage/
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import classifier
import dnc_writer
import inbox_poller
import responder

LOG_PATH = Path("/AA_MY_DRIVE/_logs/email_triage/daemon.log")
AUDIT_DIR = Path("/AA_MY_DRIVE/_audit/email_triage")
APPROVAL_QUEUE = Path("/AA_MY_DRIVE/_logs/email_triage/approval_queue.jsonl")
POLL_INTERVAL = int(os.environ.get("EMAIL_TRIAGE_POLL_SECONDS", "300"))  # 5 min
DRY_RUN = os.environ.get("EMAIL_TRIAGE_DRY_RUN", "1") == "1"


def _log(msg: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {msg}\n")


def _audit(msg_id: str, payload: dict) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    safe = msg_id.replace("/", "_").replace("<", "").replace(">", "")[:120]
    p = AUDIT_DIR / f"{int(time.time())}_{safe}.json"
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _send_via_resend(to: str, subject: str, body: str) -> dict:
    """Sends via branded_mailer ONLY (gold template, budget gates, guard).
    NO direct-Resend fallback -- doctrine: every send goes through the wrapper,
    and a broken wrapper must fail loud, not degrade to plain-text email.
    DRY_RUN=1 skips actual send and just logs."""
    if DRY_RUN:
        _log(f"[DRY_RUN] would send to={to!r} subj={subject!r} body[0:80]={body[:80]!r}")
        return {"ok": True, "dry_run": True}

    try:
        # phone workspace + Oracle deploy locations (first existing one wins)
        for root in ("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts",
                     "/home/opc/scripts", "/home/ubuntu/scripts"):
            if root not in sys.path:
                sys.path.insert(0, root)
        from content_tools.branded_mailer import send_branded_email
        result = send_branded_email(
            to=to,
            subject=subject,
            content_html=body.replace("\n", "<br>\n"),
            agent_name="Piper Reeves",
            agent_title="Wholesale Outreach Lead",
            budget_category="vip_reply",  # replies are VIP per CLAUDE.md
        )
        ok = result.get("ok", False) if isinstance(result, dict) else bool(getattr(result, "ok", False))
        return {"ok": ok, "via": "branded_mailer", "detail": str(result)[:500]}
    except Exception as e:
        _log(f"branded_mailer failed: {e}; send BLOCKED (no unbranded fallback)")
        return {"ok": False, "via": "branded_mailer", "error": str(e)}


def _queue_for_approval(msg: dict, classification: dict, draft: dict) -> None:
    APPROVAL_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.time(),
        "msg_id": msg["msg_id"],
        "sender_email": msg["sender_email"],
        "subject": msg["subject"],
        "body_preview": msg["body"][:400],
        "tag": classification["tag"],
        "confidence": classification["confidence"],
        "reasoning": classification["reasoning"],
        "draft_subject": draft.get("reply_subject"),
        "draft_body": draft.get("reply_body"),
        "draft_action": draft.get("action"),
        "draft_reason": draft.get("reason"),
    }
    with APPROVAL_QUEUE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    _log(f"queued for approval: {msg['msg_id']} (tag={classification['tag']})")


def process_message(msg: dict) -> dict:
    sender = msg["sender_email"]
    if dnc_writer.is_dnc(sender):
        _log(f"SKIP (DNC): {sender} | {msg['subject'][:60]}")
        _audit(msg["msg_id"], {"action": "skip_dnc", "msg": msg})
        return {"action": "skip_dnc", "sender": sender}

    cls = classifier.classify(msg["subject"], msg["body"], sender)
    _log(f"classified: {sender} -> {cls['tag']} (conf={cls['confidence']:.2f}) "
         f"| {cls['reasoning'][:80]}")

    draft = responder.draft(cls["tag"], sender, msg["subject"], msg["body"],
                             confidence=cls["confidence"])

    audit = {
        "msg": msg,
        "classification": cls,
        "draft": draft,
        "ts": time.time(),
    }

    if draft["action"] == "auto_send":
        # opt_out path: send confirmation, then DNC the sender
        send_result = _send_via_resend(
            to=sender,
            subject=draft["reply_subject"] or "Removed from outreach",
            body=draft["reply_body"],
        )
        audit["send_result"] = send_result
        if cls["tag"] == "opt_out":
            dnc_result = dnc_writer.add_dnc(
                email=sender,
                name=msg.get("sender_name", ""),
                reason=f"opt_out_reply: {cls['reasoning'][:80]}",
                added_by="triage_daemon",
                source_thread_id=msg.get("thread_id", ""),
            )
            audit["dnc_result"] = dnc_result
        _audit(msg["msg_id"], audit)
        return {"action": "auto_send", "sender": sender, "tag": cls["tag"],
                "send_ok": send_result.get("ok", False)}

    if draft["action"] == "queue_for_approval":
        if cls["tag"] == "legal_threat":
            # ALSO immediately DNC, even before Rich approves the reply
            dnc_writer.add_dnc(
                email=sender,
                name=msg.get("sender_name", ""),
                reason=f"legal_threat -- preemptive DNC: {cls['reasoning'][:80]}",
                added_by="triage_daemon",
                source_thread_id=msg.get("thread_id", ""),
            )
        _queue_for_approval(msg, cls, draft)
        _audit(msg["msg_id"], audit)
        return {"action": "queued", "sender": sender, "tag": cls["tag"]}

    if draft["action"] == "flag_only":
        _log(f"flag_only: {sender} -> {cls['tag']}")
        _audit(msg["msg_id"], audit)
        return {"action": "flag_only", "sender": sender, "tag": cls["tag"]}

    if draft["action"] == "archive":
        _audit(msg["msg_id"], audit)
        return {"action": "archive", "sender": sender, "tag": cls["tag"]}

    _audit(msg["msg_id"], audit)
    return {"action": "unknown", "sender": sender}


def run_once() -> dict:
    msgs = inbox_poller.fetch_new_messages(only_unseen=True)
    if not msgs:
        return {"processed": 0}
    counts = {"auto_send": 0, "queued": 0, "skip_dnc": 0,
              "flag_only": 0, "archive": 0, "unknown": 0}
    for m in msgs:
        try:
            r = process_message(m)
            action = r.get("action", "unknown")
            counts[action] = counts.get(action, 0) + 1
        except Exception as e:
            _log(f"process_message failed for {m.get('msg_id')}: {e}")
            counts["unknown"] += 1
    _log(f"poll done: {counts}")
    return {"processed": len(msgs), "counts": counts}


def main() -> int:
    _log(f"triage_daemon started (poll={POLL_INTERVAL}s, dry_run={DRY_RUN})")
    while True:
        try:
            r = run_once()
            if r.get("processed", 0) > 0:
                _log(f"cycle: {r}")
        except Exception as e:
            _log(f"cycle error: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        result = run_once()
        print(json.dumps(result, indent=2))
        sys.exit(0)
    sys.exit(main() or 0)
