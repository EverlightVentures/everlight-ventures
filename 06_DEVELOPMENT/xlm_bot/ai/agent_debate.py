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


# ---------------------------------------------------------------------------
# WHOLESALE TEAM: Chart Dawson, Filter Banks, Hammer Knox, Marcus Cole
# ---------------------------------------------------------------------------

def run_wholesale_debate(data: dict) -> DebateResult | None:
    """Wholesale pipeline debate. Data comes from rex_pipeline Supabase table.

    Expected keys: leads (list), total_leads, tier1_count, tier2_count,
    tier3_count, total_fees, contacted_count, buyer_count, top_lead (dict)
    """
    leads = data.get("leads") or []
    total = int(data.get("total_leads") or len(leads))
    t1 = int(data.get("tier1_count") or 0)
    t2 = int(data.get("tier2_count") or 0)
    t3 = int(data.get("tier3_count") or 0)
    fees = float(data.get("total_fees") or 0)
    contacted = int(data.get("contacted_count") or 0)
    buyers = int(data.get("buyer_count") or 0)
    top = data.get("top_lead") or {}

    # --- Chart Dawson: Analytics ---
    chart_signals = []
    chart_verdict = "wait"
    chart_conf = 0.5

    if total >= 10:
        chart_signals.append(f"{total} active leads in pipeline")
        chart_conf += 0.1
    elif total >= 5:
        chart_signals.append(f"{total} leads - pipeline is thin")
    else:
        chart_signals.append(f"Only {total} leads - need to source more")
        chart_conf -= 0.1

    if t1 >= 3:
        chart_signals.append(f"{t1} Tier 1 ready to close THIS WEEK")
        chart_conf += 0.15
        chart_verdict = "go"
    elif t1 >= 1:
        chart_signals.append(f"{t1} Tier 1 in play")
        chart_conf += 0.05

    if fees > 20000:
        chart_signals.append(f"${fees:,.0f} total potential fees")
        chart_conf += 0.1
    elif fees > 5000:
        chart_signals.append(f"${fees:,.0f} in potential fees")

    contact_rate = (contacted / total * 100) if total > 0 else 0
    if contact_rate < 50:
        chart_signals.append(f"Only {contact_rate:.0f}% contacted - outreach gap")

    if chart_verdict != "go":
        chart_verdict = "go" if t1 >= 2 else "cautious" if total >= 5 else "wait"
    chart_conf = max(0.1, min(1.0, chart_conf))

    chart_text = f"Pipeline: {total} leads, {t1} Tier 1, {t2} Tier 2, {t3} Long Game. "
    chart_text += f"Potential fees: ${fees:,.0f}. Contact rate: {contact_rate:.0f}%. "
    if t1 >= 2:
        chart_text += "Multiple Tier 1 deals ready. Time to close."
    elif total < 5:
        chart_text += "Pipeline is dry. Need fresh leads before anything else."
    else:
        chart_text += "Decent pipeline but nothing screaming close right now."

    chart = AgentTake(
        agent="Chart Dawson", role="Pipeline Analytics",
        verdict=chart_verdict, confidence=chart_conf,
        reasoning=chart_text, key_signals=chart_signals,
    )

    # --- Filter Banks: Lead Quality ---
    filter_signals = []
    filter_verdict = "cautious"
    filter_conf = 0.5

    if t1 > 0 and top:
        arv = float(top.get("arv") or 0)
        fee = float(top.get("assignment_fee") or 0)
        has_email = bool(top.get("owner_email"))
        filter_signals.append(f"Top lead: {top.get('address', '?')} ARV ${arv:,.0f} fee ${fee:,.0f}")
        if has_email:
            filter_signals.append("Has email contact")
            filter_conf += 0.1
        if fee >= 5000:
            filter_signals.append(f"${fee:,.0f} fee - strong margin")
            filter_conf += 0.15
            filter_verdict = "go"
        elif fee >= 2000:
            filter_signals.append(f"${fee:,.0f} fee - decent")
            filter_conf += 0.05

    if buyers >= 3:
        filter_signals.append(f"{buyers} active buyers in the network")
        filter_conf += 0.1
    elif buyers == 0:
        filter_signals.append("No buyers loaded - need investor outreach")
        filter_verdict = "no_go"
        filter_conf = 0.7

    filter_conf = max(0.1, min(1.0, filter_conf))
    if filter_verdict == "go":
        filter_text = "Lead quality checks out. " + " | ".join(filter_signals) + ". Green light to pursue."
    elif filter_verdict == "no_go":
        filter_text = "Blocking. " + " | ".join(filter_signals) + ". Fix this before chasing deals."
    else:
        filter_text = "Leads are OK but not exceptional. " + " | ".join(filter_signals) + ". Proceed with due diligence."

    filt = AgentTake(
        agent="Filter Banks", role="Lead Qualification",
        verdict=filter_verdict, confidence=filter_conf,
        reasoning=filter_text, key_signals=filter_signals,
    )

    # --- Hammer Knox: Closing ---
    hammer_signals = []
    hammer_verdict = "wait"
    hammer_conf = 0.5

    if t1 >= 1:
        hammer_signals.append(f"{t1} deals ready to close this week")
        hammer_verdict = "go"
        hammer_conf = 0.7
    if contacted > 0 and total > 0:
        hammer_signals.append(f"{contacted}/{total} contacted")
    if fees > 10000:
        hammer_signals.append(f"${fees:,.0f} on the table if we execute")
        hammer_conf += 0.1

    if top and float(top.get("assignment_fee") or 0) >= 5000:
        name = top.get("owner_name") or top.get("address") or "top lead"
        hammer_signals.append(f"Priority: {name} at ${float(top.get('assignment_fee') or 0):,.0f}")
        hammer_conf += 0.1

    hammer_conf = max(0.1, min(1.0, hammer_conf))
    if hammer_verdict == "go":
        hammer_text = "Let me at them. " + " | ".join(hammer_signals) + ". I can close this."
    else:
        hammer_text = "Nothing ready to close right now. " + " | ".join(hammer_signals) + ". Keep working the pipeline."

    hammer = AgentTake(
        agent="Hammer Knox", role="Closer",
        verdict=hammer_verdict, confidence=hammer_conf,
        reasoning=hammer_text, key_signals=hammer_signals,
    )

    # --- Marcus: Final Call ---
    agents = [chart, filt, hammer]
    return _marcus_decides(agents, data.get("context", "wholesale pipeline"), "", "", 0, 0)


# ---------------------------------------------------------------------------
# BROKER TEAM: Cupid Osei, Piper Reeves, Cash Montgomery, Marcus Cole
# ---------------------------------------------------------------------------

def run_broker_debate(data: dict) -> DebateResult | None:
    """Broker OS debate. Data from broker_ops Django models or Supabase."""
    active_deals = int(data.get("active_deals") or 0)
    pending_matches = int(data.get("pending_matches") or 0)
    total_commission = float(data.get("total_commission") or 0)
    offers = int(data.get("active_offers") or 0)
    leads = int(data.get("active_leads") or 0)
    recent_close = data.get("recent_close")
    top_deal = data.get("top_deal") or {}

    # --- Cupid Osei: Matching ---
    cupid_signals = []
    cupid_verdict = "wait"
    cupid_conf = 0.5

    if pending_matches >= 3:
        cupid_signals.append(f"{pending_matches} matches waiting for approval")
        cupid_verdict = "go"
        cupid_conf = 0.7
    elif pending_matches >= 1:
        cupid_signals.append(f"{pending_matches} match pending")
        cupid_verdict = "cautious"

    if offers >= 5 and leads >= 5:
        cupid_signals.append(f"{offers} offers x {leads} leads = strong matching pool")
        cupid_conf += 0.1
    elif offers == 0 or leads == 0:
        cupid_signals.append("Need both offers AND leads to match. Missing one side.")
        cupid_verdict = "no_go"
        cupid_conf = 0.7

    cupid_conf = max(0.1, min(1.0, cupid_conf))
    if cupid_verdict == "go":
        cupid_text = "Matches are ready. " + " | ".join(cupid_signals) + ". Approve and move to outreach."
    elif cupid_verdict == "no_go":
        cupid_text = "Cannot match. " + " | ".join(cupid_signals) + ". Source more inventory."
    else:
        cupid_text = "Matching pool is building. " + " | ".join(cupid_signals) + ". Not enough for high-quality matches yet."

    cupid = AgentTake(agent="Cupid Osei", role="Matching", verdict=cupid_verdict, confidence=cupid_conf, reasoning=cupid_text, key_signals=cupid_signals)

    # --- Piper Reeves: Outreach ---
    piper_signals = []
    piper_verdict = "cautious"
    piper_conf = 0.5

    if active_deals >= 3:
        piper_signals.append(f"{active_deals} deals in active outreach")
        piper_verdict = "go"
        piper_conf = 0.65
    elif active_deals >= 1:
        piper_signals.append(f"{active_deals} deal in play")

    if recent_close:
        piper_signals.append(f"Recent close: ${float(recent_close.get('commission') or 0):,.0f} commission")
        piper_conf += 0.1

    piper_conf = max(0.1, min(1.0, piper_conf))
    piper_text = f"Outreach status: {active_deals} active deals. "
    if piper_verdict == "go":
        piper_text += " | ".join(piper_signals) + ". Keep the pressure on. Follow up within 24h."
    else:
        piper_text += " | ".join(piper_signals) + ". Need more deals in the funnel."

    piper = AgentTake(agent="Piper Reeves", role="Outreach", verdict=piper_verdict, confidence=piper_conf, reasoning=piper_text, key_signals=piper_signals)

    # --- Cash Montgomery: Revenue ---
    cash_signals = []
    cash_verdict = "cautious"
    cash_conf = 0.5

    if total_commission >= 1000:
        cash_signals.append(f"${total_commission:,.0f} total commission earned")
        cash_conf += 0.15
    elif total_commission > 0:
        cash_signals.append(f"${total_commission:,.0f} commission so far")

    if top_deal:
        deal_val = float(top_deal.get("deal_value") or 0)
        comm = float(top_deal.get("commission") or 0)
        cash_signals.append(f"Top deal: ${deal_val:,.0f} value, ${comm:,.0f} commission")
        if comm >= 500:
            cash_verdict = "go"
            cash_conf = 0.7

    cash_conf = max(0.1, min(1.0, cash_conf))
    cash_text = f"Revenue: ${total_commission:,.0f} earned. "
    if cash_verdict == "go":
        cash_text += " | ".join(cash_signals) + ". Numbers work. Execute."
    else:
        cash_text += " | ".join(cash_signals) + ". Need higher-value deals in the pipeline."

    cash = AgentTake(agent="Cash Montgomery", role="Revenue", verdict=cash_verdict, confidence=cash_conf, reasoning=cash_text, key_signals=cash_signals)

    agents = [cupid, piper, cash]
    return _marcus_decides(agents, data.get("context", "broker pipeline"), "", "", 0, 0)


# ---------------------------------------------------------------------------
# ARCADE TEAM: Vera Lux, Penny Vance, Quinn Sharp, Marcus Cole
# ---------------------------------------------------------------------------

def run_arcade_debate(data: dict) -> DebateResult | None:
    """Arcade/blackjack debate. Data from Supabase arcade_scores + player stats."""
    active_players = int(data.get("active_players") or 0)
    total_hands = int(data.get("total_hands") or 0)
    total_chips_wagered = float(data.get("total_chips_wagered") or 0)
    gem_revenue = float(data.get("gem_revenue_usd") or 0)
    avg_session_min = float(data.get("avg_session_min") or 0)
    retention_rate = float(data.get("retention_rate") or 0)
    top_player = data.get("top_player") or {}

    # --- Vera Lux: Engagement ---
    vera_signals = []
    vera_verdict = "cautious"
    vera_conf = 0.5

    if active_players >= 10:
        vera_signals.append(f"{active_players} active players")
        vera_verdict = "go"
        vera_conf = 0.7
    elif active_players >= 3:
        vera_signals.append(f"{active_players} players online")
    else:
        vera_signals.append(f"Low traffic: {active_players} players")
        vera_conf -= 0.1

    if avg_session_min >= 15:
        vera_signals.append(f"Avg session {avg_session_min:.0f} min - strong engagement")
        vera_conf += 0.1
    elif avg_session_min > 0:
        vera_signals.append(f"Avg session {avg_session_min:.0f} min")

    if retention_rate >= 0.3:
        vera_signals.append(f"{retention_rate*100:.0f}% retention - healthy")
        vera_conf += 0.1

    vera_conf = max(0.1, min(1.0, vera_conf))
    vera_text = f"Engagement: {active_players} players, {total_hands} hands played. "
    vera_text += " | ".join(vera_signals) + "."

    vera = AgentTake(agent="Vera Lux", role="Engagement", verdict=vera_verdict, confidence=vera_conf, reasoning=vera_text, key_signals=vera_signals)

    # --- Penny Vance: Revenue ---
    penny_signals = []
    penny_verdict = "cautious"
    penny_conf = 0.5

    if gem_revenue >= 50:
        penny_signals.append(f"${gem_revenue:.2f} gem revenue")
        penny_verdict = "go"
        penny_conf = 0.7
    elif gem_revenue > 0:
        penny_signals.append(f"${gem_revenue:.2f} gem revenue - some monetization")
    else:
        penny_signals.append("Zero gem revenue - no paying players yet")
        penny_conf -= 0.1

    if total_chips_wagered > 100000:
        penny_signals.append(f"{total_chips_wagered:,.0f} chips wagered - high volume")

    penny_conf = max(0.1, min(1.0, penny_conf))
    penny_text = f"Monetization: ${gem_revenue:.2f} revenue. " + " | ".join(penny_signals) + "."

    penny = AgentTake(agent="Penny Vance", role="Finance", verdict=penny_verdict, confidence=penny_conf, reasoning=penny_text, key_signals=penny_signals)

    # --- Quinn Sharp: QA ---
    quinn_signals = []
    quinn_verdict = "go"
    quinn_conf = 0.6

    if total_hands > 0:
        quinn_signals.append(f"{total_hands} hands dealt - game is functional")
    else:
        quinn_signals.append("No hands dealt - possible game issue")
        quinn_verdict = "no_go"
        quinn_conf = 0.8

    quinn_text = "Game health: " + " | ".join(quinn_signals) + ". "
    if quinn_verdict == "go":
        quinn_text += "All systems running. No bugs detected."
    else:
        quinn_text += "Investigate game state before promoting."

    quinn = AgentTake(agent="Quinn Sharp", role="QA", verdict=quinn_verdict, confidence=quinn_conf, reasoning=quinn_text, key_signals=quinn_signals)

    agents = [vera, penny, quinn]
    return _marcus_decides(agents, data.get("context", "arcade ops"), "", "", 0, 0)


# ---------------------------------------------------------------------------
# Shared: Marcus decides for any team
# ---------------------------------------------------------------------------

def _marcus_decides(agents: list[AgentTake], context: str, direction: str, entry_type: str, score: int, threshold: int) -> DebateResult:
    """Marcus Cole breaks the tie for any team."""
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
        marcus_text = f"{go_count} out of {len(agents)} say go on {context}. Execute."
    elif consensus == "no_go":
        marcus_verdict = "no_go"
        marcus_text = f"{no_go_count} out of {len(agents)} blocking {context}. Stand down."
        blocked = [f"{a.agent.split()[0]}: {a.key_signals[0] if a.key_signals else 'risk'}" for a in agents if a.verdict == "no_go"]
        if blocked:
            marcus_text += " Reasons: " + "; ".join(blocked) + "."
    else:
        marcus_verdict = "wait"
        marcus_text = f"Split on {context}. "
        for a in agents:
            marcus_text += f"{a.agent.split()[0]} says {a.verdict}. "
        marcus_text += "Hold and reassess."

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
        direction=direction,
        entry_type=entry_type,
        score=score,
        threshold=threshold,
    )
