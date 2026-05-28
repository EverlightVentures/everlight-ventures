"""Self-hosted RSSHub Twitter mirror. Free, runs on e5-mother."""
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import feedparser

from polymarket_agent.dataflows.interface import Signal


class RSSHubClient:
    def __init__(self, base_url: str = "http://e5-mother:1200"):
        self.base_url = base_url.rstrip("/")

    def get_recent_tweets(self, usernames: list, last_minutes: int = 15) -> list:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=last_minutes)
        signals = []
        for u in usernames:
            url = f"{self.base_url}/twitter/user/{u}"
            try:
                parsed = feedparser.parse(url)
            except Exception:
                continue
            for entry in getattr(parsed, "entries", []):
                pub = getattr(entry, "published", "")
                try:
                    pub_dt = parsedate_to_datetime(pub)
                    if pub_dt.tzinfo is None:
                        pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                except (TypeError, ValueError):
                    continue
                if pub_dt < cutoff:
                    continue
                signals.append(Signal(
                    source="rsshub_twitter",
                    text=getattr(entry, "title", ""),
                    url=getattr(entry, "link", ""),
                    author=u,
                    timestamp=pub_dt.isoformat(),
                    credibility=0.85,
                ))
        return signals
