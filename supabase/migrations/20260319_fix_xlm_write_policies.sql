-- Fix XLM bot RLS write policies
-- All xlm_bot_* tables currently only have SELECT policies,
-- causing all pushes from Oracle to fail with 42501.
-- This adds INSERT/UPDATE policies so the service_role key can write.

-- xlm_bot_metrics
do $$ begin
  create policy "Service write xlm_bot_metrics" on xlm_bot_metrics for all using (true) with check (true);
exception when duplicate_object then null;
end $$;

-- xlm_bot_timeseries
do $$ begin
  create policy "Service write xlm_bot_timeseries" on xlm_bot_timeseries for all using (true) with check (true);
exception when duplicate_object then null;
end $$;

-- xlm_bot_feature_snapshots
do $$ begin
  create policy "Service write xlm_bot_feature_snapshots" on xlm_bot_feature_snapshots for all using (true) with check (true);
exception when duplicate_object then null;
end $$;

-- xlm_bot_trade_labels
do $$ begin
  create policy "Service write xlm_bot_trade_labels" on xlm_bot_trade_labels for all using (true) with check (true);
exception when duplicate_object then null;
end $$;

-- xlm_bot_report_history
do $$ begin
  create policy "Service write xlm_bot_report_history" on xlm_bot_report_history for all using (true) with check (true);
exception when duplicate_object then null;
end $$;

-- xlm_market_intel_state
do $$ begin
  create policy "Service write xlm_market_intel_state" on xlm_market_intel_state for all using (true) with check (true);
exception when duplicate_object then null;
end $$;

-- xlm_market_intel_runs
do $$ begin
  create policy "Service write xlm_market_intel_runs" on xlm_market_intel_runs for all using (true) with check (true);
exception when duplicate_object then null;
end $$;

-- xlm_market_intel_documents
do $$ begin
  create policy "Service write xlm_market_intel_documents" on xlm_market_intel_documents for all using (true) with check (true);
exception when duplicate_object then null;
end $$;

-- xlm_market_intel_claims
do $$ begin
  create policy "Service write xlm_market_intel_claims" on xlm_market_intel_claims for all using (true) with check (true);
exception when duplicate_object then null;
end $$;
