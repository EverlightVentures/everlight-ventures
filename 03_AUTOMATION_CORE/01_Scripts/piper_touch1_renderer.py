"""
Piper Touch 1 Renderer -- the wholesale_template_renderer's first cut.

Loads Vera's CANONICAL_SIM_TEMPLATES.md Stage 02 body, resolves OSINT slots
via marquise_intel.resolve_osint_slots(), picks the right relate-line based
on dominant signal, substitutes, saves a draft per target.

Usage:
  python piper_touch1_renderer.py --parcel-json PATH         # render one
  python piper_touch1_renderer.py --top-targets PATH         # render the ranked top-N file
  python piper_touch1_renderer.py --top-n 5 --top-targets PATH   # cap to N

Output: _state/piper_drafts/<parcel_id>__<addr_slug>.html (one per target)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

WS = Path("/mnt/sdcard/AA_MY_DRIVE")
DRAFT_DIR = WS / "_state" / "piper_drafts"
CT_DIR = WS / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"
if str(CT_DIR) not in sys.path:
    sys.path.insert(0, str(CT_DIR))

# Vera's canonical Stage 02 body (extracted verbatim from CANONICAL_SIM_TEMPLATES.md:131-148)
PIPER_TOUCH1_BODY = """<p>Hey {seller_first_name},</p>

<p>I came across your spot at <strong>{property_address}</strong> while pulling Shelby County records for our buyers this quarter. Records show it has been with you since {last_sale_year}, about {years_owned} years now.</p>

<p>{piper_relate_line}</p>

<p>I work the outreach side for a small Memphis acquisitions team. We have {everlight_buyers_count_quarter} buy-and-hold buyers active in your zip this quarter, all cash, no agents, no listing. Some of these get sold and the owner never knew the option existed, so I figured I would just say hello.</p>

<p>{market_context_line}</p>

<p>No pitch on this email. Just a quick two questions, if you are open:</p>
<ol>
  <li>Have you ever thought about parting with it?</li>
  <li>Is there a specific reason you have held on this long (taxes, plans for it, family, just forgot about it)?</li>
</ol>

<p>No rush on timing. If the answer is "not interested," I will close the file and not bother you again. If there is any curiosity at all, my colleague <strong>Henry Hammond</strong> on our acquisitions side can run actual numbers for you. He is the math person on our team, I am just the front door.</p>

<p>Thanks for the time, and either way, hope your week is a good one.</p>
"""

# Canonical relate-line generator (per CANONICAL_SIM_TEMPLATES.md:154-158)
def relate_line(slots: dict) -> str:
    if slots.get("owner_mailing_state_diff"):
        return (
            f"Managing a Memphis parcel from {slots.get('owner_mailing_city') or 'out of state'} is a lot. "
            "The county does not exactly send postcards when something changes."
        )
    yrs = slots.get("years_owned") or 0
    try: yrs = int(yrs)
    except: yrs = 0
    if yrs >= 10:
        return (
            f"{yrs} years is a long time to carry something. People hold for all kinds of reasons, "
            "and sometimes the reason quietly changes."
        )
    if slots.get("is_vacant_lot"):
        return (
            "Vacant lots can be quietly expensive year over year. Taxes, mowing fines, the occasional code letter. "
            "None of it shows up loud, it just compounds."
        )
    owner = (slots.get("seller_last_name", "") + slots.get("seller_first_name", "")).upper()
    if "LLC" in owner or "INC" in owner or "TRUST" in owner:
        return "Investor to investor, I figured I would just go direct. Saves us both the listing dance."
    return (
        "Memphis parcels in the older subdivisions tend to sit until the right buyer notices. "
        "Wanted to put a door on the table before assuming anything about your plans."
    )


def render_one(parsed_path: Path) -> dict:
    from marquise_intel import resolve_osint_slots
    parcel = json.loads(parsed_path.read_text())
    slots = resolve_osint_slots(parcel)
    slots["piper_relate_line"] = relate_line(slots)
    body = PIPER_TOUCH1_BODY.format(**{k: ("" if v is None else v) for k, v in slots.items()})
    addr_short = (slots.get("property_address", "") or "").split(",")[0].strip().replace(" ", "_")
    subject = f"About your spot at {addr_short.replace('_', ' ')}"
    return {
        "parcel_id": slots.get("parcel_id", ""),
        "to_address_owner": slots.get("seller_first_name", "") + " " + slots.get("seller_last_name", ""),
        "to_mailing": parcel.get("owner_mailing_street", ""),
        "to_mailing_csz": f"{parcel.get('owner_mailing_city','')}, {parcel.get('owner_mailing_state','')} {parcel.get('owner_mailing_zip','')}",
        "from_persona": "piper_reeves",
        "from_email": "piper@everlightventures.io",
        "subject": subject,
        "body_html": body,
        "slots_used": slots,
        "ready_to_send": False,
        "blocked_reason": "no_owner_email_yet",
        "next_step": "skip_trace_owner_to_resolve_email",
    }


def main(argv):
    p = argparse.ArgumentParser()
    p.add_argument("--top-targets", default=str(WS / "_state/TN_TOP_TARGETS_2026-05-18.json"))
    p.add_argument("--top-n", type=int, default=5)
    args = p.parse_args(argv)

    DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    targets = json.loads(Path(args.top_targets).read_text())
    # Dedupe by parcel_id, keep highest score
    seen = {}
    for t in targets:
        pid = t.get("parcel_id", "")
        if pid not in seen or t.get("score", 0) > seen[pid].get("score", 0):
            seen[pid] = t
    deduped = sorted(seen.values(), key=lambda x: -x.get("score", 0))[: args.top_n]

    summary = []
    for t in deduped:
        parsed_path = Path(t["path"])
        result = render_one(parsed_path)
        # File slug
        slug = result["parcel_id"].replace(" ", "_") or parsed_path.stem
        addr_slug = (result["subject"] or "").replace("About your spot at ", "").replace(" ", "_")[:30]
        out_file = DRAFT_DIR / f"{slug}__{addr_slug}.html"
        full = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{result['subject']}</title>
<style>body{{font-family:Inter,system-ui,sans-serif;max-width:680px;margin:40px auto;padding:24px;background:#0a0a0a;color:#e8e8e8}}
.meta{{background:#1a1a1a;border-left:4px solid #D4AF37;padding:16px;margin-bottom:24px;font-size:13px}}
.meta dt{{color:#D4AF37;font-weight:600;letter-spacing:1px;font-size:11px;text-transform:uppercase;margin-top:8px}}
.meta dd{{margin:4px 0 0 0;color:#e8e8e8}}
.body{{background:#fafaf8;color:#0a0a0a;padding:32px;border-radius:8px;line-height:1.6}}
.blocked{{background:#2a1818;border-left:4px solid #ff6b6b;padding:12px;margin-top:24px;color:#ffb3b3;font-size:13px}}</style>
</head><body>
<div class="meta">
<dt>Persona</dt><dd>{result['from_persona']} &lt;{result['from_email']}&gt;</dd>
<dt>To owner</dt><dd>{result['to_address_owner']}</dd>
<dt>Mailing</dt><dd>{result['to_mailing']}<br>{result['to_mailing_csz']}</dd>
<dt>Subject</dt><dd>{result['subject']}</dd>
<dt>Parcel</dt><dd>{result['parcel_id']}</dd>
</div>
<div class="body">{result['body_html']}
<p style="margin-top:24px;color:#666">--<br>Piper Reeves<br>Outreach Specialist, Wholesale Acquisitions<br>Everlight Ventures<br>piper@everlightventures.io</p>
</div>
<div class="blocked">⚠ NOT YET SENDABLE: {result['blocked_reason']}. Next step: {result['next_step']}.</div>
</body></html>"""
        out_file.write_text(full)
        summary.append({
            "parcel_id": result["parcel_id"],
            "address": result["slots_used"].get("property_address", ""),
            "owner": result["to_address_owner"],
            "mailing_state": result["slots_used"].get("owner_mailing_state", ""),
            "draft_path": str(out_file),
            "blocked": result["blocked_reason"],
        })

    # Index file
    index_path = DRAFT_DIR / "INDEX.json"
    index_path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "drafts": summary,
        "skip_trace_required": True,
        "skip_trace_tool": "Wholesale/skip_trace/intel_enricher.py",
        "next_action": "Run intel_enricher on each parcel owner to resolve owner_email; then drafts become sendable through branded_mailer.",
    }, indent=2))

    print(f"Generated {len(summary)} Piper touch-1 drafts in {DRAFT_DIR}")
    print(f"Index: {index_path}")
    for d in summary:
        print(f"  - {d['address']:50} | owner={d['owner'][:25]:25} | mail_state={d['mailing_state']:3} | draft: {Path(d['draft_path']).name}")


if __name__ == "__main__":
    main(sys.argv[1:])
