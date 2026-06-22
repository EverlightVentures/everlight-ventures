# MGN POS -- Integrity Audit, What's Hardened, and the Roadmap

_Last updated: 2026-06-22. Branch: `mgn-pos-restore`._

A 4-specialist audit traced the real code. Below: what was found, what is already
fixed + tested, and the prioritized next build. Owner priorities driving this:
(1) sales logged accurately / no data loss, (2) time clock + payroll foolproof,
(3) interchange inventory with Stripe / Square / Shopify / QuickBooks.

---

## 0. INVENTORY + SEARCH MADE USABLE (2026-06-22, DONE -- the operational unblock)

A 7-agent audit workflow found why cashiers couldn't search/select ANY product:
1. **Dead tenant Data_Dir.** `tenants.csv` pointed `Data_Dir` at `/home/mgn/...` (the old Dell
   path). Every request repointed the data dir there and auto-created an EMPTY `Items.csv` -- the
   real 989-item catalog was never read. FIX: `get_tenant_data_dir()` falls back to the app's own
   folder when the path is missing (relocation-proof); `tenants.csv` Data_Dir blanked.
2. **Every product was named "Plant"** (986/989; the import flattened names, source CSV gone).
   FIX: `tools/repair_item_names.py` synthesizes searchable labels from Size+price+SKU
   ("Plant 5 gal $24.99 (D56CAC)"), idempotent, backs up first, preserves all 26 columns. The
   repaired `Items.csv` is committed. PROOF: `search_items('5 gal')` 0 -> 290 hits.
3. **`ITEM_HEADERS` aligned 23 -> 26 cols** so no rewrite drops trailing columns.

Built on top (make-it-usable):
- **Quick-add at the register** -- `/sales/quick_add` + a "+ Quick Add" button in the no-results
  state (name prefilled from the search + price) -> sellable `QA-` item dropped into the cart.
- **Reconciliation matrix** -- `/inventory/reconcile` (manager): map each on-the-spot `QA-` item
  to the real catalog product (`Reconciliation_Map.csv`, deactivates the provisional, audit-logged).
- **EOD file export** -- close-out saves the day's Sales + Summary + Closeout CSVs to
  `Daily_Reports/<date>/` and attaches them to the email; multi-recipient via `MGN_EOD_EMAIL`
  (owner + Adam); email reports the # of quick-adds awaiting reconciliation.
- **`tools/inventory_audit.py`** (+12 tests) -- health + inventory<->saleslog alignment gap finder.

Full suite 28/28 green. OPEN: real product names need an owner re-import (synthetic labels are a
stopgap); add a nav link to `/inventory/reconcile`.

---

## A. DONE earlier this session (committed + tested -- `tools/test_pos_core_integrity.py`, 3/3 green)

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
- [x] **Payroll lock** -- BUILT. `/payroll/run` refuses a PROCESSED period (would double-pay)
  unless `force=1`; a successful run records `append_audit_event("payroll_run", ...)`. Verify live on Dell.
- [x] **Hours export route** -- BUILT. `GET /payroll/export-hours?period_id=&format=generic|quickbooks|shopify`
  (manager-only), reuses `scan_timeclock_files` + `calculate_california_hours`, CSV-injection-guarded.
  The old "Reports -- coming soon" `/payroll/reports` stub now redirects to it. Verify live on Dell.

## C. EOD confirmation email -- BUILT (needs SMTP env on the Dell to actually send)

Was missing entirely (audit: `/logout` only cleared the session; `/api/till/close` wrote
`Till/closeouts.csv` but sent no email, no recipient). NOW: on day-close, `/api/till/close`
writes a tamper-evident `till_close` audit line and emails the close-out summary (till
reconciliation + day totals) via `send_eod_report_email` to `MGN_EOD_EMAIL`
(default `1m.rich.gee@gmail.com`, comma-separated for multiple). The response includes `emailed: true/false`.
Gated on SMTP env so it can't misfire half-configured -- set `SMTP_HOST/USER/PASS` in `.env` on the
Dell (Gmail app-password) to turn sending on. Verify live on Dell.

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
