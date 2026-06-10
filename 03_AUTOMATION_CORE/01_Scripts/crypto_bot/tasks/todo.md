# Crypto Bot - Task Management

## Claude's 7 Rules

1. First think through the problem, read the codebase for relevant files, and write a plan to tasks/todo.md
2. The plan should have a list of todo items that you can check off as you complete them
3. Before you begin working, check in with me and I will verify the plan
4. Then, begin working on the todo items, marking them as complete as you go
5. Please every step of the way just give me a high level explanation of what changes you made
6. Make every task and code change you do as simple as possible. Avoid massive or complex changes. Every change should impact as little code as possible. Everything is about simplicity.
7. Finally, add a review section to the todo.md file with a summary of the changes you made and any other relevant information

---

## Current Task: Fix 401 Auth + CFM Trading

### Todo Items

- [x] Diagnose why CFM pairs list is empty
- [x] Add fallback CFM pairs (BTC-USD, ETH-USD) when API returns 401
- [x] Test that bot selects CFM-eligible pairs only (confirmed: BTC-USD, ETH-USD)
- [x] Enable hybrid mode (CFM for BTC/ETH, spot for altcoins)
- [ ] Verify trade execution works (restart bot with `rcb`)

### Review

**Changes Made (2026-02-02):**

1. **utils/universe_manager.py** - Added fallback CFM pairs
   - When `_get_cfm_pairs()` returns empty (due to 401 on products endpoint), it now falls back to `["BTC-USD", "ETH-USD"]`
   - This ensures the bot can still trade even when the authenticated products endpoint fails

2. **config.json** - Enabled hybrid mode
   - Set `cfm_only: false` to allow altcoin trading

3. **bot.py** - Added hybrid mode fallback
   - When CFM product not found for a pair (SOL, XRP, BNB, etc.), falls back to spot trading
   - SELL signals on spot are skipped (can't short spot)
   - BUY signals on altcoins execute as spot trades
   - **Spot volume multiplier**: Spot trades now multiply amount by leverage (default 4x) to compensate for no leverage
   - Log message shows calculation: "Spot trade: X x 4x = $Y"

4. **bot.py** - Fixed CFM product ID mapping (CRITICAL FIX)
   - Discovered CFM perpetuals use different product IDs (not spot pair names)
   - Added mapping: `XRP-USD` → `XPP-20DEC30-CDE`, `SOL-USD` → `SLP-20DEC30-CDE`, etc.
   - Format: `[SYMBOL]-20DEC30-CDE` for perpetuals (expire Dec 2030)
   - Found via public API: `GET /api/v3/brokerage/market/products?product_type=FUTURE`

5. **utils/coinbase_api.py** - Added price rounding + better error logging
   - Fixed `INVALID_PRICE_PRECISION` error that was blocking trades
   - Added endpoint path to 401 error messages for debugging

**Root Cause:**
- The products endpoint returns 401 (missing "View" permission on API key)
- But CFM balance/positions endpoints work fine
- **Key discovery:** CFM perpetuals use product IDs like `XPP-20DEC30-CDE`, not `XRP-USD`
- Used public endpoint to discover all available CFM products

**Available CFM Perpetuals:**
| Spot | CFM Perpetual |
|------|---------------|
| BTC-USD | BIP-20DEC30-CDE |
| ETH-USD | ETP-20DEC30-CDE |
| XRP-USD | XPP-20DEC30-CDE |
| SOL-USD | SLP-20DEC30-CDE |
| AVAX-USD | AVP-20DEC30-CDE |
| DOGE-USD | DOP-20DEC30-CDE |

6. **utils/coinbase_api.py** - CRITICAL JWT FIX
   - JWT `uri` claim was including query params, causing 401 on all endpoints with params
   - Fixed: JWT uri now uses endpoint path only (no query params)
   - Before: `GET api.coinbase.com/api/v3/brokerage/orders?limit=1` ❌
   - After: `GET api.coinbase.com/api/v3/brokerage/orders` ✅
   - This fixes orders endpoint which was returning 401

7. **bot.py** - Spot position exit on SELL signals
   - When SELL signal comes, bot now checks for existing spot balance
   - If user has spot coins (e.g., XLM), sells them instead of opening CFM short
   - Allows managing manual spot positions with automated exits

**Root Cause of Order Failures:**
- JWT uri was built with query params, but Coinbase expects path only
- Orders endpoint was returning 401 even though key had trade permissions
- Fix: `_generate_jwt(method, endpoint)` instead of `_generate_jwt(method, path_with_params)`

**Next Steps:**
- Run `rcb` to restart bot
- Watch logs for successful order placement
- XLM spot position will be sold on SELL signals
