#!/usr/bin/env python3
"""
Notification Module - Detailed Slack Alerts with Trade Approval
Logs all trades to CSV spreadsheet
"""

import csv
import logging
import time
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)


class Notifier:
    """
    Send detailed notifications via Slack with trade approval workflow
    Logs everything to CSV spreadsheet
    """

    def __init__(self, config: dict):
        self.config = config
        self.enabled = config.get("enabled", False)

        # Slack config
        self.slack_webhook = config.get("slack_webhook_url", "")

        # Telegram config (fallback)
        self.bot_token = config.get("telegram_bot_token", "")
        self.chat_id = config.get("telegram_chat_id", "")

        # Approval settings
        self.require_approval = config.get("require_approval", True)
        self.approval_timeout = config.get("approval_timeout_seconds", 300)

        # Spreadsheet logging
        self.log_to_spreadsheet = config.get("log_to_spreadsheet", True)
        self.spreadsheet_path = Path(__file__).parent.parent / config.get("spreadsheet_path", "data/trade_log.csv")

        # Service selection
        self.use_slack = bool(self.slack_webhook and self.slack_webhook != "YOUR_SLACK_WEBHOOK_URL")
        self.use_telegram = bool(self.bot_token and self.chat_id) and not self.use_slack

        # Initialize spreadsheet
        if self.log_to_spreadsheet:
            self._init_spreadsheet()

        if self.enabled:
            if self.use_slack:
                logger.info("Notifications: Slack enabled (approval required)" if self.require_approval else "Notifications: Slack enabled")
            elif self.use_telegram:
                logger.info("Notifications: Telegram enabled")
            else:
                logger.warning("Notifications enabled but no service configured")

    def _init_spreadsheet(self):
        """Initialize CSV spreadsheet with headers"""
        self.spreadsheet_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.spreadsheet_path.exists():
            headers = [
                "timestamp", "trade_id", "status", "pair", "side", "leverage",
                "amount_usd", "entry_price", "stop_loss", "take_profit",
                "liquidation_price", "risk_reward", "strategy", "confluence_score",
                "trend", "opportunity_score", "reason", "approved", "executed",
                "exit_price", "exit_time", "pnl_usd", "pnl_percent", "notes"
            ]
            with open(self.spreadsheet_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
            logger.info(f"Created trade log spreadsheet: {self.spreadsheet_path}")

    def log_trade_to_spreadsheet(self, trade_data: dict) -> bool:
        """Log trade to CSV spreadsheet"""
        if not self.log_to_spreadsheet:
            return False

        try:
            row = [
                trade_data.get("timestamp", datetime.now().isoformat()),
                trade_data.get("trade_id", ""),
                trade_data.get("status", "PENDING"),
                trade_data.get("pair", ""),
                trade_data.get("side", ""),
                trade_data.get("leverage", ""),
                trade_data.get("amount_usd", ""),
                trade_data.get("entry_price", ""),
                trade_data.get("stop_loss", ""),
                trade_data.get("take_profit", ""),
                trade_data.get("liquidation_price", ""),
                trade_data.get("risk_reward", ""),
                trade_data.get("strategy", ""),
                trade_data.get("confluence_score", ""),
                trade_data.get("trend", ""),
                trade_data.get("opportunity_score", ""),
                trade_data.get("reason", ""),
                trade_data.get("approved", ""),
                trade_data.get("executed", ""),
                trade_data.get("exit_price", ""),
                trade_data.get("exit_time", ""),
                trade_data.get("pnl_usd", ""),
                trade_data.get("pnl_percent", ""),
                trade_data.get("notes", "")
            ]

            with open(self.spreadsheet_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row)

            return True
        except Exception as e:
            logger.error(f"Failed to log to spreadsheet: {e}")
            return False

    def send_message(self, message: str, title: str = None) -> bool:
        """Send a notification message"""
        if not self.enabled or not requests:
            logger.info(f"[NOTIFY] {title}: {message}")
            return False

        if self.use_slack:
            return self._send_slack(message, title)
        elif self.use_telegram:
            return self._send_telegram(message)

        return False

    def _send_slack(self, message: str, title: str = None) -> bool:
        """Send via Slack webhook"""
        try:
            blocks = []

            if title:
                blocks.append({
                    "type": "header",
                    "text": {"type": "plain_text", "text": title, "emoji": True}
                })

            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": message}
            })

            payload = {
                "blocks": blocks,
                "text": title or message
            }

            response = requests.post(
                self.slack_webhook,
                json=payload,
                timeout=10
            )
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
            return False

    def _send_telegram(self, message: str) -> bool:
        """Send via Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, json=data, timeout=10)
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")
            return False

    def send_trade_approval_request(self, signal: dict, analysis: dict = None) -> dict:
        """
        Send detailed trade approval request to Slack
        Returns trade data for logging
        """
        trade_id = f"TRADE_{datetime.now():%Y%m%d_%H%M%S}"
        pair = signal.get("pair", "UNKNOWN")
        side = signal.get("side", "buy").upper()
        amount = signal.get("amount", 0)
        leverage = signal.get("leverage", 4)
        entry_price = signal.get("price") or signal.get("current_price", 0)
        stop_loss = signal.get("stop_loss", 0)
        take_profit = signal.get("take_profit", 0)
        strategy = signal.get("strategy", "unknown")
        reason = signal.get("reason", "")
        confluence = signal.get("confluence_score", 0)

        # Calculate metrics
        if entry_price and stop_loss:
            risk_pct = abs(entry_price - stop_loss) / entry_price * 100
            reward_pct = abs(take_profit - entry_price) / entry_price * 100 if take_profit else 0
            risk_reward = reward_pct / risk_pct if risk_pct > 0 else 0

            # Liquidation price
            if side == "BUY":
                liq_price = entry_price * (1 - 1/leverage)
            else:
                liq_price = entry_price * (1 + 1/leverage)
        else:
            risk_pct = 0
            reward_pct = 0
            risk_reward = 0
            liq_price = 0

        # Analysis data
        trend = "N/A"
        opp_score = 0
        if analysis:
            trend = analysis.get("trend_direction", "N/A")
            opp_score = analysis.get("opportunity_score", 0)

        # Build detailed Slack message
        emoji = ":chart_with_upwards_trend:" if side == "BUY" else ":chart_with_downwards_trend:"
        urgency = ":rotating_light:" if confluence and confluence > 3 else ""

        message = f"""{urgency}*TRADE APPROVAL REQUIRED*{urgency}

{emoji} *{side} {pair}*

*Trade Details:*
• Amount: `${amount:,.2f}` USD
• Leverage: `{leverage}x`
• Entry Price: `${entry_price:,.2f}`

*Risk Management:*
• Stop Loss: `${stop_loss:,.2f}` ({risk_pct:.2f}% risk)
• Take Profit: `${take_profit:,.2f}` ({reward_pct:.2f}% reward)
• Risk:Reward: `{risk_reward:.2f}:1`
• Liquidation: `${liq_price:,.2f}`

*Analysis:*
• Strategy: `{strategy}`
• Confluence: `{confluence}` signals
• Trend: `{trend}`
• Opportunity Score: `{opp_score}`

*Reason:*
_{reason}_

*Trade ID:* `{trade_id}`
*Time:* {datetime.now():%Y-%m-%d %H:%M:%S}

---
:white_check_mark: Reply `APPROVE {trade_id}` to execute
:x: Reply `REJECT {trade_id}` to cancel
:clock3: Auto-expires in {self.approval_timeout // 60} minutes"""

        # Send to Slack
        self.send_message(message, f"{side} {pair} - Approval Required")

        # Prepare trade data for spreadsheet
        trade_data = {
            "timestamp": datetime.now().isoformat(),
            "trade_id": trade_id,
            "status": "PENDING_APPROVAL",
            "pair": pair,
            "side": side,
            "leverage": leverage,
            "amount_usd": amount,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "liquidation_price": round(liq_price, 2),
            "risk_reward": round(risk_reward, 2),
            "strategy": strategy,
            "confluence_score": confluence,
            "trend": trend,
            "opportunity_score": opp_score,
            "reason": reason,
            "approved": "",
            "executed": "",
            "signal": signal  # Keep original signal for execution
        }

        # Log to spreadsheet
        self.log_trade_to_spreadsheet(trade_data)

        return trade_data

    def send_trade_executed(self, trade_data: dict, order: dict):
        """Notify that trade was executed"""
        pair = trade_data.get("pair", "")
        side = trade_data.get("side", "")
        trade_id = trade_data.get("trade_id", "")
        amount = trade_data.get("amount_usd", 0)
        entry = order.get("price", trade_data.get("entry_price", 0))

        message = f""":white_check_mark: *TRADE EXECUTED*

*{side} {pair}*
• Trade ID: `{trade_id}`
• Amount: `${amount:,.2f}`
• Entry: `${entry:,.2f}`
• Time: {datetime.now():%H:%M:%S}

_Position is now being monitored for liquidation protection._"""

        self.send_message(message, f"Executed: {side} {pair}")

        # Update spreadsheet
        trade_data["status"] = "EXECUTED"
        trade_data["executed"] = datetime.now().isoformat()
        self.log_trade_to_spreadsheet(trade_data)

    def send_trade_rejected(self, trade_data: dict, reason: str = "Manual rejection"):
        """Notify that trade was rejected"""
        pair = trade_data.get("pair", "")
        side = trade_data.get("side", "")
        trade_id = trade_data.get("trade_id", "")

        message = f""":x: *TRADE REJECTED*

*{side} {pair}*
• Trade ID: `{trade_id}`
• Reason: {reason}
• Time: {datetime.now():%H:%M:%S}"""

        self.send_message(message, f"Rejected: {side} {pair}")

        # Update spreadsheet
        trade_data["status"] = "REJECTED"
        trade_data["notes"] = reason
        self.log_trade_to_spreadsheet(trade_data)

    def send_position_update(self, position: dict, current_price: float, action: str, details: str):
        """Send position update (margin added, stop moved, etc.)"""
        pair = position.get("pair", "")
        side = position.get("side", "").upper()

        emoji_map = {
            "margin_added": ":money_with_wings:",
            "stop_moved": ":shield:",
            "breakeven": ":lock:",
            "trailing": ":runner:",
            "closed": ":door:",
            "liquidation_warning": ":warning:"
        }
        emoji = emoji_map.get(action, ":information_source:")

        message = f"""{emoji} *POSITION UPDATE*

*{side} {pair}*
• Action: `{action.upper()}`
• Current Price: `${current_price:,.2f}`
• Details: {details}
• Time: {datetime.now():%H:%M:%S}"""

        self.send_message(message, f"Position: {pair}")

    def send_trade_notification(self, strategy: str, order: dict):
        """Notify about executed trade (backward compatibility)"""
        if not self.config.get("notify_on_trade", True):
            return

        side = order.get("side", "?").upper()
        pair = order.get("product_id", "?")
        amount = order.get("size", order.get("amount", "?"))

        msg = f"""*{side}* {pair}
• Strategy: `{strategy}`
• Amount: ${amount}
• Time: {datetime.now():%H:%M:%S}"""

        self.send_message(msg, f"Trade: {side} {pair}")

    def send_error_notification(self, error: str):
        """Notify about errors"""
        if not self.config.get("notify_on_error", True):
            return

        self.send_message(f":x: `{error}`", "Bot Error")

    def send_daily_summary(self, summary: dict):
        """Send detailed daily summary"""
        if not self.config.get("daily_summary", True):
            return

        trades = summary.get("trades", 0)
        pnl = summary.get("pnl", 0)
        wins = summary.get("wins", 0)
        losses = summary.get("losses", 0)
        win_rate = (wins / trades * 100) if trades > 0 else 0

        emoji = ":moneybag:" if pnl > 0 else ":chart_with_downwards_trend:"

        msg = f"""{emoji} *DAILY SUMMARY - {summary.get('date', 'Today')}*

*Performance:*
• Total Trades: `{trades}`
• Wins: `{wins}` | Losses: `{losses}`
• Win Rate: `{win_rate:.1f}%`
• P&L: `${pnl:,.2f}`

*Capital:*
• Starting: `${summary.get('starting_capital', 0):,.2f}`
• Current: `${summary.get('current_capital', 0):,.2f}`
• Daily Target: `${summary.get('daily_target', 0):,.2f}`

_Good trading!_"""

        self.send_message(msg, "Daily Summary")

    def send_alert(self, title: str, message: str, urgent: bool = False):
        """Send a general alert"""
        prefix = ":rotating_light: " if urgent else ""
        self.send_message(message, f"{prefix}{title}")


class ConsoleNotifier(Notifier):
    """Notifier that prints to console (for testing)"""

    def __init__(self, config: dict = None):
        self.enabled = True
        self.config = config or {}
        self.use_slack = False
        self.use_telegram = False
        self.require_approval = False
        self.log_to_spreadsheet = False

    def send_message(self, message: str, title: str = None) -> bool:
        print(f"\n{'='*60}")
        if title:
            print(f"[{title}]")
        print(message)
        print(f"{'='*60}\n")
        return True
