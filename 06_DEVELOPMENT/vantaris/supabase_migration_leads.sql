-- Unified leads table for all Everlight Ventures forms
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard/project/jdqqmsmwmbsnlnstyavl/sql
CREATE TABLE IF NOT EXISTS public.leads (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  source text NOT NULL,
  name text,
  email text NOT NULL,
  phone text,
  message text,
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);

ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can submit a lead" ON public.leads
  FOR INSERT TO anon WITH CHECK (true);

CREATE POLICY "Service role reads all" ON public.leads
  FOR SELECT TO service_role USING (true);

CREATE INDEX IF NOT EXISTS idx_leads_source ON public.leads(source);
CREATE INDEX IF NOT EXISTS idx_leads_created ON public.leads(created_at DESC);
