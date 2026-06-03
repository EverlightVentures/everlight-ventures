"""Polymarket executor exception hierarchy. Same names as executor_alpaca.py
so Phase 2 framework absorb is a file move, not a refactor."""


class PolymarketExecutorError(Exception):
    """Base for all executor errors. Carries context dict for branded Slack alerts."""

    def __init__(self, message: str, context: dict | None = None):
        super().__init__(message)
        self.context = context or {}


class UnauthorizedInstrumentError(PolymarketExecutorError):
    """Market is not in the active whitelist."""


class DollarCapExceededError(PolymarketExecutorError):
    """Order exceeds max_bet_pct * bankroll."""


class LiveTradingDisabledError(PolymarketExecutorError):
    """LIVE_TRADING is not true (config OR env)."""


class WalletReconciliationError(PolymarketExecutorError):
    """Internal accounting drifted from on-chain wallet."""


class KillSwitchActiveError(PolymarketExecutorError):
    """_state/HALT exists or EV_TRADER_HALT=true."""


class OnChainBalanceShortfallError(PolymarketExecutorError):
    """Wallet USDC balance < requested amount."""


class OrderRejectedByVenueError(PolymarketExecutorError):
    """Polymarket CLOB rejected the signed order."""
