# Channel Strategy: Email-First, Progressive, Legal Everywhere

**Principle:** Effortless for the seller. Non-annoying. Fast response. Legal in all 7 active states by default, without waiting on registrations or bonds.

## The Funnel

```
1. OUTBOUND: Email (primary channel)
      |
      v
2. INBOUND: Seller replies (email / text / call)
      |
      v
3. OUTBOUND: Manual human call during legal hours (close)
      |
      v
4. DEAL: Signed assignment contract
```

## Channel Rules

### Email (primary outbound)

- **Legal everywhere 24/7** (CAN-SPAM: no call-hour restriction)
- No TCPA, no state DNC, no solicitor registration required
- Requires: physical address in footer, working unsubscribe, truthful subject line
- Rich handles compliance via `hive_outreach.send_touch()` which already adds the required footer

### Inbound SMS (always welcomed)

- TCPA does NOT regulate consumer-initiated texts to us
- If a seller texts us first, we can text back freely (they initiated)
- Captured by an inbound webhook on the Twilio or Google Voice number we publish in the email signature
- No A2P 10DLC requirement for receiving texts
- Every reply is tagged as "inbound" in the lead record -- that flag unlocks outbound texting to that one seller

### Outbound SMS (BLOCKED until registered)

- TX SB 140 blocks cold outbound SMS to TX residents without SoS registration + $10K bond
- FL FTSA exposes us to $500-$1,500 per text on class-action suits
- CTIA carrier rules require pre-approved A2P 10DLC campaign
- **Strategy: do not send cold outbound SMS.** Only reply to inbound texts from sellers who initiated contact.
- `hive_outreach.send_sms()` gate enforces this via `A2P_APPROVED` env var and `is_inbound_consent=True` flag (to be added)

### Outbound Call (manual, human, within legal hours)

- Legal hours enforced by `compliance.state_gate.check_call_hour(state)`
- Per-state windows:
  - GA / MO / AZ / TN / CA: 8am-9pm local, all days
  - TX: 9am-9pm local, all days
  - FL: 8am-8pm Mon-Fri, 9am-5pm Sat, NO SUNDAY CALLS
- All-party recording states (CA, FL): call opens with recording disclosure
- Manual dial only. **Bot calls / AI voice / autodialer to cold leads = BLOCKED** (TCPA prior-express-written-consent rule)
- `compliance.state_gate.is_bot_call_allowed(state)` returns False for every state's cold-call path

### Direct Mail (DEPRECATED 2026-04-26 -- DIGITAL ONLY)

- **Strategic decision: Everlight is a digital-only operation.** Mail lane is deprecated until further notice.
- `lob_mail_sender.py` and the mail-first orchestrator branches remain in the repo as dormant code but are NOT called from `broker_daily_orchestrator.py`. To re-enable, requires (1) explicit user direction, (2) physical return address registered for CAN-SPAM/USPS compliance, (3) Lob account or hand-mail capacity.
- Reasons to skip: $25-50/letter all-in (postage + paper + Lob fee + return-address rental), 10-30 day round-trip latency, distressed-homeowner physical mail conversion is not meaningfully higher than email-7-touch on Cleveland LTV math.
- **If a deal demands mail (e.g., elderly-no-email seller flagged by Justine):** Marquise hand-mails one letter from the user_action_assets template, logs the send to `OutreachSequence`, and skips Lob entirely.

## Progressive Disclosure

Every seller starts in "cold email only" mode. As they engage, more channels unlock.

| Seller State | Email | SMS in | SMS out | Call in | Call out | Mail |
|---|---|---|---|---|---|---|
| Cold (scouted, no contact) | YES | YES | NO | YES | **NO** (cold) | YES |
| Warm (replied to email) | YES | YES | YES | YES | YES (call hours) | YES |
| Engaged (said yes to offer) | YES | YES | YES | YES | YES (call hours) | YES |
| Under contract | YES | YES | YES | YES | YES | YES |
| Opted out (STOP / UNSUBSCRIBE) | NO | NO | NO | NO | NO | NO |

Transition triggers (captured in `leads_db.json`):
- **cold -> warm:** seller sends any reply (email, text, call)
- **warm -> engaged:** seller verbally accepts the offer
- **any -> opted_out:** seller replies STOP, UNSUBSCRIBE, REMOVE, or requests no contact

## Why This Is The Smart Play

1. **One-channel-one-registration rule.** Email is the only channel that works in all 7 states today without paperwork. SMS needs TX SoS + $10K bond, FL needs manual-only discipline, TN needs $500/yr registration. We skip all that.
2. **Conversion math.** Most pre-foreclosure sellers check their email every day because it is the least-invasive channel. Those who reply have already self-selected as motivated. SMS is noisier, costlier legally, lower conversion in this segment.
3. **Scalability.** Email fires from the Resend API at tens of thousands per day with ~$0.0004 per send. No per-state registration bottleneck.
4. **Reputation.** One seller complaining to the FTC about an unsolicited text does far more damage than a quiet unsubscribe from an email list.

## Resource Allocation

Given `effortless + fast + non-annoying + legal`:

- **90%** of outbound budget -> email (7-touch sequence, stagger days 1/3/7/14/21/30/45)
- **0%** -> cold outbound SMS
- **0%** -> direct mail (DEPRECATED 2026-04-26, digital-only operation)
- **10%** -> manual call (Harrison) on warm responders within legal hours

As inbound replies accumulate, re-allocate: every inbound reply earns a live call slot.

## Enforcement

`hive_outreach.py` (SMS), `rex_closer.py` (call), and future `rex_dialer.py` MUST:
1. Call `compliance.state_gate.check(state, channel, action)`
2. If `channel == "call"`, also call `check_call_hour(state)` and `is_bot_call_allowed(state)`
3. Refuse to send if any gate returns `ok=False`
4. Log every refused attempt to the daily compliance report Justine reviews

## Review Cadence

Justine Park reviews this doc on the 1st of each month. If any state passes new legislation or a registration opens up a new channel, update here + `state_gates.json` + post to `#compliance`.
