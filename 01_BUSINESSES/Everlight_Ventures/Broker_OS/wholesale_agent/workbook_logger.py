"""Workbook Logger - unified write layer for all 4 wholesale tracking workbooks.

Every pipeline script imports this module to log events. Handles:
- Pipeline master: lead stage transitions
- Outreach log: emails sent/received
- Deal tracker: deal stage progression
- Performance metrics: daily rollup stats

Also handles cross-platform sync:
- Supabase push (REST API)
- Slack notifications
- Blinko session logging

Usage:
    from workbook_logger import wb

    wb.log_lead_scouted(address="123 Main St", city="Atlanta", state="GA", ...)
    wb.log_email_sent(lead_id="xxx", to_email="owner@example.com", ...)
    wb.log_deal_stage_change(deal_id="xxx", new_stage="under_contract", ...)
    wb.log_agent_task(agent="rex_blackwell", task="scout", success=True, ...)
    wb.flush()  # write all pending changes to disk + sync
"""
from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

try:
    from gdocs_bridge import publish_report
except ImportError:
    publish_report = None

# Paths
_WB_DIR = Path(__file__).parent / "data" / "workbooks"
_PIPELINE = _WB_DIR / "pipeline_master.json"
_OUTREACH = _WB_DIR / "outreach_log.json"
_DEALS = _WB_DIR / "deal_tracker.json"
_METRICS = _WB_DIR / "performance_metrics.json"
_ENV_FILE = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")

# Env vars (lazy loaded)
_env_loaded = False
_supabase_url = ""
_supabase_key = ""
_slack_token = ""
_slack_channel = ""
_blinko_url = ""


def _load_env():
    global _env_loaded, _supabase_url, _supabase_key, _slack_token, _slack_channel, _blinko_url
    if _env_loaded:
        return
    env = {}
    if _ENV_FILE.exists():
        for line in _ENV_FILE.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    _supabase_url = env.get("SUPABASE_URL", os.environ.get("SUPABASE_URL", ""))
    _supabase_key = env.get("SUPABASE_SERVICE_ROLE_KEY", env.get("SUPABASE_ANON_KEY", os.environ.get("SUPABASE_KEY", "")))
    _slack_token = env.get("SLACK_BOT_TOKEN", os.environ.get("SLACK_BOT_TOKEN", ""))
    _slack_channel = env.get("SLACK_WHOLESALE_CH", os.environ.get("SLACK_WHOLESALE_CH", "C0ANLLV8JAC"))
    _blinko_url = env.get("BLINKO_URL", os.environ.get("BLINKO_URL", "http://e5-mother:1111"))
    _env_loaded = True


def _read_wb(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _write_wb(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    tmp.replace(path)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid() -> str:
    return str(uuid.uuid4())[:12]


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


class WorkbookLogger:
    """Stateful logger that batches writes and flushes on demand."""

    def __init__(self):
        self._pipeline_dirty = False
        self._outreach_dirty = False
        self._deals_dirty = False
        self._metrics_dirty = False
        self._pipeline: dict | None = None
        self._outreach: dict | None = None
        self._deals: dict | None = None
        self._metrics: dict | None = None

    def _get_pipeline(self) -> dict:
        if self._pipeline is None:
            self._pipeline = _read_wb(_PIPELINE)
        return self._pipeline

    def _get_outreach(self) -> dict:
        if self._outreach is None:
            self._outreach = _read_wb(_OUTREACH)
        return self._outreach

    def _get_deals(self) -> dict:
        if self._deals is None:
            self._deals = _read_wb(_DEALS)
        return self._deals

    def _get_metrics(self) -> dict:
        if self._metrics is None:
            self._metrics = _read_wb(_METRICS)
        return self._metrics

    # --- Pipeline Master ---

    def log_lead_scouted(self, *, address: str, city: str, state: str,
                         lead_type: str = "other", source: str = "manual",
                         owner_name: str = "", estimated_arv: float = 0,
                         motivation_score: int = 0, ai_score: bool = True,
                         **extra) -> str:
        """Log a new lead discovered by scouting. Returns lead_id.

        If ai_score=True and sheets_ai_helpers is importable, auto-score the lead
        via Filter Banks (Haiku) and stash the result in the stored record.
        """
        wb = self._get_pipeline()
        lead_id = _uid()
        lead = {
            "id": lead_id,
            "address": address,
            "city": city,
            "state": state,
            "lead_type": lead_type,
            "source": source,
            "owner_name": owner_name,
            "estimated_arv": estimated_arv,
            "motivation_score": motivation_score,
            "stage": "scouted",
            "stage_history": [{"stage": "scouted", "entered_at": _now(), "agent": "rex_blackwell"}],
            "outreach": {"emails_sent": 0, "opens": 0, "replies": 0},
            "deal": {},
            "created_at": _now(),
            "updated_at": _now(),
            **extra,
        }
        # Filter Banks auto-score via sheets_ai_helpers (Folder 08 upgrade)
        if ai_score:
            try:
                from sheets_ai_helpers import score_lead  # type: ignore
                sc = score_lead({
                    "address": address, "city": city, "state": state,
                    "owner_tags": extra.get("owner_tags", []),
                    "estimated_equity": extra.get("estimated_equity"),
                    "absentee": extra.get("absentee", False),
                    "property_condition": extra.get("property_condition", ""),
                    "days_listed": extra.get("days_listed"),
                    "owner_type": extra.get("owner_type", ""),
                })
                lead["ai_score"] = sc.get("score")
                lead["ai_tier"] = sc.get("tier")
                lead["ai_reasoning"] = sc.get("reasoning")
                lead["ai_confidence"] = sc.get("confidence")
            except Exception as _exc:  # keep logging path clean even if helper missing
                lead["ai_score"] = None
                lead["ai_score_error"] = str(_exc)
        if "leads" not in wb:
            wb["leads"] = []
        wb["leads"].append(lead)
        self._pipeline_dirty = True
        self._bump_metric("scouted")
        return lead_id

    def log_lead_stage_change(self, lead_id: str, new_stage: str,
                              agent: str = "", notes: str = ""):
        """Move a lead to a new funnel stage."""
        wb = self._get_pipeline()
        for lead in wb.get("leads", []):
            if lead.get("id") == lead_id:
                lead["stage"] = new_stage
                lead["updated_at"] = _now()
                lead.setdefault("stage_history", []).append({
                    "stage": new_stage, "entered_at": _now(),
                    "agent": agent, "notes": notes,
                })
                self._pipeline_dirty = True
                self._bump_metric(new_stage)
                return
        # Lead not found in workbook - create minimal entry
        self.log_lead_scouted(address=f"unknown-{lead_id}", city="?", state="?")

    def find_lead(self, lead_id: str) -> dict | None:
        wb = self._get_pipeline()
        for lead in wb.get("leads", []):
            if lead.get("id") == lead_id:
                return lead
        return None

    # --- Outreach Log ---

    def log_email_sent(self, *, lead_id: str, to_email: str, to_name: str = "",
                       email_type: str = "seller_intro", sender_persona: str = "piper",
                       subject: str = "", template: str = "",
                       resend_id: str = "", **extra) -> str:
        """Log an outbound email. Returns email_id."""
        wb = self._get_outreach()
        email_id = _uid()
        entry = {
            "id": email_id,
            "lead_id": lead_id,
            "direction": "outbound",
            "type": email_type,
            "sender_persona": sender_persona,
            "to_email": to_email,
            "to_name": to_name,
            "subject": subject,
            "template_used": template,
            "sent_at": _now(),
            "delivered": True,
            "opened_at": None,
            "open_count": 0,
            "replied_at": None,
            "reply_sentiment": None,
            "bounced": False,
            "resend_message_id": resend_id,
            **extra,
        }
        if "emails" not in wb:
            wb["emails"] = []
        wb["emails"].append(entry)

        # Update daily stats
        self._update_daily_outreach_stats(sender_persona, email_type)
        self._outreach_dirty = True

        # Also update pipeline lead
        plead = self.find_lead(lead_id)
        if plead:
            plead.setdefault("outreach", {})
            plead["outreach"]["emails_sent"] = plead["outreach"].get("emails_sent", 0) + 1
            plead["outreach"]["last_email_at"] = _now()
            if plead.get("stage") in ("scouted", "scored", "qualified", "matched"):
                self.log_lead_stage_change(lead_id, "outreach_sent", agent=sender_persona)
            self._pipeline_dirty = True

        self._bump_metric("outreach_sent")
        return email_id

    def log_email_reply(self, *, lead_id: str, from_email: str,
                        sentiment: str = "warm", **extra):
        """Log an inbound reply."""
        wb = self._get_outreach()
        entry = {
            "id": _uid(),
            "lead_id": lead_id,
            "direction": "inbound",
            "type": "reply",
            "to_email": from_email,
            "sent_at": _now(),
            "reply_sentiment": sentiment,
            **extra,
        }
        wb.setdefault("emails", []).append(entry)
        self._outreach_dirty = True

        plead = self.find_lead(lead_id)
        if plead:
            plead.setdefault("outreach", {})
            plead["outreach"]["replies"] = plead["outreach"].get("replies", 0) + 1
            plead["outreach"]["last_reply_at"] = _now()
            plead["outreach"]["reply_sentiment"] = sentiment
            if sentiment in ("hot", "warm"):
                self.log_lead_stage_change(lead_id, "response_received", agent="hammer_obrien")
            self._pipeline_dirty = True

        self._bump_metric("responses")

    def log_email_bounce(self, *, lead_id: str, email: str, reason: str = ""):
        wb = self._get_outreach()
        wb.setdefault("bounces", []).append({
            "lead_id": lead_id, "email": email, "reason": reason, "at": _now()
        })
        self._outreach_dirty = True

    def _update_daily_outreach_stats(self, persona: str, email_type: str):
        wb = self._get_outreach()
        today = _today()
        stats = wb.setdefault("daily_stats", [])
        today_stats = None
        for s in stats:
            if s.get("date") == today:
                today_stats = s
                break
        if not today_stats:
            # Calculate warmup budget
            start = wb.get("warmup_config", {}).get("account_start_date", "2026-03-20")
            try:
                days_active = (datetime.now(timezone.utc).date() - datetime.fromisoformat(start).date()).days
            except Exception:
                days_active = 30
            if days_active < 7:
                budget = 5
            elif days_active < 14:
                budget = 10
            elif days_active < 21:
                budget = 15
            else:
                budget = 20
            today_stats = {
                "date": today, "budget": budget, "sent": 0, "delivered": 0,
                "bounced": 0, "opened": 0, "replied": 0, "reply_rate_pct": 0,
                "by_persona": {}, "by_type": {},
            }
            stats.append(today_stats)

        today_stats["sent"] = today_stats.get("sent", 0) + 1
        today_stats["delivered"] = today_stats.get("delivered", 0) + 1
        bp = today_stats.setdefault("by_persona", {})
        bp[persona] = bp.get(persona, 0) + 1
        bt = today_stats.setdefault("by_type", {})
        bt[email_type] = bt.get(email_type, 0) + 1

    # --- Deal Tracker ---

    def log_deal_created(self, *, lead_id: str, property_address: str,
                         seller_name: str, city: str = "", state: str = "",
                         estimated_arv: float = 0, **extra) -> str:
        """Create a new deal entry. Returns deal_id."""
        wb = self._get_deals()
        deal_id = _uid()
        deal = {
            "id": deal_id,
            "lead_id": lead_id,
            "property_address": property_address,
            "city": city,
            "state": state,
            "seller_name": seller_name,
            "stage": "intro",
            "stage_history": [{"stage": "intro", "entered_at": _now(), "agent": "hammer_obrien"}],
            "financials": {"estimated_arv": estimated_arv},
            "title_company": {},
            "documents": [],
            "commission": {"rate_pct": 20, "status": "pending"},
            "created_at": _now(),
            "updated_at": _now(),
            **extra,
        }
        wb.setdefault("active_deals", []).append(deal)
        self._deals_dirty = True
        return deal_id

    def log_deal_stage_change(self, deal_id: str, new_stage: str,
                              agent: str = "hammer_obrien", notes: str = ""):
        wb = self._get_deals()
        for deal in wb.get("active_deals", []):
            if deal.get("id") == deal_id:
                deal["stage"] = new_stage
                deal["updated_at"] = _now()
                deal.setdefault("stage_history", []).append({
                    "stage": new_stage, "entered_at": _now(),
                    "agent": agent, "notes": notes,
                })
                if new_stage == "closed_won":
                    deal["closed_at"] = _now()
                    wb.setdefault("closed_deals", []).append(deal)
                    wb["active_deals"].remove(deal)
                    self._bump_metric("closed")
                elif new_stage == "closed_lost":
                    deal["closed_at"] = _now()
                    wb.setdefault("dead_deals", []).append(deal)
                    wb["active_deals"].remove(deal)
                    self._bump_metric("dead")
                self._deals_dirty = True
                return

    def log_deal_financials(self, deal_id: str, **financials):
        wb = self._get_deals()
        for deal in wb.get("active_deals", []) + wb.get("closed_deals", []):
            if deal.get("id") == deal_id:
                deal.setdefault("financials", {}).update(financials)
                deal["updated_at"] = _now()
                self._deals_dirty = True
                return

    def log_deal_document(self, deal_id: str, doc_type: str,
                          status: str = "draft", agent: str = "", **extra):
        wb = self._get_deals()
        for deal in wb.get("active_deals", []) + wb.get("closed_deals", []):
            if deal.get("id") == deal_id:
                deal.setdefault("documents", []).append({
                    "doc_type": doc_type, "status": status,
                    "created_at": _now(), "generated_by": agent, **extra,
                })
                deal["updated_at"] = _now()
                self._deals_dirty = True
                return

    def log_commission(self, deal_id: str, amount_usd: float,
                       commission_type: str = "earned", **extra):
        wb = self._get_deals()
        wb.setdefault("commission_ledger", []).append({
            "id": _uid(), "deal_id": deal_id, "type": commission_type,
            "amount_usd": amount_usd, "created_at": _now(), **extra,
        })
        self._deals_dirty = True

    # --- Performance Metrics ---

    def _bump_metric(self, stage: str):
        m = self._get_metrics()
        for period in ("30d", "60d", "90d", "all_time"):
            bucket = m.setdefault("funnel_metrics", {}).setdefault(period, {})
            bucket[stage] = bucket.get(stage, 0) + 1
        self._metrics_dirty = True

    def sync_from_leads_db(self, leads_path: Path | None = None) -> dict:
        """Derive the funnel scoreboard from the canonical leads_db.json.

        The scoreboard was orphaned: nothing called the funnel loggers, so 3,163
        real leads rendered as all-zeros. This rebuilds funnel_metrics directly
        from lead state on every run -- the scoreboard can no longer lie.
        Returns the all_time funnel dict it wrote.
        """
        path = leads_path or (Path(__file__).parent / "leads_db.json")
        try:
            leads = json.loads(path.read_text())
        except Exception:
            return {}
        if not isinstance(leads, list):
            return {}

        DEAD = {"dead", "dnc", "opted_out", "bounced", "eradicated", "lost"}
        RESPONDED = {"responded", "replied", "negotiating", "under_contract", "closed", "paid", "won"}
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

        def tally(rows: list) -> dict:
            f = {k: 0 for k in ("scouted", "scored", "qualified", "matched",
                                "outreach_sent", "responses", "negotiating",
                                "under_contract", "closed", "paid", "dead")}
            for r in rows:
                st = str(r.get("status", "")).lower()
                f["scouted"] += 1
                if r.get("score") or r.get("motivation_score"):
                    f["scored"] += 1
                if str(r.get("motivation_tier", "")).upper() in ("HIGH", "WARM") or r.get("close_tier") not in (None, "", "?"):
                    f["qualified"] += 1
                if r.get("buyer_matches"):
                    f["matched"] += 1
                if r.get("outreach_count", 0) and int(r.get("outreach_count", 0)) > 0:
                    f["outreach_sent"] += 1
                if st in RESPONDED:
                    f["responses"] += 1
                if st == "negotiating":
                    f["negotiating"] += 1
                if st == "under_contract":
                    f["under_contract"] += 1
                if st in ("closed", "won"):
                    f["closed"] += 1
                if st == "paid":
                    f["paid"] += 1
                if st in DEAD:
                    f["dead"] += 1
            return f

        m = self._get_metrics()
        fm = m.setdefault("funnel_metrics", {})
        fm["all_time"] = tally(leads)
        fm["30d"] = tally([r for r in leads if str(r.get("created_at", "")) >= cutoff])
        m.setdefault("meta", {})["last_synced_from_leads_db"] = _now()
        m.setdefault("current_period", {})["total_leads_in_db"] = len(leads)
        self._metrics_dirty = True
        return fm["all_time"]

    def log_agent_task(self, agent: str, task: str, success: bool = True,
                       count: int = 0, **extra):
        m = self._get_metrics()
        perf = m.setdefault("agent_performance", {}).setdefault(agent, {
            "tasks_run": 0, "success": 0, "fail": 0,
        })
        perf["tasks_run"] = perf.get("tasks_run", 0) + 1
        if success:
            perf["success"] = perf.get("success", 0) + 1
        else:
            perf["fail"] = perf.get("fail", 0) + 1
        if count > 0:
            # Auto-detect metric key from task name
            key = f"{task}_count" if not task.endswith("s") else task
            perf[key] = perf.get(key, 0) + count
        self._metrics_dirty = True

    def log_cost(self, source: str, amount_usd: float, count: int = 1):
        m = self._get_metrics()
        costs = m.setdefault("costs", {})
        key = f"{source}_cost_usd"
        calls_key = f"{source}_calls" if source != "resend" else "resend_emails_sent"
        costs[key] = costs.get(key, 0) + amount_usd
        costs[calls_key] = costs.get(calls_key, 0) + count
        costs["total_cost_usd"] = costs.get("total_cost_usd", 0) + amount_usd
        self._metrics_dirty = True

    def snapshot_daily(self):
        """Capture a daily snapshot for trend tracking."""
        m = self._get_metrics()
        snap = {
            "date": _today(),
            "funnel_30d": dict(m.get("funnel_metrics", {}).get("30d", {})),
            "outreach_today": self._get_outreach_today_stats(),
            "active_deals": len(self._get_deals().get("active_deals", [])),
            "pipeline_leads": len(self._get_pipeline().get("leads", [])),
        }
        m.setdefault("daily_snapshots", []).append(snap)
        # Keep last 90 days
        m["daily_snapshots"] = m["daily_snapshots"][-90:]
        self._metrics_dirty = True

    def _get_outreach_today_stats(self) -> dict:
        wb = self._get_outreach()
        today = _today()
        for s in wb.get("daily_stats", []):
            if s.get("date") == today:
                return s
        return {}

    # --- Flush & Sync ---

    def flush(self):
        """Write all dirty workbooks to disk."""
        if self._pipeline_dirty and self._pipeline:
            _write_wb(_PIPELINE, self._pipeline)
            self._pipeline_dirty = False
        if self._outreach_dirty and self._outreach:
            _write_wb(_OUTREACH, self._outreach)
            self._outreach_dirty = False
        if self._deals_dirty and self._deals:
            _write_wb(_DEALS, self._deals)
            self._deals_dirty = False
        if self._metrics_dirty and self._metrics:
            _write_wb(_METRICS, self._metrics)
            self._metrics_dirty = False

    def sync_to_supabase(self):
        """Push latest metrics + pipeline rollup to Supabase."""
        _load_env()
        if not _supabase_url or not _supabase_key:
            return
        try:
            from urllib.request import urlopen, Request
            headers = {
                "apikey": _supabase_key,
                "Authorization": f"Bearer {_supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates",
            }

            m = self._get_metrics()
            payload = {
                "id": "wholesale_daily_" + _today(),
                "date": _today(),
                "funnel_30d": json.dumps(m.get("funnel_metrics", {}).get("30d", {})),
                "conversion_rates": json.dumps(m.get("conversion_rates", {})),
                "revenue": json.dumps(m.get("revenue", {})),
                "costs": json.dumps(m.get("costs", {})),
                "agent_performance": json.dumps(m.get("agent_performance", {})),
                "active_deals": len(self._get_deals().get("active_deals", [])),
                "total_leads": len(self._get_pipeline().get("leads", [])),
            }
            url = f"{_supabase_url}/rest/v1/wholesale_metrics"
            req = Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
            urlopen(req, timeout=10)
        except Exception:
            pass  # never break pipeline on sync failure

    def post_to_slack(self, message: str, title: str = "Wholesale Pipeline Update"):
        """Post a summary to the wholesale Slack channel, creating a GDoc first when possible."""
        # Try branded GDoc first
        if publish_report is not None:
            try:
                result = publish_report(
                    title=title,
                    content=message,
                    folder="01_Broker_OS/Scout_Reports",
                    summary=message[:200],
                    agent="carlos_moreno",
                )
                if result.get("ok"):
                    return
            except Exception:
                pass
        # Fallback: raw text post
        _load_env()
        if not _slack_token:
            return
        try:
            from urllib.request import urlopen, Request
            payload = {
                "channel": _slack_channel,
                "text": message,
                "unfurl_links": False,
            }
            req = Request(
                "https://slack.com/api/chat.postMessage",
                data=json.dumps(payload).encode(),
                headers={
                    "Authorization": f"Bearer {_slack_token}",
                    "Content-Type": "application/json",
                },
            )
            urlopen(req, timeout=10)
        except Exception:
            pass

    def log_to_blinko(self, summary: str, tags: str = "#hive/wholesale #hive/pipeline"):
        """Log session to Blinko RAG."""
        _load_env()
        if not _blinko_url:
            return
        try:
            from urllib.request import urlopen, Request
            payload = {
                "content": f"# Wholesale Pipeline Run\n{tags}\n\n{summary}",
                "type": 1,
            }
            req = Request(
                f"{_blinko_url}/api/v1/note/upsert",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )
            urlopen(req, timeout=10)
        except Exception:
            pass

    def generate_summary(self) -> str:
        """Generate a human-readable summary of current state."""
        m = self._get_metrics()
        f30 = m.get("funnel_metrics", {}).get("30d", {})
        deals = self._get_deals()
        outreach = self._get_outreach()
        today_stats = self._get_outreach_today_stats()

        lines = [
            f"Pipeline: {f30.get('scouted', 0)} scouted | {f30.get('qualified', 0)} qualified | {f30.get('outreach_sent', 0)} outreached | {f30.get('responses', 0)} responses",
            f"Deals: {len(deals.get('active_deals', []))} active | {len(deals.get('closed_deals', []))} closed | {len(deals.get('dead_deals', []))} dead",
            f"Today: {today_stats.get('sent', 0)}/{today_stats.get('budget', 20)} emails sent",
        ]
        rev = m.get("revenue", {})
        if rev.get("total_commission_earned_usd", 0) > 0:
            lines.append(f"Revenue: ${rev['total_commission_earned_usd']:,.0f} earned | ${rev.get('total_commission_paid_usd', 0):,.0f} paid")

        return " | ".join(lines)


# Singleton
wb = WorkbookLogger()
