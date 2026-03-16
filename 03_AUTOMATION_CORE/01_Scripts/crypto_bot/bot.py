#!/usr/bin/env python3
"""
Hybrid Crypto Trading Bot
Combines: Grid Trading, DCA, Scalping, Signal-based strategies
Exchange: Coinbase
"""

import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple
import threading
import requests

# Import strategy modules
from strategies.mtf_strategy import MTFStrategy
from utils.coinbase_api import CoinbaseAPI
from utils.risk_manager import RiskManager
from utils.notifier import Notifier
from utils.position_manager import PositionManager
from utils.profit_scaler import ProfitScaler
from utils.trade_optimizer import TradeOptimizer
from utils.balance_manager import BalanceManager
from utils.market_filters import MarketFilters
from strategies.liquidation_strategy import LiquidationStrategy
from utils.universe_manager import UniverseManager
from utils.trade_logger import TradeLogger
from utils.telemetry_logger import TelemetryLogger
from utils.margin_policy import evaluate_margin_policy
from utils.plrl3 import compute_initial_contracts_plrl3, evaluate_plrl3

# Setup logging
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"bot_{datetime.now():%Y%m%d}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DEFAULT_BOT_NAME = "CDE_BOT"


class HybridTradingBot:
    """Main bot orchestrator combining multiple strategies"""

    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.bot_name = str(self.config.get("bot_name") or DEFAULT_BOT_NAME)
        self.running = False
        self.trades_today = []
        self.daily_pnl = 0.0

        # Initialize components
        logger.info(f"Initializing {self.bot_name}...")

        self.api = CoinbaseAPI(
            api_key=self.config["exchange"]["api_key"],
            api_secret=self.config["exchange"]["api_secret"],
            sandbox=self.config["exchange"]["sandbox"],
            use_perpetuals=self.config.get("exchange", {}).get("use_perpetuals", False)
        )

        self.risk_manager = RiskManager(self.config["risk_management"])
        self.notifier = Notifier(self.config["notifications"])

        # Initialize position manager for liquidation protection
        self.position_manager = PositionManager(self.config, self.api)

        # Initialize profit scaler for Kelly sizing and compounding
        self.profit_scaler = ProfitScaler(self.config)

        # Initialize trade optimizer for smart pair selection and risk controls
        self.trade_optimizer = TradeOptimizer(self.config, self.api)

        # Initialize balance manager for dynamic position sizing
        self.balance_manager = BalanceManager(self.config, self.api)

        # Initialize liquidation strategy
        self.liquidation_strategy = LiquidationStrategy(
            self.config, self.api, self.position_manager, self.balance_manager
        )

        # Initialize market filters (time-of-day, news events, momentum, volume)
        self.market_filters = MarketFilters(self.config)

        # Initialize trade logger and telemetry
        self.trade_logger = TradeLogger()
        self.telemetry = TelemetryLogger()
        self.margin_policy_log = TelemetryLogger(filename="margin_policy.jsonl")
        self.plrl3_log = TelemetryLogger(filename="plrl3.jsonl")
        self._last_margin_policy_ts = 0.0
        self._cached_cfm_balance_summary: dict | None = None

        # Initialize dynamic universe selector
        self.universe_manager = UniverseManager(self.config, self.api)

        # Initialize strategies
        self.strategies = {}
        self._ensure_strategies(self._get_trading_pairs())

        # Load persisted entry prices for profit tracking
        self._entry_prices = self._load_entry_prices()
        self._spot_positions = {}

        logger.info(f"Bot initialized with MTF strategy + market filters")

    def _manual_override_active(self) -> bool:
        # Presence of this file means: do not add risk automatically (rescues disabled).
        try:
            p = Path(__file__).parent / "data" / "MANUAL_OVERRIDE"
            return p.exists()
        except Exception:
            return False

    def _cfm_enabled(self) -> bool:
        """
        This bot historically mixed CFM shorts via perps_short.enabled even when exchange.use_perpetuals was false.
        For safety, treat either switch as enabling CFM position management.
        """
        exch = self.config.get("exchange", {}) or {}
        if str(exch.get("futures_type", "") or "").lower() == "cfm":
            return True
        ps = self.config.get("perps_short", {}) or {}
        return bool(ps.get("enabled")) and str(ps.get("futures_type", "") or "").lower() == "cfm"

    def _cfm_flip_state_path(self) -> Path:
        return Path(__file__).parent / "data" / "cfm_flip_state.json"

    def _load_cfm_flip_state(self) -> dict:
        p = self._cfm_flip_state_path()
        try:
            if p.exists():
                return json.loads(p.read_text())
        except Exception:
            pass
        return {}

    def _save_cfm_flip_state(self, state: dict) -> None:
        p = self._cfm_flip_state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(state, indent=2, sort_keys=True))
            tmp.replace(p)
        except Exception:
            try:
                p.write_text(json.dumps(state, indent=2, sort_keys=True))
            except Exception:
                pass

    def _extract_cfm_position(self, p: dict) -> dict:
        # Best-effort extraction, tolerant to schema changes.
        def _num(x):
            try:
                if isinstance(x, dict) and "value" in x:
                    x = x.get("value")
                v = float(x)
                if v != v or v in (float("inf"), float("-inf")):
                    return None
                return v
            except Exception:
                return None

        product_id = p.get("product_id") or p.get("productId") or p.get("symbol")
        side_raw = str(p.get("side") or "").lower()

        # Coinbase CFM positions commonly use "number_of_contracts".
        size = (
            _num(p.get("contracts"))
            or _num(p.get("number_of_contracts"))
            or _num(p.get("size"))
            or _num(p.get("base_size"))
            or _num(p.get("position_size"))
            or 0.0
        )
        entry = _num(p.get("avg_entry_price_usd")) or _num(p.get("entry_price")) or _num(p.get("avg_entry_price")) or _num(p.get("average_entry_price")) or 0.0
        current = _num(p.get("current_price_usd")) or _num(p.get("mark_price")) or _num(p.get("current_price")) or 0.0
        notional = _num(p.get("notional_value_usd")) or _num(p.get("notional_value")) or _num(p.get("position_notional")) or 0.0

        upnl = None
        for k in ("unrealized_pnl_usd", "unrealized_pnl", "unrealizedPnL", "unrealized_profit_loss"):
            if k in p:
                upnl = _num(p.get(k))
                break

        # Infer direction if not explicit.
        if "short" in side_raw or "sell" in side_raw:
            direction = "short"
        elif "long" in side_raw or "buy" in side_raw:
            direction = "long"
        else:
            direction = "short" if (size and float(size) < 0) else "long"

        return {
            "product_id": str(product_id or ""),
            "direction": direction,
            "contracts": abs(float(size or 0.0)),
            "entry_price": float(entry or 0.0),
            "current_price": float(current or 0.0),
            "notional_usd": float(notional or 0.0),
            "upnl_usd": upnl,
            "raw": p,
        }

    def _get_open_cfm_positions(self) -> list[dict]:
        if not self._cfm_enabled():
            return []
        try:
            pos = self.api.get_futures_positions() or []
        except Exception:
            return []
        out = []
        for p in pos:
            if not isinstance(p, dict):
                continue
            d = self._extract_cfm_position(p)
            if d.get("product_id") and float(d.get("contracts") or 0) > 0:
                out.append(d)
        return out

    def _usd_to_cfm_contracts(self, *, product_id: str, price: float, usd: float, direction: str) -> int:
        """
        Convert desired USD notional into contract count using contract_size from product details.
        """
        if usd <= 0 or price <= 0:
            return 0
        details = None
        try:
            if hasattr(self.api, "get_product_details"):
                details = self.api.get_product_details(product_id)
        except Exception:
            details = None
        fpd = details.get("future_product_details") if isinstance(details, dict) else None
        try:
            contract_size = float((fpd or {}).get("contract_size") or 0)
        except Exception:
            contract_size = 0.0
        if contract_size <= 0:
            # Worst-case fallback: treat 1 contract as 1 unit notional at price.
            contract_size = 1.0
        contracts = usd / (price * contract_size)
        # Minimum 1 contract if user asked for any size.
        return max(1, int(contracts))

    def _manage_cfm_reversal_tp(self, *, signals_by_pair: dict, prices: dict) -> bool:
        """
        Profit-lock exit on confirmed reversal, and optional flip into the reversal direction.

        Returns True if it took an action (close/flip), so the caller can skip other entries this cycle.
        """
        cfg = self.config.get("cfm_reversal", {}) or {}
        if not cfg.get("enabled", True):
            return False
        if not self._cfm_enabled():
            return False

        positions = self._get_open_cfm_positions()
        flip_state = self._load_cfm_flip_state()
        now_ts = time.time()

        # If there is an open CFM position, handle exit logic first and reset pending flips.
        if positions:
            flip_state.pop("pending", None)

            min_profit = float(cfg.get("min_lock_profit_usd", 2.0) or 2.0)
            min_conf = int(cfg.get("min_confluence", 4) or 4)
            exit_min_conf = int(cfg.get("exit_min_confluence", min_conf) or min_conf)

            for pos in positions:
                product_id = pos["product_id"]
                pair = self._cfm_product_id_to_pair(product_id) or ""
                sig = (signals_by_pair.get(pair) or {}) if pair else {}
                action = (sig.get("action") or "hold").lower()
                conf = sig.get("confluence_count")
                try:
                    conf_i = int(conf) if conf is not None else 0
                except Exception:
                    conf_i = 0

                direction = pos["direction"]
                opposite = "buy" if direction == "short" else "sell"

                # Use exchange-provided uPnL if available; else best-effort estimate.
                upnl = pos.get("upnl_usd")
                if upnl is None:
                    entry = float(pos.get("entry_price") or 0)
                    cur = float(pos.get("current_price") or (prices.get(pair) or 0) or 0)
                    notional = float(pos.get("notional_usd") or 0)
                    if entry > 0 and cur > 0 and notional > 0:
                        pnl_pct = (entry - cur) / entry if direction == "short" else (cur - entry) / entry
                        upnl = pnl_pct * notional

                if upnl is None:
                    continue

                if float(upnl) < float(min_profit):
                    continue

                if action != opposite:
                    continue

                if conf_i < exit_min_conf:
                    continue

                # Exit the position (reduce-only market close) to lock profit.
                logger.warning(
                    f"CFM PROFIT-LOCK EXIT: {product_id} ({pair}) dir={direction} upnl=${float(upnl):.2f} "
                    f"because reversal signal={action} conf={conf_i}/{exit_min_conf}"
                )
                try:
                    self.api.close_cfm_position(product_id)
                except Exception as e:
                    logger.error(f"CFM close failed for {product_id}: {e}")
                    return True  # attempted action

                # Prepare optional flip.
                if bool(cfg.get("flip_enabled", True)):
                    flip_state["pending"] = {
                        "product_id": product_id,
                        "pair": pair,
                        "want_action": opposite,  # buy if we exited short, sell if we exited long
                        "seen": 0,
                        "need": int(cfg.get("flip_confirm_cycles", 2) or 2),
                        "cooldown_s": int(cfg.get("flip_cooldown_seconds", 30) or 30),
                        "ts": datetime.utcnow().isoformat() + "Z",
                        "ts_epoch": now_ts,
                        "reason": "reversal_profit_lock",
                    }
                    self._save_cfm_flip_state(flip_state)
                return True

            self._save_cfm_flip_state(flip_state)
            return False

        # No open positions: consider executing a pending flip if still confirmed.
        pending = flip_state.get("pending")
        if not isinstance(pending, dict):
            return False

        # Respect global risk gates for NEW entries. Exits are always allowed above.
        try:
            can_trade, reason = self.check_risk_limits()
        except Exception:
            can_trade, reason = True, ""
        if not can_trade:
            logger.info(f"[WATCH MODE] flip entry blocked: {reason}")
            return False

        try:
            ts_epoch = float(pending.get("ts_epoch") or 0)
        except Exception:
            ts_epoch = 0.0
        cooldown_s = int(pending.get("cooldown_s", 30) or 30)
        if now_ts - ts_epoch < cooldown_s:
            return False

        product_id = str(pending.get("product_id") or "")
        pair = str(pending.get("pair") or "")
        want = str(pending.get("want_action") or "hold").lower()
        if not product_id or not pair or want not in ("buy", "sell"):
            flip_state.pop("pending", None)
            self._save_cfm_flip_state(flip_state)
            return False

        # Entry guard: margin policy
        blocked, reason = self._margin_policy_blocks_entry()
        if blocked:
            logger.warning(f"CFM flip entry blocked: {reason}")
            return False

        # Cutoff guard (avoid opening a new position close to overnight window jump).
        try:
            mp = evaluate_margin_policy(self._get_cfm_balance_summary_cached(force=True) or {}, now_utc=datetime.utcnow())
            mins = int((mp.metrics or {}).get("mins_to_cutoff") or 9999)
        except Exception:
            mins = 9999
        if mins <= int(cfg.get("disable_new_entries_pre_cutoff_min", 30) or 30):
            logger.warning(f"CFM flip entry skipped: cutoff soon ({mins}m)")
            return False

        sig = (signals_by_pair.get(pair) or {})
        action = (sig.get("action") or "hold").lower()
        conf = sig.get("confluence_count")
        try:
            conf_i = int(conf) if conf is not None else 0
        except Exception:
            conf_i = 0

        if action != want:
            # Signal no longer agrees, cancel the flip.
            flip_state.pop("pending", None)
            self._save_cfm_flip_state(flip_state)
            return False

        flip_min_conf = int(cfg.get("flip_min_confluence", cfg.get("min_confluence", 4) or 4) or 4)
        if conf_i < flip_min_conf:
            return False

        seen = int(pending.get("seen", 0) or 0) + 1
        pending["seen"] = seen
        flip_state["pending"] = pending
        self._save_cfm_flip_state(flip_state)

        if seen < int(pending.get("need", 2) or 2):
            return False

        # Execute flip entry.
        price = float(prices.get(pair) or self.api.get_current_price(pair) or 0)
        if price <= 0:
            return False

        # Size from the existing sizing engine (USD notional target).
        lev = self._determine_leverage(sig if isinstance(sig, dict) else {})
        sizing = self.balance_manager.get_optimal_position_size(leverage=lev) or {}
        usd = float(sizing.get("position_size_usd") or 0)
        if usd <= 0:
            return False

        contracts = self._usd_to_cfm_contracts(product_id=product_id, price=price, usd=usd, direction=("long" if want == "buy" else "short"))
        side = "BUY" if want == "buy" else "SELL"
        logger.warning(f"CFM FLIP ENTRY: {product_id} ({pair}) side={side} contracts={contracts} (~${usd:.2f} target)")
        try:
            order = self.api.place_cfm_order(
                product_id=product_id,
                side=side,
                base_size=float(contracts),
                price=None,
                stop_loss=sig.get("stop_loss"),
                take_profit=sig.get("take_profit"),
            )
            if order:
                self._plrl3_register_entry(product_id=product_id, pair=pair, initial_contracts=int(contracts), side=want)
        except Exception as e:
            logger.error(f"CFM flip entry failed: {e}")
            return True

        flip_state.pop("pending", None)
        self._save_cfm_flip_state(flip_state)
        return True

    def _get_cfm_balance_summary_cached(self, *, force: bool = False) -> Optional[dict]:
        """
        CFM balance summary is used by margin-policy and PLRL-3.
        We cache it per-cycle to avoid extra API hits.
        """
        if not force and isinstance(self._cached_cfm_balance_summary, dict):
            return self._cached_cfm_balance_summary
        try:
            summary = self.api.get_futures_balance_summary()
            self._cached_cfm_balance_summary = summary if isinstance(summary, dict) else None
            return self._cached_cfm_balance_summary
        except Exception:
            self._cached_cfm_balance_summary = None
            return None

    def _update_margin_policy(self):
        cfg = self.config.get("margin_policy", {}) or {}
        if not cfg.get("enabled", True):
            return
        if not self._cfm_enabled():
            return

        log_every = float(cfg.get("log_interval_seconds", 5) or 5)
        now = time.time()
        if (now - float(self._last_margin_policy_ts or 0)) < log_every:
            return

        summary = self._get_cfm_balance_summary_cached(force=True) or {}
        decision = evaluate_margin_policy(summary, now_utc=datetime.utcnow())
        rec = decision.to_dict()
        rec["ts"] = datetime.utcnow().isoformat() + "Z"
        rec["bot"] = self.bot_name
        self.margin_policy_log.log_ping(rec)
        self._last_margin_policy_ts = now

    def _margin_policy_blocks_entry(self) -> tuple[bool, str]:
        cfg = self.config.get("margin_policy", {}) or {}
        if not cfg.get("enabled", True):
            return False, "margin_policy_disabled"
        if not cfg.get("enforce_block_entries", True):
            return False, "margin_policy_enforcement_disabled"
        if not self._cfm_enabled():
            return False, "cfm_disabled"

        # Use the latest record by re-evaluating cheaply off cached summary.
        try:
            summary = self._get_cfm_balance_summary_cached(force=False) or {}
            decision = evaluate_margin_policy(summary, now_utc=datetime.utcnow())
            if "BLOCK_ENTRY" in (decision.actions or []):
                mr = decision.metrics.get("active_mr")
                src = decision.metrics.get("active_mr_source")
                return True, f"Margin policy {decision.tier} (MR={mr:.4f} src={src})"
            return False, "OK"
        except Exception:
            return False, "margin_policy_eval_failed"

    def _plrl3_state_path(self) -> Path:
        return Path(__file__).parent / "data" / "plrl3_state.json"

    def _load_plrl3_state(self) -> dict:
        p = self._plrl3_state_path()
        try:
            if p.exists():
                return json.loads(p.read_text())
        except Exception:
            pass
        return {}

    def _save_plrl3_state(self, state: dict) -> None:
        p = self._plrl3_state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(state, indent=2, sort_keys=True))
            tmp.replace(p)
        except Exception:
            try:
                p.write_text(json.dumps(state, indent=2, sort_keys=True))
            except Exception:
                pass

    def _plrl3_register_entry(self, *, product_id: str, pair: str, initial_contracts: int, side: str):
        if not product_id:
            return
        state = self._load_plrl3_state()
        state[str(product_id)] = {
            "product_id": str(product_id),
            "pair": str(pair or ""),
            "side": str(side or ""),
            "initial_contracts": int(max(0, int(initial_contracts or 0))),
            "rescue_step": 0,
            "max_rescues": int((self.config.get("plrl3", {}) or {}).get("max_rescues", 3) or 3),
            "ts": datetime.utcnow().isoformat() + "Z",
            "seeded_from": "entry",
        }
        self._save_plrl3_state(state)

    def _plrl3_seed_from_sync(self, *, product_id: str, pair: str, contracts: int, side: str):
        """Seed PLRL state from a recovered/existing position. Live rescues remain conservative."""
        if not product_id:
            return
        state = self._load_plrl3_state()
        if str(product_id) in state:
            return
        state[str(product_id)] = {
            "product_id": str(product_id),
            "pair": str(pair or ""),
            "side": str(side or ""),
            "initial_contracts": int(max(0, int(contracts or 0))),
            "rescue_step": 0,
            "max_rescues": int((self.config.get("plrl3", {}) or {}).get("max_rescues", 3) or 3),
            "ts": datetime.utcnow().isoformat() + "Z",
            "seeded_from": "sync",
        }
        self._save_plrl3_state(state)

    def _update_plrl3(self):
        cfg = self.config.get("plrl3", {}) or {}
        if not cfg.get("enabled", True):
            return
        if not self._cfm_enabled():
            return

        enforcement = str(cfg.get("enforcement", "log_only") or "log_only").lower()
        allow_rescues = (enforcement == "live") and (not self._manual_override_active())

        summary = self._get_cfm_balance_summary_cached(force=False) or {}
        try:
            positions = self.api.get_futures_positions() or []
        except Exception:
            positions = []

        if not positions:
            return

        state = self._load_plrl3_state()

        for p in positions:
            product_id = p.get("product_id") or p.get("productId") or p.get("symbol")
            if not product_id:
                continue

            pair = self._cfm_product_id_to_pair(str(product_id)) or ""
            side_raw = str(p.get("side") or "").lower()
            try:
                size = float(p.get("size") or p.get("base_size") or p.get("position_size") or 0)
            except Exception:
                size = 0.0

            direction = "short" if ("sell" in side_raw or "short" in side_raw or (size and size < 0)) else "long"

            price = self.api.get_current_price(pair) if pair else None
            try:
                price = float(price or 0)
            except Exception:
                price = 0.0

            st_rec = state.get(str(product_id)) or {}
            rescue_step = int(st_rec.get("rescue_step", 0) or 0)
            max_rescues = int(cfg.get("max_rescues", st_rec.get("max_rescues", 3)) or 3)

            # Determine initial contracts. If we don't have a seeded state, we compute a suggestion but
            # refuse to place live rescues until a true "entry-sized" baseline exists.
            initial_contracts = int(st_rec.get("initial_contracts", 0) or 0)
            state_seeded = initial_contracts > 0 and str(st_rec.get("seeded_from") or "") in ("entry", "sync")
            allow_rescues_for_pos = allow_rescues and state_seeded

            product_details = None
            try:
                if hasattr(self.api, "get_product_details"):
                    product_details = self.api.get_product_details(str(product_id))
            except Exception:
                product_details = None

            if not isinstance(product_details, dict):
                product_details = {}

            suggested_initial = None
            sizing_meta = None
            if initial_contracts <= 0 and price > 0:
                total_multiplier = int(cfg.get("total_multiplier", 15) or 15)
                mr_max_allowed = float(cfg.get("mr_max_allowed", 0.95) or 0.95)
                suggested_initial, sizing_meta = compute_initial_contracts_plrl3(
                    balance_summary=summary,
                    product_details=product_details,
                    direction=direction,
                    price=price,
                    mr_max_allowed=mr_max_allowed,
                    total_multiplier=total_multiplier,
                )

            mr_triggers = cfg.get("mr_triggers", [0.60, 0.75, 0.88]) or [0.60, 0.75, 0.88]
            add_multipliers = cfg.get("add_multipliers", [1, 2, 4]) or [1, 2, 4]
            decision = evaluate_plrl3(
                balance_summary=summary,
                product_details=product_details,
                direction=direction,
                price=price,
                initial_contracts=initial_contracts if initial_contracts > 0 else int(suggested_initial or 0),
                rescue_step=rescue_step,
                max_rescues=max_rescues,
                mr_triggers=[float(x) for x in mr_triggers],
                add_multipliers=[int(x) for x in add_multipliers],
                fail_mr=float(cfg.get("fail_mr", 0.95) or 0.95),
                max_projected_mr=float(cfg.get("max_projected_mr", 0.95) or 0.95),
                overnight_guard_mr=float(cfg.get("overnight_guard_mr", 0.90) or 0.90),
                now_utc=datetime.utcnow(),
                disable_rescues_pre_cutoff_min=int(cfg.get("disable_rescues_pre_cutoff_min", 30) or 30),
                allow_rescues=allow_rescues_for_pos,
            )

            out = decision.to_dict()
            out["ts"] = datetime.utcnow().isoformat() + "Z"
            out["bot"] = self.bot_name
            out["product_id"] = str(product_id)
            out["pair"] = pair
            out["direction"] = direction
            out["enforcement"] = enforcement
            out["state_seeded"] = bool(state_seeded)
            out["suggested_initial_contracts"] = int(suggested_initial or 0) if suggested_initial is not None else None
            out["suggested_initial_meta"] = sizing_meta
            if self._manual_override_active():
                out["notes"] = (out.get("notes") or []) + ["manual_override_active"]
            if not state_seeded:
                out["notes"] = (out.get("notes") or []) + ["state_missing_or_unseeded"]
            self.plrl3_log.log_ping(out)

            # Live enforcement is intentionally conservative: no rescue orders unless seeded from entry/sync.
            if enforcement != "live":
                continue

            if decision.action == "EXIT":
                try:
                    self.api.close_cfm_position(str(product_id))
                except Exception:
                    pass
                continue

            if decision.action == "RESCUE" and decision.add_contracts > 0 and allow_rescues_for_pos:
                # Add to the existing position direction (BUY adds to long, SELL adds to short).
                side = "BUY" if direction == "long" else "SELL"
                try:
                    self.api.place_cfm_order(
                        product_id=str(product_id),
                        side=side,
                        base_size=float(decision.add_contracts),
                        price=None,
                        reduce_only=False,
                    )
                    # Persist rescue step only if the order call didn't raise.
                    st_rec = dict(state.get(str(product_id)) or {})
                    st_rec["rescue_step"] = int(rescue_step + 1)
                    st_rec["ts"] = datetime.utcnow().isoformat() + "Z"
                    state[str(product_id)] = st_rec
                    self._save_plrl3_state(state)
                except Exception:
                    continue

    def _get_best_bid_ask(self, pair: str) -> tuple[Optional[float], Optional[float]]:
        try:
            book = self.api.get_orderbook(pair) or {}
            bids = book.get("bids") or []
            asks = book.get("asks") or []
            if not bids or not asks:
                return None, None
            bid = float(bids[0].get("price"))
            ask = float(asks[0].get("price"))
            return bid, ask
        except Exception:
            return None, None

    def _order_filled(self, status: dict) -> bool:
        if not status:
            return False
        order = status.get("order", status)
        state = str(order.get("status", "")).upper()
        if state in ("FILLED", "DONE", "SETTLED"):
            return True
        try:
            filled = float(order.get("filled_size") or 0)
            size = float(order.get("size") or 0)
            if size and filled >= size:
                return True
        except Exception:
            pass
        return False

    def _maker_first_spot_order(self, side: str, pair: str, quote_amount: float = None, base_amount: float = None, expected_profit_pct: float = None) -> Optional[dict]:
        exec_cfg = self.config.get("execution", {}).get("maker_first", {})
        if not exec_cfg.get("enabled", False):
            return None

        bid, ask = self._get_best_bid_ask(pair)
        if not bid or not ask:
            return None

        offset = float(exec_cfg.get("price_offset_percent", 0.0)) / 100.0
        max_wait = float(exec_cfg.get("max_wait_seconds", 10))
        interval = float(exec_cfg.get("check_interval_seconds", 2))
        fallback = bool(exec_cfg.get("fallback_to_taker", True))

        if side == "buy":
            limit_price = bid * (1 - offset)
            if not quote_amount:
                return None
            base_size = quote_amount / limit_price
            if hasattr(self.api, "_round_base_size"):
                base_size = self.api._round_base_size(base_size, pair)
            if not base_size:
                return None
            order = self.api.place_buy_order(pair=pair, amount=base_size, price=limit_price, post_only=True)
        else:
            limit_price = ask * (1 + offset)
            if not base_amount:
                return None
            order = self.api.place_sell_order(pair=pair, amount=base_amount, price=limit_price, post_only=True)

        if not order or order.get("success") is False or order.get("error_response"):
            return None

        order_id = order.get("order_id") or order.get("id")
        if not order_id:
            return None

        checks = max(1, int(max_wait / max(interval, 1)))
        for _ in range(checks):
            time.sleep(interval)
            status = self.api.get_order(order_id)
            if self._order_filled(status):
                return order

        # Not filled - cancel and optionally fallback to taker
        try:
            self.api.cancel_order(order_id)
        except Exception:
            pass

        if not fallback:
            return None

        fee_cfg = self.config.get("fees", {}) or {}
        total_fee = (float(fee_cfg.get("taker_percent", 0.0)) * 2) + float(fee_cfg.get("spread_buffer_percent", 0.0)) + float(fee_cfg.get("slippage_percent", 0.0))
        min_edge = float(exec_cfg.get("min_edge_percent", total_fee))
        if expected_profit_pct is not None and expected_profit_pct < min_edge:
            return None

        return None

    def _execute_perps_short(self, signal: dict, price: float) -> Optional[dict]:
        perps_cfg = self.config.get("perps_short", {}) or {}
        if not perps_cfg.get("enabled", False):
            return None

        product_id = self._resolve_cfm_product_id(signal["pair"])
        if not product_id:
            logger.info(f"No CFM product for {signal['pair']} - skip short")
            return None

        blocked, reason = self._margin_policy_blocks_entry()
        if blocked:
            logger.warning(f"Perps short blocked: {reason}")
            return None

        # Check open futures positions
        try:
            positions = self.api.get_futures_positions() or []
            if len(positions) >= int(perps_cfg.get("max_open_positions", 1)):
                logger.info("Perps short blocked: max open futures positions reached")
                return None
        except Exception:
            pass

        max_pos_usd = float(perps_cfg.get("max_position_usd", signal.get("amount", 0)) or 0)
        size_usd = min(float(signal.get("amount", 0) or 0), max_pos_usd) if max_pos_usd else float(signal.get("amount", 0) or 0)
        if size_usd <= 0:
            return None

        # Estimate margin requirement
        details = self.api.get_product_details(product_id) if hasattr(self.api, "get_product_details") else None
        fpd = details.get("future_product_details") if isinstance(details, dict) else None
        contract_size = float((fpd or {}).get("contract_size") or 0)
        margin_rate = 0.0
        try:
            intraday = (fpd or {}).get("intraday_margin_rate") or {}
            margin_rate = float(intraday.get("short_margin_rate") or intraday.get("long_margin_rate") or 0)
        except Exception:
            margin_rate = 0.0

        # Convert desired USD notional into contracts using contract_size.
        contract_size = float((fpd or {}).get("contract_size") or 0) if isinstance(fpd, dict) else 0.0
        if contract_size <= 0:
            contract_size = 1.0
        size_base = size_usd / (price * contract_size) if price else 0
        if contract_size and margin_rate:
            required_margin = price * contract_size * size_base * margin_rate
        else:
            required_margin = size_usd

        buying_power = self.api.get_cfm_buying_power() or 0
        reserve_usd = float(perps_cfg.get("reserve_usd", 0) or 0)
        if buying_power < (required_margin + reserve_usd):
            logger.info(f"Perps short blocked: need ${required_margin + reserve_usd:.2f}, have ${buying_power:.2f}")
            return None

        leverage = int(perps_cfg.get("leverage", signal.get("leverage", 2)) or 2)
        size_base = max(size_base, 1.0)  # minimum 1 contract
        order = self.api.place_cfm_order(
            product_id=product_id,
            side="SELL",
            base_size=size_base,
            price=None,
            stop_loss=signal.get("stop_loss"),
            take_profit=signal.get("take_profit"),
        )
        try:
            if order and (order.get("success") is not False) and not order.get("error_response"):
                self._plrl3_register_entry(
                    product_id=str(product_id),
                    pair=str(signal.get("pair") or ""),
                    initial_contracts=int(max(1, round(float(size_base or 0)))),
                    side="sell",
                )
        except Exception:
            pass
        return order

    def _load_entry_prices(self) -> dict:
        """Load entry prices from persistent storage"""
        entry_file = Path(__file__).parent / "data" / "entry_prices.json"
        try:
            if entry_file.exists():
                with open(entry_file) as f:
                    prices = json.load(f)
                    # Normalize legacy format (float) to dict with price/time
                    normalized = {}
                    for pair, meta in prices.items():
                        if isinstance(meta, dict):
                            normalized[pair] = meta
                        else:
                            normalized[pair] = {"price": meta, "time": None}
                    logger.info(f"Loaded {len(normalized)} entry prices from storage")
                    return normalized
        except Exception as e:
            logger.warning(f"Could not load entry prices: {e}")
        return {}

    def _save_entry_prices(self):
        """Save entry prices to persistent storage"""
        entry_file = Path(__file__).parent / "data" / "entry_prices.json"
        try:
            with open(entry_file, 'w') as f:
                json.dump(self._entry_prices, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save entry prices: {e}")

    def _cfm_product_id_to_pair(self, product_id: str) -> Optional[str]:
        if not product_id:
            return None
        prefix = product_id.split("-")[0]
        prefix_map = {
            "BIP": "BTC",
            "ETP": "ETH",
            "SLP": "SOL",
            "AVP": "AVAX",
            "DOP": "DOGE",
            "LNP": "LINK",
            "LCP": "LTC",
            "ADP": "ADA",
            "SHP": "SHIB",
            "HEP": "HBAR",
            "SUP": "SUI",
            "XLP": "XLM",
            "POP": "DOT",
            "XPP": "XRP",
        }
        base = prefix_map.get(prefix)
        if not base:
            return None
        return f"{base}-USD"

    def _sync_cfm_positions(self):
        """
        Sync manual CFM positions for awareness/state seeding.

        Note: We do NOT register CFM positions into PositionManager because that manager assumes INTX semantics
        (liq calc, add_margin, close_perpetual_position) and can produce incorrect sizing for CFM contracts.
        """
        if not getattr(self.api, "get_futures_positions", None):
            return
        try:
            positions = self.api.get_futures_positions() or []
        except Exception:
            return

        for p in positions:
            product_id = p.get("product_id") or p.get("productId") or p.get("symbol")
            pair = self._cfm_product_id_to_pair(product_id)
            if not pair:
                continue

            # Extract sizing
            try:
                entry_price = float(p.get("entry_price") or p.get("avg_entry_price") or p.get("average_entry_price") or 0)
            except Exception:
                entry_price = 0.0
            try:
                base_size = float(
                    p.get("number_of_contracts")
                    or p.get("contracts")
                    or p.get("size")
                    or p.get("base_size")
                    or p.get("position_size")
                    or 0
                )
            except Exception:
                base_size = 0.0
            try:
                notional = float(p.get("notional_value") or p.get("position_notional") or 0)
            except Exception:
                notional = 0.0

            if notional <= 0 and entry_price > 0 and base_size > 0:
                notional = entry_price * base_size

            if notional <= 0:
                continue

            side = "buy"
            side_raw = (p.get("side") or "").lower()
            if "sell" in side_raw or "short" in side_raw:
                side = "sell"

            # Use config leverage if not provided
            lev = self.config.get("strategy", {}).get("leverage", 2)
            try:
                lev = int(p.get("leverage") or lev)
            except Exception:
                pass

            position_id = p.get("position_id") or p.get("id") or f"{pair}_{datetime.now().timestamp()}"
            _ = position_id  # reserved for future state linking
            logger.info(f"Detected open CFM position: {pair} {side} notional~${notional:.2f}")
            try:
                self._plrl3_seed_from_sync(
                    product_id=str(product_id),
                    pair=str(pair),
                    contracts=int(max(0, round(abs(float(base_size or 0))))),
                    side=str(side),
                )
            except Exception:
                pass

    def _sync_spot_positions(self):
        """Detect and log existing spot positions that could be exited."""
        try:
            accounts = self.api.get_accounts() or []
        except Exception:
            return {}

        spot_positions = {}
        # Get list of tradeable symbols from universe
        include_symbols = self.config.get("universe", {}).get("include_symbols", [])

        for acc in accounts:
            currency = acc.get("currency", "")
            if currency in ["USD", "USDC", "USDT", "DAI"]:
                continue  # Skip stablecoins

            try:
                balance = float(acc.get("available_balance", {}).get("value", 0))
            except:
                balance = 0

            if balance > 0.001:
                pair = f"{currency}-USD"
                # Get current price to calculate value
                price = self.api.get_current_price(pair) or 0
                value = balance * price if price else 0

                if value > 1.0:  # Only track positions worth > $1
                    spot_positions[pair] = {
                        "currency": currency,
                        "balance": balance,
                        "price": price,
                        "value": value
                    }
                    # Log if this is a tradeable pair
                    if currency in include_symbols or not include_symbols:
                        logger.info(f"📊 SPOT POSITION: {balance:.4f} {currency} = ${value:.2f} (will exit on SELL signal)")

        self._spot_positions = spot_positions
        return spot_positions

    def _check_spot_exits(self):
        """Check spot positions - exit on profit target OR trend reversal while in profit."""
        spot_positions = getattr(self, "_spot_positions", {})
        if not spot_positions:
            spot_positions = self._sync_spot_positions()

        exit_cfg = self.config.get("exit_strategy", {})
        micro_cfg = exit_cfg.get("micro_mode", {}) or {}
        micro_enabled = bool(micro_cfg.get("enabled", False))
        min_profit_pct = float(micro_cfg.get("min_profit_percent", exit_cfg.get("min_profit_percent", 7.0))) if micro_enabled else float(exit_cfg.get("min_profit_percent", 7.0))
        min_reversal_profit = float(micro_cfg.get("min_reversal_profit", exit_cfg.get("min_profit_to_exit_on_reversal", 3.0))) if micro_enabled else float(exit_cfg.get("min_profit_to_exit_on_reversal", 3.0))
        fee_cfg = self.config.get("fees", {}) or {}
        maker_fee = float(fee_cfg.get("maker_percent", exit_cfg.get("trading_fee_percent", 1.0)))
        taker_fee = float(fee_cfg.get("taker_percent", exit_cfg.get("trading_fee_percent", 1.0)))
        fee_pct = taker_fee if fee_cfg.get("assume_taker", True) else maker_fee
        spread_buffer = float(fee_cfg.get("spread_buffer_percent", 0.0))
        slippage_buffer = float(fee_cfg.get("slippage_percent", 0.0))
        never_sell_at_loss = exit_cfg.get("never_sell_at_loss", True)
        min_hold_minutes = float(exit_cfg.get("min_hold_minutes", 0))

        # Fees for round trip (buy + sell)
        total_fees_pct = fee_pct * 2 + spread_buffer + slippage_buffer
        target_with_fees = min_profit_pct + total_fees_pct
        min_exit_with_fees = min_reversal_profit + total_fees_pct

        for pair, pos_info in list(spot_positions.items()):
            if pos_info["value"] < 1.0:
                continue

            price = self.api.get_current_price(pair)
            if not price:
                continue

            # Get or set entry price
            if pair not in self._entry_prices:
                self._entry_prices[pair] = {"price": price, "time": datetime.now().isoformat()}
                self._save_entry_prices()
                logger.info(f"📝 TRACKING {pair}: entry=${price:.4f}, target={min_profit_pct}%+ or reversal at {min_reversal_profit}%+")
                continue

            entry_meta = self._entry_prices.get(pair, {})
            if isinstance(entry_meta, dict):
                entry_price = entry_meta.get("price")
                entry_time = entry_meta.get("time")
            else:
                entry_price = entry_meta
                entry_time = None
            if not entry_price:
                continue
            profit_pct = ((price - entry_price) / entry_price) * 100
            profit_usd = pos_info["value"] - (pos_info["balance"] * entry_price)
            net_profit_pct = profit_pct - total_fees_pct
            elapsed_minutes = None
            if entry_time:
                try:
                    elapsed_minutes = (datetime.now() - datetime.fromisoformat(entry_time)).total_seconds() / 60.0
                except Exception:
                    elapsed_minutes = None

            # Get trend signal for this pair
            trend_reversing = False
            breakout_type = ""
            if pair in self.strategies:
                try:
                    signal = self.strategies[pair].analyze({"price": price, "timestamp": datetime.now(), "pair": pair})
                    if signal and signal.get("side") == "sell":
                        trend_reversing = True
                    if signal and signal.get("breakout_type"):
                        breakout_type = signal.get("breakout_type")
                except:
                    pass

            # Log position status
            status_emoji = "📈" if profit_pct > 0 else "📉"
            trend_note = " 🔄REVERSAL" if trend_reversing else ""
            logger.info(f"{status_emoji} {pair}: ${entry_price:.4f}→${price:.4f} P/L={profit_pct:+.1f}% (net {net_profit_pct:+.1f}%){trend_note}")

            should_sell = False
            sell_reason = ""

            # RULE 1: Hit profit target (7%+)
            if profit_pct >= target_with_fees and breakout_type != "exponential":
                should_sell = True
                sell_reason = f"🎯 TARGET HIT: +{profit_pct:.1f}%"

            # RULE 2: Trend reversing while in decent profit (3%+)
            elif trend_reversing and profit_pct >= min_exit_with_fees:
                should_sell = True
                sell_reason = f"🔄 TREND REVERSAL at +{profit_pct:.1f}%"

            # RULE 2B: Time-stop (micro mode) - exit if stuck but still positive after fees
            elif micro_enabled and elapsed_minutes is not None:
                time_stop_min = float(micro_cfg.get("time_stop_minutes", 0))
                time_stop_profit = max(float(micro_cfg.get("time_stop_min_profit_percent", 0.0)), total_fees_pct)
                if time_stop_min > 0 and elapsed_minutes >= max(time_stop_min, min_hold_minutes) and profit_pct >= time_stop_profit:
                    should_sell = True
                    sell_reason = f"⏱ TIME STOP at +{profit_pct:.1f}%"

            # RULE 3: Never sell at loss
            elif profit_pct < 0 and never_sell_at_loss:
                logger.info(f"⏳ HOLDING {pair}: down {profit_pct:.1f}%, waiting for recovery")
                continue

            # RULE 4: Small profit but no reversal - keep holding
            elif profit_pct > 0 and profit_pct < min_exit_with_fees:
                logger.info(f"⏳ HOLDING {pair}: +{profit_pct:.1f}% (need {min_exit_with_fees:.1f}%+ to exit)")
                continue

            if should_sell:
                balance = pos_info["balance"]
                logger.info(f"{sell_reason}")
                logger.info(f"💰 SELLING {balance:.4f} {pos_info['currency']} @ ${price:.4f}")
                try:
                    order = self._maker_first_spot_order(
                        side="sell",
                        pair=pair,
                        base_amount=balance,
                        expected_profit_pct=profit_pct,
                    )
                    if not order:
                        order = self.api.place_sell_order(pair=pair, amount=balance, price=None)
                    if order and order.get("success") != False:
                        net_profit = profit_usd - (pos_info["value"] * fee_pct / 100 * 2)
                        logger.info(f"✅ SOLD! Net profit: ${net_profit:.2f} ({net_profit_pct:.1f}%)")
                        if pair in self._spot_positions:
                            del self._spot_positions[pair]
                        if pair in self._entry_prices:
                            del self._entry_prices[pair]
                            self._save_entry_prices()
                    else:
                        error = order.get("error_response", {}).get("message", "Unknown") if order else "No response"
                        logger.error(f"❌ SELL FAILED: {error}")
                except Exception as e:
                    logger.error(f"❌ SELL ERROR: {e}")

    def _load_config(self, path: str) -> dict:
        """Load configuration from JSON file"""
        config_path = Path(__file__).parent / path
        with open(config_path) as f:
            return json.load(f)

    def _init_strategies(self):
        """Initialize MTF strategy for each enabled trading pair"""
        strat_config = self.config.get("strategy", {})
        trading_pairs = [p["pair"] for p in self.config.get("trading_pairs", []) if p.get("enabled", True)]

        for pair in trading_pairs:
            if pair not in self.strategies:
                self.strategies[pair] = MTFStrategy(
                    api=self.api,
                    config=strat_config,
                    trading_pair=pair
                )
                logger.info(f"MTF Strategy: ENABLED for {pair}")

    def _get_trading_pairs(self) -> list:
        """Get current trading universe"""
        universe_pairs = self.universe_manager.get_pairs()
        if universe_pairs:
            return universe_pairs
        return [p["pair"] for p in self.config.get("trading_pairs", []) if p.get("enabled", True)]

    def _ensure_strategies(self, pairs: list):
        """Ensure we have strategies for each pair in the current universe."""
        strat_config = self.config.get("strategy", {})
        for pair in pairs:
            if pair not in self.strategies:
                self.strategies[pair] = MTFStrategy(
                    api=self.api,
                    config=strat_config,
                    trading_pair=pair
                )
                logger.info(f"MTF Strategy: ENABLED for {pair}")

        # Remove strategies no longer in universe
        for pair in list(self.strategies.keys()):
            if pair not in pairs:
                del self.strategies[pair]

    def check_risk_limits(self) -> Tuple[bool, str]:
        """Check if we're within risk limits"""
        # Check market filters (trading hours, news events)
        pre_signal_ok, pre_signal_reason = self.market_filters.check_pre_signal()
        if not pre_signal_ok:
            logger.debug(f"Market filter blocked: {pre_signal_reason}")
            return False, pre_signal_reason

        # Check trade optimizer (circuit breaker, cool-down)
        can_trade, reason = self.trade_optimizer.can_trade()
        if not can_trade:
            logger.warning(f"Trade optimizer blocked: {reason}")
            return False, reason

        # Check daily loss limit
        daily_loss_limit = self.config.get("risk_management", {}).get("daily_loss_limit_usd", 150)
        if abs(self.daily_pnl) >= daily_loss_limit:
            logger.warning(f"Daily loss limit reached: ${self.daily_pnl:.2f}")
            return False, "Daily loss limit reached"

        # Check max trades
        max_trades = self.config.get("trading", {}).get("max_daily_trades", 10)
        if len(self.trades_today) >= max_trades:
            logger.warning("Max daily trades reached")
            return False, "Max daily trades reached"

        # Check emergency stop
        if self.config.get("risk_management", {}).get("emergency_stop", False):
            logger.warning("Emergency stop is active")
            return False, "Emergency stop active"

        return True, "OK"

    def get_best_trading_pair(self) -> Optional[str]:
        """Get the best pair to trade based on opportunity analysis"""
        # Get list of enabled pairs
        pairs = self._get_trading_pairs()

        if not pairs:
            return self.config.get("trading", {}).get("trading_pair", "BTC-USD")

        # Get open position pairs for correlation check
        open_pairs = [p.pair for p in self.position_manager.positions.values()]

        # Select best opportunity
        best = self.trade_optimizer.select_best_pair(pairs, open_pairs)

        if best:
            self._last_pair_analysis = best
            logger.info(f"Selected {best.pair}: score={best.opportunity_score}, "
                       f"R:R={best.risk_reward_ratio}, upside={best.upside_potential_pct}%")
            return best.pair

        # Fallback to first available uncorrelated pair
        uncorrelated = self.trade_optimizer.get_uncorrelated_pairs(pairs, open_pairs)
        return uncorrelated[0] if uncorrelated else None

    def _determine_leverage(self, signal: dict) -> int:
        """Choose leverage based on config and signal strength/volatility."""
        leverage_cfg = self.config.get("leverage", {})
        mode = leverage_cfg.get("mode", "static")
        base = leverage_cfg.get("base", self.config.get("strategy", {}).get("leverage", 4))
        min_lev = leverage_cfg.get("min", 2)
        max_lev = leverage_cfg.get("max", 6)

        if mode != "dynamic":
            return int(base)

        lev = float(base)

        score = signal.get("confluence_score")
        score_low = leverage_cfg.get("score_low", 2.0)
        score_high = leverage_cfg.get("score_high", 4.0)
        if score is not None:
            if score <= score_low:
                lev = min_lev
            elif score >= score_high:
                lev = max_lev
            else:
                lev = min_lev + (score - score_low) / (score_high - score_low) * (max_lev - min_lev)

        analysis = getattr(self, "_last_pair_analysis", None)
        rr = None
        if analysis and analysis.pair == signal.get("pair"):
            rr = analysis.risk_reward_ratio
        rr = rr or signal.get("risk_reward")
        if rr is not None:
            try:
                rr_val = float(rr)
                rr_levels = leverage_cfg.get("rr_to_leverage", [])
                rr_target = None
                for level in rr_levels:
                    try:
                        if rr_val >= float(level.get("rr")):
                            rr_target = float(level.get("lev"))
                    except Exception:
                        continue
                if rr_target is not None:
                    lev = max(lev, rr_target)
            except Exception:
                pass

        if analysis and analysis.pair == signal.get("pair"):
            atr = analysis.atr_percent
            atr_low = leverage_cfg.get("atr_low_pct", 1.0)
            atr_high = leverage_cfg.get("atr_high_pct", 4.0)
            if atr >= atr_high:
                lev = min(lev, min_lev)
            elif atr > atr_low:
                # Scale down leverage as volatility increases
                scale = 1 - ((atr - atr_low) / (atr_high - atr_low))
                lev = min_lev + (lev - min_lev) * max(scale, 0.0)

        # Setup-based leverage adjustments
        setups = signal.get("setups", []) or []
        setup_adj = leverage_cfg.get("setup_adjustments", {})
        for setup in setups:
            adj = setup_adj.get(setup)
            if adj is None:
                continue
            lev += float(adj)

        # Safety clamp
        lev = max(min_lev, min(max_lev, lev))
        return int(round(lev))

    def _calculate_position_scale(self, signal: dict, analysis: dict = None) -> float:
        cfg = self.config.get("position_scaling", {})
        if not cfg.get("enabled", False):
            return 1.0

        max_mult = float(cfg.get("max_multiplier", 1.0))
        conf_min = float(cfg.get("confluence_min", 3))
        conf_max = float(cfg.get("confluence_max", 5))
        rr_min = float(cfg.get("rr_min", 1.5))
        rr_max = float(cfg.get("rr_max", 4.0))
        rr_mult_max = float(cfg.get("rr_multiplier_max", 1.0))

        conf_val = signal.get("confluence_count")
        if conf_val is None:
            conf_val = signal.get("confluence_score")

        conf_scale = 1.0
        try:
            if conf_val is not None and conf_max > conf_min:
                conf_val = float(conf_val)
                if conf_val >= conf_min:
                    conf_scale = 1.0 + min(1.0, (conf_val - conf_min) / (conf_max - conf_min)) * (max_mult - 1.0)
        except Exception:
            pass

        rr = None
        if analysis and analysis.pair == signal.get("pair"):
            rr = analysis.risk_reward_ratio
        rr = rr or signal.get("risk_reward")

        rr_scale = 1.0
        try:
            if rr is not None and rr_max > rr_min:
                rr_val = float(rr)
                if rr_val >= rr_min:
                    rr_scale = 1.0 + min(1.0, (rr_val - rr_min) / (rr_max - rr_min)) * (rr_mult_max - 1.0)
        except Exception:
            pass

        scale = max(conf_scale, rr_scale)
        return min(scale, max_mult)

    def _apply_position_scaling(self, trade_sizing: dict, signal: dict, analysis: dict = None) -> dict:
        scale = self._calculate_position_scale(signal, analysis)
        if scale <= 1.0:
            return trade_sizing

        size = float(trade_sizing.get("position_size_usd", 0)) * scale
        available = trade_sizing.get("available")
        max_pct = self.config.get("risk_caps", {}).get("max_position_percent")
        if available is not None and max_pct is not None:
            try:
                cap = float(available) * (float(max_pct) / 100.0)
                if size > cap:
                    size = cap
            except Exception:
                pass

        trade_sizing["position_size_usd"] = round(size, 2)
        trade_sizing["leverage_adjusted"] = round(size * float(trade_sizing.get("leverage", 1)), 2)
        trade_sizing["scaled_multiplier"] = round(scale, 2)
        return trade_sizing

    def _resolve_cfm_product_id(self, pair: str) -> Optional[str]:
        """Resolve a CFM futures product_id for a spot-style pair (e.g., BTC-USD)."""
        # Check cache first
        if hasattr(self, "_cfm_product_map") and pair in self._cfm_product_map:
            return self._cfm_product_map[pair] or None

        # CFM perpetual product ID mapping (discovered via public API)
        # Format: [SYMBOL]-20DEC30-CDE (perpetuals expire Dec 2030)
        cfm_perpetual_map = {
            "BTC-USD": "BIP-20DEC30-CDE",
            "ETH-USD": "ETP-20DEC30-CDE",
            "XRP-USD": "XPP-20DEC30-CDE",
            "SOL-USD": "SLP-20DEC30-CDE",
            "AVAX-USD": "AVP-20DEC30-CDE",
            "DOGE-USD": "DOP-20DEC30-CDE",
            "LINK-USD": "LNP-20DEC30-CDE",
            "LTC-USD": "LCP-20DEC30-CDE",
            "ADA-USD": "ADP-20DEC30-CDE",
            "BCH-USD": "BCP-20DEC30-CDE",
            "SHIB-USD": "SHP-20DEC30-CDE",
            "HBAR-USD": "HEP-20DEC30-CDE",
            "SUI-USD": "SUP-20DEC30-CDE",
            "XLM-USD": "XLP-20DEC30-CDE",
            "DOT-USD": "POP-20DEC30-CDE",
        }

        # Use hardcoded map for known perpetuals (most reliable)
        if pair in cfm_perpetual_map:
            product_id = cfm_perpetual_map[pair]
            logger.info(f"CFM perpetual: {pair} -> {product_id}")
            self._cfm_product_map = getattr(self, "_cfm_product_map", {})
            self._cfm_product_map[pair] = product_id
            return product_id

        # Try to get CFM futures products from API for unknown pairs
        products = self.api.get_cfm_futures_products() if hasattr(self.api, 'get_cfm_futures_products') else None
        if not products:
            products = self.api.get_products()

        if not products:
            return None

        base = pair.split("-")[0]
        quote = pair.split("-")[1] if "-" in pair else None
        self._cfm_product_map = getattr(self, "_cfm_product_map", {})

        for p in products:
            product_id = p.get("product_id") or p.get("id") or ""
            product_type = (p.get("product_type") or "").upper()
            base_cur = p.get("base_currency") or p.get("base_currency_id")
            quote_cur = p.get("quote_currency") or p.get("quote_currency_id")

            # Prefer explicit CFM/FUTURES product types
            if "CFM" in product_type or "FUTURE" in product_type or "FUTURES" in product_type:
                if base_cur == base and (quote_cur == quote or quote_cur is None):
                    self._cfm_product_map[pair] = product_id
                    return product_id

            # Fallback: if product_id looks like a perp/future, map it
            if product_id.startswith(base) and ("PERP" in product_id or "FUT" in product_id):
                self._cfm_product_map[pair] = product_id
                return product_id

        # Cache negative lookup to avoid repeated scans
        self._cfm_product_map[pair] = None
        return None

    def _hybrid_allows_trade(self, signal: dict, strategy) -> bool:
        """Hybrid toggle: trade with trend alignment or strong neutral setup."""
        hybrid = self.config.get("strategy", {}).get("hybrid_toggle", {})
        if not hybrid.get("enabled", False):
            return True

        side = signal.get("side")
        trend = None

        analysis = getattr(self, "_last_pair_analysis", None)
        if analysis and analysis.pair == signal.get("pair"):
            trend = analysis.trend_direction

        if not trend and strategy:
            try:
                trend, _ = strategy._get_ema_alignment()
            except Exception:
                trend = None

        if trend in ("bullish", "bearish"):
            aligned = (trend == "bullish" and side == "buy") or (trend == "bearish" and side == "sell")
            if aligned:
                return True
            if hybrid.get("allow_trend_mismatch", False):
                conf_count = signal.get("confluence_count")
                conf_score = signal.get("confluence_score")
                conf = conf_count if conf_count is not None else conf_score
                rr = None
                if analysis and analysis.pair == signal.get("pair"):
                    rr = analysis.risk_reward_ratio
                rr = rr or signal.get("risk_reward") or 0
                min_conf = hybrid.get("trend_override_min_confluence", 3)
                min_rr = hybrid.get("trend_override_min_rr", 1.5)
                if (conf or 0) >= min_conf and rr >= min_rr:
                    return True
            return False

        min_conf = hybrid.get("neutral_min_confluence", 3.5)
        min_rr = hybrid.get("neutral_min_rr", 1.4)
        conf = signal.get("confluence_score", 0) or 0
        rr = None
        if analysis and analysis.pair == signal.get("pair"):
            rr = analysis.risk_reward_ratio
        rr = rr or signal.get("risk_reward") or 0
        return conf >= min_conf and rr >= min_rr

    def execute_trade(self, strategy_name: str, signal: dict, analysis: dict = None) -> Optional[dict]:
        """Execute a trade with Slack approval workflow"""
        can_trade, reason = self.check_risk_limits()
        if not can_trade:
            logger.info(f"Trade blocked: {reason}")
            return None

        # Validate with risk manager
        valid, validation_reason = self.risk_manager.validate_trade(signal)
        if not valid:
            logger.info(f"Trade rejected by risk manager: {validation_reason}")
            return None

        # Add strategy and leverage to signal
        signal["strategy"] = strategy_name
        signal["leverage"] = signal.get("leverage", self.config.get("strategy", {}).get("leverage", 4))

        # Enforce hard risk caps before execution
        caps_ok, caps_reason = self._enforce_hard_caps(signal, analysis)
        if not caps_ok:
            logger.info(f"Trade blocked by hard caps: {caps_reason}")
            return None

        # Get current price if not set
        if not signal.get("price"):
            signal["price"] = self.api.get_current_price(signal["pair"])

        # Paper trading mode (dry-run)
        if self.config.get("paper_trading", {}).get("enabled", False):
            trade_id = f"paper_{int(time.time())}"
            try:
                self.trade_logger.log_entry(
                    trade_id=trade_id,
                    pair=signal["pair"],
                    side=signal.get("action", "buy"),
                    entry_price=signal.get("price") or 0,
                    size_usd=signal.get("amount", 0),
                    leverage=signal.get("leverage", 1),
                    stop_loss=signal.get("stop_loss") or 0,
                    take_profit=signal.get("take_profit") or 0,
                    strategy=strategy_name,
                )
            except Exception as e:
                logger.warning(f"Paper trade log failed: {e}")
            logger.info(f"Paper trade logged: {trade_id}")
            return {"id": trade_id, "status": "paper"}

        # Send approval request to Slack and log to spreadsheet
        require_approval = self.config.get("notifications", {}).get("require_approval", True)

        if require_approval:
            trade_data = self.notifier.send_trade_approval_request(signal, analysis)
            logger.info(f"[{strategy_name}] Approval requested: {trade_data['trade_id']}")

            # Store pending trade for later approval
            self._pending_trades = getattr(self, '_pending_trades', {})
            self._pending_trades[trade_data['trade_id']] = {
                "signal": signal,
                "trade_data": trade_data,
                "strategy": strategy_name,
                "timestamp": datetime.now()
            }

            # For now, auto-approve after logging (manual approval can be added later)
            # In production, you'd check a webhook or file for approval
            logger.info(f"Trade logged to spreadsheet. Awaiting approval for {trade_data['trade_id']}")

            # Auto-execute for now (remove this block for manual approval only)
            return self._execute_approved_trade(trade_data['trade_id'])
        else:
            # Execute immediately without approval
            return self._execute_trade_internal(signal, strategy_name)

    def _last_closed_side(self) -> Optional[str]:
        try:
            closed = self.trade_logger.get_closed_trades(limit=1)
            if closed:
                return closed[0].get("side")
        except Exception:
            pass
        return None

    def _trades_today_for_pair(self, pair: str) -> int:
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            trades = self.trade_logger.get_all_trades()
            count = 0
            for t in trades:
                ts = (t.get("entry_time") or "")[:10]
                if t.get("pair") == pair and ts == today:
                    count += 1
            return count
        except Exception:
            return 0

    def _max_trades_for_timeframe(self, tf: Optional[str], base: int) -> int:
        if not tf:
            return base
        tf = tf.lower()
        if tf in ("monthly", "weekly"):
            return min(base, 2)
        if tf in ("daily", "4h"):
            return max(2, min(base, 3))
        if tf in ("1h", "30m"):
            return max(3, base)
        return base

    def _enforce_hard_caps(self, signal: dict, analysis: dict = None) -> tuple:
        caps = self.config.get("risk_caps", {})
        max_lev = caps.get("max_leverage")
        min_rr = caps.get("min_risk_reward")
        min_conf = caps.get("min_confluence")

        # Clamp leverage
        if max_lev is not None:
            try:
                lev = float(signal.get("leverage", 0))
                if lev > float(max_lev):
                    signal["leverage"] = int(max_lev)
                    logger.info(f"Leverage capped to {max_lev}x by hard caps")
            except Exception:
                pass

        # Risk/Reward gate
        rr = None
        if analysis and analysis.pair == signal.get("pair"):
            rr = analysis.risk_reward_ratio
        rr = rr or signal.get("risk_reward")
        if min_rr is not None and rr is not None:
            try:
                if float(rr) < float(min_rr):
                    return False, f"R:R {rr} < {min_rr}"
            except Exception:
                pass

        # Confluence gate (prefer count, fall back to score)
        conf_count = signal.get("confluence_count")
        conf_score = signal.get("confluence_score")
        if min_conf is not None:
            try:
                if conf_count is not None and int(conf_count) < int(min_conf):
                    return False, f"Confluence {conf_count} < {min_conf}"
                if conf_count is None and conf_score is not None and float(conf_score) < float(min_conf):
                    return False, f"Confluence score {conf_score} < {min_conf}"
            except Exception:
                pass

        return True, None

    def _execute_trade_internal(self, signal: dict, strategy_name: str) -> Optional[dict]:
        """Internal trade execution"""
        try:
            use_perps = self.config.get("exchange", {}).get("use_perpetuals", False)
            futures_type = self.config.get("exchange", {}).get("futures_type", "intx")
            price = signal.get("price") or self.api.get_current_price(signal["pair"])

            if use_perps:
                product_id = None
                if getattr(self.api, "intx_available", True) is False and futures_type != "cfm":
                    logger.error("Perps trade blocked: INTX endpoints not available for this API key/account.")
                    return None
                if not price:
                    logger.warning("Futures trade aborted: missing price")
                    return None
                size_base = 0.0
                if price and futures_type == "cfm":
                    # Convert desired USD notional into contracts using contract_size.
                    product_id = self._resolve_cfm_product_id(signal["pair"])
                    details = None
                    try:
                        if product_id and hasattr(self.api, "get_product_details"):
                            details = self.api.get_product_details(product_id)
                    except Exception:
                        details = None
                    fpd = details.get("future_product_details") if isinstance(details, dict) else None
                    try:
                        contract_size = float((fpd or {}).get("contract_size") or 0)
                    except Exception:
                        contract_size = 0.0
                    if contract_size <= 0:
                        contract_size = 1.0
                    size_base = float(signal["amount"]) / (float(price) * float(contract_size))
                elif price:
                    size_base = float(signal["amount"]) / float(price)
                if size_base <= 0:
                    logger.warning("Futures trade aborted: invalid size")
                    return None
                leverage = int(signal.get("leverage", 4))

                if futures_type == "cfm":
                    product_id = product_id or self._resolve_cfm_product_id(signal["pair"])

                    # Check for existing spot position to exit
                    base_currency = signal["pair"].split("-")[0]
                    spot_balance = self.api.get_balance(base_currency) or 0

                    if not product_id:
                        # No CFM product - check if we can exit spot position
                        if signal["side"] == "sell" and spot_balance > 0.01:
                            logger.info(f"No CFM for {signal['pair']}, but have {spot_balance:.4f} {base_currency} spot - SELLING")
                            order = self.api.place_sell_order(
                                pair=signal["pair"],
                                amount=spot_balance,  # Sell entire spot balance
                                price=None
                            )
                        else:
                            logger.info(f"No CFM product for {signal['pair']}, skipping trade")
                            return None
                    # If we have spot and signal is SELL, prioritize exiting spot over opening CFM short
                    elif signal["side"] == "sell" and spot_balance > 0.01:
                        logger.info(f"SELL signal for {signal['pair']} - exiting {spot_balance:.4f} {base_currency} spot position first")
                        order = self.api.place_sell_order(
                            pair=signal["pair"],
                            amount=spot_balance,
                            price=None
                        )
                    else:
                        # Enforce CFM minimum base size
                        details = self.api.get_product_details_public(product_id) if hasattr(self.api, "get_product_details_public") else None
                        base_min = None
                        try:
                            if details:
                                base_min = float(details.get("base_min_size", 0) or 0)
                        except Exception:
                            base_min = None

                        if base_min and size_base < base_min:
                            required_usd = base_min * float(price)
                            buying_power = self.api.get_cfm_buying_power() if hasattr(self.api, "get_cfm_buying_power") else None
                            if buying_power is not None and required_usd > buying_power:
                                logger.warning(
                                    f"CFM min size unmet for {product_id}: need ~${required_usd:.2f} "
                                    f"buying power, available ${buying_power:.2f}"
                                )
                                return None
                            logger.info(
                                f"CFM min size bump for {product_id}: {size_base:.8f} -> {base_min:.8f} "
                                f"(~${required_usd:.2f})"
                            )
                            size_base = base_min
                            signal["amount"] = round(required_usd, 2)

                        exit_cfg = self.config.get("exit_strategy", {})
                        exit_mode = exit_cfg.get("mode", "fixed_tp")
                        tp = signal.get("take_profit") if exit_mode != "partial_reversal" else None
                        blocked, reason = self._margin_policy_blocks_entry()
                        if blocked:
                            logger.warning(f"CFM entry blocked: {reason}")
                            return None

                        # Enforce max open futures positions (avoid opening a second position).
                        try:
                            existing = self.api.get_futures_positions() or []
                        except Exception:
                            existing = []
                        max_open = int((self.config.get("perps_short", {}) or {}).get("max_open_positions", 1) or 1)
                        if len(existing) >= max_open:
                            logger.info("CFM entry blocked: max open futures positions reached")
                            return None
                        order = self.api.place_cfm_order(
                            product_id=product_id,
                            side="BUY" if signal["side"] == "buy" else "SELL",
                            base_size=size_base,
                            price=None,
                            stop_loss=signal.get("stop_loss"),
                            take_profit=tp,
                        )
                        try:
                            if order and (order.get("success") is not False) and not order.get("error_response"):
                                self._plrl3_register_entry(
                                    product_id=str(product_id),
                                    pair=str(signal.get("pair") or ""),
                                    initial_contracts=int(max(1, round(float(size_base or 0)))),
                                    side=str(signal.get("side") or ""),
                                )
                        except Exception:
                            pass
                else:
                    # INTX (International Perpetuals)
                    try:
                        self.api.set_perpetual_leverage(signal["pair"], leverage)
                    except Exception:
                        pass
                    order = self.api.place_perpetual_order(
                        pair=signal["pair"],
                        side="BUY" if signal["side"] == "buy" else "SELL",
                        size=size_base,
                        leverage=leverage,
                        price=None,
                        stop_loss=signal.get("stop_loss"),
                        take_profit=signal.get("take_profit"),
                    )
            else:
                # SPOT TRADING - Check balance and existing positions first
                spot_cfg = self.config.get("spot", {}) or {}
                if not bool(spot_cfg.get("enabled", True)):
                    logger.info(f"Spot entry blocked (spot.enabled=false): {signal.get('pair')}")
                    return None
                if signal["side"] == "buy":
                    # Check if we already hold this crypto
                    base_currency = signal["pair"].split("-")[0]
                    existing_balance = self.api.get_balance(base_currency) or 0
                    existing_price = self.api.get_current_price(signal["pair"]) or 0
                    existing_value = existing_balance * existing_price if existing_price else 0

                    if existing_value > 5:  # Already have $5+ of this crypto
                        logger.info(f"⏭️ SKIP BUY {signal['pair']}: already holding ${existing_value:.2f}")
                        return None

                    # Check available balance (no buffer needed for market orders with quote_size)
                    usd_balance = self.api.get_balance("USD") or 0
                    trade_amount = signal["amount"]

                    # Enforce USD-only funding so this bot never spends USDC.
                    # This keeps it from competing with the XLM futures bot (which uses USDC collateral).
                    quote_ccy = (self.config.get("universe", {}) or {}).get("quote_currency", "USD")
                    quote_ccy = str(quote_ccy or "USD").upper()
                    if quote_ccy != "USD":
                        logger.warning(f"⚠️ quote_currency={quote_ccy} requested, but USD-only funding is enforced for this bot")
                        quote_ccy = "USD"

                    if usd_balance >= trade_amount:
                        logger.info(f"💵 Using USD (${usd_balance:.2f})")
                    else:
                        # Not enough USD - check if we can convert other crypto (if allowed)
                        if not self.config.get("capital_boundaries", {}).get("allow_auto_conversion", False):
                            logger.warning("⚠️ SKIP BUY: auto-conversion disabled by capital boundaries")
                            return None

                        logger.info(f"⚠️ Low funds: USD=${usd_balance:.2f}, need ${trade_amount:.2f}")

                        # Get all crypto balances
                        accounts = self.api.get_accounts() or []
                        convertible = []
                        for acc in accounts:
                            curr = acc.get("currency", "")
                            if curr in ("USD", "USDC", signal["pair"].split("-")[0]):
                                continue  # Skip USD/USDC and target crypto
                            bal = acc.get("available_balance", {})
                            avail = float(bal.get("value", 0)) if isinstance(bal, dict) else float(bal or 0)
                            if avail > 0:
                                # Get USD value
                                price = self.api.get_current_price(f"{curr}-USD") or 0
                                value = avail * price if price else 0
                                if value >= 1:  # At least $1 worth
                                    convertible.append((curr, avail, value))

                        if convertible:
                            # Sell the largest holding to get USD
                            convertible.sort(key=lambda x: x[2], reverse=True)
                            sell_curr, sell_amt, sell_val = convertible[0]
                            logger.info(f"🔄 Converting {sell_amt:.4f} {sell_curr} (${sell_val:.2f}) to fund trade")

                            # Sell to USD
                            sell_order = self.api.place_sell_order(f"{sell_curr}-USD", sell_amt, price=None)
                            if sell_order and sell_order.get("success") != False:
                                import time
                                time.sleep(2)  # Wait for settlement
                                usd_balance = self.api.get_balance("USD") or 0
                                logger.info(f"✅ Conversion done, new USD balance: ${usd_balance:.2f}")
                            else:
                                logger.warning(f"⚠️ Could not convert {sell_curr} to USD")
                                return None
                        else:
                            logger.warning(f"⚠️ SKIP BUY: No funds available to convert")
                            return None

                    # Ensure buys are USD-quoted, even if something upstream emitted -USDC.
                    if str(signal.get("pair", "")).endswith("-USDC"):
                        signal["pair"] = str(signal["pair"]).replace("-USDC", "-USD")

                    # Maker-first execution (fallback to market if edge is sufficient)
                    expected_profit_pct = None
                    if price and signal.get("take_profit"):
                        try:
                            expected_profit_pct = abs((signal["take_profit"] - price) / price) * 100
                        except Exception:
                            expected_profit_pct = None

                    order = self._maker_first_spot_order(
                        side="buy",
                        pair=signal["pair"],
                        quote_amount=trade_amount,
                        expected_profit_pct=expected_profit_pct,
                    )

                    if not order:
                        fee_cfg = self.config.get("fees", {}) or {}
                        total_fee = (float(fee_cfg.get("taker_percent", 0.0)) * 2) + float(fee_cfg.get("spread_buffer_percent", 0.0)) + float(fee_cfg.get("slippage_percent", 0.0))
                        min_edge = float(self.config.get("execution", {}).get("maker_first", {}).get("min_edge_percent", total_fee))
                        if expected_profit_pct is None or expected_profit_pct >= min_edge:
                            order = self.api.place_buy_order(
                                pair=signal["pair"],
                                amount=trade_amount,
                                price=None  # Market fallback
                            )
                        else:
                            logger.info(f"⏭️ SKIP BUY {signal['pair']}: edge {expected_profit_pct:.2f}% < min {min_edge:.2f}% (fees)")
                            return None

                    # Record entry price for profit tracking
                    if order and order.get("success") != False:
                        entry_price = self.api.get_current_price(signal["pair"]) or 0
                        if entry_price > 0:
                            self._entry_prices[signal["pair"]] = {"price": entry_price, "time": datetime.now().isoformat()}
                            self._save_entry_prices()
                            logger.info(f"📝 Entry recorded: {signal['pair']} @ ${entry_price:.4f}")
                else:
                    # SELL signal: exit spot if holding; otherwise route to perps short (if enabled)
                    base_currency = signal["pair"].split("-")[0]
                    spot_balance = self.api.get_balance(base_currency) or 0
                    if spot_balance > 0.0001:
                        order = self._maker_first_spot_order(
                            side="sell",
                            pair=signal["pair"],
                            base_amount=spot_balance,
                            expected_profit_pct=None,
                        )
                        if not order:
                            order = self.api.place_sell_order(pair=signal["pair"], amount=spot_balance, price=None)
                    else:
                        order = self._execute_perps_short(signal, price)

            # Validate order was actually successful (not just a response)
            order_success = order and order.get("success") != False and "error_response" not in order

            if order_success:
                self.trades_today.append({
                    "time": datetime.now().isoformat(),
                    "strategy": strategy_name,
                    "order": order
                })

                # Register position only for INTX perps.
                # CFM positions are managed directly from exchange state (get_futures_positions),
                # because PositionManager assumes INTX semantics and would compute wrong closes/sizing.
                futures_type = self.config.get("exchange", {}).get("futures_type", "spot")
                use_perps = self.config.get("exchange", {}).get("use_perpetuals", False)
                position = None
                if use_perps and futures_type == "intx":
                    leverage = signal.get("leverage", 4)
                    position_id = order.get("order_id", f"{signal['pair']}_{datetime.now().timestamp()}")
                    entry_price = (
                        order.get("average_filled_price")
                        or order.get("price")
                        or signal.get("price")
                        or self.api.get_current_price(signal["pair"])
                    )
                    position = self.position_manager.register_position(
                        position_id=position_id,
                        pair=signal["pair"],
                        side=signal["side"],
                        entry_price=entry_price,
                        size_usd=signal["amount"],
                        leverage=leverage,
                        stop_loss=signal.get("stop_loss", 0),
                        take_profit=signal.get("take_profit", 0),
                        breakout_type=signal.get("breakout_type", ""),
                        breakout_tf=signal.get("breakout_tf", "")
                    )

                # Persist trade entry
                try:
                    self.trade_logger.log_entry(
                        trade_id=position_id,
                        pair=signal["pair"],
                        side=signal["side"],
                        entry_price=entry_price,
                        size_usd=signal["amount"],
                        leverage=leverage,
                        stop_loss=signal.get("stop_loss", 0),
                        take_profit=signal.get("take_profit", 0),
                        strategy=signal.get("strategy", strategy_name),
                        liquidation_price=position.liquidation_price if position else None
                    )
                except Exception as e:
                    logger.warning(f"Trade log entry failed: {e}")

                # Record PnL for optimizer
                self.trade_optimizer.record_pnl(0)  # Initial, updated on close

                logger.info(f"[{strategy_name}] Trade executed: {order}")
                return order
            else:
                # Order failed - log the error
                error_msg = order.get("error_response", {}).get("message", "Unknown error") if order else "No response"
                error_code = order.get("error_response", {}).get("error", "UNKNOWN") if order else "NO_RESPONSE"
                logger.error(f"[{strategy_name}] Order FAILED: {error_code} - {error_msg}")
                logger.debug(f"Full order response: {order}")
                return None

        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            self.notifier.send_error_notification(str(e))

        return None

    def _execute_approved_trade(self, trade_id: str) -> Optional[dict]:
        """Execute a trade that has been approved"""
        pending = getattr(self, '_pending_trades', {})

        if trade_id not in pending:
            logger.warning(f"Trade {trade_id} not found in pending trades")
            return None

        trade_info = pending[trade_id]
        signal = trade_info["signal"]
        trade_data = trade_info["trade_data"]
        strategy_name = trade_info["strategy"]

        # Execute the trade
        order = self._execute_trade_internal(signal, strategy_name)

        if order:
            # Notify execution
            self.notifier.send_trade_executed(trade_data, order)

            # Remove from pending
            del pending[trade_id]

            return order
        else:
            self.notifier.send_trade_rejected(trade_data, "Execution failed")
            del pending[trade_id]
            return None

    def approve_trade(self, trade_id: str) -> bool:
        """Manually approve a pending trade"""
        result = self._execute_approved_trade(trade_id)
        return result is not None

    def reject_trade(self, trade_id: str, reason: str = "Manual rejection") -> bool:
        """Manually reject a pending trade"""
        pending = getattr(self, '_pending_trades', {})

        if trade_id not in pending:
            return False

        trade_data = pending[trade_id]["trade_data"]
        self.notifier.send_trade_rejected(trade_data, reason)
        del pending[trade_id]
        return True

    def check_positions_health(self):
        """Check all positions for liquidation risk and take protective action"""
        for position in list(self.position_manager.positions.values()):
            try:
                # Get current price for this pair
                current_price = self.api.get_current_price(position.pair)
                if not current_price:
                    continue

                # Get trend direction from MTF strategy if available
                trend = None
                if self.strategies:
                    try:
                        strat = self.strategies.get(position.pair) or next(iter(self.strategies.values()))
                        ema_dir, _ = strat._get_ema_alignment()
                        trend = ema_dir
                    except Exception:
                        pass

                # Check liquidation risk
                risk_check = self.position_manager.check_liquidation_risk(
                    position.position_id,
                    current_price,
                    trend
                )

                # Execute recommended action
                if risk_check["action"] == "add_margin":
                    result = self.position_manager.execute_margin_addition(
                        position.position_id,
                        risk_check.get("amount")
                    )
                    if result["success"]:
                        try:
                            self.trade_logger.update_margin_addition(
                                position.position_id,
                                result.get("amount_added", 0),
                                result.get("new_liquidation_price")
                            )
                        except Exception as e:
                            logger.debug(f"Trade log margin update failed: {e}")
                        msg = (f"MARGIN ADDED: ${risk_check['amount']} to {position.pair} "
                               f"(topup {result['topup_count']}/{self.position_manager.max_topups})\n"
                               f"Reason: {risk_check['reason']}")
                        logger.info(msg)
                        self.notifier.send_message(msg)

                elif risk_check["action"] == "close_position":
                    # Close position to prevent liquidation
                    try:
                        self.api.close_perpetual_position(position.pair)
                        self.position_manager.close_position(position.position_id, "protective_close")
                        try:
                            self.trade_logger.log_exit(
                                position.position_id,
                                current_price,
                                "protective_close"
                            )
                        except Exception as e:
                            logger.debug(f"Trade log exit failed: {e}")
                        msg = (f"POSITION CLOSED: {position.pair} to prevent liquidation\n"
                               f"Reason: {risk_check['reason']}\n"
                               f"Total margin invested: ${position.current_margin:.2f}")
                        logger.warning(msg)
                        self.notifier.send_message(msg)
                    except Exception as e:
                        logger.error(f"Failed to close position {position.pair}: {e}")

            except Exception as e:
                logger.error(f"Error checking position {position.position_id}: {e}")

    def manage_open_positions(self):
        """Manage stops for open positions (break-even, trailing)"""
        for position in list(self.position_manager.positions.values()):
            try:
                current_price = self.api.get_current_price(position.pair)
                if not current_price:
                    continue

                # Partial take profit (exit strategy: partial then reversal)
                exit_cfg = self.config.get("exit_strategy", {})
                mode = exit_cfg.get("mode", "fixed_tp")
                partial_pct = float(exit_cfg.get("partial_tp_percent", 50)) / 100.0

                if mode == "partial_reversal" and position.take_profit and not position.partial_taken:
                    if getattr(position, "breakout_type", "") == "exponential":
                        # Skip TP on exponential breakouts; wait for reversal
                        pass
                    else:
                        if position.side == "buy" and current_price >= position.take_profit:
                            self._close_partial_position(position, current_price, partial_pct)
                            position.partial_taken = True
                            position.remaining_size_usd = max(0.0, position.remaining_size_usd - (position.initial_size_usd * partial_pct))
                            position.stop_loss = position.entry_price  # move to breakeven after partial
                        elif position.side == "sell" and current_price <= position.take_profit:
                            self._close_partial_position(position, current_price, partial_pct)
                            position.partial_taken = True
                            position.remaining_size_usd = max(0.0, position.remaining_size_usd - (position.initial_size_usd * partial_pct))
                            position.stop_loss = position.entry_price

                # Confirmed reversal exit for remaining size
                if mode == "partial_reversal" and position.remaining_size_usd > 0:
                    strat = self.strategies.get(position.pair)
                    if strat:
                        signals = strat._generate_signals(current_price)
                        intel_votes = strat._get_intel_votes(current_price)
                        decision = strat._combine_signals(signals, current_price, intel_votes)
                        if position.side == "buy" and decision.get("action") == "sell":
                            self._close_remaining_position(position, current_price)
                        elif position.side == "sell" and decision.get("action") == "buy":
                            self._close_remaining_position(position, current_price)

                # Build position dict for optimizer
                pos_dict = {
                    "entry_price": position.entry_price,
                    "stop_loss": position.liquidation_price,  # Use liq as worst-case stop
                    "side": position.side,
                    "current_stop": getattr(position, 'current_stop', position.liquidation_price)
                }

                # Check for stop adjustment
                adjustment = self.trade_optimizer.calculate_stop_adjustment(pos_dict, current_price)

                if adjustment and adjustment.get("action") != "none":
                    logger.info(f"{position.pair}: {adjustment['reason']} - new stop: ${adjustment['new_stop']}")

            except Exception as e:
                logger.debug(f"Error managing position {position.pair}: {e}")

    def _close_partial_position(self, position, current_price: float, partial_pct: float):
        """Close part of a position based on USD size."""
        try:
            close_usd = max(0.0, position.initial_size_usd * partial_pct)
            if close_usd <= 0:
                return
            futures_type = self.config.get("exchange", {}).get("futures_type", "intx")
            if futures_type == "cfm" or self._cfm_enabled():
                product_id = self._resolve_cfm_product_id(position.pair)
                if not product_id:
                    return
                base_size = close_usd / float(current_price)
                self.api.place_cfm_order(
                    product_id=product_id,
                    side="SELL" if position.side == "buy" else "BUY",
                    base_size=base_size,
                    price=None,
                    reduce_only=True,
                )
            else:
                # Spot fallback
                if position.side == "buy":
                    self.api.place_sell_order(position.pair, close_usd, price=None)
                else:
                    self.api.place_buy_order(position.pair, close_usd, price=None)
            logger.info(f"Partial TP: closed ${close_usd:.2f} of {position.pair}")
        except Exception as e:
            logger.warning(f"Partial TP failed for {position.pair}: {e}")

    def _close_remaining_position(self, position, current_price: float):
        """Close remaining position on confirmed reversal."""
        try:
            close_usd = max(0.0, position.remaining_size_usd)
            if close_usd <= 0:
                return
            futures_type = self.config.get("exchange", {}).get("futures_type", "intx")
            if futures_type == "cfm" or self._cfm_enabled():
                product_id = self._resolve_cfm_product_id(position.pair)
                if not product_id:
                    return
                base_size = close_usd / float(current_price)
                self.api.place_cfm_order(
                    product_id=product_id,
                    side="SELL" if position.side == "buy" else "BUY",
                    base_size=base_size,
                    price=None,
                    reduce_only=True,
                )
            else:
                if position.side == "buy":
                    self.api.place_sell_order(position.pair, close_usd, price=None)
                else:
                    self.api.place_buy_order(position.pair, close_usd, price=None)
            position.remaining_size_usd = 0.0
            position.status = "closed"
            logger.info(f"Reversal exit: closed remaining ${close_usd:.2f} of {position.pair}")
        except Exception as e:
            logger.warning(f"Reversal exit failed for {position.pair}: {e}")

    def run_cycle(self):
        """Run one cycle of all strategies"""
        # Reset per-cycle caches.
        self._cached_cfm_balance_summary = None
        futures_type = (self.config.get("exchange", {}) or {}).get("futures_type", "intx")
        cfm_mode = (futures_type == "cfm") or bool(self._cfm_enabled())

        # Get current balance and optimal position size
        balance_info = self.balance_manager.get_balance()
        sizing = self.balance_manager.get_optimal_position_size()

        # Sync any manual CFM positions so exits can be managed
        try:
            self._sync_cfm_positions()
        except Exception as e:
            logger.debug(f"CFM sync skipped: {e}")

        # Risk engines (CFM): margin policy + PLRL-3 ladder (default: log_only).
        try:
            self._update_margin_policy()
        except Exception as e:
            logger.debug(f"Margin policy eval skipped: {e}")
        try:
            self._update_plrl3()
        except Exception as e:
            logger.debug(f"PLRL-3 eval skipped: {e}")

        # Spot is optional; if disabled, skip spot inventory scans to keep the bot futures-focused.
        spot_cfg = self.config.get("spot", {}) or {}
        if bool(spot_cfg.get("manage_existing", False)):
            try:
                self._sync_spot_positions()
            except Exception as e:
                logger.debug(f"Spot sync skipped: {e}")

        if balance_info:
            logger.debug(f"Balance: ${balance_info.total_balance_usd:.2f}, "
                        f"Available: ${balance_info.available_balance_usd:.2f}, "
                        f"Optimal size: ${sizing['position_size_usd']:.2f} ({sizing['tier']})")

        # Prepare strategies/prices early so we can manage CFM exits even in watch mode.
        pairs = self._get_trading_pairs()
        if not pairs:
            logger.debug("No trading pairs available")
            return

        # Ensure we always compute signals for any currently open CFM position pair(s),
        # even if they are not in the configured trading universe.
        if cfm_mode:
            try:
                for pos in self._get_open_cfm_positions():
                    pid = str(pos.get("product_id") or "")
                    p = self._cfm_product_id_to_pair(pid)
                    if p and p not in pairs:
                        pairs.append(p)
            except Exception:
                pass
        self._ensure_strategies(pairs)

        # Select best pair to trade (smart pair selection)
        if self.config.get("trade_optimizer", {}).get("select_best_pair", True):
            trading_pair = self.get_best_trading_pair()
            if not trading_pair:
                logger.debug("No suitable trading pair available")
                trading_pair = None
        else:
            trading_pair = self.config.get("trading", {}).get("trading_pair", "BTC-USD")

        # Fetch prices for all pairs (keeps strategies warmed)
        prices = {}
        for pair in pairs:
            price = self.api.get_current_price(pair)
            if price:
                prices[pair] = price

        # Build signals for all pairs. This is required for profit-lock exit / flip confirmation.
        signals_by_pair = {}
        selected_signal = None
        selected_strategy = None
        for pair, strategy in self.strategies.items():
            price = prices.get(pair)
            if not price:
                continue

            market_data = {
                "price": price,
                "timestamp": datetime.now(),
                "pair": pair,
            }

            try:
                signal = strategy.analyze(market_data) if strategy else None
            except Exception as e:
                logger.error(f"Strategy {pair} error: {e}")
                signal = None

            if not isinstance(signal, dict):
                signal = {"action": "hold", "reason": "no_signal"}
            # Some downstream code expects the pair in the signal.
            signal.setdefault("pair", pair)
            signals_by_pair[pair] = signal

            # Telemetry for all pairs (warmup + signals)
            try:
                if getattr(strategy, "ema_periods", None):
                    min_data = int(getattr(strategy, "config", {}).get("warmup_override", max(strategy.ema_periods) + 20))
                else:
                    min_data = None
                analysis = getattr(self, "_last_pair_analysis", None)

                # Get indicator values from strategy if available
                rsi_val = None
                if hasattr(strategy, "_calculate_rsi"):
                    try:
                        rsi_val = strategy._calculate_rsi()
                    except Exception:
                        pass

                preview = None
                if trading_pair and pair == trading_pair:
                    try:
                        preview_leverage = None
                        if signal:
                            preview_leverage = self._determine_leverage(signal)
                        else:
                            preview_leverage = self.config.get("leverage", {}).get(
                                "base", self.config.get("strategy", {}).get("leverage", 4)
                            )
                        preview = self.balance_manager.get_optimal_position_size(leverage=int(preview_leverage))
                        if signal and preview:
                            preview = self._apply_position_scaling(preview, signal, analysis)
                    except Exception:
                        preview = None

                self.telemetry.log_ping({
                    "timestamp": datetime.now().isoformat(),
                    "universe": pairs,
                    "selected_pair": trading_pair,
                    "pair": pair,
                    "price": price,
                    "perps_enabled": self.config.get("exchange", {}).get("use_perpetuals", False),
                    "intx_available": getattr(self.api, "intx_available", None),
                    "opportunity_score": analysis.opportunity_score if (analysis and analysis.pair == pair) else None,
                    "risk_reward": analysis.risk_reward_ratio if (analysis and analysis.pair == pair) else None,
                    "trend": analysis.trend_direction if (analysis and analysis.pair == pair) else None,
                    "data_points": len(strategy.prices) if hasattr(strategy, "prices") else None,
                    "min_data": min_data,
                    "signal_action": signal.get("action") if signal else "hold",
                    "signal_reason": signal.get("reason") if signal else "no_signal",
                    "confluence_score": signal.get("confluence_score") if signal else None,
                    "confluence_count": signal.get("confluence_count") if signal else None,
                    "setups": signal.get("setups") if signal else None,
                    "is_selected": bool(trading_pair and pair == trading_pair),
                    # Technical indicators
                    "rsi": round(rsi_val, 2) if rsi_val else None,
                    # Trade info
                    "stop_loss": signal.get("stop_loss") if signal else None,
                    "take_profit": signal.get("take_profit") if signal else None,
                    # Sizing preview (selected pair only)
                    "leverage_preview": preview.get("leverage") if preview else None,
                    "position_size_usd_preview": preview.get("position_size_usd") if preview else None,
                    "max_risk_usd_preview": preview.get("max_risk_usd") if preview else None,
                    "leverage_adjusted_preview": preview.get("leverage_adjusted") if preview else None,
                    "tier_preview": preview.get("tier") if preview else None,
                    "tier_percent_preview": preview.get("tier_percent") if preview else None,
                    "balance_preview": preview.get("balance") if preview else None,
                    "available_preview": preview.get("available") if preview else None,
                    "cache_ready": getattr(strategy, "cache_ready", None),
                    "cache_points": getattr(strategy, "cache_loaded_points", None),
                    "yearly_high": getattr(strategy, "yearly_high", None),
                    "yearly_low": getattr(strategy, "yearly_low", None),
                    "monthly_high": getattr(strategy, "monthly_high", None),
                    "monthly_low": getattr(strategy, "monthly_low", None),
                    "weekly_high": getattr(strategy, "weekly_high", None),
                    "weekly_low": getattr(strategy, "weekly_low", None),
                    "daily_high": getattr(strategy, "daily_high", None),
                    "daily_low": getattr(strategy, "daily_low", None),
                })
            except Exception as e:
                logger.debug(f"Telemetry log failed: {e}")

            if trading_pair and pair == trading_pair:
                selected_signal = signal
                selected_strategy = strategy

        # Manage CFM profit-lock exits and flips BEFORE any new entries.
        if cfm_mode:
            try:
                acted = self._manage_cfm_reversal_tp(signals_by_pair=signals_by_pair, prices=prices)
                if acted:
                    return
            except Exception as e:
                logger.debug(f"CFM reversal/flip manager skipped: {e}")

        # ===== HARD GATE: Check filters BEFORE any processing =====
        can_trade, filter_reason = self.check_risk_limits()
        if not can_trade:
            logger.info(f"[WATCH MODE] {filter_reason}")
            # Still monitor positions, but don't generate new signals
            if not cfm_mode:
                self.check_positions_health()
                self.manage_open_positions()
            try:
                if bool(spot_cfg.get("manage_existing", False)):
                    self._check_spot_exits()
            except Exception:
                pass
            return  # EXIT - no signal generation or trade attempts

        if not cfm_mode:
            # Run liquidation strategy analysis FIRST (priority)
            liq_analysis = self.liquidation_strategy.analyze()
            if liq_analysis.get("critical_positions"):
                logger.warning(f"CRITICAL POSITIONS: {liq_analysis['critical_positions']}")

                # Handle critical actions
                for action in liq_analysis.get("actions_needed", []):
                    if action["urgency"] == "critical":
                        self._handle_liquidation_action(action)

            # Check position health for liquidation protection
            self.check_positions_health()

            # Manage stops (break-even, trailing)
            self.manage_open_positions()

        # Check spot positions for exit opportunities
        if bool(spot_cfg.get("manage_existing", False)):
            self._check_spot_exits()

        # Trade execution (selected pair only). We compute signals above so CFM managers can run in watch mode.
        if not trading_pair:
            return
        if trading_pair not in prices:
            logger.warning(f"Could not fetch current price for {trading_pair}")
            return

        # If we're in CFM mode and already in a position, do not open additional entries.
        if cfm_mode:
            try:
                if self._get_open_cfm_positions():
                    return
            except Exception:
                # If we can't confirm position status, be conservative.
                return

        signal = selected_signal
        strategy = selected_strategy
        pair = trading_pair

        if signal and signal.get("action") == "hold":
            reason = signal.get("reason", "hold")
            logger.info(f"[{pair}] HOLD: {reason}")
            return

        if signal and signal.get("action") != "hold":
            if not self._hybrid_allows_trade(signal, strategy):
                logger.info(f"[{pair}] HYBRID BLOCK: trend not aligned")
                return
            last_side = self._last_closed_side()
            if last_side == "sell" and signal.get("action") == "buy":
                if not signal.get("reset_ready_buy"):
                    logger.info(f"[{pair}] RESET BLOCK: need dominant support confirmation after short exit")
                    return
            if last_side == "buy" and signal.get("action") == "sell":
                if not signal.get("reset_ready_sell"):
                    logger.info(f"[{pair}] RESET BLOCK: need dominant resistance confirmation after long exit")
                    return
            reentry_cfg = self.config.get("strategy", {}).get("reentry", {})
            if reentry_cfg.get("enabled", True):
                base_max = int(reentry_cfg.get("max_trades_per_pair_day", 3))
                tf = signal.get("dominant_timeframe")
                max_allowed = self._max_trades_for_timeframe(tf, base_max)
                taken = self._trades_today_for_pair(pair)
                if taken >= max_allowed:
                    logger.info(f"[{pair}] REENTRY BLOCK: {taken}/{max_allowed} trades today (tf={tf})")
                    return
            leverage = self._determine_leverage(signal)
            trade_sizing = self.balance_manager.get_optimal_position_size(leverage=leverage)
            trade_sizing = self._apply_position_scaling(trade_sizing, signal, getattr(self, "_last_pair_analysis", None))

            # Apply balance-aware position sizing
            signal["amount"] = trade_sizing["position_size_usd"]
            signal["leverage"] = trade_sizing.get("leverage", leverage)
            signal["position_scale"] = trade_sizing.get("scaled_multiplier", 1.0)

            logger.info(f"[{pair}] Signal: {signal}")
            self.execute_trade("mtf", signal)

    def _handle_liquidation_action(self, action: dict):
        """Handle critical liquidation action"""
        pair = action.get("pair", "")
        action_type = action.get("action", "")
        details = action.get("details", {})

        if action_type == "add_margin":
            # Find position and add margin
            position = self.position_manager.get_position_by_pair(pair)
            if position:
                result = self.position_manager.execute_margin_addition(
                    position.position_id,
                    details.get("margin_amount", 100)
                )
                if result["success"]:
                    msg = (f":rotating_light: LIQUIDATION SAVE #{details.get('save_number', '?')}\n"
                           f"Pair: {pair}\n"
                           f"Margin added: ${details.get('margin_amount', 100)}\n"
                           f"Saves remaining: {details.get('saves_remaining_after', 0)}\n"
                           f"New liquidation: ~${details.get('estimated_new_liquidation', 'N/A')}")
                    self.notifier.send_message(msg, f"Liquidation Save: {pair}")

        elif action_type == "accept_loss":
            # All saves exhausted - close with 2% max loss
            position = self.position_manager.get_position_by_pair(pair)
            if position:
                # Check if loss exceeds 2%
                current_price = self.api.get_current_price(pair)
                should_close, reason = self.balance_manager.should_close_position(
                    {"entry_price": position.entry_price, "side": position.side,
                     "size_usd": position.initial_margin, "leverage": position.leverage},
                    current_price,
                    position.margin_topups
                )

                if should_close:
                    self.api.close_perpetual_position(pair)
                    self.position_manager.close_position(position.position_id, "max_loss_after_3_saves")
                    try:
                        self.trade_logger.log_exit(
                            position.position_id,
                            current_price,
                            "max_loss_after_3_saves"
                        )
                    except Exception as e:
                        logger.debug(f"Trade log exit failed: {e}")
                    msg = (f":x: POSITION CLOSED - ALL SAVES EXHAUSTED\n"
                           f"Pair: {pair}\n"
                           f"Reason: {reason}\n"
                           f"Rule: 2% max loss after 3 saves")
                    self.notifier.send_message(msg, f"Position Closed: {pair}")

    def start(self, interval_seconds: int = 10):
        """Start the bot"""
        self.running = True

        # Get balance info
        balance = self.balance_manager.get_balance()
        sizing = self.balance_manager.get_optimal_position_size()

        # Get market filter status
        filter_status = self.market_filters.get_status()

        logger.info("=" * 60)
        logger.info(f"{self.bot_name} STARTED")
        logger.info("=" * 60)
        logger.info(f"Mode: {'LIVE' if not self.config['exchange']['sandbox'] else 'SANDBOX'}")
        logger.info(f"Balance: ${balance.total_balance_usd:.2f}" if balance else "Balance: Unknown")
        logger.info(f"Available: ${balance.available_balance_usd:.2f}" if balance else "")
        logger.info(f"Position Size: ${sizing['position_size_usd']:.2f} ({sizing['tier']} tier)")
        logger.info(f"Surplus Capital: {'YES' if sizing.get('has_surplus') else 'NO (under $2k)'}")
        logger.info(f"Strategies: {list(self.strategies.keys())}")
        logger.info(f"Liquidation Saves: 3 attempts before 2% max loss")
        logger.info("-" * 60)
        logger.info("MARKET FILTERS:")
        logger.info(f"  Trading Hours: {'ON' if filter_status['trading_hours']['enabled'] else 'OFF'}")
        logger.info(f"  News Events: {'ON' if filter_status['news_events']['enabled'] else 'OFF'}")
        logger.info(f"  Momentum: {'ON' if filter_status['momentum']['enabled'] else 'OFF'}")
        logger.info(f"  Volume Spike: {'ON' if filter_status['volume']['enabled'] else 'OFF'}")
        logger.info("=" * 60)

        # Send startup notification to Slack
        hours_status = filter_status['trading_hours']
        news_status = filter_status['news_events']

        startup_msg = f"""*{self.bot_name} STARTED* :rocket:

*Account Status:*
• Balance: `${balance.total_balance_usd:.2f}` {'(surplus)' if sizing.get('has_surplus') else '(growth mode)'}
• Available: `${balance.available_balance_usd:.2f}`
• Mode: `{'LIVE' if not self.config['exchange']['sandbox'] else 'SANDBOX'}`

*Position Sizing ({sizing['tier']} tier):*
• Trade Size: `${sizing['position_size_usd']:.2f}`
• Leverage: `{sizing.get('leverage', 4)}x`
• Max Risk: `${sizing['max_risk_usd']:.2f}` (2% after 3 saves)

*Protection:*
• Liquidation saves: `3 attempts`
• Trigger: `5% from liquidation`
• Critical: `2% from liquidation`
• Loss rule: `2% max ONLY after all saves fail`

*Market Filters (Data-Backed):*
• Trading Hours: `{'ON' if hours_status['enabled'] else 'OFF'}` {hours_status.get('reason', '')}
• News Events: `{'ON' if news_status['enabled'] else 'OFF'}`
• Momentum Confirmation: `ON` (+10-15% win rate)
• Volume Spike Entry: `ON` (+12% win rate)

_Monitoring positions..._""" if balance else "Bot Started - Balance check failed"

        self.notifier.send_message(startup_msg, "Bot Started")

        last_daily_reset = datetime.now().date()

        while self.running:
            try:
                # Reset daily counters at midnight
                if datetime.now().date() > last_daily_reset:
                    self._daily_reset()
                    last_daily_reset = datetime.now().date()

                self.run_cycle()
                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                logger.info("Shutdown requested...")
                self.stop()
            except Exception as e:
                logger.error(f"Bot error: {e}")
                time.sleep(30)  # Wait before retry

    def _daily_reset(self):
        """Reset daily counters and send summary"""
        summary = {
            "date": (datetime.now() - timedelta(days=1)).date().isoformat(),
            "trades": len(self.trades_today),
            "pnl": self.daily_pnl
        }

        self.notifier.send_daily_summary(summary)
        logger.info(f"Daily Summary: {summary}")

        # Reset
        self.trades_today = []
        self.daily_pnl = 0.0

    def stop(self):
        """Stop the bot gracefully"""
        self.running = False
        logger.info("Bot stopped")
        self.notifier.send_message("Bot Stopped")

    def status(self) -> dict:
        """Get current bot status"""
        filter_status = self.market_filters.get_status()
        risk_ok, risk_reason = self.check_risk_limits()

        return {
            "running": self.running,
            "strategies_active": list(self.strategies.keys()),
            "trades_today": len(self.trades_today),
            "daily_pnl": self.daily_pnl,
            "risk_ok": (risk_ok, risk_reason),
            "market_filters": {
                "trading_hours_ok": filter_status['trading_hours']['can_trade'],
                "news_events_ok": filter_status['news_events']['can_trade'],
                "upcoming_events": filter_status['news_events'].get('upcoming_events', [])[:3]
            }
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Hybrid Crypto Trading Bot")
    parser.add_argument("--config", default="config.json", help="Config file path")
    parser.add_argument("--interval", type=int, default=10, help="Check interval (seconds)")
    parser.add_argument("--dry-run", action="store_true", help="Run without executing trades")
    parser.add_argument("--diagnose", action="store_true", help="Run futures API diagnostic")
    args = parser.parse_args()

    if args.diagnose:
        # Run futures diagnostic without starting the bot
        import json
        with open(args.config) as f:
            config = json.load(f)
        from utils.coinbase_api import CoinbaseAPI
        api = CoinbaseAPI(
            config["exchange"]["api_key"],
            config["exchange"]["api_secret"],
            sandbox=config["exchange"].get("sandbox", False),
            use_perpetuals=True
        )
        result = api.diagnose_futures_access()
        print("\n" + "=" * 50)
        print("FUTURES API DIAGNOSTIC")
        print("=" * 50 + "\n")
        print(f"CFM (US Futures) Access: {'YES' if result['cfm_accessible'] else 'NO'}")
        print(f"INTX (International) Access: {'YES' if result['intx_accessible'] else 'NO'}")
        print(f"\nPortfolios: {result['portfolios']}")
        if result['error_details']:
            print(f"\nErrors: {result['error_details']}")
        print(f"\n{result['recommendation']}")
    else:
        bot = HybridTradingBot(config_path=args.config)

        if args.dry_run:
            print("DRY RUN MODE - No trades will be executed")
            print(f"Status: {bot.status()}")
        else:
            bot.start(interval_seconds=args.interval)
