"""Shared-services bridge -- the Polymarket agent USES Everlight's common
infrastructure instead of siloing: branded Slack comms + the Blinko brain.

Every method degrades gracefully (try/except, local-first). A dead Slack token
or unreachable Blinko must NEVER crash a trade cycle -- same posture as the
signal dataflows. Local brain log is append-only JSONL so the brain stays
intact even when e5/Blinko is down (per the brain-intact-local-first law).
"""
import json
import logging
import sys
import time
import urllib.request
from pathlib import Path

log = logging.getLogger("polymarket.notify")

_SCRIPTS = "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts"
# Local-first brain endpoints (proxy -> e5), tried in order; all best-effort.
_BLINKO_ENDPOINTS = ["http://127.0.0.1:2700", "http://127.0.0.1:1111", "http://e5-mother:1111"]


class Notifier:
    def __init__(self, channel_trades: str, channel_alerts: str,
                 brain_log_path=None, enabled: bool = True,
                 agent: str = "Cipher Wolfe", agent_title: str = "Alpha Markets"):
        self.channel_trades = channel_trades
        self.channel_alerts = channel_alerts
        self.enabled = enabled
        self.agent = agent
        self.agent_title = agent_title
        self.brain_log_path = Path(brain_log_path) if brain_log_path else None

    # ---- Slack (branded) ----
    def _slack(self):
        if _SCRIPTS not in sys.path:
            sys.path.insert(0, _SCRIPTS)
        from content_tools import branded_slack  # lazy import; may be absent
        return branded_slack

    def order_placed(self, bet) -> bool:
        if not self.enabled:
            return False
        try:
            self._slack().post_branded_slack(
                channel=self.channel_trades,
                title="Polymarket order placed",
                summary=f"{bet.outcome} @ {bet.limit_price} -- {bet.amount_usdc} USDC",
                fields={"market": bet.market_id, "order_id": bet.id,
                        "edge": getattr(bet, "edge", "")},
                agent_name=self.agent, agent_title=self.agent_title,
                category="deal",
            )
            return True
        except Exception as e:
            log.warning("Slack order_placed degraded: %s", e)
            return False

    def halted(self, reason: str, detail: str) -> bool:
        if not self.enabled:
            return False
        try:
            self._slack().post_branded_alert(
                channel=self.channel_alerts,
                title=f"Polymarket HALT: {reason}",
                detail=detail, severity="critical",
                agent_name="Rex Thornton",
            )
            return True
        except Exception as e:
            log.warning("Slack halt alert degraded: %s", e)
            return False

    # ---- Brain (Blinko) -- local-first, best-effort remote ----
    def brain_log(self, title: str, body: str, tags: str = "#hive/polymarket") -> bool:
        wrote = False
        # 1) local-first append (brain stays intact even if remote is down)
        if self.brain_log_path:
            try:
                self.brain_log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.brain_log_path, "a") as f:
                    f.write(json.dumps({"ts": time.time(), "title": title,
                                        "body": body, "tags": tags}) + "\n")
                wrote = True
            except Exception as e:
                log.warning("local brain log failed: %s", e)
        # 2) best-effort remote (never blocks, never raises)
        payload = json.dumps({
            "content": f"# {title}\n{tags}\n\n{body}", "type": 1,
        }).encode()
        for base in _BLINKO_ENDPOINTS:
            try:
                req = urllib.request.Request(
                    f"{base}/api/v1/note/upsert", data=payload,
                    headers={"Content-Type": "application/json"}, method="POST")
                urllib.request.urlopen(req, timeout=4)
                return True
            except Exception:
                continue
        return wrote

    def cycle_summary(self, result: dict) -> None:
        self.brain_log(
            title=f"Polymarket cycle: {result.get('placed',0)} placed / "
                  f"{result.get('markets',0)} markets",
            body=f"halt={result.get('halt')} detail={json.dumps(result)}",
        )
