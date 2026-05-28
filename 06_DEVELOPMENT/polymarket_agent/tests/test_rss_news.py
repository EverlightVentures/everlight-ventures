from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from polymarket_agent.dataflows.rss_news import RSSNews
from polymarket_agent.dataflows.interface import Signal


def test_get_recent_items_filters_by_age():
    now = datetime.now(timezone.utc)
    fresh_pub = (now - timedelta(minutes=5)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    stale_pub = (now - timedelta(hours=2)).strftime("%a, %d %b %Y %H:%M:%S +0000")

    fake_feed = MagicMock()
    fake_feed.entries = [
        MagicMock(title="Fresh", link="https://r/1", published=fresh_pub, summary="x"),
        MagicMock(title="Stale", link="https://r/2", published=stale_pub, summary="x"),
    ]

    with patch("feedparser.parse", return_value=fake_feed):
        n = RSSNews(feeds=["https://r"])
        signals = n.get_recent_items(last_minutes=15)

    assert len(signals) == 1
    assert signals[0].text.startswith("Fresh")
    assert signals[0].source == "rss"
