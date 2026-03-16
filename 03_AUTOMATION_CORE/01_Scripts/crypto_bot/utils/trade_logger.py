#!/usr/bin/env python3
"""
Trade Logger - Persistent trade history and P&L tracking
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import csv


class TradeLogger:
    """
    Logs all trades to JSON and CSV for history tracking
    """

    def __init__(self, log_dir: str = None):
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = Path(__file__).parent.parent / "logs"

        self.log_dir.mkdir(exist_ok=True)

        self.trades_file = self.log_dir / "trade_history.json"
        self.csv_file = self.log_dir / "trade_history.csv"
        self.daily_file = self.log_dir / "daily_pnl.json"

        # Initialize files if they don't exist
        if not self.trades_file.exists():
            self._save_trades([])

        if not self.daily_file.exists():
            self._save_daily({})

    def _load_trades(self) -> List[Dict]:
        """Load trade history"""
        try:
            with open(self.trades_file) as f:
                return json.load(f)
        except:
            return []

    def _save_trades(self, trades: List[Dict]):
        """Save trade history"""
        with open(self.trades_file, "w") as f:
            json.dump(trades, f, indent=2, default=str)

    def _load_daily(self) -> Dict:
        """Load daily P&L"""
        try:
            with open(self.daily_file) as f:
                return json.load(f)
        except:
            return {}

    def _save_daily(self, daily: Dict):
        """Save daily P&L"""
        with open(self.daily_file, "w") as f:
            json.dump(daily, f, indent=2)

    def log_entry(self, trade_id: str, pair: str, side: str, entry_price: float,
                  size_usd: float, leverage: float, stop_loss: float,
                  take_profit: float, strategy: str,
                  liquidation_price: float = None) -> Dict:
        """Log a trade entry with liquidation tracking"""
        # Calculate liquidation price if not provided
        if liquidation_price is None and leverage > 1:
            if side == "buy":
                liquidation_price = entry_price * (1 - 1/leverage)
            else:
                liquidation_price = entry_price * (1 + 1/leverage)

        trade = {
            "id": trade_id,
            "pair": pair,
            "side": side,
            "entry_time": datetime.now().isoformat(),
            "entry_price": entry_price,
            "size_usd": size_usd,
            "leverage": leverage,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "strategy": strategy,
            "status": "OPEN",
            # Liquidation tracking fields
            "liquidation_price": round(liquidation_price, 2) if liquidation_price else None,
            "initial_margin": size_usd,
            "margin_topups": 0,
            "total_margin_added": 0.0,
            # Exit fields
            "exit_time": None,
            "exit_price": None,
            "exit_reason": None,
            "pnl_usd": None,
            "pnl_percent": None
        }

        trades = self._load_trades()
        trades.append(trade)
        self._save_trades(trades)

        self._append_csv(trade)

        return trade

    def log_exit(self, trade_id: str, exit_price: float, exit_reason: str) -> Optional[Dict]:
        """Log a trade exit and calculate P&L"""
        trades = self._load_trades()

        for trade in trades:
            if trade["id"] == trade_id and trade["status"] == "OPEN":
                trade["exit_time"] = datetime.now().isoformat()
                trade["exit_price"] = exit_price
                trade["exit_reason"] = exit_reason
                trade["status"] = "CLOSED"

                # Calculate P&L
                if trade["side"] == "buy":
                    pnl_percent = (exit_price - trade["entry_price"]) / trade["entry_price"]
                else:
                    pnl_percent = (trade["entry_price"] - exit_price) / trade["entry_price"]

                # Apply leverage
                pnl_percent *= trade["leverage"]

                # Calculate USD P&L
                pnl_usd = trade["size_usd"] * pnl_percent

                trade["pnl_percent"] = round(pnl_percent * 100, 2)
                trade["pnl_usd"] = round(pnl_usd, 2)

                self._save_trades(trades)
                self._update_daily_pnl(pnl_usd)
                self._append_csv(trade)

                return trade

        return None

    def update_margin_addition(self, trade_id: str, amount: float,
                               new_liquidation_price: float = None) -> Optional[Dict]:
        """
        Update trade record with margin addition

        Args:
            trade_id: Trade ID to update
            amount: Amount of margin added (USD)
            new_liquidation_price: Recalculated liquidation price after margin addition

        Returns:
            Updated trade dict or None if not found
        """
        trades = self._load_trades()

        for trade in trades:
            if trade["id"] == trade_id and trade["status"] == "OPEN":
                # Update margin tracking
                trade["margin_topups"] = trade.get("margin_topups", 0) + 1
                trade["total_margin_added"] = trade.get("total_margin_added", 0) + amount

                # Update liquidation price if provided
                if new_liquidation_price:
                    trade["liquidation_price"] = round(new_liquidation_price, 2)

                self._save_trades(trades)
                return trade

        return None

    def get_trade(self, trade_id: str) -> Optional[Dict]:
        """Get a specific trade by ID"""
        trades = self._load_trades()
        for trade in trades:
            if trade["id"] == trade_id:
                return trade
        return None

    def _update_daily_pnl(self, pnl: float):
        """Update daily P&L tracking"""
        daily = self._load_daily()
        today = datetime.now().strftime("%Y-%m-%d")

        if today not in daily:
            daily[today] = {"pnl": 0, "trades": 0, "wins": 0, "losses": 0}

        daily[today]["pnl"] += pnl
        daily[today]["trades"] += 1

        if pnl > 0:
            daily[today]["wins"] += 1
        else:
            daily[today]["losses"] += 1

        self._save_daily(daily)

    def _append_csv(self, trade: Dict):
        """Append trade to CSV"""
        file_exists = self.csv_file.exists()

        with open(self.csv_file, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "id", "pair", "side", "entry_time", "entry_price",
                "size_usd", "leverage", "stop_loss", "take_profit",
                "strategy", "status", "liquidation_price", "initial_margin",
                "margin_topups", "total_margin_added", "exit_time", "exit_price",
                "exit_reason", "pnl_usd", "pnl_percent"
            ])

            if not file_exists:
                writer.writeheader()

            writer.writerow(trade)

    def get_open_trades(self) -> List[Dict]:
        """Get all open trades"""
        trades = self._load_trades()
        return [t for t in trades if t["status"] == "OPEN"]

    def get_closed_trades(self, limit: int = 50) -> List[Dict]:
        """Get closed trades"""
        trades = self._load_trades()
        closed = [t for t in trades if t["status"] == "CLOSED"]
        return sorted(closed, key=lambda x: x["exit_time"] or "", reverse=True)[:limit]

    def get_all_trades(self) -> List[Dict]:
        """Get all trades"""
        return self._load_trades()

    def get_daily_pnl(self) -> Dict:
        """Get daily P&L history"""
        return self._load_daily()

    def get_today_stats(self) -> Dict:
        """Get today's stats"""
        daily = self._load_daily()
        today = datetime.now().strftime("%Y-%m-%d")

        if today in daily:
            return daily[today]

        return {"pnl": 0, "trades": 0, "wins": 0, "losses": 0}

    def get_total_stats(self) -> Dict:
        """Get all-time stats"""
        trades = self._load_trades()
        closed = [t for t in trades if t["status"] == "CLOSED"]

        if not closed:
            return {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "best_trade": 0,
                "worst_trade": 0
            }

        wins = [t for t in closed if t["pnl_usd"] and t["pnl_usd"] > 0]
        losses = [t for t in closed if t["pnl_usd"] and t["pnl_usd"] <= 0]

        total_pnl = sum(t["pnl_usd"] or 0 for t in closed)
        pnls = [t["pnl_usd"] for t in closed if t["pnl_usd"] is not None]

        return {
            "total_trades": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / len(closed) * 100 if closed else 0,
            "total_pnl": total_pnl,
            "avg_win": sum(t["pnl_usd"] for t in wins) / len(wins) if wins else 0,
            "avg_loss": sum(t["pnl_usd"] for t in losses) / len(losses) if losses else 0,
            "best_trade": max(pnls) if pnls else 0,
            "worst_trade": min(pnls) if pnls else 0
        }

    def clear_history(self):
        """Clear all trade history (use with caution!)"""
        self._save_trades([])
        self._save_daily({})
        if self.csv_file.exists():
            self.csv_file.unlink()


# Test
if __name__ == "__main__":
    logger = TradeLogger()

    # Log a test trade
    trade = logger.log_entry(
        trade_id="test_001",
        pair="BTC-USD",
        side="buy",
        entry_price=84000,
        size_usd=1000,
        leverage=4,
        stop_loss=83500,
        take_profit=85000,
        strategy="trend_follow"
    )
    print(f"Entry logged: {trade['id']}")

    # Close it
    closed = logger.log_exit("test_001", 84800, "take_profit")
    print(f"Exit logged: P&L = ${closed['pnl_usd']}")

    # Get stats
    stats = logger.get_total_stats()
    print(f"Total stats: {stats}")
