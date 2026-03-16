"""Exchange state synchronization validator -- Score 10 upgrade.

Runs BEFORE every cycle. Verifies local bot state matches exchange reality.
Mismatch triggers emergency flatten + halt to prevent phantom positions.

Hive Mind Finding (11_sync_coordinator):
  "The bot thinks it is flat and safe, but actually holds a max-leverage
   short during a market pump."

Usage
-----
from risk.state_sync import StateSyncChecker, SyncResult

checker = StateSyncChecker(cb_client, state_store)
result = checker.verify(local_state)
if result.mismatch:
    # HALT -- emergency flatten required
    ...
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    ok: bool
    mismatch: bool
    local_side: str | None         # "LONG" | "SHORT" | "FLAT"
    exchange_side: str | None      # "LONG" | "SHORT" | "FLAT"
    local_contracts: int
    exchange_contracts: int
    delta_contracts: int           # exchange - local (negative = orphaned position)
    action_required: str           # "PROCEED" | "FLATTEN" | "RECONCILE" | "SKIP_API_DOWN"
    notes: list[str] = field(default_factory=list)
    raw_exchange: dict = field(default_factory=dict)


class StateSyncChecker:
    """Pre-cycle exchange position reconciler.

    Compares local bot state (state.json) against live Coinbase CDE
    position API.  Detects:
      - Phantom positions (bot flat, exchange has open position)
      - Missing position (bot thinks long, exchange is flat)
      - Size drift (contracts differ)

    Action matrix:
      PROCEED       -- states match, safe to continue
      FLATTEN       -- mismatch detected, close all and halt
      RECONCILE     -- contracts differ but side matches (partial fill, etc.)
      SKIP_API_DOWN -- exchange API unreachable, use local state (warn only)
    """

    def __init__(self, cb_client: Any, state_store: Any, product_id: str = "XLP-20DEC30-CDE"):
        self._cb = cb_client
        self._store = state_store
        self._product = product_id
        self._last_check_ts: datetime | None = None

    def _fetch_exchange_position(self) -> tuple[str | None, int, dict]:
        """Query CDE for current open position. Returns (side, contracts, raw)."""
        try:
            # CoinbaseAdvanced list_futures_positions
            raw = self._cb.list_futures_positions() or {}
            positions = raw.get("positions") or []
            for pos in positions:
                if str(pos.get("product_id", "")).upper() == self._product.upper():
                    side = str(pos.get("side", "")).upper()   # "LONG" | "SHORT"
                    qty = abs(int(float(pos.get("number_of_contracts", 0) or 0)))
                    return side if qty > 0 else "FLAT", qty, pos
            return "FLAT", 0, {}
        except Exception as e:
            logger.warning("state_sync: exchange API error: %s", e)
            return None, 0, {"error": str(e)}

    def _local_side(self, local_state: dict) -> tuple[str, int]:
        """Extract side + contracts from local state dict."""
        position = local_state.get("position") or {}
        if not position or not position.get("active"):
            return "FLAT", 0

        direction = str(position.get("direction", "")).upper()
        contracts = int(position.get("contracts", 0) or 0)

        side = "LONG" if "LONG" in direction else ("SHORT" if "SHORT" in direction else "FLAT")
        if contracts <= 0:
            side = "FLAT"
        return side, contracts

    def verify(self, local_state: dict | None = None) -> SyncResult:
        """Perform sync check. Returns SyncResult with action_required."""
        local_state = local_state or {}
        local_side, local_qty = self._local_side(local_state)
        self._last_check_ts = datetime.now(timezone.utc)

        # Fetch exchange truth
        exch_side, exch_qty, raw = self._fetch_exchange_position()

        # API down -- degrade gracefully
        if exch_side is None:
            return SyncResult(
                ok=False,
                mismatch=False,
                local_side=local_side,
                exchange_side=None,
                local_contracts=local_qty,
                exchange_contracts=0,
                delta_contracts=0,
                action_required="SKIP_API_DOWN",
                notes=["exchange_api_unreachable_use_local"],
                raw_exchange=raw,
            )

        # Both flat -- clean
        if local_side == "FLAT" and exch_side == "FLAT":
            return SyncResult(
                ok=True,
                mismatch=False,
                local_side="FLAT",
                exchange_side="FLAT",
                local_contracts=0,
                exchange_contracts=0,
                delta_contracts=0,
                action_required="PROCEED",
                notes=["both_flat"],
            )

        # Side mismatch -- critical
        if local_side != exch_side:
            notes = [
                f"CRITICAL_MISMATCH: local={local_side}({local_qty}) "
                f"exchange={exch_side}({exch_qty})"
            ]
            logger.critical("STATE_SYNC MISMATCH: %s", notes[0])
            return SyncResult(
                ok=False,
                mismatch=True,
                local_side=local_side,
                exchange_side=exch_side,
                local_contracts=local_qty,
                exchange_contracts=exch_qty,
                delta_contracts=exch_qty - local_qty,
                action_required="FLATTEN",
                notes=notes,
                raw_exchange=raw,
            )

        # Same side -- check contract count
        delta = exch_qty - local_qty
        if abs(delta) > 0:
            notes = [f"contract_drift: local={local_qty} exchange={exch_qty} delta={delta}"]
            logger.warning("state_sync: %s", notes[0])
            return SyncResult(
                ok=False,
                mismatch=False,
                local_side=local_side,
                exchange_side=exch_side,
                local_contracts=local_qty,
                exchange_contracts=exch_qty,
                delta_contracts=delta,
                action_required="RECONCILE",
                notes=notes,
                raw_exchange=raw,
            )

        # Perfect match
        return SyncResult(
            ok=True,
            mismatch=False,
            local_side=local_side,
            exchange_side=exch_side,
            local_contracts=local_qty,
            exchange_contracts=exch_qty,
            delta_contracts=0,
            action_required="PROCEED",
            notes=[f"synced: {local_side}({local_qty})"],
            raw_exchange=raw,
        )

    def log_to_store(self, result: SyncResult) -> None:
        """Persist sync result to state store for dashboard + audit."""
        if self._store is None:
            return
        try:
            self._store.set_kv("state_sync_last", {
                "ts": self._last_check_ts.isoformat() if self._last_check_ts else None,
                "ok": result.ok,
                "mismatch": result.mismatch,
                "action": result.action_required,
                "local_side": result.local_side,
                "exchange_side": result.exchange_side,
                "local_contracts": result.local_contracts,
                "exchange_contracts": result.exchange_contracts,
                "notes": result.notes,
            })
        except Exception as e:
            logger.warning("state_sync: store write failed: %s", e)
