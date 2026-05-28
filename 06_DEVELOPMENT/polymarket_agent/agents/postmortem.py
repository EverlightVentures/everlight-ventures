"""Postmortem (Thomas Rourke / 56_data_verifier). Brier + log loss + win rate.
Weekly branded report via existing content_tools.gdocs_bridge."""
from decimal import Decimal


class Postmortem:
    def brier_score(self, closed_bets: list) -> float:
        if not closed_bets:
            return 0.0
        total = 0.0
        for b in closed_bets:
            pred = float(b.get("predicted_prob", 0.5))
            resolved = 1.0 if b.get("outcome_resolved") == b.get("bet_outcome") else 0.0
            total += (pred - resolved) ** 2
        return total / len(closed_bets)

    def win_rate(self, closed_bets: list) -> float:
        if not closed_bets:
            return 0.0
        wins = sum(1 for b in closed_bets if Decimal(str(b.get("pnl_usdc", 0))) > 0)
        return wins / len(closed_bets)

    def total_pnl(self, closed_bets: list) -> Decimal:
        return sum((Decimal(str(b.get("pnl_usdc", 0))) for b in closed_bets), Decimal("0"))
