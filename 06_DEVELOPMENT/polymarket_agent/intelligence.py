"""Shared intelligence layer -- the 'O cent' layer: OSINT + Codex/Gemini
cross-check + Blinko brain. The Polymarket agent reuses the venture's existing
intelligence engines instead of siloing.

  1. brain_query   -> ask Blinko (RAG) for prior knowledge on a category/topic
  2. osint_enrich  -> run the 22-investigator osint_api on a named market entity
  3. cross_check   -> red-team a high-stakes prediction with Codex AND Gemini
                      (the 9-phase doctrine): place only if they do not veto.

Every method is best-effort with hard timeouts and graceful degradation -- a
dead key, missing CLI, or unreachable Blinko returns a neutral result and never
crashes or blocks the trade cycle. Cross-check runs ONLY on high-stakes bets
(caller decides) to bound latency + cost.
"""
import json
import logging
import re
import subprocess
import urllib.request
from pathlib import Path

log = logging.getLogger("polymarket.intel")

_OSINT_PATH = "/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/intel_center"
_BLINKO_ENDPOINTS = ["http://127.0.0.1:2700", "http://127.0.0.1:1111", "http://e5-mother:1111"]
_CODEX_BIN = "codex"
_GEMINI_BIN = "gemini"
_PROPER_NOUN = re.compile(r"\b([A-Z][a-zA-Z]{2,}(?:\s+[A-Z][a-zA-Z]+){0,2})\b")
_JSON_OBJ = re.compile(r"\{.*\}", re.DOTALL)
_STOP_ENTITIES = {"Will", "The", "Yes", "No", "Trump", "What", "When", "Who"}  # too-generic


class SharedIntelligence:
    def __init__(self, enabled_osint: bool = True, enabled_crosscheck: bool = True,
                 brain_endpoints=None, cross_timeout: int = 40, osint_timeout: int = 45):
        self.enabled_osint = enabled_osint
        self.enabled_crosscheck = enabled_crosscheck
        self.brain_endpoints = brain_endpoints or _BLINKO_ENDPOINTS
        self.cross_timeout = cross_timeout
        self.osint_timeout = osint_timeout

    # ---- 1. Blinko brain (RAG prior knowledge) ----
    def brain_query(self, query: str, limit: int = 5) -> str:
        payload = json.dumps({"query": query, "limit": limit}).encode()
        for base in self.brain_endpoints:
            try:
                req = urllib.request.Request(
                    f"{base}/api/v1/note/search", data=payload,
                    headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=5) as r:
                    data = json.loads(r.read())
                notes = data if isinstance(data, list) else data.get("data", [])
                return " | ".join(str(n.get("content", ""))[:200] for n in notes[:limit])
            except Exception:
                continue
        return ""  # brain unreachable -> no prior context (degrade)

    # ---- 2. OSINT entity enrichment ----
    def _entities(self, question: str) -> list:
        found = [e for e in _PROPER_NOUN.findall(question) if e not in _STOP_ENTITIES]
        # de-dup preserving order
        seen, out = set(), []
        for e in found:
            if e not in seen:
                seen.add(e); out.append(e)
        return out

    def osint_enrich(self, question: str) -> dict:
        entities = self._entities(question)
        if not self.enabled_osint or not entities:
            return {"entities": entities, "osint": None}
        try:
            import sys
            if _OSINT_PATH not in sys.path:
                sys.path.insert(0, _OSINT_PATH)
            from osint_api.orchestrator import run_investigation_sync
            # Light: investigate the primary entity, news/web sources only.
            result = run_investigation_sync(entities[0], sources=["news", "web"])
            return {"entities": entities, "osint": result}
        except Exception as e:
            log.warning("osint_enrich degraded: %s: %s", type(e).__name__, e)
            return {"entities": entities, "osint": None}

    # ---- 3. Codex + Gemini cross-check (red-team before placing) ----
    def _ask_cli(self, binary: str, prompt: str) -> dict:
        try:
            proc = subprocess.run(
                [binary, "exec", prompt] if binary == _CODEX_BIN else [binary, "-p", prompt],
                capture_output=True, text=True, timeout=self.cross_timeout,
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            m = _JSON_OBJ.search(out)
            if not m:
                return {"available": True, "agree": None, "note": out[:120]}
            d = json.loads(m.group(0))
            return {"available": True, "agree": bool(d.get("agree")),
                    "confidence": float(d.get("confidence", 0) or 0),
                    "note": str(d.get("note", ""))[:160]}
        except FileNotFoundError:
            return {"available": False}
        except Exception as e:
            return {"available": False, "error": f"{type(e).__name__}"}

    def cross_check(self, question: str, outcome: str, predicted_prob: float,
                    market_price: float, reasoning: str) -> dict:
        """Red-team a prediction with Codex + Gemini. Returns a verdict dict.
        vetoed=True if a reviewer that ANSWERED disagrees. Reviewers that are
        unavailable do not veto (degrade open is acceptable -- the 9 executor
        pre-checks remain the hard gate)."""
        if not self.enabled_crosscheck:
            return {"reviewed": False, "vetoed": False, "reason": "disabled"}
        prompt = (
            f"Red-team this prediction-market bet. Question: {question}. "
            f"Outcome: {outcome}. Market implied prob: {market_price:.3f}. "
            f"Our estimate: {predicted_prob:.3f}. Our reasoning: {reasoning}. "
            f'Is this a sound +EV bet? Reply ONLY JSON: {{"agree": true/false, '
            f'"confidence": 0..1, "note": "<short>"}}'
        )
        codex = self._ask_cli(_CODEX_BIN, prompt)
        gemini = self._ask_cli(_GEMINI_BIN, prompt)
        answered = [r for r in (codex, gemini) if r.get("available") and r.get("agree") is not None]
        vetoed = any(r.get("agree") is False for r in answered)
        return {
            "reviewed": bool(answered),
            "vetoed": vetoed,
            "codex": codex, "gemini": gemini,
        }
