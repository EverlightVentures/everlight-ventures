"""Perplexity Sonar wrapper. Reuses xlm_bot/ai/perplexity_advisor brief format."""
import sys
from pathlib import Path

# Reuse the existing advisor module
sys.path.insert(0, str(Path("/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/xlm_bot")))
try:
    from ai.perplexity_advisor import _read_cache as get_brief
except ImportError:
    def get_brief():
        return {"headlines": []}

from polymarket_agent.dataflows.interface import Signal


class Sonar:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    def get_news_velocity(self, category: str, last_minutes: int = 10) -> list:
        brief = get_brief() or {}
        signals = []
        for h in brief.get("headlines", []):
            signals.append(Signal(
                source="perplexity_sonar",
                text=h.get("text", ""),
                url=h.get("url", ""),
                sentiment=float(h.get("sentiment", 0.0)),
                credibility=0.75,
            ))
        return signals
