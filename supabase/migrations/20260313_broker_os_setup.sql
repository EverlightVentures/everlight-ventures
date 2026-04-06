-- Broker OS: Supabase tables for public lead/offer capture
-- Run via Supabase SQL Editor or CLI

-- Buyer leads from /find-tools
CREATE TABLE IF NOT EXISTS broker_leads (
  id            uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  name          text NOT NULL,
  email         text NOT NULL,
  company       text,
  role          text,
  company_size  text,
  categories_needed jsonb DEFAULT '[]'::jsonb,
  need_description text NOT NULL,
  budget_max    numeric(10,2) DEFAULT 0,
  intent        text DEFAULT 'warm',
  lead_source   text DEFAULT 'website_find_tools',
  synced_to_django boolean DEFAULT false,
  created_at    timestamptz DEFAULT now(),
  updated_at    timestamptz DEFAULT now()
);

-- Seller offers from /list-your-tool
CREATE TABLE IF NOT EXISTS broker_offers (
  id            uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  seller_name   text NOT NULL,
  seller_email  text NOT NULL,
  seller_url    text,
  title         text NOT NULL,
  category      text DEFAULT 'other',
  description   text NOT NULL,
  price_min     numeric(10,2) DEFAULT 0,
  price_max     numeric(10,2) DEFAULT 0,
  pricing_model text DEFAULT 'monthly',
  source        text DEFAULT 'website_list_tool',
  status        text DEFAULT 'active',
  synced_to_django boolean DEFAULT false,
  created_at    timestamptz DEFAULT now(),
  updated_at    timestamptz DEFAULT now()
);

-- Enable RLS
ALTER TABLE broker_leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE broker_offers ENABLE ROW LEVEL SECURITY;

-- Allow anonymous inserts (public forms)
CREATE POLICY "Allow anonymous insert on broker_leads"
  ON broker_leads FOR INSERT
  TO anon
  WITH CHECK (true);

CREATE POLICY "Allow anonymous insert on broker_offers"
  ON broker_offers FOR INSERT
  TO anon
  WITH CHECK (true);

-- Block anonymous reads (only service role can read)
CREATE POLICY "Service role can read broker_leads"
  ON broker_leads FOR SELECT
  TO service_role
  USING (true);

CREATE POLICY "Service role can read broker_offers"
  ON broker_offers FOR SELECT
  TO service_role
  USING (true);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER broker_leads_updated_at
  BEFORE UPDATE ON broker_leads
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER broker_offers_updated_at
  BEFORE UPDATE ON broker_offers
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
