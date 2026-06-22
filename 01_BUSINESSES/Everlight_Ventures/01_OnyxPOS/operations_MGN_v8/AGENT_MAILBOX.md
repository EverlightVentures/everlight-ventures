# MGN POS -- Agent Mailbox (app-local handoff for the Dell)

This copy lives INSIDE the POS app folder so it is visible even with a sparse
checkout (the canonical workspace mailbox at `_state/AGENT_MAILBOX.md` is outside
the sparse path and won't materialize on a POS-only checkout). Read this first.

Branch: `mgn-pos-restore`. App: `operations_MGN_v8` (Flask: MGN_APP.py + POS_CORE.py,
port 5000, owner login Employee 1001 / PIN 8008).

---

## [2026-06-22 PT] Inventory/search FIXED + quick-add + reconciliation + EOD export

WHY cashiers couldn't search/select ANY product (root cause verified by a 7-agent audit):
1. `Tenants/tenants.csv` `default` Data_Dir pointed at the dead Dell path
   `/home/mgn/Projects/Mountain Gardens Nursery POS`. Every request repointed the data dir
   there and auto-created an EMPTY Items.csv -- the real 989-item catalog was never read.
2. 986/989 product names were the literal word "Plant" (the import flattened them; the named
   source CSV is gone, so real names are not recoverable from data).

FIXED + SHIPPED (pushed to origin/mgn-pos-restore; full test suite 28/28 green):
- `get_tenant_data_dir()` falls back to the app's own folder when the stored path is missing
  (relocation-proof); `tenants.csv` Data_Dir blanked. Backups: `*.bak-*`.
- `tools/repair_item_names.py` synthesized searchable labels from Size+price+SKU
  ("Plant 5 gal $24.99 (D56CAC)"); idempotent; backed up Items.csv first; preserved all 26
  columns. The repaired Items.csv is committed. PROOF: search_items('5 gal') 0 -> 290 hits.
- `ITEM_HEADERS` aligned 23 -> 26 cols so no rewrite drops trailing columns.
- QUICK-ADD: `/sales/quick_add` + "+ Quick Add" button in terminal.html no-results state ->
  sellable QA- item dropped into the cart.
- RECONCILIATION: `/inventory/reconcile` (manager) maps QA- items to real catalog SKUs
  (Reconciliation_Map.csv, deactivates the provisional, audit-logged).
- EOD EXPORT: close-out saves the day's Sales + Summary + Closeout CSVs to
  `Daily_Reports/<date>/` AND attaches them to the email; multi-recipient via MGN_EOD_EMAIL.
- `tools/inventory_audit.py` (+12 tests): health + inventory<->saleslog alignment finder.

## APPLY ON THE DELL
1. `git fetch origin && git checkout mgn-pos-restore && git pull`
   (pulls the repaired Items.csv, the fixed tenants.csv, all code, and this file).
2. Restart the app: `./STOP_POS.sh; ./START_POS.sh start`  (or `python MGN_APP.py`).
3. In `.env` set:
   `MGN_EOD_EMAIL=1m.rich.gee@gmail.com,<adam-email>`
   `SMTP_HOST=smtp.gmail.com` `SMTP_PORT=587` `SMTP_USER=...` `SMTP_PASS=<app-password>`
   (local Daily_Reports/ saves happen even without SMTP).
4. Verify live: open `/sales`, search "5 gal" -> products appear + clickable; try "+ Quick Add";
   ring a sale; at close-out check `Daily_Reports/<date>/` + the email; open `/inventory/reconcile`.

> Want the FULL workspace mailbox on the Dell too? Widen the checkout once:
> `git sparse-checkout add _state` then `git checkout` -- `_state/AGENT_MAILBOX.md` appears.

---

## [2026-06-22 PT] Earlier the same restore: money-path + foolproof time clock + payroll/EOD

- Sales logging hardened: `record_sale` FAILS LOUD on a failed write (saves to
  `Sales_Logs/_FAILED_SALES.csv`) instead of silent success; `write_csv` atomic; `_IO_LOCK` on
  inventory writes; daily-revenue math fixed (Line_Total not Subtotal). Tested.
- Time clock made tamper-evident: hash-chained `Time_Clock/_audit/chain.jsonl`
  (`verify_audit_chain()` detects any edited/deleted punch); sequence guards already existed.
- Payroll-run LOCK (refuses a re-run of a PROCESSED period unless force=1, audit-logged);
  hours export `GET /payroll/export-hours?format=generic|quickbooks|shopify`.
- EOD confirmation email + `tools/inventory_transfer.py` (CSV MGN <-> Square/Shopify/QuickBooks).
- Restore basics: `requirements.txt` added; `START_POS.sh` portable; binds 127.0.0.1.

## REMAINING (multi-session follow-on)
- Real product names need an owner re-import (current labels are a searchable stopgap).
- Add a visible nav link to `/inventory/reconcile`.
- Live Stripe/Square/Shopify/QuickBooks API sync (CSV interchange already works via
  `tools/inventory_transfer.py`). Reuse map in `INTEGRITY_AND_ROADMAP.md` section D.
