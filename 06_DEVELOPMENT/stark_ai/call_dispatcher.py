"""
Call Dispatcher -- Pre-loads agent with live Supabase data before every outbound call.
Pulls prospect profile, deal history, pipeline status, and injects into call context.

Usage:
    from call_dispatcher import call_as_piper, call_as_marcus, call_as_lucrex, call_prospect
    call_as_piper("+17075551234")  # test/internal call
    call_prospect("piper", "+17075551234", prospect_email="alex@infisical.com")  # data-loaded call
"""
from __future__ import annotations
import json
import os
import requests
from pathlib import Path

# Load creds
_env = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")
if not _env.exists():
    _env = Path("/home/opc/.env")
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

EL_KEY = os.getenv("ELEVENLABS_API_KEY", "")
SB_URL = os.getenv("SUPABASE_URL", "https://jdqqmsmwmbsnlnstyavl.supabase.co")
SB_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_ANON_KEY", ""))

# Agent registry
AGENTS = {
    "piper": {
        "agent_id": "agent_2901knre633zesfvcydtjjd6pgar",
        "phone_id": "phnum_3301knqyxv8mem7teb8bvhy7hds9",
        "phone": "+17078010360",
        "name": "Piper Reeves",
    },
    "lucrex": {
        "agent_id": "agent_0501knrfnp6ye0waf1ncteth52vz",
        "phone_id": "phnum_0901knqyxweveptbygpbzpta9dts",
        "phone": "+17077607922",
        "name": "Lucrex",
    },
    "marcus": {
        "agent_id": "agent_8801knrf062terg87c2k6zh1s7et",
        "phone_id": "phnum_9401knqxqyvqeqw91447sprp0ark",
        "phone": "+18888966772",
        "name": "Marcus Cole",
    },
}


def _sb_query(table, params=""):
    """Query Supabase REST API."""
    try:
        resp = requests.get(
            "%s/rest/v1/%s?%s" % (SB_URL, table, params),
            headers={"apikey": SB_KEY, "Authorization": "Bearer %s" % SB_KEY},
            timeout=10,
        )
        return resp.json() if resp.status_code == 200 else []
    except Exception:
        return []


def get_prospect_context(email=None, name=None):
    """Pull prospect data from Supabase for call context."""
    context = []

    # Check broker leads
    if email:
        leads = _sb_query("broker_leads", "email=eq.%s&select=*&limit=5" % email)
        if leads:
            l = leads[0]
            context.append("PROSPECT DATA: %s at %s. Need: %s. Intent: %s. Score: %s." % (
                l.get("name", ""), l.get("company", ""), l.get("need_description", ""),
                l.get("intent", ""), l.get("lead_score", "")
            ))

    # Check broker offers (if they are a seller)
    if email:
        offers = _sb_query("broker_offers", "seller_email=eq.%s&select=*&limit=5" % email)
        if offers:
            o = offers[0]
            context.append("THEIR PRODUCT: %s. Category: %s. Price: $%s-%s/mo." % (
                o.get("title", ""), o.get("category", ""),
                o.get("price_min", ""), o.get("price_max", "")
            ))

    # Check deals
    if email:
        deals = _sb_query("broker_deals", "select=*&limit=5")
        # Filter client-side since deals might not have email field
        for d in deals:
            if email in json.dumps(d):
                context.append("EXISTING DEAL: Stage %s. Value: $%s. Commission: $%s." % (
                    d.get("stage", ""), d.get("deal_value", ""), d.get("commission_due", "")
                ))

    # Pipeline summary
    matches = _sb_query("broker_matches", "select=id&limit=100")
    leads_count = _sb_query("broker_leads", "select=id&limit=100")
    context.append("PIPELINE NOW: %d total leads, %d matches scored." % (len(leads_count), len(matches)))

    # Wholesale stats
    wholesale = _sb_query("wholesale_leads", "select=id,status&limit=200")
    if wholesale:
        by_status = {}
        for w in wholesale:
            s = w.get("status", "unknown")
            by_status[s] = by_status.get(s, 0) + 1
        context.append("WHOLESALE: %d leads. %s." % (
            len(wholesale),
            ", ".join("%s: %d" % (k, v) for k, v in by_status.items())
        ))

    return "\n".join(context) if context else "No prospect data found."


def call_prospect(agent_key, to_number, prospect_email=None, prospect_name=None, extra_context=""):
    """Make an outbound call with live data injected into agent context."""
    agent = AGENTS.get(agent_key)
    if not agent or not agent.get("agent_id"):
        return {"success": False, "error": "Agent %s not configured" % agent_key}

    # Pull live data
    data_context = get_prospect_context(prospect_email, prospect_name)

    override = None
    if data_context or extra_context:
        prompt_addition = "\n\nLIVE DATA FOR THIS CALL:\n%s" % data_context
        if extra_context:
            prompt_addition += "\n%s" % extra_context
        override = {
            "conversation_config_override": {
                "agent": {
                    "prompt": {
                        "prompt": prompt_addition
                    }
                }
            }
        }

    payload = {
        "agent_id": agent["agent_id"],
        "agent_phone_number_id": agent["phone_id"],
        "to_number": to_number,
    }
    if override:
        payload.update(override)

    resp = requests.post(
        "https://api.elevenlabs.io/v1/convai/twilio/outbound-call",
        headers={"xi-api-key": EL_KEY, "Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    return resp.json()


def call_as_piper(to_number, prospect_email=None, extra=""):
    return call_prospect("piper", to_number, prospect_email, extra_context=extra)

def call_as_marcus(to_number, prospect_email=None, extra=""):
    return call_prospect("marcus", to_number, prospect_email, extra_context=extra)

def call_as_lucrex(to_number, prospect_email=None, extra=""):
    return call_prospect("lucrex", to_number, prospect_email, extra_context=extra)


if __name__ == "__main__":
    print("=== Testing data loader ===")
    ctx = get_prospect_context("alexandra@infisical.com")
    print(ctx)
    print("\n=== Agent registry ===")
    for k, v in AGENTS.items():
        print("  %s: %s | %s" % (k, v["name"], v["phone"]))
