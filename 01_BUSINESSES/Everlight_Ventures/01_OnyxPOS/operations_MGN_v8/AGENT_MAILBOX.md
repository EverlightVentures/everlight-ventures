# MGN POS -- Agent Mailbox (app-local handoff for the Dell)

This copy lives INSIDE the POS app folder so it is visible even with a sparse
checkout (the canonical workspace mailbox at `_state/AGENT_MAILBOX.md` is outside
the sparse path and won't materialize on a POS-only checkout). Read this first.

Branch: `mgn-pos-restore`. App: `operations_MGN_v8` (Flask: MGN_APP.py + POS_CORE.py,
port 5000, owner login Employee 1001 / PIN 8008).

---

## [2026-06-25 PT] CRITICAL FIXES: name-save, overnight data loss, back-arrow exploit, PIN mgmt

Root causes (traced in code AND independently reproduced by a 7-agent audit workflow):
1. NAME not saving on Add -> the Add form posts first_name + last_name, but the route read a
   single "name" field that never existed, so every new hire saved with a BLANK name until you
   re-edited. FIX: the route now combines first+last (compose_full_name); create_employee also
   rejects a blank name. Editing always worked -- that is why re-editing fixed it.
2. EMPLOYEES/records "gone the next day" -> the data folder was picked per-request from
   session["tenant_id"], so a single shop could WRITE to one folder and READ another the next
   launch. The records were orphaned, not deleted. FIX: SINGLE-STORE LOCK (MGN_SINGLE_STORE=1,
   default ON) pins every read/write to ONE fixed folder, every request, every day.
3. BACK-ARROW re-login into a logged-out admin -> no cache headers, plus the secret key was the
   public default (forgeable session cookie). FIX: global no-store headers (browser can't restore
   the cached admin page on Back), session hardening (HttpOnly + SameSite=Lax + 12h expiry), and a
   per-install RANDOM secret key persisted to .secret_key (never the public default).
4. PIN management -> detail page hardcoded **** and only offered a RANDOM reset. FIX: Owner/Admin
   can VIEW a PIN (click Show) and SET a SPECIFIC 4-digit PIN (audited + employee notified). Gated
   owner/admin only -- managers excluded (new owner_required decorator).

Tests: tools/test_employee_fixes.py (6) green; MGN_APP.py + POS_CORE.py compile; templates valid.

### APPLY ON THE DELL
git fetch origin && git checkout mgn-pos-restore && git reset --hard origin/mgn-pos-restore
Restart the app. (Optional .env: SECRET_KEY=<random> -- else auto-generated to .secret_key.
MGN_SINGLE_STORE=1 is already the default.) Verify: add an employee with First+Last -> name shows
in the list; log in as owner, log out, press Back -> you get bounced to login; open an employee
-> Show PIN + Set PIN appear (owner only).

### SHIPPED 2026-06-25 (commit after the fixes above): PER-CATEGORY SALES TAX
Tax is now computed PER LINE: food-producing plants are EXEMPT (CA Reg 1588 / R&TC 6359),
ornamentals + pots + soil + tools are TAXABLE, so a tomato and a mousetrap in one cart are handled
correctly. The rate is location-set, never hardcoded (env MGN_TAX_RATE > Settings/Config.csv >
8.25% fallback; the Receipt/Tax settings page now drives it). 5 tax tests + 7 money-path tests green.
HOW TO USE: open an item -> Edit -> "Taxable" dropdown -> "Exempt - food-producing plant" for
veggies/fruit/herbs/berries; leave ornamentals + hardgoods "Taxable". New plant SKUs default to
"Needs review". Bulk helper: tools/backfill_item_tax.py (dry-run; --apply after a backup) classifies
by keywords -- but the current 989 items lost their real names in an earlier import, so it can only
match 1 today; re-run it after importing a named catalog, or classify the key sellers by hand.

### SHIPPED 2026-06-25: EOD = 3 COPIES (local PC + you + mom)
At till close the report is saved on the PC (Daily_Reports/<date>/: sales log + summary + closeout)
AND emailed to everyone set in Settings -> "End-of-Day Report Emails" (comma list, e.g. you + mom).
A _EOD_DELIVERY.txt is written each close noting whether the email sent, so the local copy is a
provable fallback. SMTP must be set in .env (SMTP_HOST/PORT/USER/PASS) for emails to actually leave;
local copies save regardless. Set recipients in Settings (or env MGN_EOD_EMAIL).

### SHIPPED 2026-06-25: CUSTOMER CAPTURE at checkout (profile + history + newsletter + receipt)
The sales screen now has optional Customer name + Email + "Email receipt" + "Add to newsletter".
On complete: the customer is saved to Customers.csv (deduped by email), the purchase is logged to
customer_receipts.csv (their purchase history), the email can be added to Newsletter_Subscribers.csv,
and a PDF receipt is emailed (best-effort; needs SMTP in .env). Also fixed: the receipt-email helpers
were never imported (the old /sales/receipt/<id>/email route was dead) -- now wired. Also fixed a
relative-path bug in upsert_customer (was writing to a CWD-relative folder). 21 tests green.

### SHIPPED 2026-06-25: CUSTOMER VIEWS (list + history + newsletter export)
/customers lists every customer with visit count + total spent; click one for their full purchase
history (so you can see what they bought and tailor offers). /newsletter lists subscribers with a
"Download CSV" button -- that is your mailing list for your own newsletters/offers. All manager-gated.

### SHIPPED 2026-06-25: OWNER/ADMIN TASK SCHEDULER (managers excluded)
/admin/schedule (owner/admin only): create recurring tasks with day-rules (1,15 = 1st & 15th;
31 = month end; DAILY; WEEKLY), assign to any owner/admin, see a 14-day "coming up" preview, and
pause schedules. Due tasks auto-assign + notify the assignee (the admin badge lights up) -- fired
idempotently at each till close, or "Run due tasks now". Note: semi-monthly (1,15) covers payroll
cadence; true nth-weekday (e.g. 2nd & 4th Friday) is day-of-month for now. 5 tests green (60 total).

### ALL FIVE ROADMAP FEATURES SHIPPED + nav links wired. Live verification on the Dell pending
(Flask can't run on the phone).

### SHIPPED 2026-06-25: INTEGRATIONS Import/Export (Menu -> Import / Export)
Wired the existing (CLI-only) inventory_transfer converter to the UI: EXPORT your catalog as a
Square / Shopify / QuickBooks / MGN CSV (download), and IMPORT a CSV from any of them (auto-detects
the format, shows a preview, then upserts by SKU with an Items.csv backup; optional "receive as
stock" creates FIFO lots). Free, no credentials. tools/test_integrations.py (3); 63 tests total.
ALSO SHIPPED 2026-06-25: ACCOUNTING EXPORT (Import/Export page -> "Accounting export"): pick a date
range -> download a daily sales summary CSV (sales, tax, COGS, cash/card) OR a QuickBooks
double-entry journal CSV (Undeposited Funds / Sales Income / Sales Tax Payable / COGS) that balances.
tools/accounting_export.py + test (2). This is the original "export to third-party accounting
software" ask, no keys needed.
LIVE API ADAPTER CHASSIS BUILT 2026-06-25 (tools/integrations_api.py, gated + inactive): operator
chose "CSV-only for now, but we'll need all 3 (QuickBooks Online, Square, Shopify) later." The adapter
layer is in place -- each platform reads its keys from .env (NEVER git/CSV), is_configured() + status()
drive a "Live sync" panel on the Import/Export page (Connected / Not connected + which env vars to set);
push_catalog/push_sale degrade gracefully until keys exist (branded_sms pattern). The real HTTP calls
are marked TODO(live) -- wired the day real keys + a live account exist to test. test_integrations_api
(4). TO ACTIVATE LATER: set QBO_* / SQUARE_ACCESS_TOKEN / SHOPIFY_* in .env, then implement the marked
API call. CSV import/export + accounting export cover transfer TODAY with no keys.
- VENDOR INVOICE INGEST + MASTER-SKU + FIFO -- SHIPPED 2026-06-25. /inventory/vendor-invoice:
  upload or paste a vendor invoice CSV; each vendor's product number maps to YOUR master item
  (Vendor_SKU_Map) and is received as a FIFO lot (carrying vendor + invoice), so consume_from_lots
  depletes oldest-first and you know exactly when a vendor's batch sold out. Unmatched lines get a
  one-click "Map & Receive" (remembered for next time). Tolerant CSV (Square/Shopify/QuickBooks/
  vendor exports). 3 vendor tests + 55 total green.

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

## [2026-06-22 PT] Payroll + bookkeeping research -> PAYROLL_AND_MONEY_OS_PLAN.md
Deep-research (8 agents) answered: how to do legally-compliant CA payroll + bookkeeping in/around this POS without QuickBooks friction. KEY CORRECTION (verified vs primary sources): free/OSS can't AUTOMATE file+remit+ACH, but a CA employer paying its OWN staff is NOT money transmission -> doing it free + manual (EFTPS + EDD e-Services + SSA BSO + own-bank ACH) is fully LEGAL. The real choice = labor + liability, not legality. DEFAULT rec: Gusto (~$109/mo, files CA+fed + direct deposit) fed by the hours CSV the POS already exports + Xero (~$20/mo, native Gusto journal sync) for books; keep the POS time clock as source of truth. Cheapest compliant: Patriot (~$87) + Wave (free books). Non-negotiable first: workers' comp + EIN + EDD account. Embedded APIs (Zeal/Check) only matter if we later RESELL payroll as a POS feature. Full report + the "Money OS" engine spec (P&L, payroll-readiness w/ catch-up, envelopes w/ sales-tax sweep, bills+autopilot w/ approval gates, provider adapter, Plaid cash-on-hand) is in PAYROLL_AND_MONEY_OS_PLAN.md. Money OS is provider-agnostic -> buildable now; provider pick is the owner's call.

## [2026-06-22 PT] Money OS built (free+manual DIY payroll path chosen) -> /money
Owner chose FREE+MANUAL DIY payroll + "build the whole engine". Built money_core.py (engine) + /money cockpit (MGN_APP.py). All @manager_required.
- Engine (tools/test_money_core.py, 10 tests; 38 total all-modules): daily/weekly P&L (revenue vs OT-correct labor vs prorated overhead -> PROFITABLE/SLOW/LOSS); payroll readiness (accrued + projected + employer-tax vs cash/envelopes -> gap; BLACK = unrun past periods = catch-up owed); envelopes + daily allocation (sweeps collected SALES TAX first -> CDTFA, then % of net to PAYROLL/PAYROLL_TAX/BILLS/RESERVE; idempotent, atomic, ledgered); bills/ordering + autopilot (OFF/SUGGEST/ARMED; ARMED only AUTO-APPROVES flagged autopay under a ceiling, never auto-PAYS; approval-gated); DIY filing_summary() -> exact EFTPS (941) + CA DE88 deposit figures to key into free gov portals.
- Cockpit: GET /money (P&L card, payday gap, envelope bars, bills, cash entry, autopilot toggle) + /api/money/pnl + /api/money/payroll-readiness + POST cash/allocate/bills(add,approve,pay)/autopilot + GET /money/filing?period_id=.
- Data: new Money_OS/ dir (Overhead, Bills, Envelopes, Envelope_Ledger, Allocation_Rules, PnL_Daily, Cash_Snapshots, Payroll_Funding, Money_Settings). Cash-on-hand = manual entry now; Plaid later.
- VERIFY LIVE ON DELL: open /money, set cash, add an overhead bill, run a pay period then hit /money/filing. PHASE 0 before first real payroll: workers' comp + EIN + EDD account (Labor Code 3700). Full plan: PAYROLL_AND_MONEY_OS_PLAN.md. Owner-dashboard nav tile to /money = small TODO.
