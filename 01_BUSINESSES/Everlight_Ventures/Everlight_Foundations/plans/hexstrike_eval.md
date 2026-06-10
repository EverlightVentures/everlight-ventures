# HexStrike - Defensive-Only Evaluation

**Owner**: Cipher (lead) + Justine (legal gate). NO delegation.
**Source**: `05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/05_OSINT_and_Security/is_hexstrike_the_best_ai_mcp_for_security.txt`
**Date**: 2026-04-21

---

## HARD RULE

HexStrike is a security-testing agent. Everlight uses it ONLY against:
1. Our own production infrastructure (Oracle, Cloudflare, Supabase)
2. Localhost / sandbox targets that Cipher owns
3. Client targets with explicit written authorization (future, if we pen-test as a service)

HexStrike is NEVER pointed at third parties without written authorization. Justine enforces this. Violation is cause for immediate termination of the tool in our stack.

## Evaluation plan

Timeline: 2-day sandbox evaluation by Cipher. No production deploy.

1. Spin up a disposable VM (Hostinger or Oracle throwaway instance).
2. Install HexStrike per the repo README.
3. Configure with our OpenRouter key for LLM inference.
4. Point at a dummy target also hosted on the same VM (e.g., a vulnerable-by-design DVWA container).
5. Observe what HexStrike can find.
6. Measure:
   - Tool quality (does it find real vulns?)
   - Risk profile (does it generate noise / attempted pivots?)
   - Legal clarity (does it self-limit to the authorized scope?)

## Outputs

- `01_BUSINESSES/Everlight_Ventures/Intel/hexstrike_findings.md` - summary of what it found on DVWA target
- `01_BUSINESSES/Everlight_Ventures/Intel/hexstrike_risk_profile.md` - Justine's review of legal + operational risk

## Decision gate

After 2 days:
- If findings quality high AND risk profile manageable: approve for internal-audit use only (audit our own Oracle/Cloudflare/Supabase).
- If findings mediocre OR risk profile concerning: shelf. Reason logged.

## What NOT to do

- Do NOT connect HexStrike to production Everlight infra during the trial.
- Do NOT expose HexStrike's web UI publicly.
- Do NOT leave the trial VM running after the 2-day window.
- Do NOT add HexStrike to any client-facing deliverable without Justine's pre-approval.

## Status

Not started. Deferred until Cipher has a 2-day sandbox window. Not blocking revenue work.

## Resume

`start hexstrike eval` to kick off when Cipher has bandwidth + a disposable VM.
