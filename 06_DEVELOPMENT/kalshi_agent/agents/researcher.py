"""Researcher (Bull Archer). Aggregates signals per market via simple keyword match.
LLM-based grouping is a later upgrade; keyword baseline is testable + free."""
import re
from collections import defaultdict


_STOP = {"will", "the", "a", "an", "in", "on", "to", "of", "and", "or", "is",
         "are", "what", "when", "where", "by", "for", "be", "?"}


def _keywords(text: str) -> set:
    return {w.lower() for w in re.findall(r"\w+", text)
            if len(w) >= 3 and w.lower() not in _STOP}


class Researcher:
    def aggregate(self, markets: list, signals: list) -> dict:
        briefs = {}
        for m in markets:
            mk_keys = _keywords(m.question)
            matched = []
            for s in signals:
                if mk_keys & _keywords(s.text):
                    matched.append(s)
            briefs[m.id] = {
                "question": m.question,
                "signals": matched,
                "category": m.category,
            }
        return briefs
