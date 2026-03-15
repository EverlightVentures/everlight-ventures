# LOVABLE PROMPT: Auth Fix -- OAuth Login + Session Persistence + Blank Loop Fix

Paste this into Lovable. This is a **P0 critical fix** -- Google/Facebook login currently either shows "Coming Soon" or completes OAuth but leaves the game in a blank loop. This prompt fixes the entire auth flow end-to-end.

---

## PROMPT:

Fix the Google and Facebook OAuth login flow for the blackjack game at `/arcade/blackjack`. Currently there are THREE bugs:

1. **"Coming Soon" gate**: Some login buttons may still show "Coming Soon" instead of working OAuth
2. **Blank loop after Google auth**: Google OAuth completes (user authorizes their Google account), browser redirects back to `/arcade/blackjack`, but the game never loads -- it's stuck in a blank state or infinite loading loop. The player never reaches their gaming profile or the lobby.
3. **State loss on refresh**: If a player IS logged in and refreshes the page, all state is lost -- chips, profile, everything resets.

**Root cause of the blank loop:** After Supabase OAuth redirect, the app needs to:
1. Detect the OAuth session from the URL hash/callback
2. Extract the user's email from the Supabase auth session
3. Call the blackjack API with `{ action: "oauth-login", email, display_name, avatar_url }` -- this is a NEW action that auto-finds or auto-creates a `player_accounts` row WITHOUT requiring date_of_birth (Google/Facebook don't provide DOB)
4. Load the returned player profile into state and show the lobby

**IMPORTANT:** The old bridge logic that called `register` FAILS because `register` requires `date_of_birth` which OAuth providers don't give -- it returns `400: "Missing display_name, email, or date_of_birth"`. The fix: call `login` first. If the player exists, done. If not (404), call `register` WITH a placeholder DOB so it doesn't fail. The frontend bridge handles this.
6. THEN load the lobby with the player's profile hydrated

This bridge between Supabase Auth and the blackjack-api `player_accounts` table is either missing or broken. Fix it as described below.

---

## FIX 1: OAuth Session Detection on Page Load

In the main blackjack page component (or a wrapping AuthProvider), add this logic that runs on mount -- BEFORE rendering the welcome screen or lobby:

```typescript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  'https://jdqqmsmwmbsnlnstyavl.supabase.co',
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww'
);

const BLACKJACK_API = 'https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/blackjack-api';
const API_HEADERS = {
  'Content-Type': 'application/json',
  'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww',
  'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww',
};
```

### The Auth Flow State Machine

The component should have these states:
```typescript
type AuthState =
  | 'initializing'    // Checking for existing session (show loading spinner)
  | 'unauthenticated' // No session found (show welcome/login screen)
  | 'bridging'        // OAuth session found, bridging to player_accounts (show "Setting up your profile...")
  | 'authenticated';  // Player profile loaded (show lobby)

const [authState, setAuthState] = useState<AuthState>('initializing');
const [player, setPlayer] = useState(null);
const [authError, setAuthError] = useState<string | null>(null);
```

### On Mount -- Session Detection & Bridge

```typescript
useEffect(() => {
  let cancelled = false;

  async function initAuth() {
    try {
      // Step 1: Check for existing Supabase session (handles both fresh OAuth redirect AND page refresh)
      const { data: { session }, error: sessionError } = await supabase.auth.getSession();

      if (sessionError) {
        console.error('Session error:', sessionError);
        // Don't block -- fall through to check localStorage
      }

      if (session?.user?.email) {
        // We have a Supabase auth session -- bridge to player_accounts
        if (!cancelled) setAuthState('bridging');
        const playerProfile = await bridgeToPlayerAccount(session.user);
        if (!cancelled && playerProfile) {
          setPlayer(playerProfile);
          // Also save to localStorage as backup
          localStorage.setItem('blackjack_player', JSON.stringify(playerProfile));
          localStorage.setItem('blackjack_player_id', playerProfile.player_id);
          setAuthState('authenticated');
          return;
        }
      }

      // Step 2: Check localStorage for previously saved player (fallback for non-OAuth logins)
      const savedPlayerId = localStorage.getItem('blackjack_player_id');
      const savedPlayer = localStorage.getItem('blackjack_player');
      if (savedPlayerId && savedPlayer) {
        try {
          const parsed = JSON.parse(savedPlayer);
          if (!cancelled) {
            setPlayer(parsed);
            setAuthState('authenticated');
            // Refresh from API in background to get latest data
            refreshPlayerFromAPI(parsed.player_id, parsed.email);
          }
          return;
        } catch (e) {
          // Corrupted localStorage, clear it
          localStorage.removeItem('blackjack_player');
          localStorage.removeItem('blackjack_player_id');
        }
      }

      // Step 3: No session found -- show login screen
      if (!cancelled) setAuthState('unauthenticated');

    } catch (err) {
      console.error('Auth init error:', err);
      if (!cancelled) {
        setAuthError('Failed to load your profile. Please try logging in again.');
        setAuthState('unauthenticated');
      }
    }
  }

  initAuth();

  // Also listen for auth state changes (handles OAuth redirect completing)
  const { data: { subscription } } = supabase.auth.onAuthStateChange(
    async (event, session) => {
      console.log('Auth state change:', event);
      if (event === 'SIGNED_IN' && session?.user?.email) {
        setAuthState('bridging');
        const playerProfile = await bridgeToPlayerAccount(session.user);
        if (playerProfile) {
          setPlayer(playerProfile);
          localStorage.setItem('blackjack_player', JSON.stringify(playerProfile));
          localStorage.setItem('blackjack_player_id', playerProfile.player_id);
          setAuthState('authenticated');
        }
      } else if (event === 'SIGNED_OUT') {
        setPlayer(null);
        localStorage.removeItem('blackjack_player');
        localStorage.removeItem('blackjack_player_id');
        setAuthState('unauthenticated');
      }
    }
  );

  return () => {
    cancelled = true;
    subscription.unsubscribe();
  };
}, []);
```

### The Bridge Function (CRITICAL -- this is what was missing/broken)

The old code either: (a) never called the blackjack API after OAuth, leaving the game with no player profile, or (b) called `register` without `date_of_birth`, which ALWAYS returns `400: "Missing display_name, email, or date_of_birth"` because Google/Facebook don't provide DOB.

The fix: call `login` first. If player exists, done. If 404, call `register` with a **placeholder DOB** (`1990-01-01`) so it passes validation. This works with the EXISTING edge function -- no backend changes needed.

```typescript
async function bridgeToPlayerAccount(authUser: { email: string; user_metadata?: any; id?: string }) {
  const email = authUser.email;
  if (!email) {
    console.error('No email in auth user');
    return null;
  }

  const displayName = authUser.user_metadata?.full_name
    || authUser.user_metadata?.name
    || email.split('@')[0];
  const avatarUrl = authUser.user_metadata?.avatar_url
    || authUser.user_metadata?.picture
    || null;

  try {
    // Step 1: Try login -- check if player_accounts row exists for this email
    const loginRes = await fetch(BLACKJACK_API, {
      method: 'POST',
      headers: API_HEADERS,
      body: JSON.stringify({ action: 'login', email }),
    });
    const loginData = await loginRes.json();

    if (loginData.success && loginData.player) {
      // Existing player found -- return their full profile
      console.log('Existing player found:', loginData.player.display_name);
      return loginData.player;
    }

    // Step 2: Player not found (404) -- auto-register with placeholder DOB
    // CRITICAL: date_of_birth is REQUIRED by the register action.
    // Google/Facebook OAuth does NOT provide DOB, so we use a placeholder.
    if (loginData.found === false || loginRes.status === 404) {
      console.log('No player account found, auto-registering via OAuth...');
      const registerRes = await fetch(BLACKJACK_API, {
        method: 'POST',
        headers: API_HEADERS,
        body: JSON.stringify({
          action: 'register',
          display_name: displayName,
          email: email,
          date_of_birth: '1990-01-01',  // Placeholder -- OAuth doesn't provide DOB
        }),
      });
      const registerData = await registerRes.json();

      if (registerData.success && registerData.player) {
        console.log('Auto-registered new player:', registerData.player.display_name);

        // Update avatar from Google/Facebook profile picture
        if (avatarUrl) {
          fetch(BLACKJACK_API, {
            method: 'POST',
            headers: API_HEADERS,
            body: JSON.stringify({
              action: 'update-profile',
              player_id: registerData.player.player_id,
              avatar_url: avatarUrl,
              display_name: displayName,
            }),
          }).catch(() => {}); // Fire-and-forget, don't block
        }

        return registerData.player;
      }

      console.error('Registration failed:', registerData.error);
      return null;
    }

    console.error('Unexpected login response:', loginData);
    return null;

  } catch (err) {
    console.error('Bridge to player account failed:', err);
    return null;
  }
}
```

### Background Refresh Function

```typescript
async function refreshPlayerFromAPI(playerId: string, email: string) {
  try {
    const res = await fetch(BLACKJACK_API, {
      method: 'POST',
      headers: API_HEADERS,
      body: JSON.stringify({ action: 'login', email }),
    });
    const data = await res.json();
    if (data.success && data.player) {
      setPlayer(data.player);
      localStorage.setItem('blackjack_player', JSON.stringify(data.player));
    }
  } catch (err) {
    console.warn('Background refresh failed, using cached data');
  }
}
```

---

## FIX 2: Remove ALL "Coming Soon" Gates on Login Buttons

Search the entire codebase for any of these patterns and REMOVE them:
- `"Coming Soon"` or `"coming soon"` text on login buttons
- `disabled` props on Google/Facebook login buttons
- `onClick={() => toast("Coming Soon")}` or similar stub handlers
- Conditional rendering that hides OAuth buttons (like `if (FEATURES.socialLogin)` or `showSocialLogin === false`)
- Any `return` or `early exit` that prevents the OAuth flow from executing

Replace ALL Google/Facebook button handlers with working OAuth calls:

```typescript
// Google Login Button
<button
  onClick={async () => {
    setIsLoggingIn(true);
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: window.location.origin + '/arcade/blackjack',
      },
    });
    if (error) {
      toast.error('Google login failed: ' + error.message);
      setIsLoggingIn(false);
    }
    // On success, browser redirects to Google, then back to /arcade/blackjack
    // The onMount auth detection (Fix 1) handles the rest
  }}
  disabled={isLoggingIn}
  className="w-full flex items-center justify-center gap-3 bg-white text-gray-800 font-semibold py-3 px-6 rounded-lg hover:bg-gray-100 transition"
>
  {isLoggingIn ? (
    <span className="animate-spin">⏳</span>
  ) : (
    <>
      <svg className="w-5 h-5" viewBox="0 0 24 24">
        {/* Google G logo SVG */}
        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
      </svg>
      Continue with Google
    </>
  )}
</button>

// Facebook Login Button
<button
  onClick={async () => {
    setIsLoggingIn(true);
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'facebook',
      options: {
        redirectTo: window.location.origin + '/arcade/blackjack',
      },
    });
    if (error) {
      toast.error('Facebook login failed: ' + error.message);
      setIsLoggingIn(false);
    }
  }}
  disabled={isLoggingIn}
  className="w-full flex items-center justify-center gap-3 bg-[#1877F2] text-white font-semibold py-3 px-6 rounded-lg hover:bg-[#166FE5] transition"
>
  {isLoggingIn ? (
    <span className="animate-spin">⏳</span>
  ) : (
    <>
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
      </svg>
      Continue with Facebook
    </>
  )}
</button>
```

Show both buttons prominently on the Welcome Screen, ABOVE the email login tabs (New Player / Returning Player). Add a divider: `--- or ---` between OAuth buttons and email login.

---

## FIX 3: Render Based on Auth State

The blackjack page component should render different UI based on `authState`:

```typescript
// In the main blackjack page component render:

if (authState === 'initializing') {
  return (
    <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin w-12 h-12 border-4 border-[#D4AF37] border-t-transparent rounded-full mx-auto mb-4" />
        <p className="text-[#D4AF37] text-lg font-semibold">Loading Everlight Casino...</p>
      </div>
    </div>
  );
}

if (authState === 'bridging') {
  return (
    <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin w-12 h-12 border-4 border-[#D4AF37] border-t-transparent rounded-full mx-auto mb-4" />
        <p className="text-[#D4AF37] text-lg font-semibold">Setting up your profile...</p>
        <p className="text-gray-400 text-sm mt-2">This only takes a moment</p>
      </div>
    </div>
  );
}

if (authState === 'unauthenticated') {
  return <WelcomeScreen onLoginSuccess={(playerData) => {
    setPlayer(playerData);
    localStorage.setItem('blackjack_player', JSON.stringify(playerData));
    localStorage.setItem('blackjack_player_id', playerData.player_id);
    setAuthState('authenticated');
  }} />;
}

// authState === 'authenticated' -- render the full lobby/game
return <BlackjackLobby player={player} ... />;
```

---

## FIX 4: Save Player State After Every Significant Action

After each hand, chip change, profile update, or purchase -- persist to BOTH the API AND localStorage:

```typescript
async function savePlayerState(updatedPlayer: PlayerProfile) {
  setPlayer(updatedPlayer);
  localStorage.setItem('blackjack_player', JSON.stringify(updatedPlayer));

  // Also update server
  try {
    await fetch(BLACKJACK_API, {
      method: 'POST',
      headers: API_HEADERS,
      body: JSON.stringify({
        action: 'update-balance',
        player_id: updatedPlayer.player_id,
        new_balance: updatedPlayer.chip_balance,
      }),
    });
  } catch (err) {
    console.warn('Failed to sync to server, will retry on next action');
  }
}
```

Call this after: bet resolution, chip purchase, daily claim, profile edit, avatar change.

---

## FIX 5: Logout Cleanup

When the player logs out:
```typescript
async function handleLogout() {
  // Sign out of Supabase (clears OAuth session)
  await supabase.auth.signOut();

  // Clear local state
  setPlayer(null);
  localStorage.removeItem('blackjack_player');
  localStorage.removeItem('blackjack_player_id');

  // Return to welcome screen
  setAuthState('unauthenticated');
}
```

---

## FIX 6: Error Recovery

If the bridge fails (network error, API down), show a recovery screen instead of blank loop:

```typescript
if (authError) {
  return (
    <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center">
      <div className="text-center max-w-md mx-auto p-8">
        <p className="text-red-400 text-lg font-semibold mb-4">{authError}</p>
        <button
          onClick={() => {
            setAuthError(null);
            setAuthState('unauthenticated');
          }}
          className="bg-[#D4AF37] text-black font-bold py-3 px-8 rounded-lg hover:bg-[#E8C84B] transition"
        >
          Try Again
        </button>
      </div>
    </div>
  );
}
```

---

---

## FIX 7: Preserve Play Intent Across OAuth Redirect (return_to token)

**This is the root cause of "clicked Play on Blackjack → ended up on Rewards page after Google login."**

When a player clicks Play (or any game action) while unauthenticated, the app captures the intended destination BEFORE launching OAuth. After OAuth completes, the app routes there instead of the default landing page.

### Before launching OAuth, store intent:

```typescript
// In WelcomeScreen or wherever login buttons live:
async function handleGoogleLogin(returnTo?: string) {
  // Save where the player was trying to go
  if (returnTo) {
    sessionStorage.setItem('auth_return_to', returnTo);
  } else {
    // Default: stay on current page
    sessionStorage.setItem('auth_return_to', window.location.pathname);
  }

  setIsLoggingIn(true);
  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: window.location.origin + '/arcade/blackjack',
    },
  });
  if (error) {
    toast.error('Google login failed: ' + error.message);
    setIsLoggingIn(false);
  }
}
```

### After auth completes, route to saved intent:

Add this to the `bridgeToPlayerAccount` success handler inside `onAuthStateChange`:

```typescript
if (event === 'SIGNED_IN' && session?.user?.email) {
  setAuthState('bridging');
  const playerProfile = await bridgeToPlayerAccount(session.user);
  if (playerProfile) {
    setPlayer(playerProfile);
    localStorage.setItem('blackjack_player', JSON.stringify(playerProfile));
    localStorage.setItem('blackjack_player_id', playerProfile.player_id);
    setAuthState('authenticated');

    // Route to intended destination, NOT the default Rewards page
    const returnTo = sessionStorage.getItem('auth_return_to');
    sessionStorage.removeItem('auth_return_to'); // consume it
    if (returnTo && returnTo !== window.location.pathname) {
      // Use router.push() or window.location.href to navigate
      router.push(returnTo); // Next.js router
      // OR: window.location.href = returnTo;
    }
    // If no returnTo saved, stay on current page (already at /arcade/blackjack)
  }
}
```

### Pass intent when Play button triggers auth:

On the Blackjack game component, when an unauthenticated player hits "Play":

```typescript
// Instead of showing a generic login screen, pass where they were
<button onClick={() => {
  if (!player) {
    // Store where they were trying to go before showing login
    sessionStorage.setItem('auth_return_to', '/arcade/blackjack');
    setShowLoginModal(true); // or setAuthState('unauthenticated')
  } else {
    startGame();
  }
}}>
  Play Blackjack
</button>
```

---

## FIX 8: Profile Merge -- Same Identity (Personal Email = Gmail)

**Scenario:** Player previously registered with their Gmail address (e.g., `john@gmail.com`) as a manual email login. Now they click "Continue with Google" -- Google returns the same email. Two separate auth paths, one identity.

The bridge function in Fix 1 already handles this correctly via the `login` step -- it finds the existing `player_accounts` row by email regardless of how it was created. **However, there are edge cases where this fails:**

1. Email case mismatch (`John@gmail.com` vs `john@gmail.com`)
2. The `login` response format not matching the `loginData.found === false` check
3. Multiple player rows for the same email (duplicates from failed registrations)

### Make the bridge email-case-insensitive:

```typescript
async function bridgeToPlayerAccount(authUser: { email: string; user_metadata?: any; id?: string }) {
  // Normalize email to lowercase for consistent matching
  const email = authUser.email?.toLowerCase().trim();
  if (!email) {
    console.error('No email in auth user');
    return null;
  }
  // ... rest of function unchanged
}
```

### Handle all login response shapes:

Replace the `if (loginData.found === false || loginRes.status === 404)` check with more robust logic:

```typescript
// Try login first
const loginRes = await fetch(BLACKJACK_API, {
  method: 'POST',
  headers: API_HEADERS,
  body: JSON.stringify({ action: 'login', email }),
});
const loginData = await loginRes.json();

// Player found -- multiple ways the API might signal success
if (loginRes.ok && (loginData.success || loginData.player)) {
  console.log('Existing player found:', loginData.player?.display_name);
  // Update avatar_url if Google provided one and player doesn't have one
  if (avatarUrl && !loginData.player?.avatar_url) {
    fetch(BLACKJACK_API, {
      method: 'POST',
      headers: API_HEADERS,
      body: JSON.stringify({
        action: 'update-profile',
        player_id: loginData.player.player_id,
        avatar_url: avatarUrl,
      }),
    }).catch(() => {});
  }
  return loginData.player;
}

// Player NOT found -- 404, error.code === 'NOT_FOUND', or error message contains "not found"
const isNotFound = loginRes.status === 404
  || loginData.found === false
  || loginData.error?.toLowerCase().includes('not found')
  || loginData.error?.toLowerCase().includes('no player');

if (isNotFound) {
  // Auto-register new player via OAuth (see existing register block)
  // ...
}
```

### Deduplication guard (prevent duplicate profiles):

If the register call returns a conflict (email already exists but login failed), fall back gracefully:

```typescript
const registerRes = await fetch(BLACKJACK_API, {
  method: 'POST',
  headers: API_HEADERS,
  body: JSON.stringify({
    action: 'register',
    display_name: displayName,
    email: email,
    date_of_birth: '1990-01-01',
  }),
});
const registerData = await registerRes.json();

if (registerData.success && registerData.player) {
  return registerData.player;
}

// If register returns "email already exists" conflict -- try login one more time
// This handles race conditions and duplicate rows
if (registerRes.status === 409 || registerData.error?.includes('already')) {
  const retryLogin = await fetch(BLACKJACK_API, {
    method: 'POST',
    headers: API_HEADERS,
    body: JSON.stringify({ action: 'login', email }),
  });
  const retryData = await retryLogin.json();
  if (retryData.success && retryData.player) {
    return retryData.player;
  }
}
```

---

## TESTING CHECKLIST (verify ALL of these work)

1. **Google OAuth**: Click "Continue with Google" → Google consent screen → redirects back → game loads with player profile → shows lobby with correct display name and chips
2. **Facebook OAuth**: Same flow as Google but with Facebook
3. **Email login**: Returning player enters email → loads profile → shows lobby
4. **Email register**: New player fills out form → creates account → shows lobby with 1,000 chips
5. **Page refresh while logged in**: Refresh the page → player is STILL logged in → chips and stats are preserved
6. **Close tab and reopen**: Navigate to `/arcade/blackjack` → player is STILL logged in
7. **Logout**: Click logout → returns to welcome screen → refreshing shows welcome screen (not auto-login)
8. **First-time Google user**: User with no existing player_accounts row uses Google login → auto-registers → starts with 1,000 chips → Google name and avatar imported
9. **Returning Google user**: User who already has a player_accounts row uses Google login → finds existing profile → loads with correct chip balance and stats
10. **Network error during bridge**: If API call fails during bridging → shows error message with "Try Again" button → does NOT show blank screen

---

## IMPORTANT: Do NOT break existing features

- Keep all existing game functionality (dealing, betting, side bets, multiplayer, leaderboard, etc.)
- Keep existing email-based login/register as a fallback option
- Keep biometric login if implemented
- Keep all visual styling and animations
- This fix ONLY changes: auth flow detection, OAuth button wiring, session persistence, and state hydration
