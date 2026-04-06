# LOVABLE PROMPT: Auth Routing & Navigation Fix

This is a TARGETED fix. Do NOT rebuild anything -- just fix these specific issues on the existing site.

**Supabase API:** `POST https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/blackjack-api`
**Headers:** `Content-Type: application/json`, `apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww`
**Authorization header:** `Bearer [same anon key above]`

---

## PROMPT:

Fix these 4 specific bugs on the Everlight Arcade. Do NOT change any styling, layout, or features -- only fix the issues described below.

---

## FIX 1: Google/Facebook OAuth Login (Broken -- Loops Forever)

**Bug:** Player clicks Google login, authorizes successfully, but the game doesn't load their profile. They get stuck in a "Setting up profile" loop or blank screen.

**Root cause:** After OAuth, the frontend calls the `register` action which requires `date_of_birth`. Google doesn't provide DOB, so it returns an error and loops.

**Fix:** Use the NEW `oauth-login` action instead. This action was just deployed and handles login-or-register without needing DOB.

After Supabase Auth confirms the OAuth session, call:

```typescript
const bridgeOAuthToPlayer = async (authUser: any) => {
  const res = await fetch('https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/blackjack-api', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww',
      'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww',
    },
    body: JSON.stringify({
      action: 'oauth-login',
      email: authUser.email,
      display_name: authUser.user_metadata?.full_name || authUser.email?.split('@')[0] || 'Player',
      avatar_url: authUser.user_metadata?.avatar_url || null,
      provider: authUser.app_metadata?.provider || 'google',
    }),
  });
  const data = await res.json();
  if (data.success && data.player) {
    return data.player; // Full player profile ready to use
  }
  throw new Error(data.error || 'Failed to bridge OAuth to player account');
};
```

Wire this into the auth flow:
- In `onAuthStateChange` and `getSession` callbacks, when a session is detected and the provider is `google` or `facebook`, call `bridgeOAuthToPlayer(session.user)` instead of calling `register` or `login`.
- On success: set the player profile in state and localStorage.
- On error: show "Couldn't load your profile. Tap to retry." with a retry button (max 2 retries, then show "Use email login instead" as fallback). NEVER loop.

Remove any "Coming Soon" gates on Google/Facebook login buttons.

---

## FIX 2: Auth Loses Player Intent (Redirects to Wrong Page)

**Bug:** Player is on the Blackjack page, clicks "Play", gets prompted to log in, logs in with Google, and lands on the Rewards page instead of back at the Blackjack table.

**Fix:** Store the player's intended destination BEFORE triggering OAuth, then redirect there AFTER auth completes.

```typescript
// BEFORE triggering any OAuth flow:
const triggerOAuth = (provider: 'google' | 'facebook', returnTo?: string) => {
  // Save where the player wants to go
  localStorage.setItem('auth_return_to', returnTo || window.location.pathname);
  supabase.auth.signInWithOAuth({
    provider,
    options: { redirectTo: window.location.origin + '/arcade' },
  });
};

// AFTER auth completes (in the auth state handler):
const onAuthSuccess = (player: any) => {
  setPlayerProfile(player);
  localStorage.setItem('player_profile', JSON.stringify(player));

  const returnTo = localStorage.getItem('auth_return_to');
  localStorage.removeItem('auth_return_to');
  navigate(returnTo || '/arcade'); // Go where they wanted, default to arcade hub
};
```

Every "Play" button and "Login with Google/Facebook" button must call `triggerOAuth` with the current page path. After auth, ALWAYS redirect to the stored path. Default to `/arcade` (the game hub), NEVER to `/arcade/rewards`.

---

## FIX 3: Session Persistence (Refresh Wipes Login)

**Bug:** Player refreshes the page and their login state is gone. They have to log in again.

**Fix:**

On successful login/bridge:
```typescript
localStorage.setItem('player_profile', JSON.stringify(player));
```

On app mount (before any auth check):
```typescript
const cached = localStorage.getItem('player_profile');
if (cached) {
  setPlayerProfile(JSON.parse(cached)); // Show cached profile immediately
}
// Then validate in background:
const { data: { session } } = await supabase.auth.getSession();
if (!session) {
  localStorage.removeItem('player_profile');
  setPlayerProfile(null); // Session expired, clear cache
}
```

This gives instant load on refresh while still validating the session.

---

## FIX 4: Error States (No More Loops or Dead Ends)

Replace all current error handling in the auth/profile flow with clear, actionable messages:

| When | Show |
|------|------|
| Profile bridge fails | "Couldn't load your profile. Tap to retry." + [Retry] button |
| After 2 failed retries | "Still having trouble. Try email login instead." + [Use Email] button |
| OAuth returns error | "Login didn't complete. Try again or use email." + [Try Again] + [Use Email] |
| Network timeout (5s) | "Connection is slow. Check your signal and retry." + [Retry] |
| Account email conflict | "This email is already linked to another account." + [Use Email] + [Contact Support] |

Rules:
- NEVER show an infinite spinner. Max 5 seconds, then show error with action.
- NEVER loop (retry automatically without user action). Always require a button tap to retry.
- NEVER block the entire UI on error. The player should still be able to navigate (back arrow, arcade hub, etc.) even if auth fails.
- Max 2 automatic retries, then stop and show fallback options.

---

## FIX 5: Back Arrows on All Arcade Pages

**Bug:** Navigating between arcade pages is tedious. No way to go back without using browser back button, which sometimes exits the app.

**Fix:** Add a back arrow (chevron-left icon, 24px) in the top-left of EVERY arcade sub-page, positioned left of the page title.

- Touch target: 44x44px minimum
- Color: #8A8A8A, brightens to #E5E5E5 on tap
- Navigates to the LOGICAL parent (not browser history):
  - `/arcade/blackjack` → `/arcade`
  - `/arcade/blackjack/table/:id` → `/arcade/blackjack`
  - `/arcade/alley-kingz` → `/arcade`
  - `/arcade/lounge` → `/arcade`
  - `/arcade/membership` → `/arcade`
  - `/arcade/rewards` → `/arcade`
  - `/arcade/profile` → `/arcade`
- `/arcade` itself (the hub) does NOT get a back arrow -- it's the root
- On mobile: back arrow + page title form a sticky top bar (48px height)
