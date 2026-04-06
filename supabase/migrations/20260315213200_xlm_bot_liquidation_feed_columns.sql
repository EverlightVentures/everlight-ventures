ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS liquidation_bias TEXT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS liquidation_events_5m INT;
ALTER TABLE xlm_bot_metrics ADD COLUMN IF NOT EXISTS liquidation_notional_5m_usd FLOAT;

ALTER TABLE xlm_bot_feature_snapshots ADD COLUMN IF NOT EXISTS liquidation_bias TEXT;
ALTER TABLE xlm_bot_feature_snapshots ADD COLUMN IF NOT EXISTS liquidation_events_5m INT;
ALTER TABLE xlm_bot_feature_snapshots ADD COLUMN IF NOT EXISTS liquidation_notional_5m_usd FLOAT;
