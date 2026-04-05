#!/usr/bin/env python3
"""
Hive-to-n8n Integration Bridge
Gives all 63 Hive agents access to n8n's 400+ integrations via simple function calls.

n8n runs on Oracle E5 at http://129.159.38.250:5678. This bridge exposes
webhook-triggered workflows so agents can:
- Push data to Google Sheets, Notion, Airtable
- Query Salesforce, HubSpot CRM
- Send messages via Telegram, Discord, WhatsApp
- Trigger any n8n workflow from Python

Viktor has 3,000 OAuth connectors. We have n8n's 400+ nodes PLUS custom webhooks.
Same capability, zero per-user cost.

Usage:
    from hive_n8n_bridge import n8n_trigger, n8n_gdoc, n8n_sheet, n8n_notify

    # Trigger any n8n webhook workflow
    n8n_trigger("my-workflow-id", {"key": "value"})

    # Shortcuts for common operations
    n8n_gdoc(title="Deal Report", content="...", folder="Broker_OS")
    n8n_sheet(sheet_id="abc123", data=[{"col": "val"}])
    n8n_notify(channel="slack", message="Deal closed!")
"""
import os
import json
import logging
import urllib.request

log = logging.getLogger("hive-n8n-bridge")

N8N_BASE = os.environ.get("N8N_URL", "http://129.159.38.250:5678")
N8N_API_KEY = os.environ.get("N8N_API_KEY", "")

# Pre-configured webhook paths (create these workflows in n8n)
WEBHOOKS = {
    "gdoc": "/webhook/hive-log-to-gdoc",
    "sheet": "/webhook/hive-to-sheets",
    "notify": "/webhook/hive-notify",
    "crm": "/webhook/hive-crm-sync",
    "generic": "/webhook/hive-generic",
}


def n8n_trigger(webhook_path: str, payload: dict, method: str = "POST") -> dict:
    """
    Trigger any n8n webhook workflow.

    Args:
        webhook_path: Full path like "/webhook/abc123" or just "abc123"
        payload: JSON payload to send
        method: HTTP method (POST default)

    Returns:
        Response dict from n8n
    """
    if not webhook_path.startswith("/"):
        webhook_path = f"/webhook/{webhook_path}"

    url = f"{N8N_BASE}{webhook_path}"
    data = json.dumps(payload).encode()

    headers = {"Content-Type": "application/json"}
    if N8N_API_KEY:
        headers["X-N8N-API-KEY"] = N8N_API_KEY

    try:
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        log.error(f"n8n webhook failed ({e.code}): {body[:200]}")
        return {"ok": False, "error": f"HTTP {e.code}", "detail": body[:200]}
    except Exception as e:
        log.error(f"n8n trigger failed: {e}")
        return {"ok": False, "error": str(e)}


def n8n_gdoc(title: str, content: str, folder: str = "Hive_Reports",
             slack_channel: str = "", summary: str = "") -> dict:
    """
    Create a Google Doc via n8n workflow.
    Uses the existing hive-log-to-gdoc webhook.
    """
    return n8n_trigger(WEBHOOKS["gdoc"], {
        "title": title,
        "content": content,
        "folder": folder,
        "slack_channel": slack_channel,
        "summary": summary,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "source": "hive-n8n-bridge",
    })


def n8n_sheet(sheet_id: str, data: list[dict], sheet_name: str = "Sheet1") -> dict:
    """
    Append rows to a Google Sheet via n8n workflow.

    Args:
        sheet_id: Google Sheet ID
        data: List of row dicts to append
        sheet_name: Sheet/tab name
    """
    return n8n_trigger(WEBHOOKS["sheet"], {
        "sheet_id": sheet_id,
        "sheet_name": sheet_name,
        "rows": data,
    })


def n8n_notify(message: str, channel: str = "slack", target: str = "") -> dict:
    """
    Send a notification via n8n (Slack, Telegram, Discord, email, etc.).

    Args:
        message: Message text
        channel: Platform (slack, telegram, discord, email)
        target: Channel ID, chat ID, or email address
    """
    return n8n_trigger(WEBHOOKS["notify"], {
        "platform": channel,
        "target": target,
        "message": message,
    })


def n8n_crm_sync(action: str, data: dict) -> dict:
    """
    Sync data to/from CRM (HubSpot, Salesforce, etc.) via n8n.

    Args:
        action: create_contact, update_deal, get_pipeline, etc.
        data: Payload for the CRM operation
    """
    return n8n_trigger(WEBHOOKS["crm"], {
        "action": action,
        **data,
    })


# ============================================================================
# n8n Workflow Management (API-based)
# ============================================================================

def n8n_list_workflows() -> list:
    """List all n8n workflows via REST API."""
    url = f"{N8N_BASE}/api/v1/workflows"
    headers = {"Accept": "application/json"}
    if N8N_API_KEY:
        headers["X-N8N-API-KEY"] = N8N_API_KEY

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            return result.get("data", [])
    except Exception as e:
        log.error(f"n8n API failed: {e}")
        return []


def n8n_activate_workflow(workflow_id: str, active: bool = True) -> dict:
    """Activate or deactivate an n8n workflow."""
    url = f"{N8N_BASE}/api/v1/workflows/{workflow_id}"
    data = json.dumps({"active": active}).encode()
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if N8N_API_KEY:
        headers["X-N8N-API-KEY"] = N8N_API_KEY

    try:
        req = urllib.request.Request(url, data=data, method="PATCH", headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log.error(f"n8n workflow update failed: {e}")
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        workflows = n8n_list_workflows()
        for wf in workflows:
            status = "ACTIVE" if wf.get("active") else "inactive"
            print(f"  [{status}] {wf.get('name', '?')} (id: {wf.get('id', '?')})")
        print(f"\nTotal: {len(workflows)} workflows")
    else:
        print("Usage: python3 hive_n8n_bridge.py list")
        print("Or import: from hive_n8n_bridge import n8n_trigger, n8n_gdoc, n8n_sheet")
