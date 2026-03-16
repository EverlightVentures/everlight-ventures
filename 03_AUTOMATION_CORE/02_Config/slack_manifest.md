# 📟 Everlight Slack OS Manifest

This document defines the communication architecture between the Hive Mind (Claude, Gemini, Codex) and your Slack workspace.

## 📁 1. Channel Organization
| Channel | Function | Agent | Webhook Purpose |
| :--- | :--- | :--- | :--- |
| `#01-war-room` | Live deliberations, raw logs, debates | **Claude** | Daily briefs & task logs |
| `#02-ai-reports` | Finalized Report Canvases & Docs | **Gemini** | Google Doc/Canvas links |
| `#03-trading-desk`| XLM bot trades, ROI, F&G alerts | **Codex** | Market state & bot metrics |
| `#04-content-factory`| Drafts, Social Assets, Ad Copies | **Gemini** | Review & approval flows |
| `#05-system-alerts`| Manifest updates, n8n errors | **Monitor**| File tree changes & sync status |

## 🔗 2. The Canvas Flow
Whenever a significant war log is written to `_logs/ai_war_room/`:
1.  **Trigger:** `log_to_canvas.py` is invoked.
2.  **Process:** Log is sent to n8n Webhook.
3.  **Result:** n8n creates a viewable Google Doc/Canvas.
4.  **Post:** A clean link is dropped into `#02-ai-reports`.

## 🤖 3. Agent Directives
- **Claude:** Post your high-level plans to `#01-war-room`.
- **Gemini:** Post your final implementation links to `#02-ai-reports`.
- **Codex:** Post your profit/loss and code changes to `#03-trading-desk`.
- **System:** Post file tree updates automatically to `#05-system-alerts`.
