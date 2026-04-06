---
title: Everlight Ventures -- Google Drive Folder Structure
created: 2026-03-13
purpose: Master blueprint for Google Drive organization. All bot/agent outputs go here as formatted Google Docs. Slack gets summary + link only.
---

# Google Drive Folder Tree

```
Everlight Ventures/
|
|-- 00_Command_Center/
|   |-- Daily_Briefings/          # Morning/evening rollup docs from all systems
|   |-- War_Room/                 # Escalations, incidents, urgent decisions
|   |-- Meeting_Notes/            # Calendar event follow-ups
|   |-- System_Status/            # Heartbeat reports, uptime, health checks
|
|-- 01_Broker_OS/
|   |-- Scout_Reports/            # New sellers/buyers found (every 4h)
|   |-- Match_Reports/            # Buyer-seller matching results (every 3h)
|   |-- Outreach_Logs/            # Email content sent, per-client tracking
|   |-- Seller_Replies/           # Gmail reply analysis + classification
|   |-- Deal_Pipeline/            # Active deals, stage updates, contracts
|   |-- Daily_KPI/                # Pipeline metrics, revenue projections
|   |-- Follow_Up_Tracker/        # Follow-up status, next actions
|
|-- 02_XLM_Bot/
|   |-- Trade_Reports/            # Per-trade and daily P&L summaries
|   |-- Strategy_Analysis/        # Backtest results, strategy performance
|   |-- Risk_Alerts/              # Margin warnings, drawdown reports
|   |-- Daily_Scoreboard/         # Daily profit/loss, win rate, ROI
|   |-- AI_Advisor_Decisions/     # Claude executive mode ENTER/EXIT/HOLD logs
|
|-- 03_Content_Factory/
|   |-- Social_Posts/             # Generated social media content
|   |-- Avatar_Output/            # Avatar orchestrator results
|   |-- Funnel_Reports/           # Lead nurture campaign performance
|   |-- SEO_Reports/              # Keyword tracking, content optimization
|   |-- Publishing_Pipeline/      # Book status, KDP reports, royalties
|
|-- 04_Revenue_Dashboard/
|   |-- Stripe_Reports/           # Payment summaries, subscription metrics
|   |-- Monthly_Revenue/          # MRR tracking across all products
|   |-- Product_Performance/      # Per-product (Onyx, HiveM, Publishing, etc.)
|   |-- Affiliate_Reports/        # HIM Loadout commission tracking
|
|-- 05_AI_Workers/
|   |-- Hive_Mind_Logs/           # Claude/Gemini/Codex collaboration logs
|   |-- Task_Handoff/             # AI-to-human task delegation reports
|   |-- Blinko_Knowledge/         # RAG knowledge base updates
|   |-- Agent_Performance/        # Worker execution stats, error rates
|
|-- 06_Infrastructure/
|   |-- Oracle_Cloud/             # VM status, Docker health, deploy logs
|   |-- N8N_Workflow_Logs/        # Workflow execution results
|   |-- Langfuse_Reports/         # AI observability, token usage, cost
|   |-- Netdata_Snapshots/        # Server performance snapshots
|   |-- Metabase_Exports/         # BI dashboard exports
|
|-- 07_Logistics/
|   |-- Client_Files/             # Per-client service documentation
|   |-- Invoices/                 # Generated invoices
|   |-- Service_Reports/          # Delivery reports, SLA tracking
|
|-- 08_Legal_Compliance/
|   |-- Contracts/                # Generated contracts (from 36_contract_writer)
|   |-- Terms_Privacy/            # ToS, privacy policy versions
|   |-- Compliance_Audits/        # Security audits, data handling
|
|-- 09_Archives/
|   |-- 2025/                     # Historical reports by year
|   |-- 2026/                     # Current year overflow/archived
```

# Slack Channel -> Google Drive Mapping

| Slack Channel            | Primary Drive Folder(s)                          | Bot/Source                              |
|--------------------------|--------------------------------------------------|-----------------------------------------|
| #all-everlightventures   | 00_Command_Center/Daily_Briefings/               | daily_report.py, everlight_engine.py    |
| #all-everlightlogistics  | 07_Logistics/, 00_Command_Center/                | Service reports, client updates         |
| #everlightlogistics      | 07_Logistics/Client_Files/                       | Client-specific ops                     |
| #gpt_bot_30              | 05_AI_Workers/Hive_Mind_Logs/                    | AI worker outputs, GPT bot logs         |

# Bot/Agent -> Google Drive Output Mapping

| Bot/Agent                       | Frequency        | Output Folder                            |
|---------------------------------|------------------|------------------------------------------|
| broker_daily_orchestrator scout | Every 4h         | 01_Broker_OS/Scout_Reports/              |
| broker_daily_orchestrator sync  | Every 1h         | 01_Broker_OS/Daily_KPI/                  |
| broker_daily_orchestrator match | Every 3h         | 01_Broker_OS/Match_Reports/              |
| broker_daily_orchestrator outreach | 3x daily      | 01_Broker_OS/Outreach_Logs/              |
| broker_daily_orchestrator followup | 2x daily      | 01_Broker_OS/Follow_Up_Tracker/          |
| broker_daily_orchestrator report | 2x daily        | 01_Broker_OS/Daily_KPI/                  |
| broker_gmail_monitor check      | Every 15min      | 01_Broker_OS/Seller_Replies/             |
| broker_gmail_monitor digest     | Daily            | 01_Broker_OS/Daily_KPI/                  |
| XLM bot daily_report            | Daily            | 02_XLM_Bot/Daily_Scoreboard/             |
| XLM bot trade execution         | Per trade        | 02_XLM_Bot/Trade_Reports/                |
| claude_advisor decisions        | Per cycle        | 02_XLM_Bot/AI_Advisor_Decisions/         |
| avatar_orchestrator             | On demand        | 03_Content_Factory/Avatar_Output/        |
| social_poster                   | Scheduled        | 03_Content_Factory/Social_Posts/         |
| funnel_nurture                  | Scheduled        | 03_Content_Factory/Funnel_Reports/       |
| profit_scoreboard               | Daily            | 04_Revenue_Dashboard/Monthly_Revenue/    |
| war_room_watcher                | Continuous       | 00_Command_Center/War_Room/              |
| hive_cmd                        | On demand        | 05_AI_Workers/Hive_Mind_Logs/            |
| blinko_bridge                   | On demand        | 05_AI_Workers/Blinko_Knowledge/          |
| 36_contract_writer              | On demand        | 08_Legal_Compliance/Contracts/           |
| deploy_oracle status            | On demand        | 06_Infrastructure/Oracle_Cloud/          |
| n8n workflows                   | Per execution    | 06_Infrastructure/N8N_Workflow_Logs/     |
| heartbeat                       | Every 6h         | 00_Command_Center/System_Status/         |

# Permission Model

| Role                | Access Level | Notes                                    |
|---------------------|-------------|------------------------------------------|
| Owner (Rich)        | Full        | Read/write/delete/share all folders      |
| Admin               | Full        | Read/write/delete all folders            |
| Manager             | Read/Write  | Read/write all folders, no delete        |
| AI Agents           | Read/Write  | Service account, write to mapped folders |
| Slack Channel Member| View Only   | Can view docs linked in their channel    |

# File Naming Convention

All Google Docs follow this pattern:
```
{YYYY-MM-DD}_{HH-MM-PT}_{source}_{report_type}.gdoc

Examples:
2026-03-13_14-30-PT_broker_scout_report.gdoc
2026-03-13_06-00-PT_xlm_daily_scoreboard.gdoc
2026-03-13_09-15-PT_broker_seller_reply_analysis.gdoc
```

# Slack Message Format (replaces raw data dumps)

```
:page_facing_up: **Broker Scout Report** -- Mar 13, 2026 2:30 PM PT
Found 3 new sellers, 2 new buyers. 1 high-confidence match.
:link: [View Full Report](https://docs.google.com/document/d/xxx)
```

Only summary + link. Never raw data in Slack.
