"""Risk Manager (Rex Thornton). Quarter-Kelly sizing + 9 pre-checks (defense in depth)."""
import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from pathlib import Path

from polymarket_agent.execution.executor_polymarket import BetRequest


@dataclass
class Prediction:
    market_id: str
    outcome: str
    predicted_prob: float
    market_price: float
    edge: float
    confidence: float
    reasoning: str = ""


class RiskManager:
    def __init__(self, max_bet_pct: Decimal, max_daily_loss_pct: Decimal,
                 max_open_positions: int, min_edge: Decimal = Decimal("0.05"),
                 min_confidence: float = 0.65, max_bet_abs: Decimal = None):
        self.max_bet_pct = max_bet_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_open_positions = max_open_positions
        self.min_edge = min_edge
        self.min_confidence = min_confidence
        # Operator growth-ladder absolute ceiling (USD). None = no extra cap.
        self.max_bet_abs = max_bet_abs

    def _quarter_kelly_size(self, bankroll: Decimal, edge: float, odds: float) -> Decimal:
        if odds <= 0 or odds >= 1:
            return Decimal("0")
        # Full Kelly: f = edge / (1 - odds) for binary -- but our edge is in prob space
        # Simpler: f = edge / odds where edge = predicted - market and odds = market price
        kelly = Decimal(str(edge)) / Decimal(str(odds))
        quarter = kelly / Decimal("4")
        sized = bankroll * quarter
        # Final size = MIN(quarter-Kelly, % cap, growth-ladder absolute ceiling).
        cap = bankroll * self.max_bet_pct / Decimal("100")
        if sized > cap:
            sized = cap
        if self.max_bet_abs is not None and sized > self.max_bet_abs:
            sized = self.max_bet_abs
        return sized.quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    def evaluate(self, predictions: list, state_path: Path, open_bets_path: Path) -> list:
        state = json.loads(Path(state_path).read_text())
        bankroll = Decimal(str(state.get("cash_usdc", 0)))
        daily_pnl = Decimal(str(state.get("daily_pnl_usdc", 0)))

        # Daily-loss kill switch
        max_loss = bankroll * self.max_daily_loss_pct / Decimal("100") * Decimal("-1")
        if daily_pnl < max_loss:
            return []

        # Max-positions cap
        open_bets = json.loads(Path(open_bets_path).read_text())
        slots_left = self.max_open_positions - len(open_bets)
        if slots_left <= 0:
            return []

        approved = []
        for p in sorted(predictions, key=lambda x: x.edge, reverse=True):
            if Decimal(str(p.edge)) < self.min_edge:
                continue
            if p.confidence < self.min_confidence:
                continue
            size = self._quarter_kelly_size(bankroll, p.edge, p.market_price)
            if size <= 0:
                continue
            approved.append(BetRequest(
                market_id=p.market_id, outcome=p.outcome,
                amount_usdc=size, limit_price=Decimal(str(p.market_price)),
                predicted_prob=p.predicted_prob, edge=p.edge,
            ))
            if len(approved) >= slots_left:
                break
        return approved
