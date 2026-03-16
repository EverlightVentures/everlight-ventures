# Everlight AI Organization Registry

This document defines the 25-agent organization for managing the Amazon Store, Book Publishing, Affiliate Marketing, and Social Media operations.

## 1. System Architecture
- **Strategy (Claude CLI):** Final authority, architectural design, high-level copy strategy.
- **Operations (Gemini CLI):** Execution lead, backup orchestrator, production writing, analytics.
- **Engineering (Codex CLI):** Implementation, automation scripts, Slack integration, asset building.
- **Intelligence (Perplexity):** Real-time research, trend hunting, market analysis.

## 2. Workspace Mapping (Personalization)
- **Publishing/Books:** `/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Publishing/`
- **Amazon/Affiliate:** `/mnt/sdcard/AA_MY_DRIVE/02_CONTENT_FACTORY/`
- **Automation/Code:** `/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/` & `/mnt/sdcard/AA_MY_DRIVE/xlm_bot/`
- **Logs/War Room:** `/mnt/sdcard/AA_MY_DRIVE/_logs/ai_war_room/` & `/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/04_Logs/`

## 3. Slack Channel Map (JSON)
```json
{
  "channels": {
    "ai-war-room": "Global status and major approvals",
    "agent-exec-logs": "Executive team internal logs",
    "agent-revenue-logs": "Amazon and Affiliate production logs",
    "agent-books-logs": "Series planning and writing logs",
    "agent-social-logs": "Campaign and trend hunter logs",
    "agent-ops-logs": "Automation and KPI auditing logs"
  }
}
```

## 4. Standard Task Object Schema
```json
{
  "task_id": "UUID",
  "owner": "Agent Name",
  "status": "pending|active|blocked|done",
  "priority": 1-5,
  "context_paths": ["/path/to/relevant/files"],
  "inputs": {},
  "outputs": {},
  "slack_thread_ts": "timestamp",
  "next_action": "description",
  "eta": "YYYY-MM-DD HH:MM"
}
```

## 5. Agent Registry & Assignments

| Team | # | Agent Name | Primary LLM | Mission |
| :--- | :--- | :--- | :--- | :--- |
| **Executive** | 01 | Chief Operator | Claude | Final Strategy/Approvals |
| | 02 | Ops Deputy | Gemini | Execution Lead/Sync |
| | 03 | Engineering Foreman | Codex | Implementation/API |
| | 04 | Intelligence Chief | Perplexity | Real-time Market Intel |
| **Revenue** | 05 | Product Scout | Perplexity | Amazon Opportunity Research |
| | 06 | Listing Strategist | Claude | Conversion Psychology |
| | 07 | Listing Writer | Gemini | Copy Production |
| | 08 | SEO Mapper | Gemini/P | Keyword Intent Mapping |
| | 09 | Offer Curator | Perplexity | Affiliate Selection |
| | 10 | Funnel Architect | Claude | Conversion Flow Design |
| | 11 | Sync Coordinator | Gemini | Launch Synchronization |
| **Books** | 12 | Showrunner | Claude | Series Roadmap/Quality |
| | 13 | Writing Lead | Claude | Outlining/Scene Beats |
| | 14 | Draft Writer | Gemini | Manuscript/Marketing Adaptation |
| | 15 | Editor/QA | Claude | Continuity/Polish |
| | 16 | Asset Builder | Codex | Format/Metadata Automation |
| **Social** | 17 | Content Director | Claude | Pillar Strategy |
| | 18 | Trend Hunter | Perplexity | Viral Signal Monitoring |
| | 19 | Platform Copywriter | Gemini | Native Post Creation |
| | 20 | Prompt Producer | Claude | Visual/Video Briefs |
| | 21 | Repurposing Agent | Gemini | Asset Multiplier |
| | 22 | Distribution Ops | Codex | Scheduling/Logging |
| **Growth** | 23 | Automation Architect | Claude | System Logic/SOPs |
| | 24 | Workflow Builder | Codex | Tool/Script Implementation |
| | 25 | Analytics Auditor | Gemini/P | KPI Tracking/Experiments |

---
---

## 6. Daily & Weekly Cadence

### Daily (Execution Focus)
- **09:00:** Perplexity Scouts/Hunters post trend digests to #ai-war-room.
- **10:00:** Chief Operator sets priorities; Ops Deputy assigns tasks.
- **14:00:** Sync Coordinator checks launch dependencies.
- **17:00:** All agents post EOD status using "Status / Next Action / Owner / ETA".

### Weekly (Strategy Focus)
- **Monday:** Strategy Director & Showrunner set campaign goals.
- **Wednesday:** Analytics Auditor presents KPI review and experiment results.
- **Friday:** Automation Architect reviews workflow health and SOP updates.

## 7. Error & Handoff Protocol
- **Conflict:** Escalate to Chief Operator (Claude).
- **Technical Failure:** Escalate to Eng Foreman (Codex).
- **Stalled Task:** Escalate to Ops Deputy (Gemini).
- **Mandatory Footer:** EVERY output must end with:
  `Status / Next Action / Owner / ETA`

**Status:** Completed Org Build | **Next Action:** User Feedback | **Owner:** Gemini CLI | **ETA:** Immediate
