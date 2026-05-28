"""Live Polymarket executor. 9 pre-checks in fixed order before any network call.
LLM proposes; this layer disposes."""
import json
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

from polymarket_agent.execution.exceptions import (
    LiveTradingDisabledError, KillSwitchActiveError, UnauthorizedInstrumentError,
    DollarCapExceededError, OnChainBalanceShortfallError, OrderRejectedByVenueError,
    PolymarketExecutorError,
)


@dataclass
class BetRequest:
    market_id: str
    outcome: str
    amount_usdc: Decimal
    limit_price: Decimal
    predicted_prob: float = 0.0
    edge: float = 0.0


@dataclass
class Bet:
    id: str
    market_id: str
    outcome: str
    amount_usdc: str
    limit_price: str
    timestamp: str
    status: str = "open"
    pnl_usdc: str = "0.0"


class PolymarketExecutor:
    def __init__(self, wallet, clob, config: dict,
                 bankroll_state_path: Path, halt_path: Path, open_bets_path: Path):
        self.wallet = wallet
        self.clob = clob
        self.config = config
        self.bankroll_state_path = Path(bankroll_state_path)
        self.halt_path = Path(halt_path)
        self.open_bets_path = Path(open_bets_path)

    def _read_state(self) -> dict:
        return json.loads(self.bankroll_state_path.read_text())

    def _read_open_bets(self) -> list:
        if not self.open_bets_path.exists():
            return []
        try:
            return json.loads(self.open_bets_path.read_text())
        except json.JSONDecodeError as e:
            raise PolymarketExecutorError(
                f"open_bets ledger corrupted at {self.open_bets_path}",
                context={"error": str(e)[:200]},
            ) from e

    def _append_open_bet(self, bet: Bet):
        bets = self._read_open_bets()
        bets.append(asdict(bet))
        tmp = self.open_bets_path.with_suffix(self.open_bets_path.suffix + ".tmp")
        tmp.write_text(json.dumps(bets, indent=2))
        os.replace(tmp, self.open_bets_path)

    def submit_order(self, req: BetRequest) -> Bet:
        # I4: type-guard amount_usdc and limit_price
        if not isinstance(req.amount_usdc, Decimal):
            raise PolymarketExecutorError(
                f"amount_usdc must be Decimal, got {type(req.amount_usdc).__name__}",
                context={"received_type": type(req.amount_usdc).__name__},
            )
        if not isinstance(req.limit_price, Decimal):
            raise PolymarketExecutorError(
                f"limit_price must be Decimal, got {type(req.limit_price).__name__}",
                context={"received_type": type(req.limit_price).__name__},
            )

        # CHECK 1: LIVE_TRADING (config AND env)
        if not self.config.get("live_trading_enabled", False):
            raise LiveTradingDisabledError(
                "config.live_trading.enabled is false",
                context={"config_enabled": False},
            )
        if os.environ.get("LIVE_TRADING", "").lower() != "true":
            raise LiveTradingDisabledError(
                "env LIVE_TRADING != true",
                context={"env_LIVE_TRADING": os.environ.get("LIVE_TRADING", "")},
            )

        # CHECK 2: HALT flag file
        if self.halt_path.exists():
            try:
                halt_data = json.loads(self.halt_path.read_text())
            except json.JSONDecodeError:
                halt_data = {}
            raise KillSwitchActiveError(
                f"halt flag at {self.halt_path}",
                context={"halt_data": halt_data},
            )

        # CHECK 3: EV_TRADER_HALT env
        if os.environ.get("EV_TRADER_HALT", "").lower() == "true":
            raise KillSwitchActiveError(
                "env EV_TRADER_HALT=true",
                context={"env_EV_TRADER_HALT": "true"},
            )

        # CHECK 4: market in active whitelist
        if "active_whitelist" not in self.config:
            raise PolymarketExecutorError(
                "config missing required key: active_whitelist",
                context={"config_keys": list(self.config.keys())},
            )
        whitelist = self.config["active_whitelist"]
        if req.market_id not in whitelist:
            raise UnauthorizedInstrumentError(
                f"market {req.market_id} not in active whitelist",
                context={"market_id": req.market_id, "whitelist_size": len(whitelist)},
            )

        # CHECK 5: amount <= max_bet_pct * bankroll
        state = self._read_state()
        bankroll = Decimal(str(state.get("cash_usdc") or 0))
        max_bet = bankroll * Decimal(str(self.config["max_bet_pct"])) / Decimal("100")
        if req.amount_usdc > max_bet:
            raise DollarCapExceededError(
                f"amount {req.amount_usdc} > max_bet {max_bet}",
                context={"amount": str(req.amount_usdc), "cap": str(max_bet),
                         "bankroll": str(bankroll)},
            )

        # CHECK 6: open_positions < max_concurrent
        open_bets = self._read_open_bets()
        if len(open_bets) >= self.config["max_open_positions"]:
            raise DollarCapExceededError(
                f"open positions {len(open_bets)} >= max {self.config['max_open_positions']}",
                context={"open": len(open_bets)},
            )

        # CHECK 7: daily_pnl > -max_daily_loss
        daily_pnl = Decimal(str(state.get("daily_pnl_usdc") or 0))
        max_daily_loss = bankroll * Decimal(str(self.config["max_daily_loss_pct"])) / Decimal("100") * Decimal("-1")
        if daily_pnl < max_daily_loss:
            raise KillSwitchActiveError(
                f"daily P&L {daily_pnl} < max loss {max_daily_loss}",
                context={"daily_pnl": str(daily_pnl), "max_loss": str(max_daily_loss)},
            )

        # CHECK 8: on-chain USDC >= amount
        on_chain = self.wallet.get_usdc_balance()
        if on_chain < req.amount_usdc:
            raise OnChainBalanceShortfallError(
                f"on-chain USDC {on_chain} < amount {req.amount_usdc}",
                context={"on_chain": str(on_chain), "amount": str(req.amount_usdc)},
            )

        # CHECK 9: sign + submit + record
        typed_data = self._build_eip712(req)
        signature = self.wallet.sign_clob_order(typed_data)

        # I3: Re-check HALT just before commit -- close the window where reconciler
        # could have detected drift and written HALT during the in-flight checks
        if self.halt_path.exists():
            raise KillSwitchActiveError(
                "HALT appeared during pre-flight -- aborting",
                context={"phase": "pre_submit_recheck", "market_id": req.market_id},
            )

        try:
            order_id = self.clob.submit_order({"typed_data": typed_data, "signature": signature})
        except Exception as e:
            raise OrderRejectedByVenueError(
                "CLOB rejected order",
                context={"market_id": req.market_id, "exception_type": type(e).__name__,
                         "error": str(e)[:200]},
            ) from e

        # I5: guard empty order_id from CLOB
        if not order_id or not isinstance(order_id, str):
            raise OrderRejectedByVenueError(
                "CLOB returned empty or invalid order_id",
                context={"market_id": req.market_id, "returned": repr(order_id)},
            )

        bet = Bet(
            id=order_id, market_id=req.market_id, outcome=req.outcome,
            amount_usdc=str(req.amount_usdc), limit_price=str(req.limit_price),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        # C2: wrap ledger write -- if it fails after a live order, HALT immediately
        try:
            self._append_open_bet(bet)
        except Exception as e:
            # Order is live but ledger write failed -- HALT immediately
            self.halt_path.write_text(json.dumps({
                "reason": "ledger_write_failed_post_submit",
                "order_id": order_id,
                "market_id": req.market_id,
                "error": str(e)[:200],
                "ts": datetime.now(timezone.utc).isoformat(),
            }, indent=2))
            raise PolymarketExecutorError(
                "ledger write failed AFTER order submitted -- HALTED",
                context={"order_id": order_id, "market_id": req.market_id},
            ) from e
        return bet

    def _build_eip712(self, req: BetRequest) -> dict:
        """Polymarket CLOB EIP-712 typed-data structure.

        Phase F wires py-clob-client which builds the real EIP-712 Order envelope
        with domain 'Polymarket CTF Exchange', primaryType 'Order', chainId 137,
        plus salt/maker/signer/taker/tokenId/makerAmount/takerAmount/expiration/
        nonce/feeRateBps/side/signatureType fields.

        The stub below is INTENTIONALLY unusable for real signing -- wallet.py
        will reject any dict missing types/primaryType/domain/message at sign time,
        which is the desired fail-loud behavior until py-clob-client integration.
        """
        raise NotImplementedError(
            "EIP-712 builder is Phase F work -- py-clob-client integration required "
            "before live signing. Executor scaffolding is paper-trade-ready only."
        )
