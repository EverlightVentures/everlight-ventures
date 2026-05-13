"""
Investigation orchestrator. Runs every selected investigator in parallel,
streams results to an asyncio.Queue, and writes the final report to disk.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator

import httpx

from . import investigators
from .investigators._common import detect_kind
from .investigation_store import save_investigation

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE/Everlight_Intel_Center")
INVESTIGATIONS_DIR = ROOT / "cache" / "investigations"


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:60] or "target"


async def run_investigation(target: str,
                            sources: list[str] | None = None,
                            kind: str | None = None,
                            triggered_by: str = "unknown",
                            lead_id: int | None = None,
                            verify_context: dict | None = None,
                            business_purpose: str = "",
                            phone: str | None = None,
                            business_name: str | None = None,
                            linkedin_url: str | None = None,
                            prior_addresses: list[str] | None = None) -> AsyncIterator[dict]:
    """
    Async generator yielding events as the investigation progresses:
      {type: "start", target, kind, total_investigators, started_at, investigators: [...]}
      {type: "investigator_start", investigator_id, name}
      {type: "result", investigator_id, payload}
      {type: "investigator_done", investigator_id, ok, elapsed_ms}
      {type: "done", target, total_findings, elapsed_ms, investigation_id, file}
    """
    # ---- CRITICAL: business_purpose required at orchestrator level ----
    # Closes the bypass vector where a direct import could skip the FastAPI 400 gate.
    if not (business_purpose or "").strip():
        from . import compliance_log
        compliance_log.log_action(
            action="policy_violation", target=target, actor=triggered_by,
            notes="orchestrator called with empty business_purpose; investigation aborted",
        )
        raise ValueError(
            "business_purpose is required (per Everlight compliance doctrine). "
            "Pass business_purpose=... when calling run_investigation()."
        )

    # ---- Lead-context enrichment ----
    # Merge new optional kwargs into verify_context so downstream investigators
    # (and the DNC check below) have access to phone/business/linkedin/prior_addresses.
    # Each non-empty input lifts the eventual profile depth score.
    if verify_context is None:
        verify_context = {}
    if phone:
        verify_context.setdefault("owner_phone", phone)
    if business_name:
        verify_context.setdefault("business_name", business_name)
    if linkedin_url:
        verify_context.setdefault("linkedin_url", linkedin_url)
    if prior_addresses:
        verify_context.setdefault("prior_addresses", list(prior_addresses))

    # ---- CRITICAL: DNC preflight ----
    # If the target matches any DNC entry, mark the payload so the renderer + every
    # downstream consumer shows the DNC banner. Knowledge is still collected (we want
    # the world picture), but no consumer is allowed to draft outreach.
    dnc_info = {"is_dnc": False, "reason": "", "entry_id": None}
    try:
        import sys as _sys
        _sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale")
        from skip_trace.dnc_check import check as _dnc_check  # type: ignore
        # Pull anything useful from verify_context for DNC matching
        ctx = verify_context or {}
        dnc_info = _dnc_check(
            owner_name=target,
            phone=str(ctx.get("owner_phone") or ""),
            email=str(ctx.get("owner_email") or ""),
            address=str(ctx.get("address") or ""),
        )
    except Exception:
        pass

    started = datetime.now()
    inv_id = f"{_slug(target)}_{int(started.timestamp())}"
    INVESTIGATIONS_DIR.mkdir(parents=True, exist_ok=True)
    if not kind:
        kind = detect_kind(target)
    selected = investigators.for_target(target, kind)
    if sources:
        selected = [m for m in selected if m.__name__.split(".")[-1] in sources]

    yield {"type": "start", "target": target, "kind": kind,
           "total_investigators": len(selected),
           "started_at": started.isoformat(),
           "investigation_id": inv_id,
           "triggered_by": triggered_by,
           "lead_id": lead_id,
           "verify_enabled": bool(verify_context and any(verify_context.values())),
           "dnc_blocked": dnc_info["is_dnc"],
           "dnc_reason": dnc_info["reason"],
           "investigators": [m.__name__.split(".")[-1] for m in selected]}

    # If DNC-blocked, emit an early visible event so the streaming UI shows the banner immediately
    if dnc_info["is_dnc"]:
        from . import compliance_log
        compliance_log.log_action(
            action="policy_violation", target=target, actor=triggered_by,
            business_purpose=business_purpose,
            notes=f"DNC entry matched: {dnc_info['reason']}; investigation continues for knowledge only",
        )

    all_results: list[dict] = []
    queue: asyncio.Queue = asyncio.Queue()

    async with httpx.AsyncClient(http2=False, follow_redirects=True) as http:
        async def run_one(mod):
            iid = mod.__name__.split(".")[-1]
            await queue.put({"type": "investigator_start",
                             "investigator_id": iid, "name": mod.NAME})
            t0 = time.time()
            try:
                payload = await mod.run(target, http)
            except Exception as e:
                payload = {"ok": False, "findings": [], "raw": {},
                           "investigator": mod.NAME, "investigator_id": iid,
                           "error": str(e)[:200],
                           "elapsed_ms": int((time.time() - t0) * 1000)}
            elapsed_ms = payload.get("elapsed_ms", int((time.time() - t0) * 1000))
            # Verification per-finding if context provided.
            # resource_lookup is a meta-investigator (catalog suggestions, not identity
            # claims) -- exempt from verification, always render as accepted.
            if verify_context and any(verify_context.values()) and iid != "resource_lookup":
                try:
                    import sys as _sys
                    _sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale")
                    from skip_trace.identity_verifier import verify_finding  # type: ignore
                    for f in payload.get("findings", []):
                        f["verification"] = verify_finding(verify_context, f, iid)
                except Exception as _e:
                    pass  # never block stream on verifier issue
            await queue.put({"type": "result", "investigator_id": iid,
                             "payload": payload})
            await queue.put({"type": "investigator_done",
                             "investigator_id": iid,
                             "ok": payload.get("ok", False),
                             "elapsed_ms": elapsed_ms})
            all_results.append(payload)

        # Launch all investigators concurrently. When the gather finishes,
        # send a sentinel to close the consumer loop.
        async def producer():
            await asyncio.gather(*(run_one(m) for m in selected),
                                 return_exceptions=True)
            await queue.put(None)  # sentinel

        producer_task = asyncio.create_task(producer())
        while True:
            event = await queue.get()
            if event is None:
                break
            yield event
        await producer_task

    elapsed_ms = int((datetime.now() - started).total_seconds() * 1000)
    total_findings = sum(len(r.get("findings", [])) for r in all_results)
    # Attribution + verification summary on the persisted record
    verification_summary = None
    if verify_context and any(verify_context.values()):
        try:
            import sys as _sys
            _sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale")
            from skip_trace.identity_verifier import verify_investigation  # type: ignore
            verification_summary = verify_investigation(verify_context, all_results)["summary"]
        except Exception:
            verification_summary = None

    final = {
        "investigation_id": inv_id,
        "target": target, "kind": kind,
        "started_at": started.isoformat(),
        "finished_at": datetime.now().isoformat(),
        "elapsed_ms": elapsed_ms,
        "total_findings": total_findings,
        "investigators_run": len(selected),
        "triggered_by": triggered_by,
        "lead_id": lead_id,
        "business_purpose": business_purpose,
        "verify_context": verify_context or {},
        "verification_summary": verification_summary,
        "dnc_blocked": dnc_info["is_dnc"],
        "dnc_reason": dnc_info["reason"],
        "dnc_entry_id": dnc_info.get("entry_id"),
        "results": all_results,
    }
    file_path = INVESTIGATIONS_DIR / f"{inv_id}.json"
    file_path.write_text(json.dumps(final, indent=2))
    try:
        import os
        os.chmod(file_path, 0o600)
    except OSError:
        pass
    save_investigation(final)

    # Persist a rendered HTML snapshot for static dashboard browsing
    try:
        from .profile_synthesizer import synthesize as _synth
        from .report_renderer import render_profile_html as _render
        from . import legal_state as _legal_state
        reports_dir = ROOT / "cache" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        profile = _synth(final)
        state_code = (verify_context or {}).get("state", "") if verify_context else ""
        state_rules = _legal_state.state_rules_for(state_code) if state_code else None
        html_str = _render(profile, state_rules=state_rules,
                           watermark={"viewer": triggered_by, "ts": datetime.now().isoformat()[:19]},
                           business_purpose=business_purpose)
        html_path = reports_dir / f"{inv_id}.html"
        html_path.write_text(html_str)
        try: __import__("os").chmod(html_path, 0o600)
        except OSError: pass
    except Exception as _e:
        pass  # never block the pipeline
    yield {"type": "done", "target": target, "total_findings": total_findings,
           "elapsed_ms": elapsed_ms, "investigation_id": inv_id,
           "file": str(file_path)}


def run_investigation_sync(target: str, sources: list[str] | None = None,
                            kind: str | None = None,
                            triggered_by: str = "cli_user",
                            lead_id: int | None = None,
                            verify_context: dict | None = None,
                            business_purpose: str = "",
                            phone: str | None = None,
                            business_name: str | None = None,
                            linkedin_url: str | None = None,
                            prior_addresses: list[str] | None = None) -> tuple[list[dict], str]:
    """
    Sync wrapper used by `intel investigate` CLI -- collects result events.
    Returns (results, investigation_id) so the CLI can print the report URL.

    Lead-context kwargs (phone, business_name, linkedin_url, prior_addresses)
    are optional but lift profile depth substantially when supplied.
    """
    inv_id_holder = {"id": ""}
    async def _collect():
        results = []
        async for event in run_investigation(target, sources, kind,
                                              triggered_by=triggered_by,
                                              lead_id=lead_id,
                                              verify_context=verify_context,
                                              business_purpose=business_purpose,
                                              phone=phone,
                                              business_name=business_name,
                                              linkedin_url=linkedin_url,
                                              prior_addresses=prior_addresses):
            if event["type"] == "start":
                inv_id_holder["id"] = event.get("investigation_id", "")
            if event["type"] == "result":
                results.append(event["payload"])
        return results
    results = asyncio.run(_collect())
    return results, inv_id_holder["id"]
