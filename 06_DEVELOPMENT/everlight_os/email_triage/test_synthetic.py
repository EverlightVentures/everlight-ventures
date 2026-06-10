"""test_synthetic -- runs 6 fake emails through classifier + responder +
dnc_writer + triage_daemon.process_message. Uses DRY_RUN so no real sends.
Demonstrates the chain end-to-end before connecting to live IMAP.

Run: EMAIL_TRIAGE_DRY_RUN=1 /AA_MY_DRIVE/.venv/bin/python3 test_synthetic.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("EMAIL_TRIAGE_DRY_RUN", "1")
sys.path.insert(0, str(Path(__file__).parent))
import triage_daemon
import dnc_writer

SAMPLES = [
    {
        "thread_id": "<test-1>",
        "msg_id": "<test-msg-1@x>",
        "sender_email": "owner.melrose@example.com",
        "sender_name": "Joe Owner",
        "subject": "Re: 942 MELROSE -- cash offer",
        "body": "Please remove me from your list. I do not want to be contacted again. Thanks.",
        "received_at": "2026-05-07T14:30:00",
    },
    {
        "thread_id": "<test-2>",
        "msg_id": "<test-msg-2@x>",
        "sender_email": "atty@law.example",
        "sender_name": "Marvin Counsel",
        "subject": "ATTORNEY -- David Streubel matter",
        "body": "I am the legal counsel for the property owner at 4435. Cease and desist all communications immediately. Failure will result in BBB complaint and FTC referral.",
        "received_at": "2026-05-07T14:31:00",
    },
    {
        "thread_id": "<test-3>",
        "msg_id": "<test-msg-3@x>",
        "sender_email": "interested.seller@example.com",
        "sender_name": "Sarah Seller",
        "subject": "Re: cash offer for 1382 FLORIDA",
        "body": "Hi, yes I am interested in selling. Can you tell me more about the timeline and what your offer would be?",
        "received_at": "2026-05-07T14:32:00",
    },
    {
        "thread_id": "<test-4>",
        "msg_id": "<test-msg-4@x>",
        "sender_email": "curious@example.com",
        "sender_name": "Pat Curious",
        "subject": "How did you find me?",
        "body": "Who are you and how did you get my address?",
        "received_at": "2026-05-07T14:33:00",
    },
    {
        "thread_id": "<test-5>",
        "msg_id": "<test-msg-5@x>",
        "sender_email": "spam@malicious.example",
        "sender_name": "",
        "subject": "WIN A FREE IPHONE!!!",
        "body": "Click here NOW to claim your iPhone 99! Limited time! https://malicious.example/click",
        "received_at": "2026-05-07T14:34:00",
    },
    {
        "thread_id": "<test-6>",
        "msg_id": "<test-msg-6@x>",
        "sender_email": "mailer-daemon@example.com",
        "sender_name": "Mail Delivery System",
        "subject": "Mail Delivery Failure: 942 MELROSE outreach",
        "body": "Your message to owner.melrose@example.com was not delivered. 550 5.1.1 Address rejected.",
        "received_at": "2026-05-07T14:35:00",
    },
    # 7th: same as #1 but different sender. Should NOT add Joe Owner twice.
    {
        "thread_id": "<test-7>",
        "msg_id": "<test-msg-7@x>",
        "sender_email": "another.owner@example.com",
        "sender_name": "Jane Other",
        "subject": "unsubscribe",
        "body": "unsubscribe",
        "received_at": "2026-05-07T14:36:00",
    },
]


def main() -> int:
    print(f"=== triage_daemon test_synthetic (DRY_RUN={os.environ['EMAIL_TRIAGE_DRY_RUN']}) ===\n")

    print("DNC list before:")
    for r in dnc_writer.list_dnc():
        print(f"  {r['email']:35} | {r['reason']}")

    print(f"\n=== processing {len(SAMPLES)} synthetic messages ===\n")

    results = []
    for m in SAMPLES:
        print(f"--- {m['sender_email']} | {m['subject'][:60]} ---")
        r = triage_daemon.process_message(m)
        print(f"  -> action={r['action']:14} tag={r.get('tag','?')} sender={r['sender']}")
        results.append(r)
        print()

    print("=== DNC list after (should include 2 new opt_outs + Streubel preemptive) ===")
    for r in dnc_writer.list_dnc():
        print(f"  {r['email']:35} | {r['reason'][:60]}")

    print("\n=== approval queue (queued items awaiting Rich) ===")
    queue = Path("/AA_MY_DRIVE/_logs/email_triage/approval_queue.jsonl")
    if queue.exists():
        for line in queue.read_text().splitlines()[-len(SAMPLES):]:
            entry = json.loads(line)
            print(f"  [{entry['tag']:14}] {entry['sender_email']:35} -- {entry['draft_action']}")
            if entry.get("draft_body"):
                print(f"     draft preview: {entry['draft_body'][:100]!r}")

    print("\n=== summary ===")
    counts = {}
    for r in results:
        counts[r["action"]] = counts.get(r["action"], 0) + 1
    for k, v in counts.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
