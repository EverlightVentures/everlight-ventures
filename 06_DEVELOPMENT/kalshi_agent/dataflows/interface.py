from dataclasses import dataclass, field


@dataclass
class Signal:
    """A news, social, or internal signal that may affect a Polymarket market."""

    source: str
    text: str
    url: str = ""
    author: str = ""
    timestamp: str = ""
    credibility: float = 0.5
    sentiment: float = 0.0
    market_ids: list = field(default_factory=list)
