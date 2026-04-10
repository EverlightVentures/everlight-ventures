# Plan: Client File System -- Full A-to-Z Deal Lifecycle in Reports

## Context
User wants every deal organized as a **client file** -- from first email to closing receipt. Every document (emails, deal sheets, contracts, signing records, payment receipts) in one place per client, with consistent branded HTML formatting, Slack notifications with Canvas + HTML links, and encrypted backup for legal compliance.

## What the user described:
- Emails should look as polished as the deal sheets (Everlight gold/black branded HTML)
- Each property/client gets its OWN folder in Reports with ALL documents
- Documents include: outreach emails, deal sheet, assignment contract, title company info, buyer pitch, signed contract, closing docs, payment receipt
- Everything posts to Slack as BOTH a Canvas (viewable in Slack) AND an HTML link (to dashboard)
- Reports page organizes by "Client Files" -- click a client -> see all their docs
- Receipts stored under the client file too
- All backed up to server, encrypted for privacy (PII protection, legally required)

## Architecture

### 1. Client File Structure (Supabase + Files)

New Supabase table: `wholesale_client_files`
```
id, deal_id, client_name, property_address, state, status,
documents JSONB (array of {type, title, url, created_at, status}),
created_at, updated_at
```

Document types per client file:
- `seller_outreach` -- branded email to seller
- `deal_sheet` -- investor presentation with financials
- `assignment_contract` -- the contract with Quality Assurance clause
- `buyer_pitch` -- custom pitch to matched buyer
- `title_order` -- title company engagement
- `signed_contract` -- executed agreement
- `closing_statement` -- HUD/settlement statement
- `payment_receipt` -- assignment fee received

### 2. Branded HTML Email Templates
Upgrade Piper's emails from plain text to the same Everlight gold/black HTML format as deal sheets. Every email is a standalone HTML document stored in the client file.

### 3. Reports Page Reorganization
- Top level: "Client Files" section showing each deal as a card
- Click a client -> expandable timeline of all documents
- Filter by status: Active, Under Contract, Closed, Dead
- Each doc clickable -> branded HTML preview

### 4. Slack Integration
Each document posts to Slack with:
- A Slack Canvas (rich formatted, viewable inline in Slack)
- An HTML link to the dashboard Reports page
- Posted to #ft-hunters or #broker-pipeline

### 5. Backup + Privacy
- All client files backed up to Oracle /home/opc/client_files_backup/
- PII fields encrypted at rest in Supabase (contact info, financial details)
- Encryption via Supabase vault or application-level AES
- Retention policy: keep 7 years per RE compliance

## Files to Create/Modify
- `wholesale_engine.py` -- upgrade email generation to branded HTML
- `deal_prep_engine.py` -- add client file creation, document registration
- React `Reports.jsx` -- add Client Files view with document timeline
- API `api.py` -- add `/api/client-files` endpoints
- Supabase migration -- `wholesale_client_files` table
- Slack posting -- Canvas creation via Slack API

## Verification
1. Create a client file for 2232 Hooper St with all document types
2. View in Reports -> Client Files -> see timeline of docs
3. Check Slack for Canvas + link posts
4. Verify backup exists on Oracle
5. Verify PII is not exposed in public endpoints
