# MGN POS -- Integrity Audit, What's Hardened, and the Roadmap

_Last updated: 2026-06-22. Branch: `mgn-pos-restore`._

A 4-specialist audit traced the real code. Below: what was found, what is already
fixed + tested, and the prioritized next build. Owner priorities driving this:
(1) sales logged accurately / no data loss, (2) time clock + payroll foolproof,
(3) interchange inventory with Stripe / Square / Shopify / QuickBooks.

---

## A. DONE this session (committed + tested -- `tools/test_pos_core_integrity.py`, 3/3 green)

| Fix | File | Why it matters |
|---|---|---|
| **Fail-loud sales** | `POS_CORE.record_sale` | A failed CSV write used to report "sale complete" anyway (silent loss). Now it returns failure, saves the sale to `Sales_Logs/_FAILED_SALES.csv`, and the cashier re-rings. |
| **Atomic inventory write** | `POS_CORE.write_csv` | `Lots.csv` was rewritten by truncation -- a crash mid-write could empty it. Now writes temp -> fsync -> atomic rename; original survives any crash. |
| **Durable append + lock** | `POS_CORE.append_csv`, `consume_from_lots` | `fsync` so power-loss can't drop the last row; a single `_IO_LOCK` serializes concurrent sales so two registers can't lost-update stock. |
| **Daily-revenue math** | `MGN_APP._compute_daily_sales_metrics` | Dashboard summed the per-line `Subtotal` (whole-ticket value repeated per line) -> revenue inflated on multi-item sales. Now sums `Line_Total`. (Till/cash totals were always correct.) |
| **Portable launcher** | `START_POS.sh` | No more hardcoded `/home/mgn/...`; auto-detects the folder. |
| **Private bind + requirements.txt** | `MGN_APP.py`, new `requirements.txt` | Binds 127.0.0.1 by default; deps were undocumented (no requirements file existed). |
| **Inventory transfer tool** | `tools/inventory_transfer.py` (+ 9 tests green) | CSV auto-format MGN <-> Square / Shopify / QuickBooks, with CSV-injection protection. Round-trips all 989 live items. |
| **Tamper-evident time clock** | `POS_CORE` audit chain (+ 2 tests green) | Every punch AND every manager edit/add/delete writes a hash-chained line to `Time_Clock/_audit/chain.jsonl`; `verify_audit_chain()` detects any edited/deleted/inserted punch even if done directly on disk. (Sequence guards, server-authoritative time, and mandatory-reason edits already existed.) |

## B. Time clock + payroll "foolproof" -- tamper-evidence DONE, payroll-lock + export NEXT

Goal (owner): "make them go extra steps to safeguard us" against punch fraud / disputes.

- [x] **Tamper-evident audit journal** -- BUILT + tested. `append_audit_event` /
  `verify_audit_chain` in POS_CORE, hash-chained `Time_Clock/_audit/chain.jsonl`, wired into all
  four punch functions + edit/add/delete.
- [x] **Sequence guards + server time** -- already present in `clock_in/out/start_break/end_break`
  (reject double clock-in, clock-out without clock-in, etc.; timestamps are server-side). Verified.
- [ ] **Payroll lock:** before `/payroll/run`, check a period-lock so a PROCESSED period can't be
  silently re-run/edited; record an immutable run event via `append_audit_event("payroll_run", ...)`
  (helper already exists -- just call it from the route).
- [ ] **Hours export route** `GET /payroll/export-hours?period_id=` (manager-only) -> CSV reusing
  `scan_timeclock_files` + `calculate_california_hours`. Formats: Generic + QuickBooks (+ Shopify).
  Replaces the current "Reports -- coming soon" stub. (Lives in MGN_APP.py -- verify live on the Dell.)

## C. NEXT -- EOD / logout confirmation email (does NOT exist today)

Audit confirmed: `/logout` only clears the session; `/api/till/close` writes a running log
(`Till/closeouts.csv`) but **sends no email**, and **no recipient was ever configured**.
Plan: on day-close, send the close-out summary via the existing `smtplib` pattern
(`send_onboarding_email` is the template) to `MGN_EOD_EMAIL` (default `1m.rich.gee@gmail.com`,
comma-separated for multiple). Gated on SMTP env so it can't misfire half-configured.

## D. NEXT -- Stripe / Square / Shopify / QuickBooks integration workflow

Reuse map (full survey done). **Don't build OAuth four times** -- a prior build already has a
generic OAuth -> token-store -> catalog-sync -> webhook engine.

| Platform | Approach | Start from |
|---|---|---|
| **Stripe** | Extend existing | `MGN_APP` already has `/billing/checkout` + `/billing/stripe/webhook`; for card-sales-into-inventory use `prototype_dec2025/backend/api/stripe_connect.py` |
| **Square** | Build on borrowed chassis | copy `prototype_dec2025/backend/api/channels.py` (OAuth+sync) -> `square.py` |
| **Shopify** | Build on same chassis | same `channels.py` template; map Products -> `Items.csv`, InventoryLevels -> `Ledger.csv` |
| **QuickBooks** | Build fresh (reuse only OAuth) | seam = `invoice_importer.py` + `Invoices_Log.csv` |

**Inventory interchange is usable NOW** via `tools/inventory_transfer.py` (CSV both directions).
Live API sync (above) is the multi-session follow-on. The MGN write-seam for all four is the
empty-but-defined `Lots.csv`/`Ledger.csv` (quantity deltas) + `Vendor_Mapping.csv` (SKU translation).

> No third-party "free secure POS" engine was ever adopted -- the only newer code is Everlight's own
> `prototype_dec2025` (Flask) and `api_v2_may2026` (FastAPI/Supabase). Those are the borrow sources.
