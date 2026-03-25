"""Agent Debate Engine (MiroFish-style).

Before the bot takes a trade, multiple agents analyze the candidate
and produce their take. They can agree, disagree, or add nuance.
Marcus Cole breaks ties and makes the final call.

This module produces structured debate output that feeds:
1. Slack threads (agents post sequentially in a thread)
2. Dashboard feed (rendered as a conversation)
3. Decision log (stored for review)

Each agent has a specialty and a decision-making framework:
- Rex Thornton (Markets): directional bias, technicals, wick zones
- Penny Vance (Finance): risk/reward, sizing, equity impact
- Cipher Nakamura (Intel): on-chain signals, funding, OI, sentiment
- Marcus Cole (Command): tie-breaker, final go/no-go
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class AgentTake:
    """One agent's analysis of a candidate trade."""
    agent: str
    role: str
    verdict: str       # "go", "no_go", "cautious", "wait"
    confidence: float  # 0.0 - 1.0
    reasoning: str     # natural language analysis
    key_signals: list[str] = field(default_factory=list)


@dataclass
class DebateResult:
    """The full debate output."""
    timestamp: str
    agents: list[AgentTake]
    consensus: str     # "go", "no_go", "split"
    final_call: str    # Marcus's decision
    final_reasoning: str
    go_count: int
    no_go_count: int
    direction: str
    entry_type: str
    score: int
    threshold: int


def run_debate(decision: dict) -> DebateResult | None:
    """Run the agent debate on a candidate trade decision.

    Args:
        decision: the bot's decision payload (from log_payload or decisions.jsonl)

    Returns:
        DebateResult with all agent takes and final call, or None if no signal.
    """
    price = decision.get("price")
    direction = decision.get("direction")
    entry = decision.get("entry_signal") or decision.get("selected_entry_type") or ""
    score = int(decision.get("v4_selected_score") or 0)
    threshold = int(decision.get("v4_selected_threshold") or 75)
    htf = decision.get("htf_trend", "neutral")
    regime = decision.get("v4_regime") or decision.get("regime") or "neutral"
    vol = decision.get("vol_phase", "?")
    align = int(decision.get("alignment_bonus") or 0)
    wz_count = int(decision.get("wick_zones_count") or 0)
    wz_top3 = decision.get("wick_zones_top3") or []
    patterns = decision.get("patterns_active") or []
    ms = decision.get("micro_sweep_promoted")
    funding = str(decision.get("contract_funding_bias") or "")
    oi = str(decision.get("contract_oi_trend") or "")
    overnight = decision.get("overnight_trading_ok")
    pnl = decision.get("pnl_today_usd")
    equity = decision.get("equity_start") or decision.get("total_funds")
    losses = int(decision.get("consecutive_losses") or 0)
    margin_window = decision.get("margin_window", "")
    bb_4h = decision.get("bb_expanding_4h")
    rvol_4h = decision.get("rvol_4h")
    wz_near = decision.get("wick_zone_near")
    wz_bias = decision.get("wick_zone_bias", "")
    pattern_mod = int(decision.get("pattern_mod") or 0)

    # --- Rex Thornton: Markets ---
    rex_signals = []
    rex_verdict = "wait"
    rex_conf = 0.5

    if htf == "bullish" and (direction == "long" or not direction):
        rex_signals.append("daily trend UP")
        rex_conf += 0.1
    elif htf == "bearish" and (direction == "short" or not direction):
        rex_signals.append("daily trend DOWN")
        rex_conf += 0.1
    elif htf and direction and htf != "neutral":
        if (htf == "bullish" and direction == "short") or (htf == "bearish" and direction == "long"):
            rex_signals.append(f"AGAINST daily trend ({htf})")
            rex_conf -= 0.15

    if align >= 6:
        rex_signals.append(f"TF alignment strong ({align:+d})")
        rex_conf += 0.15
    elif align <= -3:
        rex_signals.append(f"TF alignment weak ({align:+d})")
        rex_conf -= 0.1

    if wz_near and "support" in str(wz_bias) and direction == "long":
        rex_signals.append("price on tested support")
        rex_conf += 0.1
    elif wz_near and "resist" in str(wz_bias) and direction == "short":
        rex_signals.append("price at tested resistance")
        rex_conf += 0.1

    if patterns:
        for p in patterns[:2]:
            pname = str(p.get("pattern", "")).replace("_", " ")
            pbias = p.get("bias", "")
            rex_signals.append(f"{pname} pattern ({pbias})")
            if pbias == direction:
                rex_conf += 0.05

    if ms:
        rex_signals.append("micro-sweep fired")
        rex_conf += 0.1

    if bb_4h:
        rex_signals.append("4h BB expanding")
        rex_conf += 0.05

    if entry and direction and score >= threshold * 0.8:
        rex_verdict = "go" if score >= threshold else "cautious"
    elif not entry:
        rex_verdict = "wait"

    rex_conf = max(0.1, min(1.0, rex_conf))

    if rex_verdict == "go":
        rex_text = f"I like this {direction} setup. {entry.replace('_', ' ').upper()} at ${price:.5f}. " if price else f"I like this {direction}. "
        rex_text += f"Score {score}/{threshold}. "
        if rex_signals:
            rex_text += " | ".join(rex_signals[:4]) + ". "
        rex_text += "Take the trade."
    elif rex_verdict == "cautious":
        rex_text = f"Setup is forming but not there yet. Score {score}/{threshold}, need {threshold - score} more points. "
        if rex_signals:
            rex_text += " | ".join(rex_signals[:3]) + ". "
        rex_text += "I would wait for full confirmation."
    else:
        rex_text = "Nothing clean right now. "
        if regime == "mean_reversion":
            rex_text += f"Range regime, vol {vol}. Waiting for price to reach an edge."
        elif regime == "trend":
            rex_text += f"Trending but no pullback entry. Vol {vol}."
        else:
            rex_text += f"Regime: {regime}, vol: {vol}. Patience."
        if rex_signals:
            rex_text += " Context: " + " | ".join(rex_signals[:3])

    rex = AgentTake(
        agent="Rex Thornton", role="Head of Markets",
        verdict=rex_verdict, confidence=rex_conf,
        reasoning=rex_text, key_signals=rex_signals,
    )

    # --- Penny Vance: Finance ---
    penny_signals = []
    penny_verdict = "cautious"
    penny_conf = 0.5

    if equity:
        eq = float(equity)
        if eq < 450:
            penny_signals.append(f"equity low (${eq:.0f})")
            penny_verdict = "no_go"
            penny_conf = 0.7
        elif eq < 500:
            penny_signals.append(f"equity tight (${eq:.0f})")
            penny_verdict = "cautious"
        else:
            penny_signals.append(f"equity OK (${eq:.0f})")

    if losses >= 2:
        penny_signals.append(f"{losses} consecutive losses")
        penny_verdict = "no_go"
        penny_conf = 0.8
    elif losses == 1:
        penny_signals.append("1 recent loss")
        penny_verdict = "cautious"

    if pnl is not None:
        pnl_f = float(pnl)
        if pnl_f < -5:
            penny_signals.append(f"down ${abs(pnl_f):.2f} today")
            penny_conf += 0.1
        elif pnl_f > 5:
            penny_signals.append(f"up ${pnl_f:.2f} today")
            penny_conf -= 0.05

    if overnight is False and margin_window == "overnight":
        penny_signals.append("overnight margin tight")
        penny_verdict = "no_go"
        penny_conf = 0.8

    if score >= threshold and rex_verdict == "go" and losses < 2:
        penny_verdict = "go"
        penny_conf = max(penny_conf, 0.6)

    penny_conf = max(0.1, min(1.0, penny_conf))

    if penny_verdict == "go":
        penny_text = f"Numbers check out. "
        if penny_signals:
            penny_text += " | ".join(penny_signals) + ". "
        penny_text += "1 contract, standard risk. Green light from finance."
    elif penny_verdict == "no_go":
        penny_text = "I am blocking this. "
        if penny_signals:
            penny_text += " | ".join(penny_signals) + ". "
        penny_text += "Risk too high right now. Protect the capital."
    else:
        penny_text = "Proceed with caution. "
        if penny_signals:
            penny_text += " | ".join(penny_signals) + ". "
        penny_text += "1 contract max, tight stop."

    penny = AgentTake(
        agent="Penny Vance", role="CFO",
        verdict=penny_verdict, confidence=penny_conf,
        reasoning=penny_text, key_signals=penny_signals,
    )

    # --- Cipher Nakamura: Intel ---
    cipher_signals = []
    cipher_verdict = "wait"
    cipher_conf = 0.5

    if "RISING" in oi:
        cipher_signals.append("OI rising (new money entering)")
        cipher_conf += 0.1
        if direction == "long":
            cipher_verdict = "go"
    elif "FALLING" in oi:
        cipher_signals.append("OI falling (positions closing)")
        cipher_conf -= 0.05

    if "SHORT" in funding.upper():
        cipher_signals.append("shorts paying funding (crowded short)")
        if direction == "long":
            cipher_conf += 0.1
    elif "LONG" in funding.upper():
        cipher_signals.append("longs paying funding (crowded long)")
        if direction == "short":
            cipher_conf += 0.1

    if wz_count and wz_count >= 8:
        cipher_signals.append(f"{wz_count} wick zones across all TFs")
        cipher_conf += 0.05

    if pattern_mod > 3:
        cipher_signals.append(f"pattern confluence +{pattern_mod}")
        cipher_conf += 0.05
    elif pattern_mod < -3:
        cipher_signals.append(f"pattern headwind {pattern_mod}")
        cipher_conf -= 0.05

    if score >= threshold and cipher_conf >= 0.5:
        cipher_verdict = "go"
    elif cipher_conf < 0.4:
        cipher_verdict = "no_go"

    cipher_conf = max(0.1, min(1.0, cipher_conf))

    if cipher_verdict == "go":
        cipher_text = "On-chain and market microstructure support this. "
        if cipher_signals:
            cipher_text += " | ".join(cipher_signals) + ". "
        cipher_text += "The data backs the trade."
    elif cipher_verdict == "no_go":
        cipher_text = "Data does not support entry. "
        if cipher_signals:
            cipher_text += " | ".join(cipher_signals) + ". "
        cipher_text += "Stay flat until signals improve."
    else:
        cipher_text = "Mixed signals from the data layer. "
        if cipher_signals:
            cipher_text += " | ".join(cipher_signals) + ". "
        cipher_text += "Not enough edge to commit."

    cipher = AgentTake(
        agent="Cipher Nakamura", role="Head of Intelligence",
        verdict=cipher_verdict, confidence=cipher_conf,
        reasoning=cipher_text, key_signals=cipher_signals,
    )

    # --- Marcus Cole: Final Call ---
    agents = [rex, penny, cipher]
    go_count = sum(1 for a in agents if a.verdict == "go")
    no_go_count = sum(1 for a in agents if a.verdict == "no_go")

    if go_count >= 2 and no_go_count == 0:
        consensus = "go"
    elif no_go_count >= 2:
        consensus = "no_go"
    else:
        consensus = "split"

    if consensus == "go":
        marcus_verdict = "go"
        marcus_text = f"{go_count} out of 3 say go. Consensus is clear. "
        if entry and direction:
            marcus_text += f"Execute: {entry.replace('_', ' ').upper()} {direction.upper()}. 1 contract."
        else:
            marcus_text += "Standing by for entry signal."
    elif consensus == "no_go":
        marcus_verdict = "no_go"
        marcus_text = f"{no_go_count} out of 3 blocking. We stand down. "
        blocked_reasons = []
        for a in agents:
            if a.verdict == "no_go":
                blocked_reasons.append(f"{a.agent.split()[0]}: {a.key_signals[0] if a.key_signals else 'risk'}")
        if blocked_reasons:
            marcus_text += "Reasons: " + "; ".join(blocked_reasons) + "."
    else:
        marcus_verdict = "wait"
        marcus_text = "Split decision. "
        for a in agents:
            marcus_text += f"{a.agent.split()[0]} says {a.verdict}. "
        if score >= threshold:
            marcus_text += "Score passes but team is not aligned. Reduce size or wait for better setup."
        else:
            marcus_text += "Hold position. Wait for alignment."

    marcus = AgentTake(
        agent="Marcus Cole", role="Chief of Staff",
        verdict=marcus_verdict, confidence=0.9 if consensus != "split" else 0.5,
        reasoning=marcus_text, key_signals=[f"consensus: {consensus}", f"{go_count} go / {no_go_count} no_go"],
    )
    agents.append(marcus)

    return DebateResult(
        timestamp=datetime.now(timezone.utc).isoformat(),
        agents=agents,
        consensus=consensus,
        final_call=marcus_verdict,
        final_reasoning=marcus_text,
        go_count=go_count,
        no_go_count=no_go_count,
        direction=direction or "",
        entry_type=entry,
        score=score,
        threshold=threshold,
    )


def debate_to_slack_blocks(result: DebateResult) -> list[str]:
    """Convert debate result to a list of Slack messages (one per agent).

    First message is the thread parent, rest are replies.
    """
    if not result:
        return []

    messages = []
    # Parent: Marcus's final call
    marcus = result.agents[-1] if result.agents else None
    if marcus:
        icon = "GREEN" if result.final_call == "go" else "RED" if result.final_call == "no_go" else "YELLOW"
        parent = f"*TRADE DEBATE* | {icon} | {result.direction.upper() or 'SCAN'} | Score {result.score}/{result.threshold}\n\n"
        parent += f"*{marcus.agent}* ({marcus.role}): {marcus.reasoning}"
        messages.append(parent)

    # Replies: each agent's take
    for agent in result.agents[:-1]:
        verdict_icon = "GO" if agent.verdict == "go" else "NO" if agent.verdict == "no_go" else "WAIT"
        msg = f"*{agent.agent}* ({agent.role}) | {verdict_icon} | {agent.confidence:.0%}\n{agent.reasoning}"
        messages.append(msg)

    return messages


def debate_to_dashboard(result: DebateResult) -> list[dict]:
    """Convert debate result to a list of dicts for the dashboard feed."""
    if not result:
        return []

    feed = []
    for agent in result.agents:
        feed.append({
            "agent": agent.agent,
            "role": agent.role,
            "verdict": agent.verdict,
            "confidence": agent.confidence,
            "text": agent.reasoning,
            "signals": agent.key_signals,
        })
    feed.append({
        "agent": "CONSENSUS",
        "role": "Final",
        "verdict": result.final_call,
        "confidence": 1.0,
        "text": result.final_reasoning,
        "signals": [f"{result.go_count} go / {result.no_go_count} no_go"],
    })
    return feed
