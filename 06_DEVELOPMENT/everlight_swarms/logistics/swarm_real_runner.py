"""swarm_real_runner -- v0.3: real LLM-produced artifacts under the budget
gate, without spinning up the full agency_swarm orchestrator.

Why this exists:
  - v0.1 produced mock-content stubs (status/shape, no real text)
  - v0.2 proved the budget gate works on a single LLM call
  - v0.3 (this) wires both together: each agent's instructions.md becomes a
    real Haiku/Sonnet system prompt, the orchestrator chains them in
    dispatch order, every call goes through swarm_budget, every artifact
    lands on disk as a real client-shaped deliverable.

The agency_swarm framework is installed and importable, but we're NOT using
its full Agency/Handoff machinery yet -- that's a v0.4 wire-up. For now
this runner does the same thing in 200 lines of Python, with full budget
visibility per call.

Cost per RFP at Haiku rates: ~$0.05-$0.15 (6 agents x ~2k tokens each).
Cost at Sonnet rates: ~$0.30-$0.80.

Trigger: invoked by swarm_queue_poller when SWARM_LIVE=1 in env.
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
RUNS_DIR = WORKSPACE / "_logs/hive_reports/swarm_logistics"

sys.path.insert(0, str(WORKSPACE / "03_AUTOMATION_CORE/01_Scripts"))
sys.path.insert(0, str(LOGISTICS_DIR / "patches"))

# Default model strategy: Haiku for simple agents, Sonnet for content-heavy
AGENT_MODELS = {
    "intake": "claude-haiku-4-5-20251001",
    "research": "claude-haiku-4-5-20251001",
    "pricing": "claude-haiku-4-5-20251001",  # Penny is precise but compact
    "docs": "claude-sonnet-4-5",  # MSA + SOW need legal precision
    "slides": "claude-sonnet-4-5",  # client-facing copy
    "onboarding": "claude-haiku-4-5-20251001",
}

# Max output tokens per agent. When SWARM_LLM_PROVIDER=tgpt, free providers
# truncate long generations -- caps below are tgpt-friendly. For Anthropic
# direct, larger caps work fine; the runtime auto-doubles when the provider
# is anthropic (see _max_tokens_for()).
AGENT_MAX_TOKENS = {
    "intake": 1200,
    "research": 1500,
    "pricing": 1500,
    "docs": 2500,
    "slides": 2500,
    "onboarding": 1500,
}


def _max_tokens_for(agent_name: str) -> int:
    base = AGENT_MAX_TOKENS.get(agent_name, 1500)
    if os.environ.get("SWARM_LLM_PROVIDER", "anthropic").lower() == "anthropic":
        return min(int(base * 1.6), 4000)  # paid providers, give headroom
    return base

# Dispatch order (per orchestrator's instructions.md)
DISPATCH_ORDER = ["intake", "research", "pricing", "docs", "slides", "onboarding"]


def _log(msg: str) -> None:
    log_path = WORKSPACE / "_logs/swarm_real_runner.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {msg}"
    print(line)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _read_instructions(agent_name: str) -> str:
    p = LOGISTICS_DIR / f"agents/{agent_name}/instructions.md"
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def _build_user_prompt(agent_name: str, rfp: dict, prior_outputs: dict) -> str:
    """Per agent, assemble a user prompt referring to the RFP + any
    prior agents' outputs they need."""
    base = (f"INPUT RFP:\n{json.dumps(rfp, indent=2)}\n\n"
             f"TRACE ID: {rfp.get('trace_id', 'unknown')}\n")
    if agent_name == "intake":
        return base + "Produce the scope.json as specified in your instructions."
    if agent_name == "research":
        scope = prior_outputs.get("intake", {})
        return (base + f"\nSCOPE FROM INTAKE:\n{json.dumps(scope, indent=2)}\n\n"
                 "Produce the research.json as specified.")
    if agent_name == "pricing":
        scope = prior_outputs.get("intake", {})
        research = prior_outputs.get("research", {})
        return (base
                 + f"\nSCOPE:\n{json.dumps(scope, indent=2)}\n\n"
                 + f"RESEARCH (comps):\n{json.dumps(research, indent=2)}\n\n"
                 + "Produce the pricing.json with tier table + walk-away check.")
    if agent_name == "docs":
        scope = prior_outputs.get("intake", {})
        pricing = prior_outputs.get("pricing", {})
        return (base
                 + f"\nSCOPE:\n{json.dumps(scope, indent=2)}\n\n"
                 + f"PRICING:\n{json.dumps(pricing, indent=2)}\n\n"
                 + "Produce two HTML strings, separated by '<!-- SOW SPLIT -->': "
                 + "MSA first, then SOW. Brand-locked, no deadline language.")
    if agent_name == "slides":
        scope = prior_outputs.get("intake", {})
        pricing = prior_outputs.get("pricing", {})
        research = prior_outputs.get("research", {})
        return (base
                 + f"\nSCOPE:\n{json.dumps(scope, indent=2)}\n\n"
                 + f"PRICING:\n{json.dumps(pricing, indent=2)}\n\n"
                 + f"RESEARCH:\n{json.dumps(research, indent=2)}\n\n"
                 + "Produce a single self-contained HTML deck (8-10 slides). "
                 + "Gold-on-dark, Playfair + Inter. Output only the HTML.")
    if agent_name == "onboarding":
        scope = prior_outputs.get("intake", {})
        pricing = prior_outputs.get("pricing", {})
        return (base
                 + f"\nSCOPE:\n{json.dumps(scope, indent=2)}\n\n"
                 + f"PRICING:\n{json.dumps(pricing, indent=2)}\n\n"
                 + "Produce a JSON onboarding package per your spec.")
    return base + f"Produce the artifact for agent {agent_name}."


def _try_parse_json(text: str) -> dict | None:
    """Best-effort JSON parse; many agents' outputs may be JSON-with-prose."""
    text = text.strip()
    if not text:
        return None
    # find first {  and matching last }
    s = text.find("{")
    e = text.rfind("}")
    if s < 0 or e <= s:
        return None
    try:
        return json.loads(text[s:e + 1])
    except Exception:
        return None


def run_agent(agent_name: str, rfp: dict, prior_outputs: dict,
                 attribution: str, trace_id: str) -> dict:
    """Run one agent, return {ok, text, parsed?, cost_usd, tokens, ...}"""
    from budget_gated_llm import call_llm
    instructions = _read_instructions(agent_name)
    if not instructions:
        return {"ok": False, "error": f"no instructions.md for {agent_name}"}

    model = AGENT_MODELS.get(agent_name, "claude-haiku-4-5-20251001")
    max_tok = _max_tokens_for(agent_name)

    # Inject runtime context into the system prompt
    system = (instructions
              + f"\n\n--- RUNTIME CONTEXT ---\n"
              + f"trace_id: {trace_id}\n"
              + f"attribution_agent: {attribution}\n"
              + f"workspace: AceMagician (Tennessee operator)\n"
              + f"branding: gold #D4A843, Playfair Display + Inter\n"
              + f"output style: produce ONLY the artifact specified -- "
                f"no preamble, no commentary, no markdown code fences "
                f"unless the artifact is HTML/JSON/CODE.")

    user_prompt = _build_user_prompt(agent_name, rfp, prior_outputs)

    provider = os.environ.get("SWARM_LLM_PROVIDER", "anthropic")
    _log(f"  [{agent_name}] calling {model} via {provider} (max {max_tok} tok)...")
    r = call_llm(
        model=model,
        system=system,
        user_prompt=user_prompt,
        max_tokens=max_tok,
        category="proposal",
        agent=f"{agent_name}_agent",
        trace_id=trace_id,
    )

    if not r.get("ok"):
        _log(f"  [{agent_name}] FAIL: {r.get('blocked_reason')}")
        return {"ok": False, "error": r.get("blocked_reason"),
                 "agent": agent_name}

    # Empty/truncated response retry: tgpt and other free providers
    # occasionally return 0-output. One retry with shorter prompt catches it.
    if not r.get("text", "").strip() and provider in ("tgpt", "ollama"):
        _log(f"  [{agent_name}] empty response -- retrying once")
        r = call_llm(model=model, system=system,
                      user_prompt=user_prompt + "\n\nProduce the artifact NOW. "
                      "Do not stop early. Output the full content.",
                      max_tokens=max_tok,
                      category="proposal", agent=f"{agent_name}_agent_retry",
                      trace_id=trace_id)
        if not r.get("ok"):
            return {"ok": False, "error": r.get("blocked_reason"),
                     "agent": agent_name}

    parsed = _try_parse_json(r["text"])
    _log(f"  [{agent_name}] OK -- {r['input_tokens']}->{r['output_tokens']} tok, "
          f"${r['cost_usd']:.4f}, {r['latency_s']}s, parsed_json={bool(parsed)}")
    return {
        "ok": True,
        "agent": agent_name,
        "model": model,
        "text": r["text"],
        "parsed": parsed,
        "input_tokens": r["input_tokens"],
        "output_tokens": r["output_tokens"],
        "cost_usd": r["cost_usd"],
        "latency_s": r["latency_s"],
    }


def run_orchestration(rfp: dict) -> dict:
    """Drive the full agent chain on one RFP. Returns the orchestrator's
    summary record (matches the schema used by swarm_queue_poller)."""
    trace_id = rfp.get("trace_id") or f"real-{int(time.time())}"
    attribution = rfp.get("attribution_agent", "Lucrex")
    run_dir = RUNS_DIR / trace_id
    run_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    _log(f"=== real orchestration: trace={trace_id} client={rfp.get('client')} ===")

    prior = {}
    artifacts = {}
    total_in = total_out = 0
    total_cost = 0.0
    halt_reason = None

    for agent_name in DISPATCH_ORDER:
        result = run_agent(agent_name, rfp, prior, attribution, trace_id)
        if not result["ok"]:
            halt_reason = f"{agent_name}: {result.get('error')}"
            _log(f"  HALT at {agent_name}: {halt_reason}")
            break

        # write artifact -- JSON if parseable, else raw text
        ext = "json" if result.get("parsed") else (
            "html" if agent_name in ("docs", "slides") else "txt")
        if agent_name == "docs":
            # split MSA + SOW on the marker
            text = result["text"]
            split = "<!-- SOW SPLIT -->"
            if split in text:
                msa, sow = text.split(split, 1)
                msa_path = run_dir / "msa.html"
                sow_path = run_dir / "sow.html"
                msa_path.write_text(msa.strip(), encoding="utf-8")
                sow_path.write_text(sow.strip(), encoding="utf-8")
                artifacts["msa"] = str(msa_path)
                artifacts["sow"] = str(sow_path)
            else:
                # fallback: write whole as msa, no sow
                msa_path = run_dir / "msa.html"
                msa_path.write_text(text, encoding="utf-8")
                artifacts["msa"] = str(msa_path)
        else:
            path = run_dir / f"{agent_name}.{ext}"
            content = (json.dumps(result["parsed"], indent=2)
                        if result.get("parsed") else result["text"])
            path.write_text(content, encoding="utf-8")
            artifacts[agent_name] = str(path)

        prior[agent_name] = result.get("parsed") or {"raw": result["text"][:1500]}
        total_in += result["input_tokens"]
        total_out += result["output_tokens"]
        total_cost += result["cost_usd"]

        # Halt-gate: if pricing returned walk_away=true, stop the chain
        if (agent_name == "pricing" and result.get("parsed")
                and result["parsed"].get("walk_away")):
            halt_reason = (f"pricing.walk_away=true: "
                           f"{result['parsed'].get('fail_close_reason') or 'unknown'}")
            _log(f"  WALK-AWAY at pricing: {halt_reason}")
            break

    elapsed = round(time.time() - started, 2)
    status = "halted" if halt_reason else "done"

    summary = {
        "trace_id": trace_id, "status": status,
        "halt_reason": halt_reason,
        "artifacts": artifacts,
        "attribution_agent": attribution,
        "elapsed_seconds": elapsed,
        "tokens_total": total_in + total_out,
        "tokens_input": total_in, "tokens_output": total_out,
        "cost_usd_total": round(total_cost, 6),
        "mode": "real_v03",
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2),
                                             encoding="utf-8")
    _log(f"=== orchestration complete: status={status} cost=${total_cost:.4f} "
          f"elapsed={elapsed}s ===")
    return summary


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # smoke test with a real Haiku-cost RFP
        test_rfp = {
            "client": "Mid-South Logistics Co (TEST)",
            "scope": "warehouse intake automation for a 50k sqft Memphis facility, "
                     "with SLA-backed reporting and integration to existing WMS",
            "region": "Memphis TN",
            "term_months": 12,
            "pricing_tier": "silver",
            "deadline": None,
            "attribution_agent": "Penny Vance",
            "trace_id": f"poc-real-{int(time.time())}",
        }
        result = run_orchestration(test_rfp)
        print()
        print(json.dumps({k: v for k, v in result.items() if k != "artifacts"},
                          indent=2))
        print(f"\nartifacts:")
        for k, v in result["artifacts"].items():
            print(f"  {k}: {v}")
    else:
        # read one RFP from stdin and run
        rfp = json.loads(sys.stdin.read())
        print(json.dumps(run_orchestration(rfp), indent=2, default=str))
