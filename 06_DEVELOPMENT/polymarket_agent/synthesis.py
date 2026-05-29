"""360 decision synthesis -- fuse the WHOLE infrastructure into ONE call.

Instead of deciding with a single model, a high-value market is judged by
multiple independent minds (Claude + Perplexity + Codex + Gemini), each fed the
same gathered intel (Sonar news + RSS signals + OSINT entity intel + Blinko
brain prior knowledge). Their probability estimates are synthesized:

  - final prob   = median of the minds that answered
  - agreement    = 1 - normalized spread of estimates (tight = high)
  - confidence   = mean raw confidence x agreement  (disagreement LOWERS it)

Wide divergence between minds => low confidence => skip or size down. This is
the Hive 7-mind triangulation / 9-phase doctrine applied to the trade brain.
Two-tier by design: a cheap single-model SCREEN narrows candidates upstream;
the full 360 runs only on the few that pass, to bound latency + cost.

Every mind is best-effort: a missing key/CLI just drops that vote; the decision
proceeds on whoever answered (and reports how many). Never crashes the cycle.
"""
import json
import logging
import statistics
from dataclasses import dataclass, field

log = logging.getLogger("polymarket.synth")


@dataclass
class ConsensusEstimate:
    predicted_prob: float
    confidence: float
    agreement: float
    n_minds: int
    market_price: float
    edge: float
    per_mind: dict = field(default_factory=dict)   # name -> (prob, conf)
    intel: dict = field(default_factory=dict)       # gathered context provenance
    reasoning: str = ""


class Decision360:
    def __init__(self, predictor, intel, sonar=None, min_minds: int = 1):
        # predictor: agents.predictor.Predictor (Claude)  -- required
        # intel: intelligence.SharedIntelligence (OSINT + cross-check + brain)
        # sonar: dataflows.perplexity_sonar.Sonar (Perplexity reasoning vote)
        self.predictor = predictor
        self.intel = intel
        self.sonar = sonar
        self.min_minds = min_minds

    # ---- independent minds: each returns (prob, conf) or None ----
    def _claude_vote(self, brief) -> tuple | None:
        try:
            prob, conf, reason = self.predictor._llm_predict(brief)
            return (prob, conf, reason) if conf > 0 else None
        except Exception as e:
            log.warning("claude vote failed: %s", e)
            return None

    def _perplexity_vote(self, brief) -> tuple | None:
        """Perplexity (Sonar) as a reasoning vote, not just a news fetch."""
        if not self.sonar or not getattr(self.sonar, "api_key", None):
            return None
        q = brief.get("question", "")
        outcome = brief.get("_outcome", "YES")
        mp = brief.get("_market_price", 0.5)
        prompt = (
            f"Prediction market: {q}. Outcome: {outcome}. Market implied prob: "
            f"{mp:.3f}. Estimate the TRUE probability with live information. "
            f'Reply ONLY JSON: {{"predicted_prob":0..1,"confidence":0..1}}'
        )
        try:
            content = self.sonar._call_sonar(prompt)
            import re
            m = re.search(r"\{.*\}", content, re.DOTALL)
            if not m:
                return None
            d = json.loads(m.group(0))
            prob = max(0.0, min(1.0, float(d.get("predicted_prob", mp))))
            conf = max(0.0, min(1.0, float(d.get("confidence", 0.0))))
            return (prob, conf, "perplexity") if conf > 0 else None
        except Exception as e:
            log.warning("perplexity vote failed: %s", e)
            return None

    def _cli_vote(self, which: str, brief) -> tuple | None:
        """Codex or Gemini as a probability vote via the intel cross-check CLI path."""
        q = brief.get("question", "")
        outcome = brief.get("_outcome", "YES")
        mp = brief.get("_market_price", 0.5)
        prompt = (
            f"Prediction market: {q}. Outcome: {outcome}. Market prob: {mp:.3f}. "
            f'Estimate TRUE probability. Reply ONLY JSON: '
            f'{{"predicted_prob":0..1,"confidence":0..1}}'
        )
        binary = "codex" if which == "codex" else "gemini"
        try:
            r = self.intel._ask_cli(binary, prompt)
            if not r.get("available"):
                return None
            # _ask_cli parses {agree,confidence,note}; re-parse for prob if present
            note = r.get("note", "")
            import re
            m = re.search(r"\{.*\}", note, re.DOTALL)
            if m:
                d = json.loads(m.group(0))
                prob = float(d.get("predicted_prob", mp))
                conf = float(d.get("confidence", r.get("confidence", 0.0)))
                return (max(0.0, min(1.0, prob)), max(0.0, min(1.0, conf)), which)
            return None
        except Exception as e:
            log.warning("%s vote failed: %s", which, e)
            return None

    def synthesize(self, brief: dict, use_cli_minds: bool = True) -> ConsensusEstimate:
        mp = float(brief.get("_market_price", 0.5))

        # 1) GATHER intel from the whole infra (best-effort), attach to brief
        intel_ctx = {}
        try:
            intel_ctx["brain"] = self.intel.brain_query(brief.get("question", ""))
        except Exception:
            intel_ctx["brain"] = ""
        try:
            intel_ctx["osint"] = self.intel.osint_enrich(brief.get("question", ""))
        except Exception:
            intel_ctx["osint"] = {}

        # 2) INDEPENDENT VOTES from multiple minds
        votes = {}
        for name, fn in (("claude", lambda: self._claude_vote(brief)),
                         ("perplexity", lambda: self._perplexity_vote(brief))):
            v = fn()
            if v:
                votes[name] = v
        if use_cli_minds:
            for name in ("codex", "gemini"):
                v = self._cli_vote(name, brief)
                if v:
                    votes[name] = v

        if len(votes) < self.min_minds or not votes:
            return ConsensusEstimate(
                predicted_prob=mp, confidence=0.0, agreement=0.0,
                n_minds=len(votes), market_price=mp, edge=0.0,
                per_mind={k: (v[0], v[1]) for k, v in votes.items()},
                intel=intel_ctx, reasoning="insufficient minds answered",
            )

        # 3) SYNTHESIZE: median prob, agreement from spread, confidence x agreement
        probs = [v[0] for v in votes.values()]
        confs = [v[1] for v in votes.values()]
        final_prob = statistics.median(probs)
        spread = (max(probs) - min(probs)) if len(probs) > 1 else 0.0
        # agreement: 0 spread -> 1.0; >=0.30 spread -> 0.0
        agreement = max(0.0, 1.0 - spread / 0.30)
        base_conf = sum(confs) / len(confs)
        final_conf = base_conf * agreement if len(probs) > 1 else base_conf
        edge = final_prob - mp

        reason = (f"{len(votes)} minds; median {final_prob:.3f} vs mkt {mp:.3f}; "
                  f"spread {spread:.3f}; agreement {agreement:.2f}")
        return ConsensusEstimate(
            predicted_prob=final_prob, confidence=final_conf, agreement=agreement,
            n_minds=len(votes), market_price=mp, edge=edge,
            per_mind={k: (v[0], v[1]) for k, v in votes.items()},
            intel=intel_ctx, reasoning=reason,
        )
