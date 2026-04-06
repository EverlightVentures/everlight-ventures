-- Customer Onboarding Pipeline
-- Syncs customers + subscriptions from Django payments to Supabase
-- for public site reads + self-service portal

-- Customers table (source of truth: Django, synced here)
CREATE TABLE IF NOT EXISTS customers (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    django_id INTEGER UNIQUE,
    stripe_customer_id TEXT UNIQUE,
    email TEXT NOT NULL,
    name TEXT,
    company TEXT,
    product TEXT,  -- onyx_pos, hive_mind, alley_kingz, ai_consulting, etc.
    plan_tier TEXT DEFAULT 'free',  -- free, starter, pro, enterprise
    status TEXT DEFAULT 'active',  -- active, churned, paused, trial
    onboarded_at TIMESTAMPTZ,
    slack_workspace_id TEXT,
    slack_bot_token TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Subscriptions (synced from Stripe via Django)
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    stripe_subscription_id TEXT UNIQUE,
    product TEXT NOT NULL,
    plan_tier TEXT NOT NULL,
    status TEXT DEFAULT 'active',  -- active, past_due, canceled, trialing
    mrr_cents INTEGER DEFAULT 0,
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Onboarding steps (tracks where each customer is in setup)
CREATE TABLE IF NOT EXISTS onboarding_steps (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    step TEXT NOT NULL,  -- welcome_email, slack_setup, api_keys, first_session, training_call
    status TEXT DEFAULT 'pending',  -- pending, in_progress, completed, skipped
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Unique constraint: one step per customer
CREATE UNIQUE INDEX IF NOT EXISTS idx_onboarding_customer_step
    ON onboarding_steps(customer_id, step);

-- RLS policies
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE onboarding_steps ENABLE ROW LEVEL SECURITY;

-- Service role can do everything (Django sync)
CREATE POLICY customers_service ON customers FOR ALL
    USING (true) WITH CHECK (true);
CREATE POLICY subscriptions_service ON subscriptions FOR ALL
    USING (true) WITH CHECK (true);
CREATE POLICY onboarding_service ON onboarding_steps FOR ALL
    USING (true) WITH CHECK (true);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_stripe ON customers(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_customers_product ON customers(product);
CREATE INDEX IF NOT EXISTS idx_subscriptions_customer ON subscriptions(customer_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
