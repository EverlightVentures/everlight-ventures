"""swarm_queue_poller -- 5-minute cron-fired poller that consumes
queue/incoming.jsonl, dispatches each RFP through the swarm, and writes
queue/outgoing.jsonl with the resulting artifact URIs.

v0.1 scope:
  - reads incoming.jsonl line by line, deduped by trace_id
  - calls swarm_budget.check_budget() BEFORE invoking any LLM
  - in MOCK mode (default), does NOT actually invoke OpenSwarm yet -- it
    produces a deterministic stub package per agent so the chain shape
    can be validated end-to-end without API spend
  - in LIVE mode (SWARM_LIVE=1), calls the openswarm CLI
  - writes outgoing.jsonl on every completion (status: done | halted | error)
  - logs to /AA_MY_DRIVE/_logs/swarm_queue_poller.log

Per Marcus's policy: kill-switch is `systemctl --user stop
everlight-swarm-logistics`. Restart only after Marcus signs off.

Per Forge's deploy plan: artifacts written to
/AA_MY_DRIVE/_logs/hive_reports/swarm_logistics/<run_id>/ so the existing
report nginx can serve them.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/AA_MY_DRIVE")
LOGISTICS_DIR = WORKSPACE / "06_DEVELOPMENT/everlight_swarms/logistics"
INCOMING = LOGISTICS_DIR / "queue/incoming.jsonl"
OUTGOING = LOGISTICS_DIR / "queue/outgoing.jsonl"
PROCESSED_LOG = LOGISTICS_DIR / "queue/processed.jsonl"  # dedupe ledger
RUNS_DIR = WORKSPACE / "_logs/hive_reports/swarm_logistics"
LOG_PATH = WORKSPACE / "_logs/swarm_queue_poller.log"

SWARM_LIVE = os.environ.get("SWARM_LIVE", "0") == "1"

# Path to content_tools so we can import swarm_budget + branded_slack
sys.path.insert(0, str(WORKSPACE / "03_AUTOMATION_CORE/01_Scripts"))


def _log(msg: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {msg}"
    print(line)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _processed_trace_ids() -> set[str]:
    if not PROCESSED_LOG.exists():
        return set()
    out = set()
    with PROCESSED_LOG.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line)
                if "trace_id" in row:
                    out.add(row["trace_id"])
            except Exception:
                continue
    return out


def _record_processed(trace_id: str, status: str, halt_reason: str = "") -> None:
    PROCESSED_LOG.parent.mkdir(parents=True, exist_ok=True)
    with PROCESSED_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "trace_id": trace_id, "status": status,
            "halt_reason": halt_reason,
            "ts": datetime.now(timezone.utc).isoformat(),
        }) + "\n")


def _append_outgoing(row: dict) -> None:
    OUTGOING.parent.mkdir(parents=True, exist_ok=True)
    with OUTGOING.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")


def _stub_artifact(run_dir: Path, name: str, content: str) -> str:
    run_dir.mkdir(parents=True, exist_ok=True)
    p = run_dir / name
    p.write_text(content, encoding="utf-8")
    return str(p)


def process_rfp_mock(rfp: dict) -> dict:
    """Run the chain in MOCK mode -- no LLM calls, just stub artifacts.

    Validates the orchestration shape end-to-end without API spend.
    """
    trace_id = rfp.get("trace_id") or f"mock-{int(time.time())}"
    run_dir = RUNS_DIR / trace_id
    started = time.time()

    # Pre-flight budget gate
    try:
        from content_tools.swarm_budget import check_budget
        dec = check_budget(category="proposal",
                            est_input_tokens=20000,
                            est_output_tokens=5000)
        if not dec.allowed:
            _log(f"BUDGET BLOCKED: {dec.reason}")
            row = {
                "trace_id": trace_id, "status": "halted",
                "halt_reason": f"budget: {dec.reason}",
                "artifacts": {}, "elapsed_seconds": 0,
                "tokens_total": 0, "cost_usd_total": 0.0,
                "attribution_agent": rfp.get("attribution_agent", "Lucrex"),
            }
            return row
    except ImportError as e:
        _log(f"swarm_budget import failed (non-fatal in mock): {e}")

    # MOCK chain: produce stub artifacts in dispatch order
    intake = _stub_artifact(run_dir, "scope.json", json.dumps({
        "trace_id": trace_id,
        "client_legal_name": rfp.get("client", "Unknown"),
        "scope_description_normalized": rfp.get("scope", "(empty)"),
        "deliverables": ["[mock] deliverable 1", "[mock] deliverable 2"],
        "geo": {"region": rfp.get("region", "?"), "state": None},
        "term_months": rfp.get("term_months", 12),
        "service_categories": ["[mock] warehouse_intake"],
        "stated_pricing_tier_preference": rfp.get("pricing_tier"),
        "ambiguities": ["[mock] none specified"],
        "fail_close_reason": None,
        "agent": "intake_agent (MOCK)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2))

    research = _stub_artifact(run_dir, "research.json", json.dumps({
        "trace_id": trace_id, "scope_title": rfp.get("scope"),
        "comps": [
            {"source": "samgov", "source_url": "https://sam.gov/mock/award/1",
             "vendor_name": "MOCK Logistics A", "scope_match_pct": 80,
             "monthly_price_usd": 3500, "term_months": 12, "notes": "[mock]"},
            {"source": "competitor", "source_url": "https://example.com/mock",
             "vendor_name": "MOCK Vendor B", "scope_match_pct": 75,
             "monthly_price_usd": 4200, "term_months": 12, "notes": "[mock]"},
        ],
        "median_monthly_usd": 3850, "p25_monthly_usd": 3500,
        "p75_monthly_usd": 4200, "n_comps_above_75pct_match": 2,
        "comp_status": "verified", "fail_close_reason": None,
        "agent": "research_agent (MOCK)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2))

    pricing = _stub_artifact(run_dir, "pricing.json", json.dumps({
        "trace_id": trace_id, "client": rfp.get("client"),
        "tiers": {
            "bronze": {"price_monthly": 2500, "gross_margin_pct": 65, "scope": "[mock] basic"},
            "silver": {"price_monthly": 3800, "gross_margin_pct": 72, "scope": "[mock] mid"},
            "gold":   {"price_monthly": 5500, "gross_margin_pct": 78, "scope": "[mock] full"},
        },
        "cogs_table": [{"item": "tokens", "monthly_cost": 25.00},
                        {"item": "opportunity hours", "monthly_cost": 800.00}],
        "breakeven_units": 1, "walk_away_price": 2200,
        "comps": [{"source": "samgov", "price": 3500,
                    "url": "https://sam.gov/mock/award/1"}],
        "comp_status": "verified", "risk_premium_pct": 30,
        "rev_projection_24mo": [3800] * 24,
        "rev_projection_total": 91200,
        "walk_away": False, "fail_close_reason": None,
        "agent": "pricing_agent (MOCK)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2))

    msa_html = _stub_artifact(run_dir, "msa.html",
        f"<!DOCTYPE html><html><head><title>MSA -- {rfp.get('client')}</title></head>"
        f"<body><h1>MASTER SERVICES AGREEMENT (MOCK)</h1>"
        f"<p>Parties: Everlight Logistics LLC and {rfp.get('client')}.</p>"
        f"<p>This is a v0.1 mock. Real MSA generated only when SWARM_LIVE=1.</p>"
        f"<footer>Drafted by {rfp.get('attribution_agent','Forge')} via Logistics Swarm v0.1 -- Swarm-assisted, human-reviewed before send.</footer>"
        f"</body></html>")
    sow_html = _stub_artifact(run_dir, "sow.html",
        f"<!DOCTYPE html><html><body><h1>STATEMENT OF WORK (MOCK)</h1>"
        f"<p>Tier: {rfp.get('pricing_tier','silver')}.</p></body></html>")
    deck_html = _stub_artifact(run_dir, "deck.html",
        f"<!DOCTYPE html><html><body><h1>PITCH DECK (MOCK) -- {rfp.get('client')}</h1>"
        f"<p>Recommended tier: {rfp.get('pricing_tier','silver')}.</p></body></html>")

    elapsed = time.time() - started
    return {
        "trace_id": trace_id, "status": "done", "halt_reason": None,
        "artifacts": {
            "scope": intake, "research": research, "pricing": pricing,
            "msa": msa_html, "sow": sow_html, "deck": deck_html,
        },
        "attribution_agent": rfp.get("attribution_agent", "Lucrex"),
        "elapsed_seconds": round(elapsed, 2),
        "tokens_total": 0,    # mock = no real tokens
        "cost_usd_total": 0.0,
        "mode": "mock",
    }


def process_rfp_live(rfp: dict) -> dict:
    """v0.3: real LLM-produced artifacts via swarm_real_runner.

    Each agent's instructions.md becomes a real Haiku/Sonnet system prompt;
    swarm_budget gates every call. Verified cost ~$0.16 per full RFP.
    """
    sys.path.insert(0, str(LOGISTICS_DIR))
    try:
        from swarm_real_runner import run_orchestration
    except Exception as e:
        return {
            "trace_id": rfp.get("trace_id"), "status": "error",
            "halt_reason": f"swarm_real_runner import failed: {e}",
            "artifacts": {}, "elapsed_seconds": 0,
            "tokens_total": 0, "cost_usd_total": 0.0,
            "attribution_agent": rfp.get("attribution_agent", "Lucrex"),
        }
    summary = run_orchestration(rfp)

    # v0.4: post-hook branded comms (Slack card + GDoc publish)
    if summary["status"] == "done":
        _post_hooks(summary, rfp)

    return summary


def _post_hooks(summary: dict, rfp: dict) -> None:
    """Fire branded comms post-hooks when a real package completes.
    Best-effort -- failures here do NOT change the orchestration status."""
    sys.path.insert(0, str(WORKSPACE / "03_AUTOMATION_CORE/01_Scripts"))
    trace_id = summary.get("trace_id", "?")
    client = rfp.get("client", "?")

    # Slack card
    try:
        from content_tools.branded_slack import post_branded_slack
        msg = (f"Logistics package ready for review: *{client}*\n"
                f"Trace: `{trace_id}` | Tier: {rfp.get('pricing_tier','silver')} | "
                f"Cost: ${summary.get('cost_usd_total',0):.4f} | "
                f"Elapsed: {summary.get('elapsed_seconds',0)}s\n"
                f"Artifacts: {len(summary.get('artifacts',{}))} files in "
                f"`{Path(list(summary.get('artifacts',{}).values())[0]).parent if summary.get('artifacts') else '?'}`")
        post_branded_slack(
            channel="#ft-consult", title=f"Swarm package ready: {client}",
            summary=msg, category="report",
            agent_name=rfp.get("attribution_agent", "Penny Vance"),
            agent_title="Logistics Swarm v0.3",
        )
        _log(f"  branded_slack posted to #ft-consult")
    except Exception as e:
        _log(f"  branded_slack post failed (non-fatal): {e}")

    # GDoc publish for the deck (most client-facing artifact)
    try:
        from content_tools.n8n_replacements import publish_gdoc
        deck_path = summary.get("artifacts", {}).get("slides")
        if deck_path and Path(deck_path).exists():
            html = Path(deck_path).read_text(encoding="utf-8")
            r = publish_gdoc(
                title=f"Logistics Pitch Deck -- {client} -- {trace_id[:12]}",
                html_content=html,
                agent_name=rfp.get("attribution_agent", "Penny Vance"),
                agent_title="Logistics Swarm v0.3",
            )
            _log(f"  publish_gdoc result: ok={getattr(r, 'ok', '?')}")
    except Exception as e:
        _log(f"  publish_gdoc failed (non-fatal): {e}")


def run_once() -> dict:
    """One pass over the queue. Returns a summary."""
    if not INCOMING.exists():
        _log(f"no incoming.jsonl yet; nothing to do")
        return {"processed": 0, "halted": 0, "errors": 0}

    seen = _processed_trace_ids()
    processed = halted = errors = 0
    rfps_to_process = []
    with INCOMING.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rfp = json.loads(line)
            except Exception as e:
                _log(f"  parse error on incoming line: {e}")
                errors += 1
                continue
            tid = rfp.get("trace_id")
            if tid and tid in seen:
                continue
            rfps_to_process.append(rfp)

    _log(f"queue: {len(rfps_to_process)} new RFPs to process "
          f"(SWARM_LIVE={SWARM_LIVE}, mode={'live' if SWARM_LIVE else 'mock'})")

    for rfp in rfps_to_process:
        tid = rfp.get("trace_id", f"unknown-{int(time.time())}")
        _log(f"  processing {tid} ({rfp.get('client', '?')})")
        try:
            if SWARM_LIVE:
                result = process_rfp_live(rfp)
            else:
                result = process_rfp_mock(rfp)
            _append_outgoing(result)
            _record_processed(tid, result["status"], result.get("halt_reason") or "")
            if result["status"] == "done":
                processed += 1
            elif result["status"] == "halted":
                halted += 1
            else:
                errors += 1
            _log(f"    -> {result['status']} ({result.get('elapsed_seconds',0)}s)")
        except Exception as e:
            errors += 1
            _log(f"    ERROR: {e}")
            _record_processed(tid, "error", str(e)[:200])

    return {"processed": processed, "halted": halted, "errors": errors,
            "total_seen": len(rfps_to_process)}


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        result = run_once()
        print(json.dumps(result, indent=2))
        sys.exit(0)
    # default: poll forever every 5 min
    poll_seconds = int(os.environ.get("SWARM_POLL_SECONDS", "300"))
    _log(f"swarm_queue_poller starting (poll={poll_seconds}s, "
          f"live={SWARM_LIVE})")
    while True:
        try:
            run_once()
        except Exception as e:
            _log(f"loop error: {e}")
        time.sleep(poll_seconds)
