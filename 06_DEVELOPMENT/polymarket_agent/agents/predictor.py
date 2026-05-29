"""Predictor (Cipher Wolfe). Real Claude probability estimate + brain bridge.

_llm_predict makes a REAL Anthropic call (Claude Sonnet) to estimate the true
probability of an outcome from the research brief, then the brain bridge scales
confidence. Cost discipline: predict() only spends an LLM call on markets that
actually have matched signals -- no information means no edge, so we skip (most
markets, e.g. joke markets, have zero signals). Degrades safely: if the API key
is missing or the call fails, returns the market price with 0 confidence, which
yields edge 0 -> no bet (never bet blind)."""
import json
import os
import re
from pathlib import Path

from polymarket_agent.agents.risk_manager import Prediction

_DEFAULT_BRAIN = {"decisive_score": 0.5, "logical_score": 0.5,
                  "self_healing_score": 0.5, "plasticity_score": 0.5}
_JSON_OBJ = re.compile(r"\{.*\}", re.DOTALL)


def _load_anthropic_key() -> str | None:
    # Cross-host resolution (phone .env -> e5 .env -> env var); .env authoritative.
    from polymarket_agent.paths import read_env_key
    return read_env_key("ANTHROPIC_API_KEY")


def _signal_text(s) -> tuple:
    """Accept either Signal objects or asdict'd dicts."""
    if isinstance(s, dict):
        return float(s.get("sentiment", 0.0)), str(s.get("text", ""))
    return float(getattr(s, "sentiment", 0.0)), str(getattr(s, "text", ""))


class Predictor:
    def __init__(self, min_edge: float = 0.05, min_confidence: float = 0.6,
                 model: str = "claude-sonnet-4-6", api_key: str = None,
                 max_llm_calls: int = 15):
        self.min_edge = min_edge
        self.min_confidence = min_confidence
        self.model = model
        self._api_key = api_key  # None -> lazy-load from env/.env
        # Cost control: never spend more than N Claude calls per cycle. Prioritize
        # markets whose signals are HIGH credibility (smart-money 0.9, rsshub 0.85)
        # over generic RSS (0.7) -- so we don't burn API on loose keyword matches.
        self.max_llm_calls = max_llm_calls

    def _brain_adjust(self, raw_confidence: float, brain_policy: dict) -> float:
        bp = {**_DEFAULT_BRAIN, **brain_policy}
        boost = (bp["decisive_score"] * 0.3 +
                 bp["logical_score"] * 0.3 +
                 bp["plasticity_score"] * 0.2 +
                 bp["self_healing_score"] * 0.2)
        return raw_confidence * boost

    def _llm_predict(self, brief: dict) -> tuple:
        """REAL Claude call. Returns (predicted_prob, raw_confidence, reasoning).
        Safe default on any failure: (market_price, 0.0, reason) -> edge 0 -> no bet."""
        market_price = float(brief.get("_market_price", 0.5))
        outcome = brief.get("_outcome", "YES")
        key = self._api_key or _load_anthropic_key()
        if not key:
            return (market_price, 0.0, "llm_unavailable:no_key")

        sigs = brief.get("signals", []) or []
        sig_lines = "\n".join(
            f"- ({sent:+.1f}) {text}" for sent, text in
            (_signal_text(s) for s in sigs[:12]) if text
        ) or "(no fresh signals)"

        prompt = (
            f"Prediction market question: {brief.get('question','')}\n"
            f"Outcome being priced: {outcome}\n"
            f"Current MARKET implied probability of '{outcome}': {market_price:.3f}\n"
            f"Recent signals (sentiment in parens):\n{sig_lines}\n\n"
            f"You are a sharp prediction-market analyst. Estimate the TRUE probability "
            f"of '{outcome}' resolving yes, independent of the market price. Only express "
            f"high confidence when the signals give you a real informational edge. "
            f"Return ONLY JSON: "
            f'{{"predicted_prob": <0..1>, "confidence": <0..1>, "reasoning": "<one sentence>"}}'
        )
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=key)
            msg = client.messages.create(
                model=self.model, max_tokens=400,
                system="You output only valid JSON. You are calibrated and skeptical; "
                       "you do not claim edge you do not have.",
                messages=[{"role": "user", "content": prompt}],
            )
            content = "".join(getattr(b, "text", "") for b in msg.content)
            m = _JSON_OBJ.search(content)
            if not m:
                return (market_price, 0.0, "llm_parse_fail")
            data = json.loads(m.group(0))
            prob = max(0.0, min(1.0, float(data.get("predicted_prob", market_price))))
            conf = max(0.0, min(1.0, float(data.get("confidence", 0.0))))
            return (prob, conf, str(data.get("reasoning", ""))[:300])
        except Exception as e:
            return (market_price, 0.0, f"llm_error:{type(e).__name__}")

    def _best_cred(self, brief) -> float:
        sigs = brief.get("signals") or []
        best = 0.0
        for s in sigs:
            c = s.get("credibility", 0) if isinstance(s, dict) else getattr(s, "credibility", 0)
            best = max(best, float(c or 0))
        return best

    def predict(self, briefs: dict, brain_policy: dict) -> list:
        out = []
        # Cost control: rank briefs by best signal credibility, only LLM-evaluate
        # the top N (high-cred signals first), skip the rest this cycle.
        ranked = sorted(
            [(mid, b) for mid, b in briefs.items() if (b.get("signals") or [])],
            key=lambda kv: self._best_cred(kv[1]), reverse=True,
        )[: self.max_llm_calls]
        for market_id, brief in ranked:
            # Cost + edge discipline: no matched signals -> no information edge ->
            # skip (do not burn an LLM call, do not bet blind).
            if not (brief.get("signals") or []):
                continue
            primary = brief.get("_outcome", "YES")
            market_price = brief.get("_market_price", 0.5)
            # Claude estimates P(primary outcome) once.
            try:
                pred_prob, raw_conf, reasoning = self._llm_predict(brief)
            except Exception:
                continue
            adjusted_conf = self._brain_adjust(raw_conf, brain_policy)
            if adjusted_conf < self.min_confidence:
                continue

            # Evaluate BOTH sides. P(primary)=pred_prob implies P(other)=1-pred_prob.
            # Bet whichever side the market under-prices by >= min_edge. This is
            # what lets us FADE overpriced longshots (bet the favorite/NO side).
            prices = brief.get("_prices") or {}
            outcomes = brief.get("_outcomes") or [primary]
            other = next((o for o in outcomes if o != primary), None)
            other_price = prices.get(other) if other else (1.0 - market_price)

            candidates = [(primary, pred_prob, market_price)]
            if other is not None and other_price is not None:
                candidates.append((other, 1.0 - pred_prob, float(other_price)))

            # Choose the side with the largest positive edge >= min_edge.
            best = None
            for side, p_true, p_mkt in candidates:
                e = p_true - p_mkt
                if e >= self.min_edge and (best is None or e > best[3]):
                    best = (side, p_true, p_mkt, e)
            if best is None:
                continue
            side, p_true, p_mkt, e = best
            out.append(Prediction(
                market_id=market_id, outcome=side,
                predicted_prob=p_true, market_price=p_mkt,
                edge=e, confidence=adjusted_conf, reasoning=reasoning,
            ))
        return out
