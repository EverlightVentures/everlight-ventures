import json
from decimal import Decimal
from pathlib import Path
import pytest
from polymarket_agent.execution.executor_polymarket_paper import PaperExecutor, PaperBetRequest


def test_paper_executor_does_not_import_wallet():
    """Critical: paper module must not reach the wallet module at all."""
    import polymarket_agent.execution.executor_polymarket_paper as paper_mod
    src = Path(paper_mod.__file__).read_text()
    assert "from polymarket_agent.execution.wallet" not in src
    assert "import polymarket_agent.execution.wallet" not in src
    assert "PolygonWallet" not in src


def test_paper_executor_updates_local_bankroll(tmp_path: Path):
    state_path = tmp_path / "paper_bankroll.json"
    state_path.write_text(json.dumps({"cash_usdc": 250.0, "open_positions_value_usdc": 0.0}))
    bets_path = tmp_path / "paper_open_bets.json"
    bets_path.write_text(json.dumps([]))

    ex = PaperExecutor(paper_state_path=state_path, paper_open_bets_path=bets_path)
    req = PaperBetRequest(market_id="mkt_1", outcome="YES",
                          amount_usdc=Decimal("10"), limit_price=Decimal("0.5"))
    bet = ex.submit_order(req)

    assert bet.id.startswith("paper_")
    state = json.loads(state_path.read_text())
    assert state["cash_usdc"] == 240.0  # 250 - 10
    bets = json.loads(bets_path.read_text())
    assert len(bets) == 1
