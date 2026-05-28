"""Predictor (Cipher Wolfe). Claude Sonnet 4.6 narrative analysis + brain bridge.
LLM call is mockable via _llm_predict for tests."""
from polymarket_agent.agents.risk_manager import Prediction


_DEFAULT_BRAIN = {"decisive_score": 0.5, "logical_score": 0.5,
                  "self_healing_score": 0.5, "plasticity_score": 0.5}


class Predictor:
    def __init__(self, min_edge: float = 0.05, min_confidence: float = 0.6):
        self.min_edge = min_edge
        self.min_confidence = min_confidence

    def _brain_adjust(self, raw_confidence: float, brain_policy: dict) -> float:
        bp = {**_DEFAULT_BRAIN, **brain_policy}
        boost = (bp["decisive_score"] * 0.3 +
                 bp["logical_score"] * 0.3 +
                 bp["plasticity_score"] * 0.2 +
                 bp["self_healing_score"] * 0.2)
        return raw_confidence * boost

    def _llm_predict(self, brief: dict) -> tuple:
        """Returns (predicted_prob, raw_confidence, reasoning).
        Wired to Claude Sonnet 4.6 in integration; mocked in tests."""
        # Placeholder for unit tests; real implementation calls anthropic SDK
        # via existing ai_workers infrastructure
        return (0.5, 0.5, "stub")

    def predict(self, briefs: dict, brain_policy: dict) -> list:
        out = []
        for market_id, brief in briefs.items():
            market_price = brief.get("_market_price", 0.5)
            outcome = brief.get("_outcome", "YES")
            try:
                pred_prob, raw_conf, reasoning = self._llm_predict(brief)
            except Exception:
                continue
            edge = pred_prob - market_price
            adjusted_conf = self._brain_adjust(raw_conf, brain_policy)
            if edge < self.min_edge:
                continue
            if adjusted_conf < self.min_confidence:
                continue
            out.append(Prediction(
                market_id=market_id, outcome=outcome,
                predicted_prob=pred_prob, market_price=market_price,
                edge=edge, confidence=adjusted_conf, reasoning=reasoning,
            ))
        return out
