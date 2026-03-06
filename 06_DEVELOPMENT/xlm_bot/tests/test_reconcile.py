from __future__ import annotations

import unittest
from datetime import datetime, timezone

from risk.reconcile import reconcile_exchange_truth


class _FakeAPI:
    def __init__(self, positions=None):
        self._positions = positions or []

    def select_xlm_product(self, selector_cfg: dict, direction: str = "long") -> dict | None:
        return {"product_id": "XLP-20DEC30-CDE"}

    def get_futures_positions(self):
        return list(self._positions)

    def get_open_orders(self):
        return []

    def get_product_details(self, product_id: str):
        return {"future_product_details": {"contract_size": "5000"}}


class ReconcileTests(unittest.TestCase):
    def test_reconstructs_local_position_from_exchange(self):
        api = _FakeAPI(
            positions=[
                {
                    "product_id": "XLP-20DEC30-CDE",
                    "number_of_contracts": "2",
                    "side": "LONG",
                    "avg_entry_price": "0.156",
                    "leverage": "4",
                }
            ]
        )
        state = {
            "day": "2026-02-11",
            "trades": 0,
            "losses": 0,
            "pnl_today_usd": 0.0,
            "transfers_today_usd": 0.0,
            "equity_start_usd": 100.0,
        }
        out = reconcile_exchange_truth(
            api,
            {"product_id": "XLP-20DEC30-CDE", "leverage": 4},
            state,
            None,
            now=datetime(2026, 2, 11, 12, 0, tzinfo=timezone.utc),
            mark_price=0.157,
        )
        self.assertTrue(out.repaired)
        self.assertIsNone(out.closed_trade)
        self.assertIsInstance(out.state.get("open_position"), dict)
        self.assertEqual(out.state["open_position"]["product_id"], "XLP-20DEC30-CDE")
        self.assertEqual(out.state["open_position"]["size"], 2)

    def test_closes_local_position_when_exchange_flat(self):
        api = _FakeAPI(positions=[])
        state = {
            "day": "2026-02-11",
            "trades": 0,
            "losses": 0,
            "pnl_today_usd": 0.0,
            "transfers_today_usd": 0.0,
            "equity_start_usd": 100.0,
            "open_position": {
                "product_id": "XLP-20DEC30-CDE",
                "entry_time": "2026-02-11T11:00:00+00:00",
                "entry_price": 0.155,
                "direction": "long",
                "size": 1,
                "leverage": 4,
                "contract_size": 5000.0,
            },
        }
        out = reconcile_exchange_truth(
            api,
            {"product_id": "XLP-20DEC30-CDE", "leverage": 4},
            state,
            None,
            now=datetime(2026, 2, 11, 12, 0, tzinfo=timezone.utc),
            mark_price=0.153,
        )
        self.assertTrue(out.repaired)
        self.assertIsNotNone(out.closed_trade)
        self.assertIsNone(out.state.get("open_position"))
        self.assertEqual(out.closed_trade["exit_reason"], "exchange_side_close")
        self.assertEqual(out.state["losses"], 1)


if __name__ == "__main__":
    unittest.main()
