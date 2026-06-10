-- ============================================================
-- Everlight / Vantaris -- redeem_requests (KYC / sweeps cash-out)
-- Migration: 20260602000100_redeem_requests_kyc.sql
--
-- Purpose-bound store for sweeps-coin redemption + the KYC data the
-- /redeem page currently collects and THROWS AWAY on an alert().
-- This is NOT analytics. PII lives here, behind strict RLS, and never
-- in analytics_events (per the privacy lane of the architecture).
--
-- Idempotent + additive. Safe to run repeatedly.
--
-- LEGAL NOTE: the exact required KYC fields per operating state must be
-- confirmed by counsel (Theo / the legal team). This is a sensible
-- default superset. Do NOT store raw bank/card numbers here -- payout_ref
-- holds a tokenized reference or last4 ONLY.
-- ============================================================

create extension if not exists pgcrypto;

create table if not exists public.redeem_requests (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid references auth.users(id) on delete set null,
  player_id       uuid,
  full_legal_name text not null,
  date_of_birth   date not null,
  address_line1   text not null,
  address_line2   text,
  city            text not null,
  state           text not null,
  postal_code     text not null,
  country         text not null default 'US',
  payout_method   text not null,            -- paypal | bank | check | giftcard
  payout_ref      text,                     -- tokenized ref or last4 ONLY (never full PAN/account)
  amount_sc       numeric not null check (amount_sc > 0),
  amount_usd      numeric not null check (amount_usd >= 0),
  status          text not null default 'pending'
                    check (status in ('pending','review','approved','paid','rejected')),
  reject_reason   text,
  created_at      timestamptz not null default now(),
  reviewed_at     timestamptz,
  reviewed_by     uuid
);

create index if not exists idx_redeem_user    on public.redeem_requests(user_id);
create index if not exists idx_redeem_status  on public.redeem_requests(status);
create index if not exists idx_redeem_created on public.redeem_requests(created_at desc);

alter table public.redeem_requests enable row level security;

-- Redemption requires sign-in (KYC needs a known identity). Owner submits own request.
drop policy if exists "redeem_insert_own" on public.redeem_requests;
create policy "redeem_insert_own" on public.redeem_requests
  for insert to authenticated
  with check (auth.uid() = user_id);

-- Owner may read their own requests for status tracking. NO public read, NO anon.
drop policy if exists "redeem_select_own" on public.redeem_requests;
create policy "redeem_select_own" on public.redeem_requests
  for select to authenticated
  using (auth.uid() = user_id);

-- Admin review runs via service_role (bypasses RLS). No anon policy = no anon access.
