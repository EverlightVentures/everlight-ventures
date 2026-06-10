"""budget_gated_llm -- thin wrapper around Anthropic + OpenAI clients that
calls swarm_budget BEFORE every model call and record_call AFTER.

Why this exists: OpenSwarm/agency_swarm ship their own LLM clients. Until
we run the full swarm install, we still need a way to exercise the budget
gate end-to-end with real tokens. This module is THE one chokepoint:
  - import budget_gated_llm.call_anthropic(...) instead of anthropic.Client
  - import budget_gated_llm.call_openai(...) instead of openai.Client
  - the gate enforces $50/mo, $5/day soft, $10/day hard, all per Marcus

Once OpenSwarm is installed, monkey-patch agency_swarm's LLM client to
route through these wrappers (1-line patch in patches/patch_budget_gate.py).

Usage:
    from budget_gated_llm import call_anthropic
    response = call_anthropic(
        model="claude-haiku-4-5-20251001",
        system="You are a test agent.",
        user_prompt="Output one word: 'green'",
        max_tokens=20,
        category="proposal",
        agent="poc_test",
        trace_id="poc-001",
    )
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

WORKSPACE = Path("/AA_MY_DRIVE")
sys.path.insert(0, str(WORKSPACE / "03_AUTOMATION_CORE/01_Scripts"))


def _bootstrap_env() -> None:
    if (os.environ.get("LUCREX_ANTHROPIC_KEY") or
            os.environ.get("ANTHROPIC_API_KEY")):
        return
    p = WORKSPACE / ".env"
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip("'\""))


_bootstrap_env()


def call_anthropic(model: str, system: str, user_prompt: str,
                    max_tokens: int = 1024, category: str = "proposal",
                    agent: str = "unknown", trace_id: str = "",
                    deal_id: str = "") -> dict:
    """Budget-gated Anthropic call. Returns:
       {ok, text, input_tokens, output_tokens, cost_usd, blocked_reason}
    """
    from content_tools.swarm_budget import (check_budget, record_call,
                                              _est_cost_usd)

    # Estimate input tokens conservatively: chars / 3.5 is a decent proxy
    est_in = (len(system) + len(user_prompt)) // 3
    est_out = max_tokens

    dec = check_budget(category=category,
                        est_input_tokens=est_in,
                        est_output_tokens=est_out,
                        model=model)
    if not dec.allowed:
        return {"ok": False, "text": "", "input_tokens": 0,
                "output_tokens": 0, "cost_usd": 0.0,
                "blocked_reason": dec.reason}

    api_key = (os.environ.get("LUCREX_ANTHROPIC_KEY")
                or os.environ.get("ANTHROPIC_API_KEY"))
    if not api_key:
        return {"ok": False, "text": "", "input_tokens": 0,
                "output_tokens": 0, "cost_usd": 0.0,
                "blocked_reason": "no Anthropic key in env"}

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        t0 = time.time()
        r = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
        )
        latency = round(time.time() - t0, 2)
        text = r.content[0].text if r.content else ""
        in_tok = r.usage.input_tokens if hasattr(r, "usage") else 0
        out_tok = r.usage.output_tokens if hasattr(r, "usage") else 0
        cost = _est_cost_usd(model, in_tok, out_tok)
        record_call(category=category, agent=agent, model=model,
                     input_tokens=in_tok, output_tokens=out_tok,
                     cost_usd=cost, trace_id=trace_id, deal_id=deal_id)
        return {"ok": True, "text": text,
                "input_tokens": in_tok, "output_tokens": out_tok,
                "cost_usd": cost, "latency_s": latency,
                "blocked_reason": None}
    except Exception as e:
        return {"ok": False, "text": "", "input_tokens": 0,
                "output_tokens": 0, "cost_usd": 0.0,
                "blocked_reason": f"anthropic api error: {e}"}


def call_ollama(model: str, system: str, user_prompt: str,
                 max_tokens: int = 1024, category: str = "proposal",
                 agent: str = "unknown", trace_id: str = "",
                 deal_id: str = "",
                 host: str = "http://127.0.0.1:11434") -> dict:
    """Local-LLM fallback. FREE, no API spend, no budget gate needed
    (Ollama runs on local hardware -- the only "cost" is electricity +
    GPU time, both already-paid). Still records to ledger so we have
    full per-agent token traces.

    Models tested: mistral:latest, phi3:latest, qwen2.5-coder:7b,
    fast-chat:latest. Map any anthropic/openai model name to a local
    equivalent at the call site.
    """
    import urllib.request, urllib.parse, json as _j
    from content_tools.swarm_budget import record_call
    payload = {
        "model": model,
        "prompt": f"<<SYSTEM>>\n{system}\n<<END_SYSTEM>>\n\n{user_prompt}",
        "stream": False,
        "options": {"num_predict": max_tokens},
    }
    try:
        t0 = time.time()
        req = urllib.request.Request(
            f"{host}/api/generate",
            data=_j.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=600) as r:
            d = _j.loads(r.read())
        latency = round(time.time() - t0, 2)
        text = d.get("response", "").strip()
        in_tok = d.get("prompt_eval_count", 0)
        out_tok = d.get("eval_count", 0)
        # local = $0, but we still record for audit
        record_call(category=category, agent=agent,
                     model=f"ollama/{model}",
                     input_tokens=in_tok, output_tokens=out_tok,
                     cost_usd=0.0, trace_id=trace_id, deal_id=deal_id)
        return {"ok": True, "text": text, "input_tokens": in_tok,
                "output_tokens": out_tok, "cost_usd": 0.0,
                "latency_s": latency, "blocked_reason": None,
                "provider": "ollama"}
    except Exception as e:
        return {"ok": False, "text": "", "blocked_reason": f"ollama error: {e}",
                "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
                "provider": "ollama"}


def call_tgpt(model: str, system: str, user_prompt: str,
                max_tokens: int = 1024, category: str = "proposal",
                agent: str = "unknown", trace_id: str = "",
                deal_id: str = "") -> dict:
    """tgpt CLI fallback. FREE, no auth, no API key. Aggregates DuckDuckGo /
    Phind / Pollinations providers under the hood. Slower than paid APIs
    (~12-30s typical) but unlimited.

    Combines system+user into one prompt since tgpt is single-shot.
    Records to ledger with cost=0.
    """
    import subprocess
    from content_tools.swarm_budget import record_call
    combined = (f"INSTRUCTIONS:\n{system}\n\n=== END INSTRUCTIONS ===\n\n"
                 f"TASK:\n{user_prompt}")
    try:
        t0 = time.time()
        r = subprocess.run(
            ["tgpt", "-q", combined],
            capture_output=True, text=True, timeout=180,
        )
        latency = round(time.time() - t0, 2)
        if r.returncode != 0:
            return {"ok": False, "text": "",
                    "blocked_reason": f"tgpt rc={r.returncode}: {r.stderr[:200]}",
                    "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
                    "provider": "tgpt"}
        text = r.stdout.strip()
        # tgpt has no token counts; estimate from char counts
        in_tok = len(combined) // 3
        out_tok = len(text) // 3
        record_call(category=category, agent=agent, model=f"tgpt/{model}",
                     input_tokens=in_tok, output_tokens=out_tok,
                     cost_usd=0.0, trace_id=trace_id, deal_id=deal_id)
        return {"ok": True, "text": text, "input_tokens": in_tok,
                "output_tokens": out_tok, "cost_usd": 0.0,
                "latency_s": latency, "blocked_reason": None,
                "provider": "tgpt"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "text": "",
                "blocked_reason": "tgpt timeout (180s)",
                "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
                "provider": "tgpt"}
    except Exception as e:
        return {"ok": False, "text": "",
                "blocked_reason": f"tgpt error: {e}",
                "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
                "provider": "tgpt"}


def call_ollama_openai(model: str, system: str, user_prompt: str,
                        max_tokens: int = 1024, category: str = "proposal",
                        agent: str = "unknown", trace_id: str = "",
                        deal_id: str = "") -> dict:
    """Ollama via OpenAI-compatible endpoint at :11434/v1. Same client works
    as standard OpenAI SDK. Free, local, unlimited tokens. Faster than
    /api/generate path because it streams properly.

    Default model: phi3:latest (smallest + fastest). Override via
    SWARM_OLLAMA_MODEL env. Cost recorded as $0 in ledger.
    """
    from content_tools.swarm_budget import record_call
    try:
        from openai import OpenAI
    except ImportError:
        return {"ok": False, "text": "",
                "blocked_reason": "openai SDK not installed",
                "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
                "provider": "ollama-openai"}
    client = OpenAI(base_url="http://127.0.0.1:11434/v1", api_key="ollama")
    ollama_model = os.environ.get("SWARM_OLLAMA_MODEL", "phi3:latest")
    try:
        t0 = time.time()
        r = client.chat.completions.create(
            model=ollama_model, max_tokens=max_tokens,
            messages=[{"role": "system", "content": system},
                       {"role": "user", "content": user_prompt}],
            timeout=600,
        )
        latency = round(time.time() - t0, 2)
        text = r.choices[0].message.content if r.choices else ""
        in_tok = r.usage.prompt_tokens if r.usage else 0
        out_tok = r.usage.completion_tokens if r.usage else 0
        record_call(category=category, agent=agent,
                     model=f"ollama-openai/{ollama_model}",
                     input_tokens=in_tok, output_tokens=out_tok,
                     cost_usd=0.0, trace_id=trace_id, deal_id=deal_id)
        return {"ok": True, "text": text, "input_tokens": in_tok,
                "output_tokens": out_tok, "cost_usd": 0.0,
                "latency_s": latency, "blocked_reason": None,
                "provider": "ollama-openai"}
    except Exception as e:
        return {"ok": False, "text": "",
                "blocked_reason": f"ollama-openai error: {e}",
                "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
                "provider": "ollama-openai"}


def call_codex_cli(model: str, system: str, user_prompt: str,
                    max_tokens: int = 1024, category: str = "proposal",
                    agent: str = "unknown", trace_id: str = "",
                    deal_id: str = "") -> dict:
    """codex CLI exec mode. Subscription-backed (Rich's Codex sub), free
    at runtime. Slower than Ollama (~10-30s) but produces high-quality
    output (Codex uses GPT-5/Opus-class reasoning under the hood).
    """
    import subprocess
    from content_tools.swarm_budget import record_call
    combined = (f"=== INSTRUCTIONS ===\n{system}\n\n=== TASK ===\n{user_prompt}\n\n"
                f"Output ONLY the requested artifact. No preamble.")
    try:
        t0 = time.time()
        r = subprocess.run(
            ["codex", "exec", combined],
            capture_output=True, text=True, timeout=300,
        )
        latency = round(time.time() - t0, 2)
        if r.returncode != 0:
            return {"ok": False, "text": "",
                    "blocked_reason": f"codex rc={r.returncode}: {r.stderr[:200]}",
                    "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
                    "provider": "codex"}
        # codex output has scaffolding -- strip "session id" / "user" / "codex" / "tokens used" lines
        lines = r.stdout.split("\n")
        # find the "codex" header line and take everything after until "tokens used"
        text_lines = []
        in_response = False
        for line in lines:
            if line.strip() == "codex":
                in_response = True
                continue
            if line.startswith("tokens used"):
                in_response = False
                continue
            if in_response:
                text_lines.append(line)
        text = "\n".join(text_lines).strip()
        in_tok = len(combined) // 3
        out_tok = len(text) // 3
        record_call(category=category, agent=agent, model=f"codex/{model}",
                     input_tokens=in_tok, output_tokens=out_tok,
                     cost_usd=0.0, trace_id=trace_id, deal_id=deal_id)
        return {"ok": True, "text": text, "input_tokens": in_tok,
                "output_tokens": out_tok, "cost_usd": 0.0,
                "latency_s": latency, "blocked_reason": None,
                "provider": "codex"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "text": "",
                "blocked_reason": "codex timeout (300s)",
                "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
                "provider": "codex"}
    except Exception as e:
        return {"ok": False, "text": "",
                "blocked_reason": f"codex error: {e}",
                "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
                "provider": "codex"}


def call_llm(model: str, system: str, user_prompt: str, **kwargs) -> dict:
    """Provider-routed wrapper. SWARM_LLM_PROVIDER env picks the path.
    Solutions-first cascade (per CLAUDE.md): paid -> ollama-openai -> codex
    -> tgpt -> ollama-raw. Each layer falls back on credit/throttle/empty.
    """
    provider = os.environ.get("SWARM_LLM_PROVIDER", "anthropic").lower()
    if provider == "tgpt":
        return call_tgpt(model, system, user_prompt, **kwargs)
    if provider == "ollama":
        ollama_model = os.environ.get("SWARM_OLLAMA_MODEL", "phi3:latest")
        return call_ollama(ollama_model, system, user_prompt, **kwargs)
    if provider == "ollama-openai":
        return call_ollama_openai(model, system, user_prompt, **kwargs)
    if provider == "codex":
        return call_codex_cli(model, system, user_prompt, **kwargs)
    if provider == "openai":
        return call_openai(model, system, user_prompt, **kwargs)
    # default: anthropic with cascading fallback per solutions-first doctrine.
    # Order: anthropic -> ollama-openai (free, fast) -> codex (free, smart)
    # -> tgpt (free, weak)
    def _is_credit_or_auth_fail(reason: str) -> bool:
        r = (reason or "").lower()
        return any(k in r for k in ("credit", "balance", "401", "billing",
                                      "rate_limit", "no anthropic key"))

    r = call_anthropic(model, system, user_prompt, **kwargs)
    if r.get("ok"):
        return r
    if _is_credit_or_auth_fail(r.get("blocked_reason", "")):
        # Try ollama-openai (fastest free path)
        r2 = call_ollama_openai(model, system, user_prompt, **kwargs)
        if r2.get("ok") and r2.get("text", "").strip():
            return r2
        # Fall through to codex
        r3 = call_codex_cli(model, system, user_prompt, **kwargs)
        if r3.get("ok") and r3.get("text", "").strip():
            return r3
        # Last resort: tgpt
        return call_tgpt(model, system, user_prompt, **kwargs)
    return r


def call_openai(model: str, system: str, user_prompt: str,
                 max_tokens: int = 1024, category: str = "proposal",
                 agent: str = "unknown", trace_id: str = "",
                 deal_id: str = "") -> dict:
    from content_tools.swarm_budget import check_budget, record_call, _est_cost_usd
    est_in = (len(system) + len(user_prompt)) // 3
    dec = check_budget(category=category, est_input_tokens=est_in,
                        est_output_tokens=max_tokens, model=model)
    if not dec.allowed:
        return {"ok": False, "text": "", "blocked_reason": dec.reason,
                "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"ok": False, "text": "", "blocked_reason": "no OpenAI key",
                "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        t0 = time.time()
        r = client.chat.completions.create(
            model=model, max_tokens=max_tokens,
            messages=[{"role": "system", "content": system},
                       {"role": "user", "content": user_prompt}],
        )
        latency = round(time.time() - t0, 2)
        msg = r.choices[0].message.content if r.choices else ""
        in_tok = r.usage.prompt_tokens if r.usage else 0
        out_tok = r.usage.completion_tokens if r.usage else 0
        cost = _est_cost_usd(model, in_tok, out_tok)
        record_call(category=category, agent=agent, model=model,
                     input_tokens=in_tok, output_tokens=out_tok,
                     cost_usd=cost, trace_id=trace_id, deal_id=deal_id)
        return {"ok": True, "text": msg, "input_tokens": in_tok,
                "output_tokens": out_tok, "cost_usd": cost,
                "latency_s": latency, "blocked_reason": None}
    except Exception as e:
        return {"ok": False, "text": "",
                "blocked_reason": f"openai error: {e}",
                "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}


if __name__ == "__main__":
    # Smoke test: a single Haiku call ($0.001-ish) to validate gate + record
    print("=== budget_gated_llm smoke test ===")
    r = call_anthropic(
        model="claude-haiku-4-5-20251001",
        system="You are a test agent. Output one word only.",
        user_prompt="Output the single word 'green' if you can read this.",
        max_tokens=10,
        category="test",
        agent="poc_smoke",
        trace_id="poc-smoke-001",
    )
    import json
    print(json.dumps(r, indent=2, default=str))
    print()
    from content_tools.swarm_budget import budget_status
    print("=== budget after the call ===")
    print(json.dumps(budget_status(), indent=2))
