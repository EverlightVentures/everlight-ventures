from __future__ import annotations

import unittest
from datetime import datetime, timezone
from execution.coinbase_advanced import CoinbaseAdvanced
from main import _apply_expectancy_size_multiplier, _build_entry_preflight_snapshot, _build_smoke_check_preview, _compute_contract_ladder, _compute_contract_readiness, _compute_friday_break_risk, _compute_position_size, _evaluate_hard_risk_gates, _lane_specific_expectancy_multiplier, _materialize_pending_fill_position, _nontrade_slack_allowed, _resolve_margin_window_playbook, _score_weekly_research_modifier, _select_growth_ladder_stage
from market.orderbook_context import score_orderbook_modifier

class RiskGateTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "risk": {}
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

    def test_clears_stale_safe_mode_flags(self):
        self.state["_safe_mode"] = True
        self.state["safe_mode"] = True
        self.state["_safe_mode_reason"] = "hard_drawdown_cap: -$35.24 today >= cap $25.00"
        self.state["safe_mode_reason"] = "hard_drawdown_cap: -$35.24 today >= cap $25.00"
        reason = _evaluate_hard_risk_gates(self.config, self.state, 0.0, self.equity_start, self.recovery_info, self.now)
        self.assertIsNone(reason)
        self.assertNotIn("_safe_mode", self.state)
        self.assertNotIn("safe_mode", self.state)
        self.assertNotIn("_safe_mode_reason", self.state)
        self.assertNotIn("safe_mode_reason", self.state)

    def test_block_when_live_tick_dead(self):
        self.config["freshness_gates"] = {"enabled": True, "block_on_dead_tick": True}
        reason = _evaluate_hard_risk_gates(
            self.config,
            self.state,
            0.0,
            self.equity_start,
            self.recovery_info,
            self.now,
            pulse={"regime": "neutral", "components": {"tick_health": "dead"}},
            live_tick_age_sec=301.0,
        )
        self.assertEqual(reason, "entry_blocked_live_tick_dead")

    def test_block_when_market_brief_stale(self):
        self.config["freshness_gates"] = {
            "enabled": True,
            "block_on_stale_market_brief": True,
            "max_market_brief_age_min": 45,
        }
        reason = _evaluate_hard_risk_gates(
            self.config,
            self.state,
            0.0,
            self.equity_start,
            self.recovery_info,
            self.now,
            pulse={"regime": "neutral", "components": {"tick_health": "live", "brief_age_min": 61}},
            live_tick_age_sec=2.0,
        )
        self.assertEqual(reason, "entry_blocked_market_brief_stale")

    def test_block_when_pulse_danger(self):
        self.config["freshness_gates"] = {"enabled": True, "block_on_pulse_danger": True}
        reason = _evaluate_hard_risk_gates(
            self.config,
            self.state,
            0.0,
            self.equity_start,
            self.recovery_info,
            self.now,
            pulse={"regime": "danger", "components": {"tick_health": "live", "brief_age_min": 5}},
            live_tick_age_sec=5.0,
        )
        self.assertEqual(reason, "entry_blocked_market_pulse_danger")

    def test_daily_loss_no_longer_blocks(self):
        self.state["exchange_pnl_today_usd"] = -100.0
        reason = _evaluate_hard_risk_gates(self.config, self.state, 0.0, self.equity_start, self.recovery_info, self.now)
        self.assertIsNone(reason)


class GrowthLadderTests(unittest.TestCase):
    def setUp(self):
        self.ps_cfg = {
            "enabled": True,
            "base_risk_pct": 0.03,
            "max_risk_pct": 0.08,
            "min_contracts": 1,
            "max_contracts": "auto",
            "equity_per_contract": 180,
            "max_contracts_hard_cap": 5,
            "lane_budgets": {"V": 1.0},
            "tier_multipliers": {"FULL": 1.25},
            "growth_ladder": {
                "enabled": True,
                "stages": [
                    {"label": "BUILD_A", "max_equity": 750, "max_contracts": 1, "base_risk_pct": 0.025, "max_risk_pct": 0.04},
                    {"label": "BUILD_D", "max_equity": 5000, "max_contracts": 5, "base_risk_pct": 0.025, "max_risk_pct": 0.05},
                ],
            },
        }

    def test_select_growth_stage(self):
        stage = _select_growth_ladder_stage(self.ps_cfg, 400.0)
        self.assertEqual(stage.get("label"), "BUILD_A")

    def test_growth_ladder_caps_small_account_to_one_contract(self):
        contracts, meta = _compute_position_size(
            equity=400.0,
            price=0.16,
            stop_price=0.158,
            contract_size_val=5000.0,
            lane="V",
            quality_tier="FULL",
            consecutive_wins=0,
            consecutive_losses=0,
            ps_cfg=self.ps_cfg,
        )
        self.assertEqual(contracts, 1)
        self.assertEqual(meta.get("growth_stage_label"), "BUILD_A")
        self.assertEqual(meta.get("growth_stage_max_contracts"), 1)

    def test_growth_ladder_allows_more_contracts_when_equity_grows(self):
        contracts, meta = _compute_position_size(
            equity=3200.0,
            price=0.16,
            stop_price=0.1595,
            contract_size_val=5000.0,
            lane="V",
            quality_tier="FULL",
            consecutive_wins=1,
            consecutive_losses=0,
            ps_cfg=self.ps_cfg,
        )
        self.assertGreaterEqual(contracts, 2)
        self.assertEqual(meta.get("growth_stage_label"), "BUILD_D")


class LaneSpecificExpectancyTests(unittest.TestCase):
    def test_lane_w_promotes_when_profitable(self):
        mult, meta = _lane_specific_expectancy_multiplier(
            "W",
            {"W": {"count": 8, "win_rate": 0.625, "avg_pnl_usd": 18.5, "sharpe": 0.6}},
            {},
        )
        self.assertGreater(mult, 1.0)
        self.assertEqual(meta["lane_expectancy_mode"], "promote")

    def test_lane_w_reduces_when_cold(self):
        mult, meta = _lane_specific_expectancy_multiplier(
            "W",
            {"W": {"count": 8, "win_rate": 0.25, "avg_pnl_usd": -7.0, "sharpe": -0.4}},
            {},
        )
        self.assertLess(mult, 1.0)
        self.assertEqual(meta["lane_expectancy_mode"], "reduce")


class SlackModeTests(unittest.TestCase):
    def test_nontrade_slack_blocked_by_default(self):
        self.assertFalse(_nontrade_slack_allowed({"slack_alerts": {"trade_only_mode": True}}, {"open_position": False}))

    def test_nontrade_slack_allowed_when_in_trade(self):
        self.assertTrue(_nontrade_slack_allowed({"slack_alerts": {"trade_only_mode": True}}, {"open_position": True}))


class SmokeCheckTests(unittest.TestCase):
    class _FakeApi:
        def select_xlm_product(self, selector_cfg, direction="long"):
            return {"product_id": "XLP-20DEC30-CDE"}

        def get_product_details(self, product_id):
            return {"mid_market_price": "0.1660", "contract_size": "5000"}

        def estimate_required_margin(self, product_id, size, direction, price=None):
            px = float(price or 0.1660)
            return {"required_margin": round(px * 5000 * size / 4, 4), "margin_rate": 0.25, "notional": round(px * 5000 * size, 4)}

        def is_product_available(self, product_id):
            return True

        def get_spread_pct(self, product_id):
            return 0.0008

        def place_order_with_bracket(self, product_id, side, size, *, stop_loss=None, take_profit=None, paper=True, client_order_id=""):
            from execution.coinbase_advanced import OrderResult
            return OrderResult(True, "paper-order", "paper mode")

        def place_order(self, product_id, side, size, leverage, paper=True, client_order_id=""):
            from execution.coinbase_advanced import OrderResult
            return OrderResult(True, "paper-order", "paper mode")

    def test_smoke_check_builds_valid_long_bracket(self):
        cfg = {
            "selector": {},
            "leverage": 4,
            "data_product_id": "XLM-USD",
            "risk": {"smoke_check_stop_pct": 0.0025},
            "exits": {
                "attach_exchange_tp": True,
                "tp1_move": 0.30,
                "tp2_move": 0.60,
                "tp3_move": 1.00,
                "tp_full_close_if_single_contract": True,
            },
        }
        preview = _build_smoke_check_preview(cfg, self._FakeApi(), direction="long", size=1)
        self.assertTrue(preview.get("ok"))
        self.assertTrue(preview.get("bracket_valid"))
        self.assertEqual(preview.get("product_id"), "XLP-20DEC30-CDE")
        self.assertLess(preview.get("stop_loss"), preview.get("entry_price"))
        self.assertGreater(preview.get("take_profit"), preview.get("entry_price"))
        self.assertTrue(preview.get("protection", {}).get("exchange_tp_requested"))

    def test_entry_preflight_blocks_invalid_short_bracket(self):
        cfg = {"regime_gates": {"spread_max_pct": 0.0025}}
        snap = _build_entry_preflight_snapshot(
            cfg,
            self._FakeApi(),
            product_id="XLP-20DEC30-CDE",
            direction="short",
            size=1,
            entry_price=0.1660,
            stop_loss=0.1600,
            take_profit=0.1700,
            attach_exchange_tp=True,
        )
        self.assertFalse(snap.get("ok"))
        self.assertEqual(snap.get("reason"), "invalid_bracket_geometry")


class PendingFillRecoveryTests(unittest.TestCase):
    def test_materialize_pending_fill_position_restores_seed(self):
        pending_meta = {
            "open_position_seed": {
                "product_id": "XLP-20DEC30-CDE",
                "direction": "long",
                "size": 1,
                "entry_price": 0.1660,
                "entry_type": "liquidity_sweep",
                "protection_mode": "software_managed",
            }
        }
        restored = _materialize_pending_fill_position(pending_meta, fill_price=0.1664, fees_usd=1.25)
        self.assertIsInstance(restored, dict)
        self.assertEqual(restored.get("entry_price"), 0.1664)
        self.assertEqual(restored.get("entry_fees_usd"), 1.25)
        self.assertTrue(restored.get("entry_fill_verified"))
        self.assertTrue(restored.get("pending_fill_recovered"))


class MarginWindowPlaybookTests(unittest.TestCase):
    class _Decision:
        def __init__(self, metrics):
            self.metrics = metrics

    def setUp(self):
        self.config = {
            "margin_policy": {
                "playbook": {
                    "enabled": True,
                    "intraday": {
                        "label": "INTRADAY_ATTACK",
                        "objective": "press_A_plus_setups_and_close_before_cutoff",
                        "allow_multi_contract": True,
                        "max_new_contracts": 2,
                        "min_quality_for_multi_contract": "FULL",
                        "force_exit_before_cutoff": True,
                    },
                    "pre_cutoff": {
                        "label": "PRE_CUTOFF_DEFENSE",
                        "objective": "no_new_risk_manage_existing_position_and_be_flat_before_overnight",
                        "block_new_entries": True,
                        "max_new_contracts": 1,
                        "force_exit_before_cutoff": True,
                    },
                    "overnight": {
                        "label": "OVERNIGHT_DEFENSE",
                        "objective": "preserve_capital_trade_small_only_if_overnight_margin_is_safe",
                        "block_new_entries_if_not_safe": True,
                        "block_new_entries_when_safe": False,
                        "allow_multi_contract_when_safe": False,
                        "max_new_contracts_when_safe": 1,
                        "max_new_contracts_when_unsafe": 1,
                    },
                }
            }
        }

    def test_intraday_playbook_allows_multi_when_ready(self):
        guide = _resolve_margin_window_playbook(
            config=self.config,
            mp_decision=self._Decision({"margin_window": "intraday", "mins_to_cutoff": 120}),
            overnight_trading_ok=False,
            quality_tier="FULL",
            two_contract_ready={"ready": True, "reason": "ready"},
        )
        self.assertEqual(guide.get("label"), "INTRADAY_ATTACK")
        self.assertTrue(guide.get("allow_multi_contract"))
        self.assertEqual(guide.get("max_new_contracts"), 2)

    def test_pre_cutoff_playbook_blocks_new_entries(self):
        guide = _resolve_margin_window_playbook(
            config=self.config,
            mp_decision=self._Decision({"margin_window": "pre_cutoff", "mins_to_cutoff": 10}),
            overnight_trading_ok=True,
            quality_tier="MONSTER",
            two_contract_ready={"ready": True, "reason": "ready"},
        )
        self.assertTrue(guide.get("block_new_entries"))
        self.assertEqual(guide.get("max_new_contracts"), 1)

    def test_overnight_playbook_blocks_when_not_safe(self):
        guide = _resolve_margin_window_playbook(
            config=self.config,
            mp_decision=self._Decision({"margin_window": "overnight", "mins_to_cutoff": 600}),
            overnight_trading_ok=False,
            quality_tier="MONSTER",
            two_contract_ready={"ready": True, "reason": "ready"},
        )
        self.assertTrue(guide.get("block_new_entries"))
        self.assertFalse(guide.get("allow_multi_contract"))

    def test_unknown_margin_window_falls_back_to_schedule(self):
        guide = _resolve_margin_window_playbook(
            config=self.config,
            mp_decision=self._Decision({"margin_window": "unknown", "mins_to_cutoff": 600}),
            overnight_trading_ok=False,
            quality_tier="FULL",
            two_contract_ready={"ready": False, "reason": "growth_stage_caps_at_1"},
            now_utc=datetime(2026, 3, 16, 14, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(guide.get("label"), "INTRADAY_ATTACK")

    def test_friday_break_force_flat_overrides_playbook(self):
        guide = _resolve_margin_window_playbook(
            config=self.config,
            mp_decision=self._Decision({"margin_window": "intraday", "mins_to_cutoff": 180}),
            overnight_trading_ok=True,
            quality_tier="MONSTER",
            two_contract_ready={"ready": True, "reason": "ready"},
            friday_break={"enabled": True, "force_flat_now": True, "notes": ["flatten_before_exchange_break"]},
        )
        self.assertEqual(guide.get("label"), "FRIDAY_BREAK_FORCE_FLAT")
        self.assertTrue(guide.get("block_new_entries"))
        self.assertTrue(guide.get("force_flat_now"))


class ContractReadinessTests(unittest.TestCase):
    class _FakeApi:
        def estimate_required_margin(self, product_id, size, direction, price=None):
            px = float(price or 0.1660)
            return {"required_margin": round(px * 5000 * size / 4, 4), "margin_rate": 0.25, "notional": round(px * 5000 * size, 4)}

        def ensure_futures_margin(self, **kwargs):
            return True, {"futures_buying_power": 450.0}

    def test_two_contract_not_ready_when_growth_stage_caps_size(self):
        config = {
            "futures_funding": {"buffer_pct": 0.02, "currency": "USDC"},
            "position_sizing": {
                "growth_ladder": {
                    "enabled": True,
                    "stages": [
                        {"label": "BUILD_A", "max_equity": 750, "max_contracts": 1},
                        {"label": "BUILD_D", "max_equity": 5000, "max_contracts": 5},
                    ]
                },
                "readiness": {"two_contract_buffer_pct": 0.10},
            },
        }
        status = _compute_contract_readiness(
            self._FakeApi(),
            product_id="XLP-20DEC30-CDE",
            direction="long",
            config=config,
            state={},
            transfers_today=0.0,
            target_size=2,
            stage_equity=440.0,
        )
        self.assertFalse(status.get("ready"))
        self.assertEqual(status.get("reason"), "growth_stage_caps_at_1")

    def test_two_contract_ready_when_stage_and_buffer_pass(self):
        config = {
            "futures_funding": {"buffer_pct": 0.02, "currency": "USDC"},
            "position_sizing": {
                "growth_ladder": {
                    "enabled": True,
                    "stages": [
                        {"label": "BUILD_D", "max_equity": 5000, "max_contracts": 5},
                    ]
                },
                "readiness": {"two_contract_buffer_pct": 0.05},
            },
        }
        status = _compute_contract_readiness(
            self._FakeApi(),
            product_id="XLP-20DEC30-CDE",
            direction="long",
            config=config,
            state={},
            transfers_today=0.0,
            target_size=2,
            stage_equity=2000.0,
        )
        self.assertTrue(status.get("ready"))

    def test_contract_ladder_reports_multiple_sizes(self):
        config = {
            "futures_funding": {"buffer_pct": 0.02, "currency": "USDC"},
            "position_sizing": {
                "growth_ladder": {
                    "enabled": True,
                    "stages": [
                        {"label": "BUILD_D", "max_equity": 5000, "max_contracts": 5},
                    ]
                },
                "readiness": {"contract_buffer_pct": 0.05},
            },
        }
        ladder = _compute_contract_ladder(
            self._FakeApi(),
            product_id="XLP-20DEC30-CDE",
            direction="long",
            config=config,
            state={},
            transfers_today=0.0,
            stage_equity=2000.0,
        )
        self.assertIn("1", ladder)
        self.assertIn("2", ladder)
        self.assertIn("3", ladder)
        self.assertIn("5", ladder)
        self.assertTrue(ladder["1"].get("ready"))


class FridayBreakRiskTests(unittest.TestCase):
    def test_friday_break_prelock_detected(self):
        risk = _compute_friday_break_risk(
            config={"margin_policy": {"friday_break": {"enabled": True}}},
            now_utc=datetime(2026, 3, 13, 20, 15, tzinfo=timezone.utc),
        )
        self.assertTrue(risk.get("pre_break_lock"))
        self.assertEqual(risk.get("label"), "FRIDAY_BREAK_PRELOCK")

    def test_friday_break_active_detected(self):
        risk = _compute_friday_break_risk(
            config={"margin_policy": {"friday_break": {"enabled": True}}},
            now_utc=datetime(2026, 3, 13, 21, 30, tzinfo=timezone.utc),
        )
        self.assertTrue(risk.get("active"))
        self.assertEqual(risk.get("label"), "FRIDAY_BREAK_ACTIVE")


class MarginWindowTests(unittest.TestCase):
    def test_estimate_required_margin_uses_overnight_rate_when_active(self):
        api = CoinbaseAdvanced.__new__(CoinbaseAdvanced)
        api.get_current_margin_window = lambda: {"current_margin_window": "OVERNIGHT"}
        api.get_product_details = lambda product_id: {
            "price": "0.16",
            "future_product_details": {
                "contract_size": "5000",
                "intraday_margin_rate": {"long_margin_rate": "0.25", "short_margin_rate": "0.25"},
                "overnight_margin_rate": {"long_margin_rate": "0.52", "short_margin_rate": "0.52"},
            },
        }
        out = api.estimate_required_margin("XLP-20DEC30-CDE", size=1, direction="long")
        self.assertEqual(out.get("margin_window"), "overnight")
        self.assertAlmostEqual(out.get("required_margin"), 416.0, places=4)

    def test_estimate_required_margin_uses_intraday_rate_when_active(self):
        api = CoinbaseAdvanced.__new__(CoinbaseAdvanced)
        api.get_current_margin_window = lambda: {"current_margin_window": "INTRADAY"}
        api.get_product_details = lambda product_id: {
            "price": "0.16",
            "future_product_details": {
                "contract_size": "5000",
                "intraday_margin_rate": {"long_margin_rate": "0.25", "short_margin_rate": "0.25"},
                "overnight_margin_rate": {"long_margin_rate": "0.52", "short_margin_rate": "0.52"},
            },
        }
        out = api.estimate_required_margin("XLP-20DEC30-CDE", size=1, direction="long")
        self.assertEqual(out.get("margin_window"), "intraday")
        self.assertAlmostEqual(out.get("required_margin"), 200.0, places=4)


class ConvertFlowTests(unittest.TestCase):
    def test_convert_usd_to_usdc_uses_account_based_quote_and_commit(self):
        api = CoinbaseAdvanced.__new__(CoinbaseAdvanced)

        class _Inner:
            def get_account_by_currency(self, currency):
                return {"uuid": f"{currency.lower()}-uuid", "currency": currency, "default": True}

            def create_convert_quote(self, from_account, to_account, amount):
                return {"trade_id": "trade-123", "from_account": from_account, "to_account": to_account, "amount": str(amount)}

            def commit_convert_trade(self, trade_id, from_account, to_account):
                return {"success": True, "trade_id": trade_id, "from_account": from_account, "to_account": to_account}

        api.api = _Inner()
        out = api.convert_usd_to_usdc(25.0)
        self.assertTrue(out.get("ok"))
        self.assertEqual(out.get("reason"), "convert_committed")
        self.assertEqual(out.get("trade_id"), "trade-123")
        self.assertEqual(out.get("from_account"), "usd-uuid")
        self.assertEqual(out.get("to_account"), "usdc-uuid")


class ExpectancyPromotionTests(unittest.TestCase):
    def test_promotes_size_when_edge_is_material(self):
        size, meta = _apply_expectancy_size_multiplier(1, 1.2, {"promotion_min_size_mult": 1.15})
        self.assertEqual(size, 2)
        self.assertEqual(meta.get("expectancy_mode"), "promote")

    def test_holds_size_when_edge_is_marginal(self):
        size, meta = _apply_expectancy_size_multiplier(1, 1.05, {"promotion_min_size_mult": 1.15})
        self.assertEqual(size, 1)
        self.assertEqual(meta.get("expectancy_mode"), "hold")


class WeeklyResearchModifierTests(unittest.TestCase):
    def test_bullish_weekly_research_supports_longs(self):
        bonus, reasons = _score_weekly_research_modifier(
            "long",
            {
                "directional_bias": "bullish",
                "xlm_bias": "bullish",
                "macro_regime": "neutral",
                "confidence": 0.72,
                "window_label": "MONDAY_OPENING_BIAS",
            },
            {"market_intel": {"weekly_research": {"enabled": True, "score_bonus_max": 3, "min_confidence": 0.45}}},
        )
        self.assertGreater(bonus, 0)
        self.assertIn("weekly_xlm_bias_bullish", reasons)


class OrderBookModifierTests(unittest.TestCase):
    def test_bid_absorption_supports_longs(self):
        result = score_orderbook_modifier(
            "long",
            {
                "depth_bias": "BID_HEAVY",
                "imbalance_ratio": 0.63,
                "spread_bps": 2.1,
                "absorption_bias": "BID_ABSORBING",
                "bid_replenishment_ratio": 1.08,
                "ask_replenishment_ratio": 0.72,
                "spoof_risk": 0.15,
                "spoof_side": "NONE",
                "depth_flip": True,
            },
            {"bonus_max": 4},
        )
        self.assertGreater(result.bonus, 0)
        self.assertTrue(any("absorption" in reason for reason in result.reasons))

    def test_spoof_risk_penalizes_trade(self):
        result = score_orderbook_modifier(
            "long",
            {
                "depth_bias": "BALANCED",
                "imbalance_ratio": 0.51,
                "spread_bps": 1.8,
                "absorption_bias": "NEUTRAL",
                "bid_replenishment_ratio": 0.88,
                "ask_replenishment_ratio": 0.92,
                "spoof_risk": 0.82,
                "spoof_side": "ASK",
                "depth_flip": False,
            },
            {"bonus_max": 4, "spoof_penalty": 2},
        )
        self.assertLess(result.bonus, 0)
        self.assertTrue(any("spoof" in reason for reason in result.reasons))

if __name__ == "__main__":
    unittest.main()
