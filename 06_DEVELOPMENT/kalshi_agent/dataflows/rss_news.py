"""RSS news feed aggregator. Free; uses feedparser."""
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import feedparser

from kalshi_agent.dataflows.interface import Signal


class RSSNews:
    def __init__(self, feeds: list):
        self.feeds = feeds

    def get_recent_items(self, last_minutes: int = 15) -> list:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=last_minutes)
        signals = []
        for feed_url in self.feeds:
            parsed = feedparser.parse(feed_url)
            for entry in getattr(parsed, "entries", []):
                pub = getattr(entry, "published", "") or getattr(entry, "updated", "")
                try:
                    pub_dt = parsedate_to_datetime(pub)
                    if pub_dt.tzinfo is None:
                        pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                except (TypeError, ValueError):
                    continue
                if pub_dt < cutoff:
                    continue
                title = getattr(entry, "title", "")
                summary = getattr(entry, "summary", "")
                signals.append(Signal(
                    source="rss",
                    text=f"{title} -- {summary}"[:500],
                    url=getattr(entry, "link", ""),
                    timestamp=pub_dt.isoformat(),
                    credibility=0.7,
                ))
        return signals
