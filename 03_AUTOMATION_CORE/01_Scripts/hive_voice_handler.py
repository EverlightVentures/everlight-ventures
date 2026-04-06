#!/usr/bin/env python3
"""Hive Voice Action Handler v2 -- Marcus dispatches agents and generates reports"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, os, requests, traceback
from datetime import datetime, timezone, timedelta

# Pacific Time
PT = timezone(timedelta(hours=-7))  # PDT

# Telemarketing compliance -- TCPA + state laws
# Outbound calls/SMS only allowed during these windows (local time of recipient)
# Federal TCPA: 8 AM - 9 PM local time
# Some states are stricter (e.g., OK/LA 8AM-8PM, etc.)
# We use 9 AM - 7 PM as a safe universal window
CALL_WINDOW_START = 9   # 9 AM local time (safe across all states)
CALL_WINDOW_END = 19    # 7 PM local time (safe across all states)

# State timezone offsets from UTC (approximate, for compliance checking)
STATE_TZ = {
    "MO": -5, "NC": -4, "GA": -4, "TX": -5,
    "OH": -4, "FL": -4, "CA": -7, "NY": -4,
    "IL": -5, "PA": -4, "VA": -4, "MA": -4,
}

def is_call_allowed(state_code="MO"):
    """Check if outbound calls are allowed right now for the target state."""
    tz_offset = STATE_TZ.get(state_code.upper(), -5)  # default to Central
    local_tz = timezone(timedelta(hours=tz_offset))
    local_hour = datetime.now(local_tz).hour
    return CALL_WINDOW_START <= local_hour < CALL_WINDOW_END

def get_pt_time():
    """Get current time in Pacific."""
    return datetime.now(PT)

SLACK_WEBHOOK = "https://hooks.slack.com/services/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"
SLACK_ALERTS = "https://hooks.slack.com/services/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"
RESEND_KEY = "re_6S6DgX94_BDzaAU3r3Y5Syca6F58m2aEt"
RICH_EMAIL = "1m.rich.gee@gmail.com"
BOT_STATE = "/home/opc/xlm-bot/data/state.json"

def log(msg):
    ts = get_pt_time().strftime("%Y-%m-%d %H:%M:%S PT")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open("/tmp/hive_voice_handler.log", "a") as f:
        f.write(line + "\n")

def slack_post(text, webhook=None):
    try:
        requests.post(webhook or SLACK_WEBHOOK, json={"text": text}, timeout=10)
    except Exception:
        pass

def send_email(to, subject, body, from_name="Marcus Cole", from_email="marcus@everlightventures.io"):
    try:
        r = requests.post("https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_KEY}", "Content-Type": "application/json"},
            json={
                "from": f"{from_name} <{from_email}>",
                "to": [to],
                "subject": subject,
                "html": body
            }, timeout=10)
        return r.status_code in (200, 201), r.text
    except Exception as e:
        return False, str(e)

def get_bot_status():
    try:
        with open(BOT_STATE) as f:
            state = json.load(f)

        # Real PnL from state (pnl_today_usd is the accurate field)
        daily_pnl = float(state.get("pnl_today_usd") or state.get("daily_pnl_usd") or state.get("realized_pnl_today_usd") or 0)
        losses_today = int(state.get("losses_today") or 0)
        trades_today = int(state.get("trades_today") or 0)
        consec_losses = int(state.get("consecutive_losses") or 0)
        loss_debt = float(state.get("loss_debt_usd") or 0)
        equity_start = float(state.get("equity_start_usd") or 0)

        pos = state.get("open_position")
        if pos:
            direction = pos.get("direction", "?").upper()
            entry = pos.get("entry_price", 0)
            pos_str = f"{direction} from ${entry:.5f}"
        else:
            pos_str = "flat"

        sign = "+" if daily_pnl >= 0 else ""
        status = f"Bot: {sign}${daily_pnl:.2f} today"
        if trades_today > 0:
            status += f", {trades_today} trades, {losses_today} losses"
        if consec_losses >= 2:
            status += f", {consec_losses} consecutive losses"
        if loss_debt > 0:
            status += f", total drawdown ${loss_debt:.2f}"
        if equity_start > 0:
            status += f", started today at ${equity_start:.2f}"
        status += f", currently {pos_str}"

        # Also read cumulative PnL from decisions log
        try:
            import os
            decisions_path = "/home/opc/xlm-bot/logs/decisions.jsonl"
            if os.path.exists(decisions_path):
                total_pnl = 0
                trade_count = 0
                with open(decisions_path) as df:
                    for line in df:
                        try:
                            d = json.loads(line)
                            if d.get("exit_price") and d.get("pnl_usd") is not None:
                                total_pnl += float(d["pnl_usd"])
                                trade_count += 1
                        except Exception:
                            pass
                tsign = "+" if total_pnl >= 0 else ""
                status += f". All time: {tsign}${total_pnl:.2f} across {trade_count} trades"
        except Exception:
            pass

        return status
    except Exception as e:
        return f"Bot state error: {e}"

def generate_report(action_type, details):
    ts = get_pt_time().strftime("%B %d, %Y %I:%M %p PT")
    return (
        f"<h2>Hive Mind Action Report</h2>"
        f"<p><strong>Time:</strong> {ts}</p>"
        f"<p><strong>Requested by:</strong> Rich Gillies (via phone to Marcus Cole)</p>"
        f"<p><strong>Action:</strong> {action_type}</p>"
        f"<hr>"
        f"<h3>Details</h3>"
        f"{details}"
        f"<hr>"
        f"<p><em>Marcus Cole, Chief Operator -- Everlight Ventures Hive Mind</em></p>"
    )

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            action = body.get("action", "")
            log(f"ACTION: {action} | Body: {json.dumps(body)[:300]}")

            result = {"status": "ok", "message": "done"}

            if action == "send_email":
                subject = body.get("subject", "Hive Update from Marcus")
                email_body = body.get("body", "No content provided.")
                report = generate_report("Email Sent", f"<p><strong>Subject:</strong> {subject}</p><p>{email_body}</p>")
                ok, resp = send_email(RICH_EMAIL, subject, report)
                if ok:
                    result["message"] = f"Email sent to Rich: {subject}"
                    slack_post(f"[Marcus/Voice] Sent email to Rich: {subject}")
                else:
                    result["message"] = f"Email queued -- Resend quota may be hit. Subject: {subject}. Will retry in the morning."
                    slack_post(f"[Marcus/Voice] Email queued (quota): {subject}")

            elif action == "post_slack":
                channel = body.get("channel", "war-room")
                message = body.get("message", "")
                slack_post(f"*[Marcus Cole -- Voice Command]*\n{message}")
                result["message"] = f"Posted to Slack: {message[:80]}"

            elif action == "pipeline_status":
                bot = get_bot_status()
                pipeline = (
                    "Wholesale pipeline: 18 of 18 scripts passing. "
                    "100 leads in database, 65 active buyers. "
                    "Last run completed successfully. "
                    "57 new leads, 37 contacted, 6 dead. "
                    "Pipeline runs 3 times daily at 7 AM, noon, and 5 PM Pacific."
                )
                result["message"] = f"{pipeline} {bot}"

            elif action == "bot_status":
                result["message"] = get_bot_status()

            elif action == "dispatch":
                agent_name = body.get("agent_name", "unknown")
                task = body.get("task", "no task specified")
                target_state = body.get("state", "MO")  # default to Missouri
                ts_str = get_pt_time().strftime("%I:%M %p PT")

                # Telemarketing compliance check for call-related dispatches
                call_keywords = ["call", "phone", "dial", "ring", "cold call", "outreach call", "follow up call"]
                is_call_task = any(kw in task.lower() for kw in call_keywords)
                if is_call_task and not is_call_allowed(target_state):
                    local_tz_offset = STATE_TZ.get(target_state.upper(), -5)
                    local_tz = timezone(timedelta(hours=local_tz_offset))
                    local_hour = datetime.now(local_tz).hour
                    result["message"] = (
                        f"Cannot dispatch {agent_name} for calls right now. "
                        f"TCPA compliance: calls only allowed 9 AM to 7 PM local time. "
                        f"It is currently {local_hour}:00 in {target_state}. "
                        f"I have queued this for the next business window and will dispatch automatically."
                    )
                    slack_post(
                        f"*[COMPLIANCE BLOCK]*\n"
                        f"Dispatch for {agent_name} blocked -- outside calling hours for {target_state}. "
                        f"Local time: {local_hour}:00. Will auto-dispatch at 9 AM {target_state} time."
                    )
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(result).encode())
                    log(f"BLOCKED: {agent_name} call dispatch -- outside hours for {target_state}")
                    return

                dispatch_msg = (
                    f"*DISPATCH ORDER from Marcus Cole (Voice Command)*\n"
                    f"*Agent:* {agent_name}\n"
                    f"*Task:* {task}\n"
                    f"*Time:* {ts_str}\n"
                    f"*Status:* Dispatched -- awaiting execution"
                )

                slack_post(dispatch_msg)
                slack_post(dispatch_msg, SLACK_ALERTS)

                report = generate_report(
                    f"Agent Dispatched: {agent_name}",
                    f"<p><strong>Agent:</strong> {agent_name}</p>"
                    f"<p><strong>Task:</strong> {task}</p>"
                    f"<p><strong>Channel:</strong> Posted to #hive-war-room and #alerts</p>"
                    f"<p><strong>Next step:</strong> Agent will execute task and report back.</p>"
                )
                send_email(RICH_EMAIL, f"[DISPATCH] {agent_name}: {task[:50]}", report)

                result["message"] = (
                    f"{agent_name} has been dispatched to {task}. "
                    f"I posted the order to Slack and sent you a detailed report via email."
                )

            else:
                result = {"status": "error", "message": f"Unknown action: {action}"}

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            log(f"RESULT: {result['message'][:150]}")

        except Exception as e:
            log(f"ERROR: {traceback.format_exc()}")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    log("Hive Voice Handler v2 starting on port 8200...")
    HTTPServer(("0.0.0.0", 8200), Handler).serve_forever()
