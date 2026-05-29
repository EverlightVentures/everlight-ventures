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
                 min_confidence: float = 0.65, max_bet_abs: Decimal = None,
                 convex_max_price: Decimal = Decimal("0.20"),
                 convex_min_edge: Decimal = Decimal("0.03"),
                 convex_min_confidence: float = 0.45,
                 convex_budget_pct: Decimal = Decimal("15.0"),
                 convex_stake_pct: Decimal = Decimal("1.0")):
        self.max_bet_pct = max_bet_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_open_positions = max_open_positions
        self.min_edge = min_edge
        self.min_confidence = min_confidence
        # Operator growth-ladder absolute ceiling (USD). None = no extra cap.
        self.max_bet_abs = max_bet_abs
        # CONVEXITY LANE (operator: don't miss the big asymmetric trades).
        # A cheap outcome (<= convex_max_price, pays >= 1/price multiple) with a
        # positive model edge is a lottery ticket -- small stake, huge upside.
        # We take these on RELAXED gates but cap total convex exposure so a string
        # of moonshot misses can't drain the bankroll.
        self.convex_max_price = convex_max_price          # e.g. <=0.20 -> >=5x payout
        self.convex_min_edge = convex_min_edge            # relaxed edge bar
        self.convex_min_confidence = convex_min_confidence  # relaxed confidence bar
        self.convex_budget_pct = convex_budget_pct        # max % bankroll on convex at once
        self.convex_stake_pct = convex_stake_pct          # stake per convex bet (% bankroll)

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
        convex_spent = Decimal("0")
        convex_budget = bankroll * self.convex_budget_pct / Decimal("100")
        convex_stake = bankroll * self.convex_stake_pct / Decimal("100")

        for p in sorted(predictions, key=lambda x: x.edge, reverse=True):
            price = Decimal(str(p.market_price))
            edge = Decimal(str(p.edge))
            is_convex = price <= self.convex_max_price  # cheap, high-multiple outcome

            if is_convex:
                # Relaxed gates for moonshots, bounded by the convex budget.
                if edge < self.convex_min_edge or p.confidence < self.convex_min_confidence:
                    continue
                if convex_spent + convex_stake > convex_budget:
                    continue  # convex budget exhausted -- protect the bankroll
                size = convex_stake.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
                convex_spent += size
            else:
                # Core wealth-engine bets: full gates + quarter-Kelly sizing.
                if edge < self.min_edge or p.confidence < self.min_confidence:
                    continue
                size = self._quarter_kelly_size(bankroll, p.edge, p.market_price)

            if size <= 0:
                continue
            approved.append(BetRequest(
                market_id=p.market_id, outcome=p.outcome,
                amount_usdc=size, limit_price=price,
                predicted_prob=p.predicted_prob, edge=p.edge,
            ))
            if len(approved) >= slots_left:
                break
        return approved
