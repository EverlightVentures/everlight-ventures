# XLM Bot Reliability Test Plan

## Objective
Verify the robustness of the "Institutional-Grade" hardening updates, focusing on risk gates, circuit breakers, and operational stability.

## 1. Risk Gate Verification (Unit Tests)
- [ ] **Daily Loss Cap**: Verify that `max_daily_loss_pct` correctly blocks entries when reached.
- [ ] **AI Override Immunity**: Ensure AI executive mode cannot bypass the hard daily loss cap.
- [ ] **Safe Mode Persistence**: Verify `SAFE_MODE` blocks entries regardless of signal quality.
- [ ] **P&L Source Fallback**: Verify logic correctly switches between `exchange_pnl_today_usd` and `pnl_today_usd`.

## 2. Circuit Breaker Escalation (Integration/Shell Tests)
- [ ] **Tier 1 (SOFT_HALT)**: Verify 3 losses trigger `.cb_soft_halt` and update `state.json`.
- [ ] **Tier 2 (EMERGENCY)**: Verify 5 losses trigger `.cb_emergency` and signal an emergency exit.
- [ ] **Tier 3 (KILL)**: Verify 7 losses/3 tracebacks trigger `.circuit_breaker` and stop the `systemd` service.
- [ ] **Watchdog Protection**: Ensure `watchdog.sh` does NOT restart the bot if `.circuit_breaker` exists.

## 3. Resource Management
- [ ] **Log Rotation**: Verify `log_rotate.sh` trims logs when thresholds (50k lines) are hit.
- [ ] **Memory Guard**: Verify `memory_guard.sh` kills non-essential services (dashboard/ws) under RAM pressure.
- [ ] **Disk Guard**: Verify emergency rotation triggers at 88% disk usage.

## 4. Acceptance Criteria (V1 Gate)
- **Target Win Rate**: > 55%
- **Max Drawdown**: < 15% of equity (Hard Cap)
- **Service Uptime**: > 99.5% (Watchdog managed)
- **Fill Quality**: Slippage < 0.2% on average.

## 5. Manual Verification Steps
1. Deploy to staging/paper.
2. Manually inject a large loss into `trades.csv`.
3. Verify `circuit_breaker.sh` detects it and creates the appropriate T1/T2/T3 files.
4. Verify Slack alerts are received for each tier.
