# Workspace Manifest & Semantic Map
*Last Synced: 2026-03-15*

This document is the absolute source of truth for the directory structure.
ALL AI agents MUST use this map to locate data before executing file operations.

## Directory Tree

```
AA_MY_DRIVE/
├── 01_BUSINESSES/
│   ├── Everlight_Ventures/          Parent brand & venture studio
│   │   ├── 00_Core/                 Brand guidelines, business plans, roles, SOPs, training
│   │   ├── 02_Operations/           Finance, payroll, schedules, Slack config
│   │   ├── 03_Content/              Drafts, published, assets, avatar assets
│   │   ├── 04_Automation/           N8N workflows, scripts, logs
│   │   ├── Alley_Kingz/             Mobile PvP game (HTML5 prototypes + Unity)
│   │   ├── Everlight_Cannabis/      Cannabis venture docs
│   │   ├── Everlight_Crypto/        BCARDI token, Zilliqa, crypto projects
│   │   ├── Everlight_Foundations/   Core brand docs, SVG logos, plans, site copy
│   │   │   └── gear_engine/         Daily Drop Engine config, fallback queue, Lovable prompt, SQL seeds
│   │   ├── Everlight_Literature/    Publishing (Sam & Robo, Beyond the Veil, TSW)
│   │   ├── Broker_OS/               Autonomous B2B deal matchmaking SaaS
│   │   ├── Everlight_Logistics/     Shipping & fulfillment service
│   │   ├── Last_Light_Protocol/     Gaming clan / community
│   │   ├── Personal_Training/       Fitness coaching
│   │   └── trading/                 Trading strategies & research
│   └── onyx_pos/                    Onyx POS SaaS (Flask app, launch plan)
│
├── 02_CONTENT_FACTORY/
│   ├── 00_Inbox/                    Raw ideas, photos, clips
│   ├── 01_Queue/                    AI-prepared drafts
│   ├── 02_Published/                Content archive
│   ├── 03_Assets/                   Brand kits, templates, voice guides
│   ├── 04_Analytics/                Performance metrics
│   ├── AI_Workteams/                Collaborative AI session outputs
│   └── kdp_metadata/                Amazon KDP metadata for all books
│
├── 03_AUTOMATION_CORE/
│   ├── 00_N8N/                      N8N workflow definitions
│   ├── 01_Scripts/                  Python automation scripts
│   ├── 02_Config/                   YAML configs
│   ├── 03_Credentials/              Encrypted vault (GPG)
│   ├── 04_Logs/                     System & automation logs
│   ├── 05_Slack_Workflows/          Slack bot configs
│   └── 06_AI_Tools/                 AI utility scripts
│
├── 04_MEDIA_LIBRARY/
│   ├── Games/                       Game assets & builds
│   ├── Music/                       Audio files
│   └── Photos/                      Photography & screenshots
│
├── 05_PERSONAL/
│   ├── 01_Finance/                  Personal financial docs
│   ├── 02_Training/                 Fitness & training logs
│   ├── 03_Creative/                 Creative projects
│   ├── 04_Learning/                 Educational materials
│   ├── 05_Life_Admin/               Life management
│   ├── A_Personal_Notebook/         Personal notes
│   └── B_Security_Notebook/         Security notes
│
├── 06_DEVELOPMENT/
│   ├── Active_Projects/             Current dev projects
│   ├── A_Projects/                  Project archives
│   ├── Archives/                    Old/completed projects
│   ├── everlight_os/                Everlight OS modules, infra stacks, and knowledge base
│   ├── Experiments/                 Dev experiments
│   ├── GetMyOS/                     Custom OS project
│   ├── hivemind_saas/               Hive Mind SaaS codebase
│   ├── HTML_Files/                  Standalone HTML tools
│   ├── Learning/                    Dev learning materials
│   ├── nextcloud/                   Nextcloud setup
│   ├── RG_OS/                       RG OS project
│   ├── saas_factory/                SaaS factory templates
│   ├── xlm_bot/                     XLM trading bot (LIVE on Oracle Cloud)
│   └── Zfold_Customizations/        Z Fold device configs
│
├── 07_STAGING/
│   ├── _Archive_Root_Cleanup/       Archived cleanup artifacts
│   ├── C_Downloads/                 Downloaded files to sort
│   ├── Inbox/                       Unsorted incoming files
│   ├── Narrator_Selection/          Audiobook narrator samples
│   ├── Processing/                  Files being processed
│   └── Review/                      Files under review
│
├── 08_BACKUPS/
│   ├── Business_Archives/           Old business docs
│   ├── Credentials_Plaintext_Backup/ Legacy credential backups
│   ├── D_Backups/                   General backups
│   ├── D_TOOLKIT/                   Tools & utilities backup
│   ├── Old_Phone_Dumps/             Old device data
│   ├── ProtonDrive/                 Proton Drive sync
│   ├── SMS_CallLogs/                Phone logs
│   ├── System_Artifacts/            System files
│   ├── System_Snapshots/            Point-in-time snapshots
│   ├── Takeout/                     Google Takeout data
│   └── Trash_Dedupe/                Duplicate cleanup
│
├── 09_DASHBOARD/
│   ├── aa_dashboard/                FastAPI file browser
│   ├── hive_dashboard/              Django ops center (hive, business_os, broker_ops, taskboard, funnel, payments)
│   ├── master_dashboard/            Master file browser + analytics
│   ├── reports/                     Trade & business reports
│   └── streamlit_app/               Streamlit analytics dashboards
│
├── Non_Business/                    Non-Everlight businesses & side projects
│   ├── Customer_Support/            Support docs
│   ├── Mountain Gardens Nursery POS/  Mountain Gardens POS (client)
│   ├── Shared/                      Shared resources
│   ├── Solar/                       Solar business docs
│   ├── Solar_Business/              Solar business plans
│   ├── Sunflower_Land/              Sunflower Land project
│   └── The_Yung_Printz/             Yung Printz project
│
└── [Agent Config Directories]
    ├── .claude/                      Claude agents, skills, modes, hooks, memory
    ├── .gemini/                      Gemini agents, skills, plans
    ├── .codex/                       Codex agents
    └── .perplexity/                  Perplexity agents
```

## Key Project Paths (Quick Reference)

| Project | Path |
|---------|------|
| XLM Bot (LIVE) | `06_DEVELOPMENT/xlm_bot/` |
| XLM feature store | `06_DEVELOPMENT/xlm_bot/feature_store.py` |
| Hive Mind SaaS | `06_DEVELOPMENT/hivemind_saas/` |
| Onyx POS | `01_BUSINESSES/onyx_pos/` |
| Alley Kingz | `01_BUSINESSES/Everlight_Ventures/Alley_Kingz/` |
| Sam & Robo Books | `01_BUSINESSES/Everlight_Ventures/Everlight_Literature/Ebook_Sells/Adventures_Series/` |
| Beyond the Veil | `01_BUSINESSES/Everlight_Ventures/Everlight_Literature/Ebook_Sells/BEYOND_THE_VEIL_HaileyPink_Book1/` |
| Brand Assets | `01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/assets/` |
| Site Copy | `01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/LOVABLE_SITE_MASTER.md` |
| Lovable build prompt | `01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/LOVABLE_MASTER_PROMPT.md` |
| Lovable blackjack prompt | `01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/LOVABLE_BLACKJACK_BUSINESS_OS_PROMPT.md` |
| Django Dashboard | `09_DASHBOARD/hive_dashboard/` |
| Business OS dashboard | `09_DASHBOARD/hive_dashboard/business_os/` |
| Blackjack Django app | `09_DASHBOARD/hive_dashboard/blackjack/` |
| Public funnel pages | `09_DASHBOARD/hive_dashboard/funnel/templates/funnel/` |
| War Room Logs | `_logs/ai_war_room/` |
| Everlight OS | `06_DEVELOPMENT/everlight_os/` |
| Oracle observability deploy | `06_DEVELOPMENT/everlight_os/deploy_oracle_observability.sh` |
| Broker OS | `01_BUSINESSES/Everlight_Ventures/Broker_OS/` |
| Broker OS Django app | `09_DASHBOARD/hive_dashboard/broker_ops/` |
| Broker OS scripts | `03_AUTOMATION_CORE/01_Scripts/broker_*.py` |
| Broker OS MCP server | `06_DEVELOPMENT/mcp_servers/broker_os/` |
| Business OS Supabase schema | `supabase/sql/business_os_schema.sql` |
| Blackjack audit | `09_DASHBOARD/reports/EVERLIGHT_BLACKJACK_OS_AUDIT_2026.md` |
| Queue-mode n8n stack | `06_DEVELOPMENT/everlight_os/n8n/docker-compose.queue.yml` |
| Uptime monitoring stack | `06_DEVELOPMENT/everlight_os/uptime_kuma/` |
| Trading watchtower sync | `03_AUTOMATION_CORE/01_Scripts/trading_watchtower_sync.py` |
| Bot-native watchtower sync | `06_DEVELOPMENT/xlm_bot/trading_watchtower_sync.py` |
| Oracle deploy scripts | `06_DEVELOPMENT/xlm_bot/push_updates.sh` |

## Agent File Save Rules

CRITICAL: Agents MUST save outputs to the correct project folder.

| Content Type | Save To |
|-------------|---------|
| Alley Kingz game files | `01_BUSINESSES/Everlight_Ventures/Alley_Kingz/` |
| Book manuscripts & assets | `01_BUSINESSES/Everlight_Ventures/Everlight_Literature/` |
| Brand docs, site copy, logos | `01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/` |
| Lovable sync prompts | `01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/LOVABLE_*.md` |
| Public site templates | `09_DASHBOARD/hive_dashboard/funnel/` |
| Crypto/token docs | `01_BUSINESSES/Everlight_Ventures/Everlight_Crypto/` |
| Logistics docs | `01_BUSINESSES/Everlight_Ventures/Everlight_Logistics/` |
| Broker OS docs & plans | `01_BUSINESSES/Everlight_Ventures/Broker_OS/` |
| Broker OS scripts | `03_AUTOMATION_CORE/01_Scripts/broker_*.py` |
| Broker OS Django app | `09_DASHBOARD/hive_dashboard/broker_ops/` |
| Broker OS MCP server | `06_DEVELOPMENT/mcp_servers/broker_os/` |
| Business OS dashboard/code | `09_DASHBOARD/hive_dashboard/business_os/` |
| Blackjack dashboard/game code | `09_DASHBOARD/hive_dashboard/blackjack/` |
| Business OS database schema | `supabase/sql/business_os_schema.sql` |
| Onyx POS code | `01_BUSINESSES/onyx_pos/` |
| Bot code & configs | `06_DEVELOPMENT/xlm_bot/` |
| Bot feature store | `06_DEVELOPMENT/xlm_bot/feature_store.py` |
| Bot watchtower runtime | `06_DEVELOPMENT/xlm_bot/trading_watchtower_sync.py` |
| Hive Mind SaaS code | `06_DEVELOPMENT/hivemind_saas/` |
| Content drafts | `02_CONTENT_FACTORY/01_Queue/` |
| Published content | `02_CONTENT_FACTORY/02_Published/` |
| N8N workflows | `03_AUTOMATION_CORE/00_N8N/` |
| n8n infrastructure stacks | `06_DEVELOPMENT/everlight_os/n8n/` |
| Observability deployment scripts | `06_DEVELOPMENT/everlight_os/` |
| Scripts | `03_AUTOMATION_CORE/01_Scripts/` |
| Trading watchtower automation | `03_AUTOMATION_CORE/01_Scripts/trading_watchtower_sync.py` |
| Infra monitoring stacks | `06_DEVELOPMENT/everlight_os/uptime_kuma/` |
| Trade reports | `09_DASHBOARD/reports/` |
| Product audits | `09_DASHBOARD/reports/` |
| Plans & audits | `01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/plans/` |
| Screenshots & media | `04_MEDIA_LIBRARY/Photos/` |
| Unsorted incoming | `07_STAGING/Inbox/` |

NEVER save project files at the workspace root or in random directories.
