# PC Transfer Guide -- Everything You Need

> Last updated: 2026-04-10
> This file is your checklist for setting up a new PC with the full Everlight stack.

---

## Step 1: Clone the Repo

```bash
git clone git@github.com:EverlightVentures/everlight-ventures.git
cd everlight-ventures
git checkout server-auth-blackjack
```

This gives you:
- 85 agent .md files (`.claude/agents/`)
- Claude commands, hooks, modes, skills, memory (`.claude/`)
- Full Hive Mind (roster.yaml, EMPLOYEE_DIRECTORY, TEAM_PROFILES, TEAM_FIRMWARE)
- All scripts, bots, dashboards, Supabase migrations
- .env.example template

---

## Step 2: Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

Claude Code reads `.claude/` automatically. All 79 agents, hooks, and commands will load.

---

## Step 3: Set Up Credentials

Copy `.env.example` to `03_AUTOMATION_CORE/03_Credentials/.env` and fill in:

| Key | Where to get it |
|-----|----------------|
| ANTHROPIC_API_KEY | console.anthropic.com |
| OPENAI_API_KEY | platform.openai.com |
| COINBASE_API_KEY + SECRET | coinbase.com/settings/api |
| SUPABASE_URL | jdqqmsmwmbsnlnstyavl.supabase.co |
| SUPABASE_ANON_KEY | Supabase dashboard > Settings > API |
| SUPABASE_ACCESS_TOKEN | Supabase dashboard > Account > Access tokens |
| STRIPE_SECRET_KEY | dashboard.stripe.com/apikeys |
| RESEND_API_KEY | resend.com/api-keys |
| ELEVENLABS_API_KEY | elevenlabs.io/app/settings/api-keys |
| SLACK_BOT_TOKEN (warroom) | api.slack.com/apps > Bot User OAuth Token |
| SLACK_BOT_TOKEN (xlmbot) | api.slack.com/apps > Bot User OAuth Token |
| ATTOM_API_KEY | api.attomdata.com |

These are also stored in memory: see `.claude/projects/*/memory/credentials_map.md`

---

## Step 4: SSH Keys for Oracle + GitHub

```bash
# Generate new SSH key
ssh-keygen -t ed25519 -C "lucrex@everlightventures.io" -f ~/.ssh/github_deploy

# Add to GitHub: Settings > Deploy keys > Add
cat ~/.ssh/github_deploy.pub

# Oracle SSH config (~/.ssh/config):
Host oracle-e5
    HostName 129.159.38.250
    User opc
    IdentityFile ~/.ssh/oracle_key

# Get Oracle key from current phone:
# The Oracle private key is NOT in the repo (security).
# Transfer from phone: /root/.ssh/oracle_key
```

---

## Step 5: Oracle Connection Verification

```bash
ssh oracle-e5 "systemctl --user list-units --state=running | head -20"
```

You should see: xlm-bot, xlm-dash-react, n8n, blinko, hive-django, hive-voice, etc.

---

## Step 6: Install Dependencies

```bash
# Python
pip install anthropic openai supabase coinbase-advanced-py resend httpx

# Node (for everlightventures site)
cd 06_DEVELOPMENT/everlightventures && npm install

# Supabase CLI
npm install -g supabase
```

---

## Step 7: Verify Everything

```bash
# Agents loaded?
ls .claude/agents/*.md | wc -l  # Should be 85

# Hive Mind intact?
grep "79 agents" 06_DEVELOPMENT/everlight_os/hive_mind/roster.yaml

# Bot reachable?
ssh oracle-e5 "curl -s localhost:8502" | head -5

# Blinko reachable?
curl -s http://129.159.38.250:1111/api/v1/note/list | head -5

# Dashboard reachable?
curl -s http://129.159.38.250:8504 | head -5
```

---

## What Lives WHERE

| Thing | Location | Notes |
|-------|----------|-------|
| Code + Agents + Config | GitHub repo | `git clone` gets it all |
| Credentials | `.env` files | Fill from template or transfer |
| Oracle SSH keys | `~/.ssh/` | Transfer from phone manually |
| Claude Code credentials | `~/.claude/.credentials.json` | Re-auth with `claude login` |
| Oracle servers | 129.159.38.250 | Always running, connect from anywhere |
| Supabase | Cloud | Log in at supabase.com |
| Stripe | Cloud | Log in at stripe.com |
| Slack | Cloud | Bot tokens in .env |
| Cloudflare | Cloud | Log in at cloudflare.com |
| GitHub | Cloud | SSH key gives access |

---

## Cloud Subscriptions (just log in)

- **Anthropic**: console.anthropic.com
- **Supabase**: supabase.com (project: jdqqmsmwmbsnlnstyavl)
- **Stripe**: dashboard.stripe.com
- **Cloudflare**: dash.cloudflare.com (everlightventures.io)
- **Oracle Cloud**: cloud.oracle.com (2 VMs)
- **ElevenLabs**: elevenlabs.io
- **Resend**: resend.com
- **Slack**: everlightventures.slack.com
- **Google Workspace**: workspace.google.com (Drive, Docs, Calendar)
- **Namecheap**: namecheap.com (domain registrar)
- **GitHub**: github.com/EverlightVentures
- **ImprovMX**: improvmx.com (email forwarding for @everlightventures.io)

---

## The ONE Thing You Can't Git Clone

**Oracle SSH private key.** Transfer it manually from phone:
```bash
# On phone, copy to PC via USB/ADB/scp:
/root/.ssh/oracle_key -> PC's ~/.ssh/oracle_key
chmod 600 ~/.ssh/oracle_key
```

Everything else is either in the repo or in the cloud.
