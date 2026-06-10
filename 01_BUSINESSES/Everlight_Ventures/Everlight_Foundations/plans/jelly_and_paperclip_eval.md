# Jellyfin + PaperClip - Evaluation + Deploy Plans

**Date**: 2026-04-21
**Folder**: `05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/04_Self_Hosting_and_Offline_AI/`
**Transcripts**:
- `jellyfin_media_server_automated.txt`
- `best_jellyfin_projects_2026.txt`
- `how_to_deploy_paperclip_on_hostinger.txt`

---

## Jellyfin - Media Server for Everlight Archive

### Role in the Hive

Primarily personal / archival use, not revenue-bearing. If deployed, Jellyfin serves as:
1. Unified viewer for any video/audio assets produced by Content Factory (Beyond the Veil clips, Alley Kingz promos, studio sessions)
2. Offline-ready library for personal consumption
3. Archive of voice recordings from Marcus handler + call recordings from Piper receptionist (once live)

### Deploy plan (when Oracle disk allows)

Prerequisite: Oracle free disk above 15GB. Currently 2.8GB. Do NOT deploy until cleanup completes.

```bash
# On Oracle E5 (future, once disk available)
sudo dnf install -y epel-release
curl https://repo.jellyfin.org/install-debuntu.sh | sudo bash -s  # works on RHEL-family with adjustment
# OR container approach:
sudo podman pull docker.io/jellyfin/jellyfin:latest
mkdir -p /home/opc/jellyfin/{config,cache,media}
sudo podman run -d --name jellyfin \
  --network host \
  -v /home/opc/jellyfin/config:/config \
  -v /home/opc/jellyfin/cache:/cache \
  -v /home/opc/jellyfin/media:/media \
  docker.io/jellyfin/jellyfin:latest
# Access via http://163.192.19.196:8096 (firewall to internal only!)
```

### Plugins to add (from `best_jellyfin_projects_2026.txt`)

- **Jellyfin-MPV-Shim** (desktop client with proper subtitle rendering)
- **SubCleaner** (auto-fetch subtitles)
- **Intro Skipper** (auto-skip intros/credits)
- **MusicBrainz** (metadata enrichment for audio files)

### Security

- Firewall 8096 to localhost. Access via Oracle SSH tunnel or tailscale (future).
- Never expose to the open internet without auth hardening.

### Priority

Tier 3. Nice-to-have. Revisit after Oracle disk free + Alley Kingz store live. Not blocking anything revenue-bearing.

---

## PaperClip - Self-Hosted ChatGPT UI

### Role in the Hive

Evaluation candidate for a UI layer that operators (Lucrex, Forge) can use when SSH'd into Oracle but don't want a terminal. Competes with the Django :8504 dashboard's chat panel.

### Eval plan

**Decision gate**: Do NOT deploy to production Oracle. Use a $4/mo Hostinger trial VPS for 7 days. If PaperClip earns a daily habit from Lucrex or Forge in that week, consider absorbing onto Oracle. If it does not, cancel.

### Deploy on Hostinger VPS (trial)

Per the transcript, Hostinger has a pre-built PaperClip template. Rough steps:

1. Sign up https://hostinger.com, KVM2 plan monthly ($10-12).
2. Pick the PaperClip application template during VPS setup.
3. After 2 minutes it deploys. Access via provided URL.
4. Point PaperClip at an OpenRouter API key (the `$OPENROUTER_API_KEY` from our credentials).
5. Use for 7 days. Measure: did any real work get done here vs in Django :8504?

### What to watch for

- If PaperClip UX is meaningfully better than Django's chat panel, lift its design patterns into the Django view.
- If PaperClip feels like "ChatGPT clone", cancel. We already have chat via Claude Code CLI + Django.

### Priority

Tier 3. Optional. Low cost, low commitment. Decision in 1 week if Lucrex chooses to evaluate.

---

## Meta

Both Jellyfin and PaperClip are deliberate NO for this session and likely the next. They are filed for when Oracle disk clears + Lucrex explicitly asks to evaluate.

If Jellyfin ships, it lands at `/home/opc/jellyfin/` on Oracle with config in git.
If PaperClip wins its eval, either absorb onto Oracle in a sandboxed container or shell it permanently. No halfway-there deploy.
