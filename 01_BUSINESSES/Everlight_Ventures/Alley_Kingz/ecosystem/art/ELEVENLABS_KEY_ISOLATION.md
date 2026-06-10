# Alley Kingz -- ElevenLabs Key Isolation

Goal: the Alley Kingz game audio must NOT share budget, credits, or blast-radius
with Rich's other ~11 ElevenLabs projects (Wholesale AI caller, hive-voice,
avatar_orchestrator, stark_ai, the AI receptionist consulting product, etc.).

## The problem (found 2026-06-03)
There is ONE shared `ELEVENLABS_API_KEY` in `03_Credentials/.env` (line 54). A
workspace grep found ~30 files referencing it across the whole ecosystem. Every
one of those draws down the SAME starter-plan budget (61,987 chars/cycle) and the
SAME Music credits as Alley Kingz. Account: tier `starter`, user_id
`user_9301kkcs9naafpcvs0bfc93j8e1y`. If the game burns credits on theme music,
the voice caller and receptionist run dry, and vice versa. They are twisted
together today.

## The fix -- two layers

### Layer 1: code (DONE)
`generate_audio.py` + `check_account.py` now read keys in this order:
  1. `ALLEY_KINGZ_ELEVENLABS_API_KEY`   <- dedicated, preferred
  2. `AK_ELEVENLABS_API_KEY`            <- short alias
  3. `ELEVENLABS_API_KEY`               <- shared fallback (prints a SHARED warning)
So nothing breaks today, and the instant a dedicated key exists the game switches
to it automatically. No other Alley Kingz code touches the shared key.

### Layer 2: account (MANUAL -- 2 minutes, Rich does this in the dashboard)
ElevenLabs supports multiple API keys per account, each with its OWN scopes and
its OWN optional credit limit. Steps:
  1. elevenlabs.io -> profile icon (top right) -> Workspace settings ->
     Service Accounts / API Keys tab.
  2. "Create API Key". Name it: `alley-kingz-game`.
  3. Set a credit LIMIT on the key (e.g. cap it at the credits you want the game
     to ever spend). This is the real isolation -- a per-key credit cap means the
     game can NEVER drain the voice-caller budget even if a loop misfires.
  4. Restrict scopes to what the game needs: Text to Speech + Music (Sound
     Generation). It does NOT need Conversational AI / agents / phone.
  5. Copy the new `sk_...` value.
  6. Add to `03_Credentials/.env`:
       ALLEY_KINGZ_ELEVENLABS_API_KEY=sk_<the_new_key>
  7. (Optional, cleaner) Move Alley Kingz to its OWN ElevenLabs WORKSPACE so its
     custom voices + history are fully separate from the other projects. A
     separate workspace = separate billing surface and separate voice library.

### Layer 3: secrets hygiene (per the crypto-seed-vault doctrine)
The dedicated key should ALSO go into Proton Pass (the canonical secret store per
`reference_crypto_seed_vault.md`), tagged "Alley Kingz only". The plaintext `.env`
line is the operational copy; Proton Pass is the source of truth. Never commit the
raw key to git -- `.env` is gitignored; these scripts only read it from the
environment, they never hardcode it.

## Verify isolation later
Run `python3 check_account.py` with the dedicated key exported. The `KEY tail:`
line and the per-key credit cap in the dashboard confirm the game is on its own
lane. If `generate_audio.py` prints `[key] using ELEVENLABS_API_KEY [SHARED ...]`
the dedicated key is NOT set yet -- still twisted.
