"""hive_dispatcher -- event-driven worker router.

Runs on the phone at 127.0.0.1:8600. Receives events from:
  - Supabase Database Webhooks (via the Oracle MCP tunnel -> n8n -> here)
  - n8n workflows (Gmail, Stripe, Slack triggers)
  - local scripts posting directly

Each event type fires the right worker script. This replaces polling crons
with event-driven execution -- rex_belfort fires only when there IS a new
lead, not every hour regardless.

Endpoints:
  GET  /health
  POST /event/wholesale_lead_new     body: {"lead_id": "..."} or Supabase INSERT payload
  POST /event/wholesale_reply        body: {"thread_id": "...", "from_email": "...", "lead_id?": "..."}
  POST /event/stripe_charge          body: Stripe event payload
  POST /event/slack_dm               body: Slack event payload

Every event is:
  1. Logged to /mnt/sdcard/AA_MY_DRIVE/_logs/dispatcher/events.jsonl
  2. Posted to Slack #deploy-log (summary)
  3. Routed to its handler, which spawns the worker async

Worker stdout/stderr go to per-event log files so they can be reviewed.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
LOG_DIR = ROOT / "_logs" / "dispatcher"
LOG_DIR.mkdir(parents=True, exist_ok=True)
EVENTS_LOG = LOG_DIR / "events.jsonl"
WORKER_LOG_DIR = LOG_DIR / "workers"
WORKER_LOG_DIR.mkdir(parents=True, exist_ok=True)

WHOLESALE_DIR = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Broker_OS" / "wholesale_agent"

# ---- config -----------------------------------------------------------------

AUTH_TOKEN = os.environ.get("HIVE_DISPATCHER_TOKEN", "").strip()
# If blank, the dispatcher requires no auth (binding 127.0.0.1 is the
# primary trust boundary). Set the env to require a Bearer header.


def _slack_post(text: str, channel: str = "#deploy-log") -> None:
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        return
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=json.dumps({"channel": channel, "text": text}).encode(),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
        )
        urllib.request.urlopen(req, timeout=6).read()
    except Exception:
        pass  # best effort


def _log_event(event_type: str, payload: dict[str, Any], outcome: str, worker_log: str | None = None) -> str:
    event_id = uuid.uuid4().hex[:12]
    row = {
        "id": event_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "outcome": outcome,
        "worker_log": worker_log,
        "payload": payload,
    }
    with EVENTS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return event_id


def _check_auth(request: Request) -> None:
    if not AUTH_TOKEN:
        return
    header = request.headers.get("authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    if header[len("Bearer "):].strip() != AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="bad token")


def _spawn(name: str, cmd: list[str], env_extra: dict[str, str] | None = None) -> str:
    """Start a worker subprocess, redirect stdio to a per-event log file.

    Returns the log file path (relative, for logging).
    """
    ts = time.strftime("%Y%m%d-%H%M%S")
    log_path = WORKER_LOG_DIR / f"{ts}_{name}_{uuid.uuid4().hex[:6]}.log"
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    try:
        with log_path.open("w") as f:
            f.write(f"# cmd: {' '.join(shlex.quote(c) for c in cmd)}\n")
            f.write(f"# started: {datetime.now(timezone.utc).isoformat()}\n\n")
            subprocess.Popen(
                cmd,
                stdout=f,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=str(cmd[0]).rsplit("/", 1)[0] if cmd[0].startswith("/") else None,
                start_new_session=True,  # detach from dispatcher PID
            )
    except FileNotFoundError as e:
        log_path.write_text(f"spawn_failed: {e}\n")
    return str(log_path)


# ---- app --------------------------------------------------------------------

app = FastAPI(title="Hive Dispatcher", version="1.0.0")


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "version": app.version,
        "time": datetime.now(timezone.utc).isoformat(),
        "auth": "required" if AUTH_TOKEN else "open-loopback",
    }


def _extract_supabase_row(payload: dict[str, Any]) -> dict[str, Any]:
    """Supabase Database Webhooks send {type, table, record, old_record}.
    Direct caller may just send {lead_id: X} or the row fields directly."""
    if "record" in payload and isinstance(payload["record"], dict):
        return payload["record"]
    return payload


@app.post("/event/wholesale_lead_new")
async def wholesale_lead_new(request: Request):
    _check_auth(request)
    body = await request.json()
    row = _extract_supabase_row(body)
    lead_id = row.get("id") or row.get("lead_id") or body.get("lead_id")
    if not lead_id:
        event_id = _log_event("wholesale_lead_new", body, "missing_lead_id")
        raise HTTPException(status_code=400, detail={"error": "missing_lead_id", "event_id": event_id})

    addr = row.get("address", "?")
    state = row.get("state", "?")

    cmd = [
        "/usr/bin/python3",
        str(WHOLESALE_DIR / "rex_belfort_sequence.py"),
        "--lead-id", str(lead_id),
    ]
    # Pass the outreach env the original cron passed
    env_extra = {
        "IMAP_USER": os.environ.get("IMAP_USER", "1m.rich.gee@gmail.com"),
        "IMAP_PASS": os.environ.get("IMAP_PASS", "dqyo wjlb jyzo mbmg"),
        "RESEND_API_KEY": os.environ.get("RESEND_API_KEY", "re_6S6DgX94_BDzaAU3r3Y5Syca6F58m2aEt"),
        "SLACK_BOT_TOKEN": os.environ.get("SLACK_BOT_TOKEN", "xoxb-8645963765681-10542494223845-M2gIADgkLB2HYJN4F8lGpbuI"),
    }
    worker_log = _spawn("rex_belfort", cmd, env_extra)
    event_id = _log_event("wholesale_lead_new", body, "dispatched", worker_log)
    _slack_post(f":dart: new wholesale lead `{lead_id}` @ `{addr}` ({state}) -> rex_belfort fired (event {event_id})")
    return JSONResponse({"ok": True, "event_id": event_id, "lead_id": lead_id, "worker_log": worker_log})


@app.post("/event/wholesale_reply")
async def wholesale_reply(request: Request):
    _check_auth(request)
    body = await request.json()
    thread_id = body.get("thread_id") or body.get("threadId")
    from_email = body.get("from_email") or body.get("from")
    lead_id = body.get("lead_id")
    if not (thread_id or lead_id):
        event_id = _log_event("wholesale_reply", body, "missing_thread_and_lead")
        raise HTTPException(status_code=400, detail={"error": "need thread_id or lead_id", "event_id": event_id})

    cmd = ["/usr/bin/python3", str(WHOLESALE_DIR / "rex_negotiator.py")]
    if thread_id:
        cmd += ["--thread-id", str(thread_id)]
    if lead_id:
        cmd += ["--lead-id", str(lead_id)]
    env_extra = {
        "IMAP_USER": os.environ.get("IMAP_USER", "1m.rich.gee@gmail.com"),
        "IMAP_PASS": os.environ.get("IMAP_PASS", "dqyo wjlb jyzo mbmg"),
        "RESEND_API_KEY": os.environ.get("RESEND_API_KEY", "re_6S6DgX94_BDzaAU3r3Y5Syca6F58m2aEt"),
        "SLACK_BOT_TOKEN": os.environ.get("SLACK_BOT_TOKEN", "xoxb-8645963765681-10542494223845-M2gIADgkLB2HYJN4F8lGpbuI"),
    }
    worker_log = _spawn("rex_negotiator", cmd, env_extra)
    event_id = _log_event("wholesale_reply", body, "dispatched", worker_log)
    _slack_post(f":incoming_envelope: reply from `{from_email}` -> rex_negotiator fired (event {event_id})")
    return JSONResponse({"ok": True, "event_id": event_id, "worker_log": worker_log})


@app.post("/event/stripe_charge")
async def stripe_charge(request: Request):
    _check_auth(request)
    body = await request.json()
    event_id = _log_event("stripe_charge", body, "logged")
    # Onboarding handler to be wired next pass; for now we just log + Slack
    amount = (body.get("data", {}).get("object", {}).get("amount")
              or body.get("amount") or "?")
    cust = (body.get("data", {}).get("object", {}).get("customer")
            or body.get("customer") or "?")
    _slack_post(f":money_with_wings: Stripe charge cust=`{cust}` amount=`{amount}` logged (event {event_id})")
    return JSONResponse({"ok": True, "event_id": event_id})


@app.post("/event/slack_dm")
async def slack_dm(request: Request):
    _check_auth(request)
    body = await request.json()
    event_id = _log_event("slack_dm", body, "logged")
    return JSONResponse({"ok": True, "event_id": event_id})




@app.get("/lead/{lead_id}")
def lookup_lead(lead_id: str):
    """Return a lead from the phone-local leads_db.json so the Django CashOfferScan
    page can render it through the reverse SSH tunnel."""
    import json
    p = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/leads_db.json")
    if not p.exists():
        raise HTTPException(status_code=404, detail="leads_db.json not found")
    try:
        leads = json.loads(p.read_text())
    except Exception:
        raise HTTPException(status_code=500, detail="leads_db.json corrupt")
    for l in leads:
        if str(l.get("id") or l.get("lead_id")) == str(lead_id):
            return l
    raise HTTPException(status_code=404, detail="lead_id not found")


@app.post("/event/magnet_click")
async def magnet_click(request: Request):
    _check_auth(request)
    body = await request.json()
    event_id = _log_event("magnet_click", body, "logged")
    return JSONResponse({"ok": True, "event_id": event_id})


@app.post("/event/magnet_accept")
async def magnet_accept(request: Request):
    _check_auth(request)
    body = await request.json()
    event_id = _log_event("magnet_accept", body, "logged")
    _slack_post(f":white_check_mark: magnet ACCEPT lead=`{body.get('lead_id','?')}` magnet=`{body.get('magnet','?')}` -- Piper take over (event {event_id})")
    return JSONResponse({"ok": True, "event_id": event_id})


@app.post("/event/magnet_counter")
async def magnet_counter(request: Request):
    _check_auth(request)
    body = await request.json()
    event_id = _log_event("magnet_counter", body, "logged")
    _slack_post(f":arrows_counterclockwise: magnet COUNTER lead=`{body.get('lead_id','?')}` -- needs higher number (event {event_id})")
    return JSONResponse({"ok": True, "event_id": event_id})


@app.post("/event/magnet_call")
async def magnet_call(request: Request):
    _check_auth(request)
    body = await request.json()
    event_id = _log_event("magnet_call", body, "logged")
    _slack_post(f":telephone_receiver: magnet CALL REQUEST lead=`{body.get('lead_id','?')}` -- call triggered (event {event_id})")
    return JSONResponse({"ok": True, "event_id": event_id})


@app.post("/event/magnet_not_interested")
async def magnet_not_interested(request: Request):
    _check_auth(request)
    body = await request.json()
    event_id = _log_event("magnet_not_interested", body, "logged")
    return JSONResponse({"ok": True, "event_id": event_id})

if __name__ == "__main__":
    host = os.environ.get("HIVE_DISPATCHER_HOST", "127.0.0.1")
    port = int(os.environ.get("HIVE_DISPATCHER_PORT", "8600"))
    uvicorn.run(app, host=host, port=port, log_level="info")
