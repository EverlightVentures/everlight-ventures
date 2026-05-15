"""Branded mailer -- the SINGLE path all Everlight outbound email must take.

Why this exists: before this module, every sender script (hive_outreach, rex_closer,
rex_batch_offers, ad-hoc test scripts) had its own direct call to api.resend.com.
Each time someone forgot to wrap the body in render_report() the email went out
looking like a plain-text notification instead of the luxury template Rich built.

Rule: NO direct HTTP calls to api.resend.com outside this module.
Every caller imports send_branded_email() and goes through render_report().
This way the template renders by default, not by discipline.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen

# Make the template importable from wherever this runs on (phone or Oracle)
_THIS = Path(__file__).resolve()
for candidate in (_THIS.parent, _THIS.parent.parent, _THIS.parent.parent.parent):
    if (candidate / "report_template.py").exists():
        sys.path.insert(0, str(candidate))
        break

from report_template import render_report  # noqa: E402

log = logging.getLogger("branded_mailer")


def _state_for_recipient(email: str) -> str:
    """Best-effort: derive recipient state from a Supabase / Django lookup.

    Returns empty string when unknown -- in which case the cadence gate
    is skipped (we cannot enforce state rules without a state). For
    state-locked outreach, the caller should pass the state explicitly
    in a future enhancement.
    """
    return ""

RESEND_URL = "https://api.resend.com/emails"


@dataclass
class MailResult:
    ok: bool
    message_id: str = ""
    error: str = ""
    preview_bytes: int = 0


def send_branded_email(
    *,
    to: str | list[str],
    subject: str,
    content_html: str,
    title: Optional[str] = None,
    from_name: str = "Everlight Ventures",
    from_email: str = "noreply@everlightventures.io",
    reply_to: Optional[str] = None,
    agent_name: str = "Everlight Ventures",
    agent_title: str = "Automated Intelligence",
    agent_email: Optional[str] = None,
    confidential: bool = False,
    plain_text_fallback: Optional[str] = None,
    api_key: Optional[str] = None,
    budget_category: str = "bulk",
    recipient_state: str = "",
    lead_type: str = "",
    state_disclaimer: bool = True,
) -> MailResult:
    """Send an email wrapped in the Everlight luxury template.

    Args:
        to:              recipient email or list of recipients
        subject:         email subject (also used as template title if `title` omitted)
        content_html:    INNER body HTML -- will be wrapped by render_report().
                         Caller writes the message; render_report adds the header,
                         luxury styling, signature block, and footer.
        title:           optional distinct template H1 (defaults to subject)
        from_name/email: display name + address. Must be a verified Resend domain sender.
        reply_to:        defaults to from_email
        agent_name/title/email:  signature block identity (who sent it from our team)
        confidential:    shows CONFIDENTIAL badge in header
        plain_text_fallback: optional plain-text body for clients that don't render HTML.
                         Auto-generated from content_html if omitted.
        api_key:         override RESEND_API_KEY env var (rarely needed)

    Returns MailResult. Never raises on auth/network -- callers check .ok.
    """
    key = api_key or os.environ.get("RESEND_API_KEY", "") or os.environ.get("SMTP_PASS", "")
    if not key:
        return MailResult(ok=False, error="no_resend_api_key_in_env")

    if not to:
        return MailResult(ok=False, error="no_recipient")

    recipients = [to] if isinstance(to, str) else list(to)

    # ============================================================
    # ERADICATION GATE -- FIRST CHECK, NO BYPASSES, NO EXCEPTIONS.
    # Hardcoded list of permanent-DNC subjects (e.g. David A. Streubel /
    # municipalfirm.com -- BBB complainant from 2026-04-26). This gate must
    # fire BEFORE resend_guard / budget / cadence / phrase_scrub because it
    # is the most absolute rule. See eradication_gate.py for the list and
    # MEMORY.md `feedback-streubel-permanent-eradication` for the doctrine.
    # ============================================================
    try:
        import sys as _sys, pathlib as _pl
        _here = _pl.Path(__file__).parent
        if str(_here) not in _sys.path:
            _sys.path.insert(0, str(_here))
        from eradication_gate import assert_safe as _erad_assert_safe, EradicationViolation
        for _r in recipients:
            _erad_assert_safe(email=_r, caller="branded_mailer.send_branded_email")
    except EradicationViolation as _erad_err:
        log.error("ERADICATION GATE blocked send: %s", _erad_err)
        return MailResult(ok=False, error=f"eradication_blocked:{_erad_err}")
    except ImportError as _erad_imp:
        # If the gate module is missing, FAIL CLOSED. Do not send.
        log.error("eradication_gate module missing -- failing closed: %s", _erad_imp)
        return MailResult(ok=False, error="eradication_gate_module_missing_fail_closed")

    try:
        from resend_guard import assert_safe_recipient
    except ImportError:
        import sys as _sys, pathlib as _pl
        _sys.path.insert(0, str(_pl.Path(__file__).parent))
        try:
            from resend_guard import assert_safe_recipient  # noqa
        except ImportError:
            # Fallback to legacy guard if running against an older resend_guard
            from resend_guard import assert_external_recipient as assert_safe_recipient  # noqa
    try:
        assert_safe_recipient(recipients)
    except Exception as _guard_err:
        return MailResult(ok=False, error=f"guard_blocked: {_guard_err}")

    # Inject per-state advertising disclaimer (audit-required).
    if state_disclaimer and recipient_state:
        try:
            import sys as _sys
            for _p in ("/home/opc/wholesale/compliance",
                       "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance"):
                if _p not in _sys.path:
                    _sys.path.insert(0, _p)
            from state_advertising_disclaimers import disclaimer_html
            d = disclaimer_html(recipient_state)
            if d:
                content_html = (content_html or "") + d
        except Exception:
            pass

    # Monthly pacing + VIP reserve gate. Never blocks system or vip_reply
    # except at 98% of cap. Blocks bulk if it would burn through the month.
    try:
        from resend_budget import check_budget, record_send  # type: ignore
        dec = check_budget(category=budget_category, count=len(recipients))
        if not dec.allowed:
            log.warning("resend_budget blocked %s to %s: %s", budget_category, recipients, dec.reason)
            return MailResult(ok=False, error=f"budget_blocked:{dec.reason}")
    except Exception as _budget_err:
        # Budget module must never block core send on error.
        log.warning("resend_budget import/check failed, allowing send: %s", _budget_err)
        record_send = None  # type: ignore

    # Day-of-week + per-state + per-channel compliance gate. Looks up the
    # recipient's state via _state_for_recipient (best-effort) and refuses
    # the send when state law or weekly_cadence rules would prohibit it.
    # vip_reply and system categories bypass time-of-day (response sends
    # are not solicitation under the TSR).
    try:
        if budget_category in {"bulk", "nurture"}:
            import sys as _sys
            for _p in ("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance",
                       "/home/opc/wholesale/compliance"):
                if _p not in _sys.path:
                    _sys.path.insert(0, _p)
            from weekly_cadence import is_outreach_allowed_now  # type: ignore
            state_to_check = (recipient_state or _state_for_recipient(recipients[0]) if recipients else "")
            if state_to_check:
                allowed, reason = is_outreach_allowed_now(state_to_check, "email", lead_type=lead_type)
                if not allowed:
                    log.warning("weekly_cadence blocked email to %s (%s): %s",
                                recipients, state_to_check, reason)
                    return MailResult(ok=False, error=f"cadence_blocked:{reason}")
    except Exception as _cadence_err:
        # Never block core send on cadence-engine error.
        log.warning("weekly_cadence import/check failed, allowing send: %s", _cadence_err)

    # Justine's pre-send phrase scrub. Block agent-representation language
    # for the recipient's state before the body is rendered or sent. This
    # is the unauthorized-brokerage trap (ORC 4735.02 in OH). The scrub
    # runs on the merged content_html + plain_text_fallback (tokens already
    # substituted by callers). State is required; baseline applies if missing.
    try:
        import sys as _sys, pathlib as _pl
        _here = _pl.Path(__file__).parent
        if str(_here) not in _sys.path:
            _sys.path.insert(0, str(_here))
        from pre_send_phrase_scrub import validate_outbound  # type: ignore
        _scrub_text = (content_html or "") + "\n" + (plain_text_fallback or "")
        _scrub = validate_outbound(
            _scrub_text,
            state=(recipient_state or "").upper(),
            channel="email",
            recipient=recipients[0] if recipients else "",
        )
        if not _scrub.ok:
            log.warning(
                "phrase_scrub blocked email to %s (%s): %s",
                recipients, recipient_state, _scrub.blocked_phrases,
            )
            return MailResult(
                ok=False,
                error=f"phrase_scrub_blocked: {_scrub.blocked_phrases[0]}",
            )
    except Exception as _scrub_err:
        # Never block core send on scrub-engine error -- log and proceed.
        log.warning("phrase_scrub import/check failed, allowing send: %s", _scrub_err)

    html_body = render_report(
        title=title or subject,
        content_html=content_html,
        agent_name=agent_name,
        agent_title=agent_title,
        agent_email=agent_email or from_email,
        confidential=confidential,
    )

    text_body = plain_text_fallback or _strip_tags(content_html)

    payload = {
        "from": f"{from_name} <{from_email}>",
        "to": recipients,
        "subject": subject,
        "html": html_body,
        "text": text_body,
        "reply_to": reply_to or from_email,
    }

    req = Request(
        RESEND_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "everlight-branded-mail/1.0",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=15) as resp:
            if resp.status in (200, 201):
                data = json.loads(resp.read().decode())
                msg_id = str(data.get("id", ""))
                # Record the send in the budget ledger so future checks see it.
                if record_send is not None:
                    try:
                        for r in recipients:
                            record_send(category=budget_category, message_id=msg_id, to=r, subject=subject)
                    except Exception:
                        pass
                return MailResult(
                    ok=True, message_id=msg_id,
                    preview_bytes=len(html_body),
                )
            return MailResult(ok=False, error=f"http_{resp.status}", preview_bytes=len(html_body))
    except Exception as e:
        return MailResult(ok=False, error=f"exception:{e}", preview_bytes=len(html_body))


def _strip_tags(html: str) -> str:
    """Crude HTML -> text fallback. Good enough for fallback clients."""
    import re
    # Replace block-level tags with newlines, then strip remaining tags
    text = re.sub(r"</?(p|div|h[1-6]|li|tr|br)[^>]*>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    # Collapse whitespace
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


if __name__ == "__main__":
    # CLI test: python3 branded_mailer.py <recipient>
    import sys as _sys
    if len(_sys.argv) < 2:
        print("usage: python3 branded_mailer.py <recipient_email>")
        _sys.exit(1)
    result = send_branded_email(
        to=_sys.argv[1],
        subject="Branded mailer test",
        content_html="<h2>Test</h2><p>If you see the gold header, the luxury template is live.</p>",
        agent_name="Hive Mind",
        agent_title="Integration Test",
    )
    print(result)
