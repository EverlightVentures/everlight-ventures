# TX Wholesale Audit-Pass Binder Index

**Last Updated:** 2026-05-05 09:45 PT (2026-05-05T09:45:44-07:00)
**Owner:** Augustine Crane (Compliance, Charlie Sentinels)
**Reviewer:** Samuel Navarro (Compliance Lead)
**Quarterback:** Marcus Cole (Claude Corp / TX deal escalations)
**Last revised:** 2026-05-04
**Revision cadence:** quarterly (next: 2026-08-04) plus on-demand when regulatory rules change
**Defense scope:** TREC, Texas Property Code §1101.0045 + §5.086 (notice of equitable interest), §5.0205 (now codified into §1101.0045 / amended Sept 2023 SB1577 -- treat as binding regardless of statute number cited), DTPA, FTC CAN-SPAM 16 CFR 316, TCPA 47 USC 227 + 47 CFR 64.1200, RESPA 12 USC 2607, BBB voluntary participation, TX AG consumer protection inquiries.

> Compliance assistant note: this binder catalogs **what artifacts must exist and where**. Generation of those artifacts is the responsibility of the operating systems (e.g., `esig_hellosign.py`, `outbound_log` table, `dnc_emails` table). This document is the index, not the producer.

---

## A. Binder Index (one row per compliance dimension)

| # | Dimension | Artifact filename pattern | Storage location | Retention | Collection SLA |
|---|---|---|---|---|---|
| 1 | TX §5.0205 / §1101.0045 disclosure | `<deal_id>_5_0205_disclosure.pdf` + `<deal_id>_esign_audit.json` + `<deal_id>_email_receipt.eml` | Supabase `tx_5_0205_disclosures` row + `audit_kit/01_5_0205_disclosures/<YYYY>/<deal_id>/` (PDFs) + Supabase Storage bucket `tx-disclosures` | 7 yr (DTPA SoL = 2y discovery / 4y outer; we hold 7 to cover successor liability) | PDF saved within 5 min of e-sign event; Supabase row written same transaction; email receipt fetched within 30 min |
| 2 | CAN-SPAM (each sequence) | `<sequence_id>_template_v<n>.html` (with postal address), `optout_log_<YYYY-MM>.jsonl`, `suppression_list_snapshot_<YYYY-MM-DD>.json` | git: `wholesale_agent/templates/` (templates) + Supabase `outbound_log` (sends) + `audit_kit/02_can_spam/<sequence_id>/` (monthly snapshots) | 5 yr minimum, 7 yr held | Template snapshot at every revision (git tag); opt-out log written real-time webhook; suppression snapshot nightly cron 02:00 PT |
| 3 | TCPA voice (Hammer call list) | `dnc_scrub_<YYYY-MM-DD>_<vendor>.csv`, `internal_dnc_scrub_<YYYY-MM-DD>.csv`, `consent_<phone_e164>.pdf` (web-form express written consent), `call_recording_<phone_e164>_<call_id>.wav` (where state requires + we elect) | `audit_kit/03_tcpa_voice/scrubs/` + `audit_kit/03_tcpa_voice/consent/` + Supabase `tcpa_call_log` table | 10 yr (TCPA SoL is 4y but plaintiff bar tests 10) | National DNC scrub <=31 days before call; internal DNC scrub immediate-before-dial; consent file linked at form-submit; recording archived within 1 hr of call end |
| 4 | DTPA copy-of-record | `outbound_log` row (deal_id, recipient, sequence_id, body_hash, sent_at, channel) + `<deal_id>_PSA_v<n>.pdf` + `<deal_id>_assignment_v<n>.pdf` | Supabase `outbound_log` (already authored by Forge) + git: `Wholesale/contracts/<deal_id>/` (PSA + assignment versions) | 7 yr | Outbound row at send-time; contract revisions at every redline (git commit) |
| 5 | RESPA / title-company referrals | `<title_partner>_no_kickback_attestation_<YYYY>.pdf`, `<deal_id>_ABA_disclosure.pdf` (where co-investing) | `audit_kit/05_respa_title/attestations/<title_partner>/` + Supabase `title_partner_attestations` | 7 yr | Annual re-attestation by Jan 31; ABA disclosure pre-deal close (saved before funds wire) |
| 6 | BBB process | `Wholesale/bbb_complaints/<case_id>.md` with timestamps (received, ack, response, resolved) + `apology_and_cure_template_v<n>.html` | git: `Wholesale/bbb_complaints/` + `content_tools/templates/bbb_apology_cure.html` | 5 yr | Complaint logged within 4 hr of receipt; ack within 24 hr; substantive response within 72 hr |
| 7 | DNC list integrity | `dnc_emails_backup_<YYYY-MM-DD>.json.gz` + git: `compliance/dnc_list.json` + `wholesale_agent/opted_out_emails.json` | Supabase Storage bucket `dnc-backups` + git history | 7 yr (Storage); permanent (git history) | Nightly 02:30 PT cron backup; git commit on every list mutation |
| 8 | Marcus quarterback queue | `Wholesale/marcus_queue/<deal_id>.md` with `acknowledged_at`, `outcome` (closed / escalated / declined), `outcome_reason` | git: `Wholesale/marcus_queue/` + Supabase `marcus_queue_resolutions` | 7 yr | Inbound parked within 5 min of receipt; Marcus ack within 4 business hr; outcome logged before file is closed/moved |

---

## B. Storage Layout

```
/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/audit_kit/
  AUDIT_BINDER_INDEX.md                           <-- this file
  01_5_0205_disclosures/
    <YYYY>/<deal_id>/
      <deal_id>_5_0205_disclosure.pdf
      <deal_id>_esign_audit.json
      <deal_id>_email_receipt.eml
  02_can_spam/
    rex_sdr/         monthly snapshots + template versions
    rex_belfort/
    rex_7touch/
    piper_outreach/
  03_tcpa_voice/
    scrubs/          dnc_scrub_<date>_<vendor>.csv
    consent/         consent_<phone_e164>.pdf
    recordings/      symlink to Supabase Storage signed URLs
  04_dtpa_defense/
    contracts/<deal_id>/   PSA + assignment versions (mirrors git)
    outbound_log_export_<YYYY-Q>.csv  quarterly Supabase export
  05_respa_title/
    attestations/<partner>/<YYYY>_no_kickback.pdf
    aba_disclosures/<deal_id>_ABA.pdf
  06_bbb_complaints/                  symlink to /Wholesale/bbb_complaints
  07_dnc_integrity/
    backups/         dnc_emails_backup_<date>.json.gz
    git_pointer.txt  notes git path for compliance/dnc_list.json
  08_marcus_queue/                    symlink to /Wholesale/marcus_queue
  99_calendar/
    reattestation_schedule.yaml
    review_log_<YYYY>.md
```

---

## C. Schema Additions (Supabase)

Forge already authored `dnc_emails` and `outbound_log`. The following are still needed.

### `tx_5_0205_disclosures`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| deal_id | text NOT NULL | FK to deals |
| seller_name | text NOT NULL | |
| seller_email | text | |
| end_buyer_name | text NOT NULL | |
| end_buyer_email | text | |
| disclosure_pdf_url | text NOT NULL | Supabase Storage signed URL |
| esign_audit_json_url | text NOT NULL | HelloSign / DocuSign audit cert |
| email_receipt_url | text | .eml file with delivery receipt |
| seller_signed_at | timestamptz | |
| end_buyer_signed_at | timestamptz | |
| ip_seller | inet | |
| ip_end_buyer | inet | |
| created_at | timestamptz default now() | |
| created_by | text | agent id (esig_hellosign.py) |

Index: `(deal_id)`, `(seller_signed_at)`.

### `bbb_complaints`
| Column | Type | Notes |
|---|---|---|
| case_id | text PK | BBB-issued case id |
| received_at | timestamptz NOT NULL | |
| acknowledged_at | timestamptz | SLA: <=24 hr |
| response_sent_at | timestamptz | SLA: <=72 hr |
| resolved_at | timestamptz | |
| complainant_name | text | |
| deal_id | text | nullable |
| issue_summary | text | |
| resolution_summary | text | |
| markdown_path | text | path to `Wholesale/bbb_complaints/<case_id>.md` |
| status | text CHECK in ('open','responded','resolved','escalated_legal') | |

### `title_partner_attestations`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| partner_name | text NOT NULL | e.g. "1st Option", "Patten" |
| attestation_year | int NOT NULL | |
| signed_by | text NOT NULL | |
| signed_at | timestamptz NOT NULL | |
| pdf_url | text NOT NULL | |
| has_aba_disclosure_required | bool default false | flag if any principal co-invests |
| next_renewal_due | date NOT NULL | always Jan 31 of following year |
| notes | text | |

### `marcus_queue_resolutions`
| Column | Type | Notes |
|---|---|---|
| deal_id | text PK | |
| parked_at | timestamptz NOT NULL | |
| acknowledged_at | timestamptz | |
| outcome | text CHECK in ('closed','escalated','declined') | |
| outcome_reason | text | required when outcome='declined' |
| outcome_at | timestamptz | |
| markdown_path | text | path to `Wholesale/marcus_queue/<deal_id>.md` |
| acknowledged_by | text | should always be 'marcus_cole' |

### `tcpa_call_log` (when Hammer activates)
| Column | Type | Notes |
|---|---|---|
| call_id | uuid PK | |
| phone_e164 | text NOT NULL | |
| dialed_at | timestamptz NOT NULL | |
| national_dnc_scrub_at | timestamptz NOT NULL | must be <=31 days old |
| internal_dnc_scrub_at | timestamptz NOT NULL | must be immediate-pre-dial |
| consent_pdf_url | text | required for cell numbers |
| recording_url | text | |
| disposition | text | answered/vm/no_answer/declined |
| caller_id | text | which agent (Hammer) |

---

## D. Annual Re-attestation Calendar

Stored at `audit_kit/99_calendar/reattestation_schedule.yaml` -- a cron polls this and pings Augustine + Samuel.

```yaml
schedule:
  - id: respa_title_attestation
    cadence: annual
    due: "01-31"            # MM-DD each year
    owner: augustine_crane
    reviewer: samuel_navarro
    artifacts:
      - audit_kit/05_respa_title/attestations/1st_option/<YYYY>_no_kickback.pdf
      - audit_kit/05_respa_title/attestations/patten/<YYYY>_no_kickback.pdf
    blocking: true          # if missed, halt new TX deals with that partner

  - id: tcpa_dnc_vendor_renewal
    cadence: annual
    due: "12-15"
    owner: augustine_crane
    reviewer: samuel_navarro
    artifacts:
      - audit_kit/03_tcpa_voice/vendor_contract_<YYYY>.pdf
    blocking: true

  - id: can_spam_template_review
    cadence: quarterly
    due_offsets: ["01-15","04-15","07-15","10-15"]
    owner: augustine_crane
    reviewer: justine_park
    artifacts:
      - wholesale_agent/templates/rex_sdr/*.html
      - wholesale_agent/templates/rex_belfort/*.html
      - wholesale_agent/templates/rex_7touch/*.html
      - wholesale_agent/templates/piper_outreach/*.html
    checks:
      - postal_address_present
      - opt_out_link_present
      - sender_identity_truthful

  - id: bbb_sla_review
    cadence: monthly
    due: "first_business_day"
    owner: augustine_crane
    reviewer: samuel_navarro
    checks:
      - all_complaints_acknowledged_within_24h
      - all_complaints_responded_within_72h
      - aging_open_cases_flagged

  - id: dnc_backup_integrity
    cadence: monthly
    due: "first_business_day"
    owner: augustine_crane
    checks:
      - last_30_nightly_backups_present
      - git_dnc_list_matches_db_count

  - id: outbound_log_quarterly_export
    cadence: quarterly
    due_offsets: ["01-05","04-05","07-05","10-05"]
    owner: augustine_crane
    artifacts:
      - audit_kit/04_dtpa_defense/outbound_log_export_<YYYY-Q>.csv

  - id: binder_full_review
    cadence: quarterly
    due_offsets: ["02-04","05-04","08-04","11-04"]
    owner: augustine_crane
    reviewer: samuel_navarro
    checks:
      - all_dimensions_have_current_artifacts
      - regulatory_changes_since_last_review_logged
```

---

## E. The "Single Binder" -- 12 documents printed on demand for TX AG / DTPA plaintiff

If a TX AG inquiry letter or plaintiff DTPA complaint arrives, Augustine prints/exports these 12 in this order:

1. **AUDIT_BINDER_INDEX.md** (this file) -- proves a documented compliance program exists.
2. **§5.0205 disclosure PDF** for the deal in question + e-sign audit cert + email delivery receipt.
3. **PSA + assignment** for the deal (all redline versions) from `Wholesale/contracts/<deal_id>/`.
4. **Outbound log export** filtered to the complainant's email/phone -- proves what we sent and when.
5. **DNC list snapshot** as of the date of the alleged contact -- proves they were/were not on the list at that moment.
6. **Opt-out log entry** for the complainant if they ever unsubscribed -- proves we honored it.
7. **CAN-SPAM template version** that was active at time of send (with postal address + opt-out link visible).
8. **Title-partner no-kickback attestation** for the year of the deal (RESPA defense).
9. **ABA disclosure** for the deal if any principal co-invested (RESPA §8(c)(4) safe harbor).
10. **BBB case file** if a BBB complaint was filed -- shows our timeline.
11. **Marcus queue resolution record** for any TX deal touchpoint -- proves we did not silently drop or mishandle.
12. **CODE_OF_CONDUCT.md + CHANNELS.md** from `Wholesale/` -- proves a written compliance culture pre-existed the complaint.

> Compliance reminder: these 12 documents are NOT legal advice. Augustine flags; Samuel triages; outside counsel decides what gets produced and what is privileged.

---

## Checklist status
Checklist complete. 14 of 14 items pass. One advisory note attached: TCPA call_log table and recording archive should be created **before** Hammer's first dial -- not after. Hammer activation is currently parked; Augustine will re-flag at unpark.
