# BEC Wire-Fraud Protocol

**Plan reference:** v3 Move H + Dispatch #9.
**Owners:** Shield (financial safeguard), Penny Vance (Wholesale Vertical CEO), Hammer Ortiz (closer).
**Why:** BEC (Business Email Compromise) is the **#1 real-estate crime vector** per FBI IC3. Average loss: **$185,000 per incident.** Atlanta + DFW are top hit metros. We have zero margin to absorb a fraud loss in our broke-state operating window. This protocol is non-negotiable for every Deal 1 onwards.

---

## The three threats this protocol stops

### Threat A: Wire instruction interception via spoofed email

**Mechanism:** Buyer's inbox or title firm's inbox is compromised (often weeks before the deal). Attacker monitors the conversation. 24-48 hours before scheduled wire, attacker sends "updated wire instructions" from a lookalike domain (`firm.com` -> `f1rm.com`, `firm-co.com`). Buyer wires to attacker's mule account.

### Threat B: Title firm impersonation

**Mechanism:** Attacker sends fake "title coordinator" email to buyer with attacker's routing number. Real title firm only learns when the wire never lands.

### Threat C: Last-minute change-the-instructions call

**Mechanism:** Attacker calls buyer pretending to be Penny or Hammer with "the firm just changed banks, send to this account instead." Verbal pressure. No paper trail.

---

## The protocol -- runs on EVERY closing

### 48 hours before wire (DBA-name preflight)

1. Penny pulls the most recent business checking statement.
2. Confirms account holder name reads **EXACTLY** "Richard Gee d/b/a Everlight Ventures."
3. Sends to title firm: voided check + W-9 with that exact name.
4. Title firm confirms the name on their wiring instructions matches.
5. **If any name mismatch is detected, the wire is HELD until corrected.** Bank rejection of a name-mismatched wire returns the funds 3-5 days later -- deal-week cash flow dies.

### 24 hours before wire (instruction lockdown)

6. **Zero changes accepted within 24 hours of scheduled wire.** Any "updated instructions" email or call within this window automatically requires full re-verification, even if it looks legitimate.
7. Wiring instructions are delivered IN PERSON or via password-protected PDF. **Never plain email.** The password is shared via SMS to a phone number Penny independently sourced (NOT from any email).

### Day of wire (out-of-band confirmation)

8. **Buyer call-back verification.** Buyer calls the title firm using a phone number Penny pulled from the title firm's website (NOT a number in any email).
9. Buyer reads back the **last 4 digits of the routing number** to a named human at the title firm.
10. Title firm rep confirms the last 4. Provides their name.
11. Buyer logs: timestamp + named title-firm rep + last-4 confirmed. Logged in Deal record.
12. **No call, no wire.** This single control kills 90% of BEC per FBI guidance.

### After wire is sent

13. Title firm confirms wire receipt within 4 hours via separate channel (call, not email).
14. If wire receipt not confirmed in 4 hours, immediate escalation to bank fraud line + FBI IC3 filing.
15. Penny + Hammer + Shield receive Slack alert in #ft-profit-engine and #compliance.

---

## What Penny and Hammer NEVER do

- **Touch funds.** Buyer wires direct to title firm escrow. Lucrex DBA bank account only ever receives the disbursement, never the original EMD.
- **Accept "verbal" instruction changes.** Even if the seller, buyer, or title rep "really sounds like Brittany." Written paper trail with named rep + timestamp + last-4 readback is the only legitimate change channel.
- **Respond to wire-instruction emails on autopilot.** Every wire email -- without exception -- triggers the out-of-band call-back verification.
- **Use mobile data on closing day.** Phone calls happen on a known network (home wifi or cellular with no public-wifi exposure). Avoids man-in-the-middle on coffee-shop wifi.

---

## Phishing-resistant email hygiene (Lucrex inbox)

To make our outbound less spoofable:

1. **SPF / DKIM / DMARC** on `everlightventures.io` set to `p=reject` (strict). Already configured per branded_mailer doctrine. Confirm with `dig +short TXT _dmarc.everlightventures.io`.
2. **Display-name discipline** -- never show a free-form display name in outbound emails on closing days. Use `Penny Vance <penny@everlightventures.io>` exactly. Attackers exploit display-name spoof against trained-eye buyers.
3. **No alias forwarding to personal email** -- our @everlightventures.io addresses route through ImprovMX. Confirm forwarding chain doesn't leak into a personal Gmail (which is the most-compromised inbox class). If chain ends in personal Gmail, switch to direct.
4. **Calendar invite from finalize-step contains** the wire instructions PDF AS AN ATTACHMENT (password-protected), not as a link. Links can be hijacked at the redirect layer.

---

## What buyers should be told (cut-and-paste)

When introducing the closing process to a buyer, send this verbatim:

> Hi, before we get to closing, I want to set the wire-fraud-prevention rules our firm follows because BEC is the #1 RE crime per FBI IC3 and the average loss is $185k. Three rules:
>
> 1. We will send you wiring instructions only via password-protected PDF. The password comes by SMS to the phone number on this email signature, never as a separate email.
>
> 2. **No changes to wiring instructions accepted within 24 hours of wire.** If you receive any email or call claiming "updated wire instructions" within that window, please call me directly to verify -- and if I'm telling you to update, that's also a flag. Real changes get fully re-verified, not last-minute swapped.
>
> 3. Day of wire: please call the title firm at the number on **their website** (not from any email) and read back the **last 4 digits of the routing number** to a named rep at the firm. Get their name. Note the time. Then send.
>
> If anything in the closing process feels rushed or off, please pause and call me. We have time to verify. We do not have time to recover a stolen wire.

---

## Audit + post-deal review

Each closing logs to `_logs/wholesale/wire_audit/{deal_id}.json`:

```json
{
  "deal_id": "deal-atl-001",
  "wire_amount": 5000,
  "title_firm": "Campbell & Brannon",
  "title_rep_named": "Brittany Hayes",
  "last_4_routing_confirmed": "8421",
  "buyer_callback_timestamp_pt": "2026-05-08T14:23:11-07:00",
  "callback_phone_source": "campbellbrannon.com/contact",
  "instruction_pdf_password_sent_via": "sms-to-buyer-+14045551212",
  "wire_sent_timestamp_pt": "2026-05-08T14:31:44-07:00",
  "wire_received_confirmed_timestamp_pt": "2026-05-08T15:47:09-07:00",
  "anomaly_flags": []
}
```

After Deal 1 wires safely, Shield reviews the audit and opens a `WIRE_PROTOCOL_LESSONS.md` -- adds whatever almost-tripped-us-up to the protocol for Deal 2 onwards. The protocol gets sharper with every closing, not weaker.
