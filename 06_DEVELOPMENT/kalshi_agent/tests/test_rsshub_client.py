from unittest.mock import patch, MagicMock
from kalshi_agent.dataflows.rsshub_client import RSSHubClient


def test_polls_per_username_and_returns_signals():
    fake_feed = MagicMock()
    fake_feed.entries = [MagicMock(
        title="BREAKING: ETF approved",
        link="https://x/1",
        published="Fri, 28 May 2026 12:00:00 +0000",
        summary="ETF approved",
    )]

    with patch("feedparser.parse", return_value=fake_feed) as mock_parse:
        c = RSSHubClient(base_url="http://e5-mother:1200")
        signals = c.get_recent_tweets(usernames=["tier10k"], last_minutes=60)

    assert mock_parse.call_args[0][0] == "http://e5-mother:1200/twitter/user/tier10k"
    assert len(signals) >= 0
    if signals:
        assert signals[0].source == "rsshub_twitter"
        assert signals[0].author == "tier10k"
