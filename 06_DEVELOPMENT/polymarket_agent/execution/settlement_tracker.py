"""
settlement_tracker.py

Recomputes daily_pnl_usdc in the bankroll state JSON by summing pnl_usdc
from closed_bets.json for bets settled on the target date.

This activates the daily-loss circuit breaker in executor + risk_manager,
which reads daily_pnl_usdc but previously had nothing writing it.
"""

import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional


def _today_utc() -> str:
    """Return current UTC date as YYYY-MM-DD string."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


class SettlementTracker:
    """
    Reads closed_bets.json, sums pnl_usdc for bets settled on `today`,
    and writes the result back to the bankroll state atomically.

    Parameters
    ----------
    state_path : Path
        Path to bankroll JSON file (paper_bankroll.json or bankroll.json).
    closed_bets_path : Path
        Path to closed_bets.json list file.
    today : str or None
        Injected date string "YYYY-MM-DD" for testability.
        Defaults to current UTC date if None.
    """

    def __init__(
        self,
        state_path: Path,
        closed_bets_path: Path,
        today: Optional[str] = None,
    ) -> None:
        self._state_path = Path(state_path)
        self._closed_bets_path = Path(closed_bets_path)
        self._today: str = today if today is not None else _today_utc()

    def recompute_daily_pnl(self) -> Decimal:
        """
        Recompute daily_pnl_usdc for today and persist it atomically.

        Returns
        -------
        Decimal
            Sum of pnl_usdc for bets settled today (may be negative).

        Raises
        ------
        json.JSONDecodeError
            If closed_bets file exists but contains invalid JSON.
            Fail-loud -- never silently swallow corrupt data.
        """
        # Step 1: Read current state.
        state = json.loads(self._state_path.read_text())

        # Step 2: If closed_bets file is missing, daily pnl is zero.
        if not self._closed_bets_path.exists():
            daily_pnl = Decimal("0")
        else:
            # Step 3: Read closed bets -- let JSONDecodeError propagate (fail loud).
            bets = json.loads(self._closed_bets_path.read_text())

            # Step 4: Sum pnl_usdc for bets settled today.
            daily_pnl = Decimal("0")
            for bet in bets:
                settled_date_str = bet.get("settled_date", "")
                # settled_date[:10] gives "YYYY-MM-DD" regardless of timezone suffix.
                if settled_date_str[:10] == self._today:
                    daily_pnl += Decimal(str(bet["pnl_usdc"]))

        # Step 5: Write back atomically via temp + os.replace.
        state["daily_pnl_usdc"] = float(daily_pnl)
        state["daily_pnl_date"] = self._today

        tmp_path = self._state_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(state, indent=2))
        os.replace(tmp_path, self._state_path)

        # Step 6: Return Decimal sum.
        return daily_pnl
