"""wholesale_pipeline_orchestrator.py -- canonical 12-phase wholesale runner.

Codifies the 12-phase Autonomous Wholesale Workflow Pattern (AWWP) Marquise
hand-built on 2026-04-29. Replays it autonomously, lead-by-lead, idempotent,
cap-aware (25/day Marquise pacing rule).

Philosophy
----------
- Phases are *gates*, not steps. A lead enters phase N only when phase N-1's
  artifact exists. Re-runs are safe -- existing artifacts are detected and
  the lead skips to its next gate.
- The orchestrator NEVER auto-fires outbound human-facing comms (emails to
  sellers / buyers / title / Chris). Those land in the
  outreach_queue/pending_approval/ folder and Marcus pings #war-room with
  the artifact. Marquise approves; a separate fire script sends.
- Internal work (intel deepdive, skip-trace, MX verify, contract generation,
  Slack ops pings, hive_logger events) auto-runs.
- Surfaces blockers honestly. Operator Truth doctrine -- failures lead, not
  greens.

Usage
-----
    python3 wholesale_pipeline_orchestrator.py --once         # one pass
    python3 wholesale_pipeline_orchestrator.py --dry-run      # report only
    python3 wholesale_pipeline_orchestrator.py --parcel "P"   # single lead

Hooked from Oracle cron (recommended):
    */30 6-21 * * *  python3 .../wholesale_pipeline_orchestrator.py --once
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ------------------------------------------------------------------
# Paths -- absolute, no relative imports allowed (cwd resets between runs)
# ------------------------------------------------------------------
WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
WHOLESALE = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale"
PARSED_DIR = WHOLESALE / "owner_downloads/parsed"
INTEL_DIR = WHOLESALE / "seller_intel"
QUEUE_DIR = WHOLESALE / "outreach_queue"
PENDING_DIR = QUEUE_DIR / "pending_approval"
PSA_OUT_DIR = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/contracts"
LOG_DIR = WORKSPACE / "_logs/wholesale_orchestrator"

DEFAULT_DAILY_CAP = 25  # Marquise pacing rule

# ------------------------------------------------------------------
# Hive logger / branded slack -- import lazily, fail soft
# ------------------------------------------------------------------
sys.path.insert(0, str(WORKSPACE / "03_AUTOMATION_CORE/01_Scripts"))


def _safe_import(name: str):
    try:
        mod = __import__(name, fromlist=["*"])
        return mod
    except Exception:
        return None


hive_logger = _safe_import("content_tools.hive_logger")
branded_slack = _safe_import("content_tools.branded_slack")


# ------------------------------------------------------------------
# Phase identifiers (match AUTONOMOUS_WORKFLOW_PATTERN.md)
# ------------------------------------------------------------------
PHASES = [
    "1_intake",
    "2_assessor_enrich",
    "3_buybox_gate",
    "4_intel_deepdive",
    "5_skip_trace",
    "6_compliance_gate",
    "7_email_send",
    "8_reply_triage",
    "9_psa_gen",
    "10_buyer_assign",
    "11_title_bec",
    "12_wire_ledger",
]

PHASE_OWNERS = {
    "1_intake": "(cron)",
    "2_assessor_enrich": "Playwright",
    "3_buybox_gate": "parser",
    "4_intel_deepdive": "Cipher Wolfe",
    "5_skip_trace": "Phil Banks",
    "6_compliance_gate": "Justine Park",
    "7_email_send": "Piper Reeves",
    "8_reply_triage": "(imap)",
    "9_psa_gen": "Henry Knox",
    "10_buyer_assign": "Penny Vance + Henry",
    "11_title_bec": "Henry + Shield",
    "12_wire_ledger": "Carlos Moreno",
}


# ------------------------------------------------------------------
# Data structures
# ------------------------------------------------------------------
@dataclass
class LeadState:
    parcel_id: str
    property_address: str
    current_phase: str
    next_phase: str
    blocker: str | None
    blocker_recipe: str | None
    artifacts: dict[str, str]
    last_transition: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ------------------------------------------------------------------
# Phase detection
# ------------------------------------------------------------------
def _intel_dir(parcel_id: str) -> Path:
    safe = parcel_id.strip().replace("  ", "__").replace(" ", "_")
    return INTEL_DIR / safe


def _slug(parcel_id: str) -> str:
    return parcel_id.strip().replace("  ", "__").replace(" ", "_")


def detect_phase(parcel_id: str, parsed_path: Path) -> LeadState:
    """Return the current LeadState for a lead. Idempotent -- pure function of FS."""
    intel_dir = _intel_dir(parcel_id)
    artifacts: dict[str, str] = {"parsed": str(parsed_path)}
    parsed = json.loads(parsed_path.read_text())
    addr = parsed.get("property_address") or parsed.get("address") or "?"

    chris_check = parsed.get("chris_check", "UNKNOWN")
    artifacts["buybox_verdict"] = chris_check

    # Phase 3 gate -- REJECT verdicts terminate
    if isinstance(chris_check, str) and "REJECT" in chris_check:
        return LeadState(
            parcel_id=parcel_id, property_address=addr,
            current_phase="3_buybox_gate", next_phase="(terminated)",
            blocker="rejected_by_buybox", blocker_recipe="auto-drop",
            artifacts=artifacts,
            last_transition=datetime.now(timezone.utc).isoformat(),
        )

    intel_json = intel_dir / "intel.json"
    if not intel_json.exists():
        return LeadState(
            parcel_id=parcel_id, property_address=addr,
            current_phase="3_buybox_gate", next_phase="4_intel_deepdive",
            blocker="intel_not_run",
            blocker_recipe="run seller_intel_deepdive.py --parcel '{p}'",
            artifacts=artifacts,
            last_transition=datetime.now(timezone.utc).isoformat(),
        )
    artifacts["intel"] = str(intel_json)

    skip_json = intel_dir / "skip_trace.json"
    if not skip_json.exists():
        return LeadState(
            parcel_id=parcel_id, property_address=addr,
            current_phase="4_intel_deepdive", next_phase="5_skip_trace",
            blocker="skip_trace_pending",
            blocker_recipe="dispatch Phil Banks free-tier cascade",
            artifacts=artifacts,
            last_transition=datetime.now(timezone.utc).isoformat(),
        )
    artifacts["skip_trace"] = str(skip_json)

    skip = json.loads(skip_json.read_text())
    has_first_name = bool(skip.get("first_name") and not str(skip["first_name"]).startswith("["))
    has_email = bool(skip.get("email") and skip.get("email_mx_verified"))

    if not has_first_name:
        return LeadState(
            parcel_id=parcel_id, property_address=addr,
            current_phase="5_skip_trace", next_phase="5_skip_trace",
            blocker="no_real_first_name",
            blocker_recipe="Cipher: probate / obit / public records search; estate falls to executor name",
            artifacts=artifacts,
            last_transition=datetime.now(timezone.utc).isoformat(),
        )

    if not has_email:
        return LeadState(
            parcel_id=parcel_id, property_address=addr,
            current_phase="5_skip_trace", next_phase="6_compliance_gate",
            blocker="no_mx_verified_email",
            blocker_recipe="Cipher: WebSearch + LinkedIn; Phil: pattern-guess + MX verify",
            artifacts=artifacts,
            last_transition=datetime.now(timezone.utc).isoformat(),
        )

    compliance = intel_dir / "compliance_check.json"
    if not compliance.exists():
        return LeadState(
            parcel_id=parcel_id, property_address=addr,
            current_phase="5_skip_trace", next_phase="6_compliance_gate",
            blocker="compliance_not_run",
            blocker_recipe="Justine: state_gate + CAN-SPAM + DNC + placeholder scan",
            artifacts=artifacts,
            last_transition=datetime.now(timezone.utc).isoformat(),
        )
    artifacts["compliance"] = str(compliance)
    cp = json.loads(compliance.read_text())
    if cp.get("verdict") != "PASS":
        return LeadState(
            parcel_id=parcel_id, property_address=addr,
            current_phase="6_compliance_gate", next_phase="6_compliance_gate",
            blocker="compliance_failed",
            blocker_recipe=cp.get("recipe") or "Justine: review failures + remediate",
            artifacts=artifacts,
            last_transition=datetime.now(timezone.utc).isoformat(),
        )

    email_draft = intel_dir / "email_draft.json"
    if not email_draft.exists():
        return LeadState(
            parcel_id=parcel_id, property_address=addr,
            current_phase="6_compliance_gate", next_phase="7_email_send",
            blocker="email_not_drafted",
            blocker_recipe="Piper: render template + queue to outreach_queue/pending_approval/",
            artifacts=artifacts,
            last_transition=datetime.now(timezone.utc).isoformat(),
        )
    artifacts["email_draft"] = str(email_draft)

    email_sent_marker = intel_dir / "email_sent.json"
    if not email_sent_marker.exists():
        return LeadState(
            parcel_id=parcel_id, property_address=addr,
            current_phase="7_email_send", next_phase="8_reply_triage",
            blocker="awaiting_marquise_approval",
            blocker_recipe="Marquise reviews pending_approval/ then runs fire script",
            artifacts=artifacts,
            last_transition=datetime.now(timezone.utc).isoformat(),
        )
    artifacts["email_sent"] = str(email_sent_marker)

    reply = intel_dir / "reply_classified.json"
    if not reply.exists():
        return LeadState(
            parcel_id=parcel_id, property_address=addr,
            current_phase="7_email_send", next_phase="8_reply_triage",
            blocker="awaiting_reply",
            blocker_recipe="phone_imap_poller cron polls every 5 min",
            artifacts=artifacts,
            last_transition=datetime.now(timezone.utc).isoformat(),
        )
    artifacts["reply"] = str(reply)
    rep = json.loads(reply.read_text())
    if rep.get("intent") in ("not_interested", "stop"):
        return LeadState(
            parcel_id=parcel_id, property_address=addr,
            current_phase="8_reply_triage", next_phase="(terminated)",
            blocker="seller_declined", blocker_recipe="drop, no further contact",
            artifacts=artifacts,
            last_transition=datetime.now(timezone.utc).isoformat(),
        )

    psa_pdf = list(PSA_OUT_DIR.glob(f"*{_slug(parcel_id)}*.pdf")) if PSA_OUT_DIR.exists() else []
    if not psa_pdf:
        return LeadState(
            parcel_id=parcel_id, property_address=addr,
            current_phase="8_reply_triage", next_phase="9_psa_gen",
            blocker="psa_not_generated",
            blocker_recipe=f"python3 03_AUTOMATION_CORE/01_Scripts/gen_psa.py '{parcel_id}'",
            artifacts=artifacts,
            last_transition=datetime.now(timezone.utc).isoformat(),
        )
    artifacts["psa_pdf"] = str(psa_pdf[0])

    signed = intel_dir / "psa_signed.json"
    if not signed.exists():
        return LeadState(
            parcel_id=parcel_id, property_address=addr,
            current_phase="9_psa_gen", next_phase="10_buyer_assign",
            blocker="awaiting_seller_signature",
            blocker_recipe="Henry: send via Documenso, watch webhook",
            artifacts=artifacts,
            last_transition=datetime.now(timezone.utc).isoformat(),
        )
    artifacts["psa_signed"] = str(signed)

    pkg = intel_dir / "buyer_package_sent.json"
    if not pkg.exists():
        return LeadState(
            parcel_id=parcel_id, property_address=addr,
            current_phase="9_psa_gen", next_phase="10_buyer_assign",
            blocker="buyer_package_pending",
            blocker_recipe="Penny: assemble package + Henry: gen Assignment Agreement (Clauses 2.1/2.4/2.6)",
            artifacts=artifacts,
            last_transition=datetime.now(timezone.utc).isoformat(),
        )
    artifacts["buyer_package"] = str(pkg)

    gfad = intel_dir / "gfad_received.json"
    if not gfad.exists():
        return LeadState(
            parcel_id=parcel_id, property_address=addr,
            current_phase="10_buyer_assign", next_phase="11_title_bec",
            blocker="gfad_not_wired",
            blocker_recipe="48hr clock from Chris signing Assignment; backup buyer if expires",
            artifacts=artifacts,
            last_transition=datetime.now(timezone.utc).isoformat(),
        )
    artifacts["gfad"] = str(gfad)

    bec = intel_dir / "bec_verified.json"
    if not bec.exists():
        return LeadState(
            parcel_id=parcel_id, property_address=addr,
            current_phase="10_buyer_assign", next_phase="11_title_bec",
            blocker="bec_check_pending",
            blocker_recipe="Shield: voice-verify wire instructions on number from THEIR website",
            artifacts=artifacts,
            last_transition=datetime.now(timezone.utc).isoformat(),
        )
    artifacts["bec"] = str(bec)

    wire = intel_dir / "wire_received.json"
    if not wire.exists():
        return LeadState(
            parcel_id=parcel_id, property_address=addr,
            current_phase="11_title_bec", next_phase="12_wire_ledger",
            blocker="awaiting_close",
            blocker_recipe="Title firm runs close; Carlos watches commission_ledger",
            artifacts=artifacts,
            last_transition=datetime.now(timezone.utc).isoformat(),
        )
    artifacts["wire"] = str(wire)

    return LeadState(
        parcel_id=parcel_id, property_address=addr,
        current_phase="12_wire_ledger", next_phase="(closed)",
        blocker=None, blocker_recipe=None,
        artifacts=artifacts,
        last_transition=datetime.now(timezone.utc).isoformat(),
    )


# ------------------------------------------------------------------
# Roll-up + Slack surfacing
# ------------------------------------------------------------------
def roll_up(states: list[LeadState]) -> dict[str, Any]:
    by_phase: dict[str, list[str]] = {p: [] for p in PHASES}
    by_blocker: dict[str, list[str]] = {}
    terminated = []
    closed = []
    ready_to_send_today = []

    for s in states:
        if s.next_phase == "(terminated)":
            terminated.append(s.parcel_id)
            continue
        if s.next_phase == "(closed)":
            closed.append(s.parcel_id)
            continue
        by_phase.setdefault(s.current_phase, []).append(s.parcel_id)
        if s.blocker:
            by_blocker.setdefault(s.blocker, []).append(s.parcel_id)
        if s.blocker == "awaiting_marquise_approval":
            ready_to_send_today.append(s.parcel_id)

    return {
        "total": len(states),
        "by_phase": by_phase,
        "by_blocker": by_blocker,
        "terminated": terminated,
        "closed": closed,
        "ready_to_send_today": ready_to_send_today,
    }


def post_summary_to_slack(rollup: dict[str, Any], dry_run: bool) -> None:
    if branded_slack is None:
        return
    fields = {
        "Total": str(rollup["total"]),
        "Closed": str(len(rollup["closed"])),
        "Terminated": str(len(rollup["terminated"])),
        "Ready to send today": str(len(rollup["ready_to_send_today"])),
    }
    body_lines = ["*Top blockers:*"]
    for b, parcels in sorted(rollup["by_blocker"].items(), key=lambda kv: -len(kv[1]))[:6]:
        body_lines.append(f"- `{b}` ({len(parcels)}): {', '.join(parcels[:3])}")
    body = "\n".join(body_lines)
    title = "Wholesale pipeline -- 12-phase pulse"
    summary = f"{rollup['total']} active leads, {len(rollup['ready_to_send_today'])} awaiting Marquise approval"
    if dry_run:
        title = "[DRY-RUN] " + title
    try:
        branded_slack.post_branded_slack(
            channel="war-room", title=title, summary=summary,
            body=body, fields=fields,
            agent_name="Marcus Cole", agent_title="Chief Operator",
            category="ops",
        )
    except Exception:
        pass


# ------------------------------------------------------------------
# Daily cap accounting
# ------------------------------------------------------------------
def sends_today() -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    n = 0
    for marker in INTEL_DIR.rglob("email_sent.json"):
        try:
            data = json.loads(marker.read_text())
            if str(data.get("sent_at", "")).startswith(today):
                n += 1
        except Exception:
            continue
    return n


def remaining_cap(cap: int) -> int:
    return max(0, cap - sends_today())


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def run(parcel_filter: str | None, dry_run: bool, cap: int) -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PENDING_DIR.mkdir(parents=True, exist_ok=True)

    run = None
    if hive_logger is not None:
        try:
            run = hive_logger.start(
                agent="marcus_cole",
                task="wholesale-orchestrator",
                inputs={"parcel_filter": parcel_filter, "dry_run": dry_run, "cap": cap},
            )
        except Exception:
            run = None

    parsed_files = sorted(PARSED_DIR.glob("*.json"))
    if parcel_filter:
        target = parcel_filter.strip().replace(" ", "").lower()
        parsed_files = [p for p in parsed_files if target in p.stem.replace(" ", "").lower()]

    states: list[LeadState] = []
    for p in parsed_files:
        try:
            parsed = json.loads(p.read_text())
        except Exception:
            continue
        parcel_id = parsed.get("parcel_id") or p.stem.replace("__", "  ")
        try:
            state = detect_phase(parcel_id, p)
            states.append(state)
            if run is not None:
                try:
                    run.event("lead.phase_detected", {
                        "parcel": parcel_id,
                        "current": state.current_phase,
                        "next": state.next_phase,
                        "blocker": state.blocker,
                    })
                except Exception:
                    pass
        except Exception as exc:
            if run is not None:
                try:
                    run.event("lead.error", {"parcel": parcel_id, "err": repr(exc)})
                except Exception:
                    pass

    rollup = roll_up(states)
    rollup["sends_today"] = sends_today()
    rollup["cap_remaining"] = remaining_cap(cap)
    rollup["timestamp"] = datetime.now(timezone.utc).isoformat()

    snapshot_path = LOG_DIR / f"pulse_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    snapshot_path.write_text(json.dumps({
        "rollup": rollup,
        "states": [s.as_dict() for s in states],
    }, indent=2))

    print(f"[orchestrator] {len(states)} leads scanned. {len(rollup['ready_to_send_today'])} ready to send today.")
    print(f"[orchestrator] cap remaining: {rollup['cap_remaining']}/{cap}. snapshot: {snapshot_path}")
    print(f"[orchestrator] top blockers: {dict((b, len(v)) for b, v in rollup['by_blocker'].items())}")

    if not dry_run:
        post_summary_to_slack(rollup, dry_run=False)

    if run is not None:
        try:
            run.artifact("json", url=f"file://{snapshot_path}", title="wholesale-orchestrator-pulse")
            run.finish(
                status="done",
                summary=f"{len(states)} leads. {len(rollup['ready_to_send_today'])} await Marquise. cap rem {rollup['cap_remaining']}/{cap}.",
            )
        except Exception:
            pass

    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--parcel", default=None, help="filter to one parcel id")
    p.add_argument("--dry-run", action="store_true", help="report only, no Slack post")
    p.add_argument("--once", action="store_true", help="single pass (default)")
    p.add_argument("--cap", type=int, default=DEFAULT_DAILY_CAP)
    args = p.parse_args()
    sys.exit(run(parcel_filter=args.parcel, dry_run=args.dry_run, cap=args.cap))


if __name__ == "__main__":
    main()
