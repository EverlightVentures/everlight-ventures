from __future__ import annotations

import unittest
from datetime import datetime, timezone
from main import _evaluate_hard_risk_gates

class RiskGateTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "risk": {
                "max_daily_loss_pct": 0.05
            }
        }
        self.state = {
            "exchange_pnl_today_usd": 0.0,
            "pnl_today_usd": 0.0
        }
        self.recovery_info = {"mode": "NORMAL"}
        self.now = datetime.now(timezone.utc)
        self.equity_start = 1000.0

    def test_no_block_when_pnl_is_zero(self):
        reason = _evaluate_hard_risk_gates(self.config, self.state, 0.0, self.equity_start, self.recovery_info, self.now)
        self.assertIsNone(reason)

    def test_block_when_daily_loss_exceeded_exchange(self):
        self.state["exchange_pnl_today_usd"] = -51.0  # 5.1% loss
        reason = _evaluate_hard_risk_gates(self.config, self.state, 0.0, self.equity_start, self.recovery_info, self.now)
        self.assertEqual(reason, "entry_blocked_max_daily_loss")

    def test_block_when_daily_loss_exceeded_local_fallback(self):
        self.state["exchange_pnl_today_usd"] = 0.0
        pnl_today = -51.0
        reason = _evaluate_hard_risk_gates(self.config, self.state, pnl_today, self.equity_start, self.recovery_info, self.now)
        self.assertEqual(reason, "entry_blocked_max_daily_loss")

    def test_block_when_safe_mode(self):
        self.recovery_info["mode"] = "SAFE_MODE"
        reason = _evaluate_hard_risk_gates(self.config, self.state, 0.0, self.equity_start, self.recovery_info, self.now)
        self.assertEqual(reason, "entry_blocked_recovery_safe_mode")

    def test_disabled_gate_ignores_loss(self):
        self.config["risk"]["max_daily_loss_pct"] = 0.0
        self.state["exchange_pnl_today_usd"] = -100.0
        reason = _evaluate_hard_risk_gates(self.config, self.state, 0.0, self.equity_start, self.recovery_info, self.now)
        self.assertIsNone(reason)

if __name__ == "__main__":
    unittest.main()
