VANTARIS "TRACK EVERYTHING" -- ORDERED WIRING CHECKLIST
Paths are absolute. Names below are the ONE contract (migration == taxonomy == analytics.ts).

PHASE 0 -- DB FOUNDATION (do first; everything else fails silently without it)
[ ] 1. The migration already exists at
       /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/vantaris/supabase/migrations/20260602000000_track_everything_analytics.sql
       Replace its contents with the migration_sql from this deliverable (adds the contract
       comment block + verified lead_id text note; schema is otherwise identical).
[ ] 2. Apply it:  supabase db push   (or paste into the Supabase SQL editor for project jdqqmsmwmbsnlnstyavl).
[ ] 3. Verify RLS lets anon INSERT but NOT SELECT analytics_events / page_views / web_leads,
       and that high_scores + casino_leaderboard are publicly readable. If anon SELECT is
       allowed on event tables, flush() leaks data; if anon INSERT is blocked, flush() retries forever.

PHASE 1 -- CLIENT SDK
[ ] 4. Create /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/vantaris/src/lib/analytics.ts with analytics_ts.
[ ] 5. Create /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/vantaris/src/components/shared/AnalyticsProvider.tsx with provider_tsx.

PHASE 2 -- MOUNT + EDGE BEACON
[ ] 6. Edit /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/vantaris/src/components/layout/ClientLayout.tsx:
       import { AnalyticsProvider } from '../shared/AnalyticsProvider'
       Wrap children just inside <AuthProvider>:
         <AuthProvider><AnalyticsProvider> ...existing tree... </AnalyticsProvider></AuthProvider>
[ ] 7. Edit /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/vantaris/src/app/layout.tsx:
       import Script from 'next/script'; add as the LAST child of <body>, after <ClientLayout>:
         <Script id="cf-web-analytics" strategy="afterInteractive"
           src="https://static.cloudflareinsights.com/beacon.min.js"
           data-cf-beacon='{"token":"REPLACE_WITH_CF_ZONE_TOKEN"}' />
       Get the token: Cloudflare dashboard -> Web Analytics -> add everlightventures.io -> copy token.

PHASE 3 -- GAMES (fixes the biggest data loss; do the chokepoint first)
[ ] 8. Edit /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/vantaris/src/lib/casino-engine.ts persistRound():
       after the saveGameRound({...}) call, add:
         track('game_round', { game, currency: 'GC', bet, win, net: win - bet, multiplier,
           xp_earned: Math.max(1, Math.floor(bet/100)), balance_after: newBalance, is_win: win > bet,
           round_id: <returned round.id> })
       (import { track } from './analytics'). One chokepoint = all 6 games once they call persistRound.
[ ] 9. Wire crash, mines, plinko, roulette to call casino-engine.persistRound() (they import nothing today).
       This fixes BOTH the lost casino_game_rounds rows AND emits game_round in one move.
[ ] 10. Blackjack: stop relying on django-sync.syncHandResult (deferred/unreachable). Route the
        resolved hand through persistRound() so it lands in casino_game_rounds + emits game_round.
[ ] 11. On bet placed (crash/mines/plinko/dice/roulette/blackjack):
        track('game_started', { game, currency }).
[ ] 12. On mid-round cashout (crash/mines):
        track('game_cashout', { game, currency, cashout_multiplier, payout, round_id }).
[ ] 13. On a new personal/global best, call analytics.submitHighScore({ game, score, metric, period,
        playerId, displayName }) -- it writes high_scores AND emits high_score_set. Do NOT hand-roll
        a separate event name.

PHASE 4 -- LEADS (server holds the PII; client logs the event only)
[ ] 14. Edit /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/vantaris/supabase/functions/notify-lead/index.ts:
        INSERT into public.web_leads (source, name, email, phone, message, anon_id, session_id,
        user_id, page, utm_*, metadata) BEFORE firing the Resend email. The function keeps the PII.
[ ] 15. On each lead form submit success (sell, wholesale, onyx, hivemind, alley-kingz, logistics,
        consulting, list-your-tool): track('lead_captured', { source, page_path }).
        DO NOT put email/phone/name/message in props (sanitizeProps strips them anyway).
[ ] 16. find-tools search/filter: track('search', { search_term, search_scope: 'tools', results_count }).

PHASE 5 -- AUTH
[ ] 17. signUp success branch: track('sign_up', { method: 'email' }).
[ ] 18. signIn / Google success: track('login', { method }); identify(userId) is already handled by
        AnalyticsProvider's onAuthStateChange, but calling identify(userId) inline is harmless.

PHASE 6 -- COMMERCE (revenue truth is server-side)
[ ] 19. createCheckout button: track('checkout_started', { value: <cents>, currency: 'USD', product: slug }).
[ ] 20. Stripe webhook (edge fn handling checkout.session.completed) writes the REVENUE-TRUTH event
        server-side: insert analytics_events row event_name='checkout_completed' with
        { value, currency:'USD', product, transaction_id }. transaction_id is the dedupe key.
        NEVER fire checkout_completed from the client.

PHASE 7 -- WHOLESALE MIRROR
[ ] 21. Build a server-side sync: Broker_OS leads_db.json -> public.wholesale_events (service_role key).
        lead_id is the text key (e.g. lead_ad8eec735f). Emit wholesale_lead_created on new records,
        wholesale_status_changed on stage transitions. Log state for reporting; the TN-only gate stays
        in the pipeline, not here. NEVER write owner_name/address into props (firewalled in Broker_OS).

PHASE 8 -- PRIVACY + RETENTION
[ ] 22. Add the privacy-policy delta paragraph to
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/vantaris/src/app/privacy/page.tsx
        ("We do not sell or share your personal information", cookieless CF, 90-day raw retention, rights).
[ ] 23. Add a lightweight "Privacy & Cookies" notice/link in SiteFooter (no blocking consent wall needed
        while first-party + cookieless; the wall is required the moment any ad pixel is added).
[ ] 24. Schedule a Supabase cron (pg_cron or scheduled edge fn): roll up daily aggregates FIRST, then
        DELETE FROM analytics_events WHERE created_at < now() - interval '90 days'. Keep aggregates 25 months.

PHASE 9 -- VERIFY (receipts, not assurances)
[ ] 25. Load the site, click around 2-3 routes, play one dice round, submit one lead.
[ ] 26. In Supabase: confirm rows landed in sessions, analytics_events (page_view, session_start,
        game_round, lead_captured), page_views, high_scores (if a best), web_leads.
[ ] 27. Confirm NO email/phone/name/address strings appear in any analytics_events.props value.
[ ] 28. Confirm casino_leaderboard returns ranked rows and site_traffic_daily shows today's counts.
[ ] 29. Deploy: this is the Cloudflare Pages site -- merge to the deploy branch; CF Pages auto-builds.
        (Do NOT run deploy_to_oracle.sh -- that is for xlm_bot / 01_Scripts, not the website.)
