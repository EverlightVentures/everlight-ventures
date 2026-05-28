"""PAPER executor. ENTIRELY SEPARATE from live executor.

This module does NOT import wallet.py.
This module does NOT import py-clob-client.
This module CANNOT submit real orders.

The only way to switch from paper to live is to (a) swap main.py's import
line AND (b) set LIVE_TRADING=true in env. Cannot be confused with live."""
import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


@dataclass
class PaperBetRequest:
    market_id: str
    outcome: str
    amount_usdc: Decimal
    limit_price: Decimal
    predicted_prob: float = 0.0
    edge: float = 0.0


@dataclass
class PaperBet:
    id: str
    market_id: str
    outcome: str
    amount_usdc: str
    limit_price: str
    timestamp: str
    status: str = "open"
    pnl_usdc: str = "0.0"


class PaperExecutor:
    def __init__(self, paper_state_path: Path, paper_open_bets_path: Path):
        self.state_path = Path(paper_state_path)
        self.bets_path = Path(paper_open_bets_path)

    def submit_order(self, req: PaperBetRequest) -> PaperBet:
        state = json.loads(self.state_path.read_text())
        cash = Decimal(str(state.get("cash_usdc", 0)))
        if req.amount_usdc > cash:
            raise ValueError(f"paper bankroll {cash} insufficient for {req.amount_usdc}")
        state["cash_usdc"] = float(cash - req.amount_usdc)
        state["open_positions_value_usdc"] = float(
            Decimal(str(state.get("open_positions_value_usdc", 0))) + req.amount_usdc
        )
        self.state_path.write_text(json.dumps(state, indent=2))

        bet = PaperBet(
            id=f"paper_{uuid.uuid4().hex[:12]}",
            market_id=req.market_id,
            outcome=req.outcome,
            amount_usdc=str(req.amount_usdc),
            limit_price=str(req.limit_price),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        bets = json.loads(self.bets_path.read_text()) if self.bets_path.exists() else []
        bets.append(asdict(bet))
        self.bets_path.write_text(json.dumps(bets, indent=2))
        return bet
