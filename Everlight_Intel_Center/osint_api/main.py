"""
FastAPI service for OSINT investigations on port 8677.
Streams investigator results live via Server-Sent Events.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse

from . import investigators, live_log, compliance_log, legal_state, template_lint
from .orchestrator import run_investigation
from .investigation_store import list_investigations, load_investigation
from .profile_synthesizer import synthesize as synth_profile
from .report_renderer import render_profile_html

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE/Everlight_Intel_Center")

# Refuse to start if any pitch template contains a phrase_scrub trip word.
# This catches the class of bug where a forbidden phrase lurks in a template
# and only surfaces at send time. See osint_api/template_lint.py.
template_lint.assert_clean()

app = FastAPI(title="Everlight Intel Center -- OSINT API",
              version="1.0", docs_url="/api/docs")


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = ROOT / "osint_api" / "osint.html"
    return HTMLResponse(html_path.read_text())


@app.get("/sources")
async def sources():
    return [
        {"id": m.__name__.split(".")[-1],
         "name": m.NAME,
         "domains": getattr(m, "DOMAINS", []),
         "when": getattr(m, "WHEN", ["*"])}
        for m in investigators.ALL
    ]


@app.get("/investigations")
async def investigations(limit: int = 50):
    return list_investigations(limit=limit)


@app.get("/investigations/{inv_id}")
async def investigation(inv_id: str):
    data = load_investigation(inv_id)
    if not data:
        return JSONResponse({"error": "not found"}, status_code=404)
    return data


@app.get("/live-audit")
async def live_audit(window: int = 30):
    return live_log.stats(window_days=window)


@app.get("/report/{inv_id}", response_class=HTMLResponse)
async def report(inv_id: str, request: Request, viewer: str = "Operator"):
    """Render a branded HTML profile report. Logs every view to compliance_log."""
    payload = load_investigation(inv_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Investigation not found")
    profile = synth_profile(payload)
    state = (payload.get("verify_context") or {}).get("state") or \
            (payload.get("lead_context") or {}).get("state") or ""
    state_rules = legal_state.state_rules_for(state) if state else None
    business_purpose = payload.get("business_purpose", "")
    watermark = {"viewer": viewer,
                 "ts": datetime.now().isoformat()[:19] if False else __import__("datetime").datetime.now().isoformat()[:19]}
    # Log this view to compliance_log
    compliance_log.log_action(
        action="view_report",
        target=payload.get("target", ""),
        actor=viewer,
        lead_id=payload.get("lead_id"),
        business_purpose=business_purpose,
        ip_addr=str(request.client.host if request.client else ""),
        user_agent=request.headers.get("user-agent", "")[:200],
        state=state,
        state_rules=state_rules,
        notes=f"investigation_id={inv_id}",
    )
    html_out = render_profile_html(profile, state_rules=state_rules,
                                     watermark=watermark,
                                     business_purpose=business_purpose)
    return HTMLResponse(html_out, headers={"Cache-Control": "no-store"})


@app.get("/events")
async def events(target: str, sources: str = "", kind: str = "",
                 triggered_by: str = "web_user",
                 lead_id: int | None = None,
                 business_purpose: str = "",
                 verify_for_state: str = "",
                 verify_for_city: str = "",
                 verify_for_email: str = "",
                 verify_for_phone: str = "",
                 verify_for_address: str = ""):
    """
    SSE stream. Per-finding verification when any `verify_for_*` param is set.

    Examples:
      ?target=Linda%20Smith&verify_for_state=CA&verify_for_city=Sacramento
      ?target=Acme%20Corp&triggered_by=cipher_wolfe&lead_id=99
    """
    src_list = [s.strip() for s in sources.split(",") if s.strip()] or None
    kind_val = kind.strip() or None
    purpose_val = (business_purpose or "").strip()
    if not purpose_val:
        raise HTTPException(
            status_code=400,
            detail="business_purpose is required (per Everlight compliance doctrine -- record why you are investigating this target)"
        )
    verify_context = {
        "owner_name": target,
        "state": verify_for_state.strip() or None,
        "city": verify_for_city.strip() or None,
        "owner_email": verify_for_email.strip() or None,
        "owner_phone": verify_for_phone.strip() or None,
        "address": verify_for_address.strip() or None,
    }

    # Compliance log entry for the investigation start
    state_rules = (legal_state.state_rules_for(verify_for_state.strip())
                   if verify_for_state.strip() else None)
    compliance_log.log_action(
        action="investigate", target=target, actor=triggered_by,
        lead_id=lead_id, business_purpose=purpose_val,
        state=verify_for_state.strip(), state_rules=state_rules,
        notes=f"sources={sources}, kind={kind}",
    )

    async def event_gen():
        async for event in run_investigation(
            target, sources=src_list, kind=kind_val,
            triggered_by=triggered_by, lead_id=lead_id,
            verify_context=verify_context,
            business_purpose=purpose_val,
        ):
            yield {"event": event.get("type", "message"),
                   "data": json.dumps(event)}

    return EventSourceResponse(event_gen())


@app.get("/healthz")
async def healthz():
    return {"ok": True, "service": "intel_osint", "port": 8677}
