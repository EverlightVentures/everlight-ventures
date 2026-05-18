# Self-OSINT Audit - Everlight Ventures

**Owner**: Cipher (intel) + Justine (compliance review)
**Date**: 2026-04-21
**Source**: `05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/05_OSINT_and_Security/osint_tools_to_track_you_down.txt`

---

## Rationale

Running the "threat-actor perspective" OSINT exercise against our own public footprint so we see what an attacker could discover in a 2-hour pass. Prevents social engineering, targeted phishing, and reputation risk.

## Pass 1 - Domain + public site

Queries run (via Google + Shodan + crt.sh):

| Query | Finding | Risk | Action |
|---|---|---|---|
| `site:everlightventures.io` | Public site pages indexed. Clean. | Low | OK |
| `crt.sh certificate search for everlightventures.io` | 3 active certs (primary + WWW + wildcard). All from Cloudflare. | Low | OK |
| `shodan.io "everlightventures"` | No exposed ports on the public domain (Cloudflare front). | Low | OK |
| `site:github.com "everlightventures"` | Repo visible. README + plan files. Verify no secrets. | Medium | Action below |
| GitHub scan for secrets | None found via `git secrets --scan` or truffleHog on HEAD | Low | Rotate any accidentally-committed keys |
| LinkedIn + Twitter footprint | Minimal, by design | Low | OK |

## Pass 2 - Credentials on public paste sites

Queries:
- `pastebin.com "everlight"` - no hits
- `github.com search for "sk_live_"` + our org - no hits
- `haveibeenpwned.com` for Lucrex's primary email - historical hits from 2019 LinkedIn breach only. Not current.

## Pass 3 - API surface

Queries:
- Cloudflare workers at `/api/*` on the public site - verified no auth-bypass on checkout flow
- Supabase public project URL (`jdqqmsmwmbsnlnstyavl.supabase.co`) - RLS enforced on all tables
- n8n public webhook at `:5678/webhook/...` - not authenticated by design (webhook tokens in path). Ensure none leak past necessary recipients.

## Findings summary

| Severity | Finding | Owner |
|---|---|---|
| High | None | - |
| Medium | GitHub repo public; ensure .env.example never contains real values | Forge |
| Medium | n8n webhook URLs are effectively bearer tokens. Rotate quarterly. | Forge |
| Low | LinkedIn breach hit from 2019 still in datasets; change password if not already | Lucrex |
| Low | Cloudflare Pages build logs sometimes echo env var names; cross-check. | Forge |

## Remediations opened

- [ ] Forge: audit .env.example for accidental real values before next commit
- [ ] Forge: quarterly calendar reminder to rotate n8n webhook paths
- [ ] Lucrex: confirm primary email password not reused elsewhere
- [ ] Cipher: re-run this audit 2026-07-21 (quarterly)

## What we did NOT find (good news)

- No credential leaks
- No exposed services bypassing Cloudflare
- No RLS misconfig on Supabase
- No public S3 bucket named against Everlight
- No Shodan hits that would indicate Oracle IP is indexed as "Everlight"

## Resume

`quarterly osint self audit` in a future session triggers a re-run.
