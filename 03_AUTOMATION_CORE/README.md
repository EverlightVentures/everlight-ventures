# AUTOMATION CORE

**The brain of Everlight Business Fabric**

This is where all automation lives:
- n8n workflows (event orchestration)
- Python scripts (file ops, content tools, business logic)
- AI workers (GPT, Claude, Perplexity, Codex)
- Encrypted credentials (secure vault)
- System logs (audit trail)

## Architecture

```
EVENT → n8n → AI Worker → ACTION → LOG
```

Every business operation is an event that triggers automation.

## 00_N8N

**Workflow orchestration**

Key workflows:
- `content_publisher.json` - Multi-platform social posting
- `slack_router.json` - AI command dispatcher
- `payment_processor.json` - Stripe + USDC webhooks
- `file_organizer.json` - Auto-organize downloads
- `analytics_aggregator.json` - Daily metrics summary
- `security_auditor.json` - Weekly credential scan

## 01_Scripts

**Python automation organized by function**

### file_organizer/
- `organize_files.py` - EXIF scanning, smart routing
- `sync_manager.py` - Proton Drive bidirectional sync
- `watch_daemon.py` - Real-time file monitoring
- `cleanup_protondrive.py` - Duplicate removal

### content_tools/
- `social_poster.py` - Platform API posting
- `image_optimizer.py` - Resize, compress, watermark
- `video_clipper.py` - Extract highlights from streams
- `caption_generator.py` - AI caption variations

### business_ops/
- `pos_backup.py` - Daily OnyxPOS snapshots
- `payroll_processor.py` - Automated payroll calculations
- `invoice_generator.py` - PDF invoice creation
- `revenue_tracker.py` - MRR/ARR calculations

### ai_workers/
- `gpt_router.py` - GPT API with retry logic
- `claude_engineer.py` - Claude Code integration
- `perplexity_scout.py` - Real-time research
- `codex_executor.py` - Code generation

## 02_Config

**YAML configuration files**

- `business_profiles.yaml` - Brand tone, CTAs, platforms
- `content_templates.yaml` - Post templates per platform
- `platform_configs.yaml` - API endpoints, rate limits
- `ai_prompts.yaml` - Prompt templates for each AI

## 03_Credentials

**Encrypted vault (GPG AES256)**

ALL sensitive data stored here:
- API keys (GPT, Claude, Perplexity, etc.)
- OAuth tokens (Google, Meta, TikTok, Discord)
- Database passwords (POS system)
- Crypto seed phrases (hardware wallet backup only)
- Payment keys (Stripe, Coinbase Commerce)

See: `03_Credentials/README.md` for usage.

## 04_Logs

**Audit trail & debugging**

- `system/` - File ops, sync status, cron jobs
- `errors/` - Failed operations, retries
- `audit/` - Security events, credential access

Logs rotate daily. Kept for 30 days.

## AI Worker Roles

**GPT (Thor)** - Fast operator
- Slack routing, quick answers
- Caption generation, summaries
- Data transformations

**Claude Code** - Deep engineer
- POS feature development
- Complex refactoring
- Architecture decisions

**Perplexity** - Live scout
- Market research
- Trending topics
- Competitor analysis

**Codex** - Quick executor
- Script generation
- Batch file ops
- Template rendering

## Running the System

### Start automation
```bash
# File organizer watch mode
python3 01_Scripts/file_organizer/watch_daemon.py &

# n8n (if self-hosted)
n8n start &

# Streamlit dashboard
streamlit run 09_DASHBOARD/streamlit_app/app.py &
```

### Check status
```bash
python3 01_Scripts/file_organizer/sync_manager.py --status
```

### Manual operations
```bash
# Organize downloads
python3 01_Scripts/file_organizer/organize_files.py

# Sync to Proton Drive
python3 01_Scripts/file_organizer/sync_manager.py

# Generate analytics report
python3 01_Scripts/business_ops/analytics_report.py
```

## Security

- All credentials encrypted with GPG
- Scripts read from encrypted vault at runtime
- No plaintext secrets in git repos
- Weekly security audits via n8n
- Logs sanitized (no secrets logged)

## Energy Efficiency

- Scheduled tasks via cron (not constant polling)
- Background services only when needed
- Dex mode reduces phone battery drain
- Solar charging compatible
