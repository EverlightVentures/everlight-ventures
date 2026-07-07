from __future__ import annotations

import os

_TAGS = {5: "rotating_light", 4: "warning", 3: "bell"}


def ntfy_sender(event: dict, priority: int) -> bool:
    """Push an alert via ntfy. No-op (False) if SLD_NTFY_URL is unset.

    SLD_NTFY_URL is a full topic URL, e.g. https://ntfy.sh/ev-secops-<secret>
    or a self-hosted http://e5-mother:2586/ev-secops. Priority 1-5 (5 breaks DND).
    """
    url = os.environ.get("SLD_NTFY_URL")
    if not url:
        return False
    import httpx

    lvl = event.get("threat_level", "")
    dist = f" {event['distance_mi']}mi" if event.get("distance_mi") is not None else ""
    title = f"[{lvl}] {event.get('type') or 'Incident'}"
    body = f"{event.get('geo_label') or ''}{dist}\n{(event.get('body') or '')[:200]}"
    try:
        r = httpx.post(
            url,
            data=body.encode("utf-8"),
            headers={
                "Title": title,
                "Priority": str(priority or 3),
                "Tags": _TAGS.get(priority, "bell"),
            },
            timeout=10,
        )
        return r.status_code < 300
    except Exception:  # noqa: BLE001 - alert transport must never crash the worker
        return False


def email_sender(event: dict, priority: int) -> bool:
    """Email an alert via the branded mailer. No-op if unavailable or unconfigured."""
    to = os.environ.get("SLD_ALERT_EMAIL")
    if not to:
        return False
    try:
        from content_tools.branded_mailer import send_branded_email
    except Exception:  # noqa: BLE001 - content_tools only lives on e5/Oracle
        return False
    lvl = event.get("threat_level", "")
    subject = f"[SECOPS][{lvl}] {event.get('type') or 'Incident'} {event.get('distance_mi') or ''}".strip()
    html = (
        f"<h2>{event.get('type') or 'Incident'}</h2>"
        f"<p><b>Threat:</b> {lvl} &middot; <b>Distance:</b> {event.get('distance_mi')} mi</p>"
        f"<p><b>Where:</b> {event.get('geo_label') or ''}</p>"
        f"<pre>{(event.get('body') or '')[:1000]}</pre>"
    )
    try:
        res = send_branded_email(to=to, subject=subject, html=html, budget_category="system")
        return bool(getattr(res, "ok", res))
    except Exception:  # noqa: BLE001
        return False
