import pytest
from polymarket_agent.execution.exceptions import (
    PolymarketExecutorError,
    UnauthorizedInstrumentError,
    DollarCapExceededError,
    LiveTradingDisabledError,
    WalletReconciliationError,
    KillSwitchActiveError,
    OnChainBalanceShortfallError,
    OrderRejectedByVenueError,
)


def test_all_inherit_from_base():
    for cls in [UnauthorizedInstrumentError, DollarCapExceededError,
                LiveTradingDisabledError, WalletReconciliationError,
                KillSwitchActiveError, OnChainBalanceShortfallError,
                OrderRejectedByVenueError]:
        assert issubclass(cls, PolymarketExecutorError)


def test_carries_context_dict():
    e = DollarCapExceededError("over cap", context={"requested": 100, "cap": 50})
    assert e.context["requested"] == 100
    assert e.context["cap"] == 50
