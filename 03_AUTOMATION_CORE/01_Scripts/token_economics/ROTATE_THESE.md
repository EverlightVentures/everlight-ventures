# ROTATE / RELOCATE checklist (Token Economics OS, Phase 1)

Generated 2026-06-25 by the key-registry leak scan. These secrets are hardcoded
in plaintext inside `/.mcp.json`.

## Severity: MODERATE (not an emergency)
`.mcp.json` is **NOT tracked by git** (`git ls-files` does not match it). So these
values were never committed to history. This is local-file hygiene, not a public
breach. Still worth fixing so a single shared/synced file is not a one-stop secret grab.

## What is exposed and where

| Secret | Where in .mcp.json | Note |
|---|---|---|
| Resend API key (`re_...`) | key `RESEND_API_KEY` AND reused as `SMTP_PASS` | same key, two spots |
| Supabase access token (`sbp_...`) | a positional MCP server arg (the `args[]` array) | no key name, passed as a CLI flag value |

## Recommended actions (Rich runs these; we do not auto-rotate live keys)

1. **Relocate, do not retype.** Move each value into the vault, then reference it:
   - `python3 content_tools/secrets_vault.py set RESEND_API_KEY '<value>'`
   - `python3 content_tools/secrets_vault.py set SUPABASE_ACCESS_TOKEN '<value>'`
   - Then in `.mcp.json` replace the literal with an env reference if your MCP client
     supports `${VAR}` interpolation; if it does not, leave the file as-is locally and
     rely on the fact that it is gitignored (the real protection here).
2. **Rotate only if the file was ever shared** (synced to PC, emailed, screen-shared).
   If it never left the phone, relocation is enough. If unsure, rotate:
   - Resend: dashboard -> API Keys -> roll. Update vault + `branded_mailer` consumers.
   - Supabase: dashboard -> Account -> Access Tokens -> revoke + regenerate. Update vault.
3. **After relocating**, re-run `python3 -m token_economics.populate_registry`. The
   LEAK lines should drop to zero. That is the receipt that the loop is closed.

## Why this is the right call
- No auto-rotation: rotating a live key from a script can break running services
  (the MCP servers, branded_mailer, Supabase writes) with no human in the loop.
- The registry already records these under `status: leaked` so they stay visible
  until you clear them.
