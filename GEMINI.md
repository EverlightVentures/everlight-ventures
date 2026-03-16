# Everlight Master Workspace Memory

This is the top-level context for `/mnt/sdcard/AA_MY_DRIVE`.

## The Hive Mind Protocol
You are operating as part of an AI Triad (Claude, Gemini, Codex). 
- **Collaboration Rules:** Read `HIVE_MIND.md`.
- **War Room:** Log handoffs and progress in `_logs/ai_war_room/`.

## Operating Style (Synergy Mode)
- **Plan before execution.**
- Keep outputs concise and actionable.
- Prefer editing files directly over long inline code blocks.
- **Default Response Shape:** Summary, Steps, Risks, Rollback.
- Use shell/tools only when needed for the task.

## Safety & Security
- Treat shell/file-destructive actions as high risk.
- **Read-first behavior** when the task is unclear.
- **Credential Protection:** Never log, print, or commit secrets.
- Cite sources when external/current information is required.

## Modes & Skill Handoffs
- **Planning only:** Switch to `.gemini/plan`.
- **Architecture walkthroughs:** Switch to `.gemini/explain`.
- **Custom Everlight Commands:**
  - `activate_skill ev_plan`: Structured planning.
  - `activate_skill ev_execute`: Scoped implementation.
  - `activate_skill ev_review`: Security/QA review.
  - `activate_skill ticket-manager`: Manage project tickets.

## Data Flow & Automation
```
┌─────────────────────────────────────────────────────────────┐
│                    DATA FLOW                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   USB/Upload ──┐                                            │
│                │                                            │
│   Downloads ───┼──▶ STAGING ──▶ ORGANIZE ──▶ LOCAL TREE    │
│                │                                ↓           │
│   Phone ───────┘                          PROTON DRIVE      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### File Destinations
| Type | Extensions | Destination |
|------|------------|-------------|
| Photos | .jpg .png .heic | `B_Media/All_Pictures/[subfolder]` |
| Videos | .mp4 .mkv .mov | `B_Media/All_MP4s/YYYY-MM/` |
| Audio | .mp3 .flac .m4a | `B_Media/Music/` |
| Docs | .pdf .docx | `A_My_Docs/G_PDF_Files/` |
| Spreadsheets | .xlsx .csv | `A_My_Docs/F_Spreadsheets/` |
| Text | .txt .md .org | `A_My_Docs/B_Text_Files/` |
| Code | .py .js .sh | `A_My_Docs/A_Python_Scripts/` |
| Ebooks | .epub .mobi | `A_My_Docs/G_Literature/` |
| Archives | .zip .tar .7z | `D_Backups/` |

### Naming Convention
- `YYYY-MM-DD_OriginalFilename_[tags].ext`

## Claude Integration
All existing Claude skills, agents, and plans have been successfully migrated to `.gemini/`. 
- **Skills:** Found in `.gemini/skills/`
- **Agents:** Found in `.gemini/agents/`
- **Original Context:** Refer to `CLAUDE.md` and `A_Rich/CLAUDE.md` for legacy details.
- **Workspace Structure & Mind Map:** The exact layout of the workspace (and the Mermaid semantic map) is located in `WORKSPACE_MANIFEST.md`. ALWAYS refer to this file before executing file operations or making data-driven business recommendations.
