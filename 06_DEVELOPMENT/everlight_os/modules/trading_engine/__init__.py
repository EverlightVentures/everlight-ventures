"""
Trading Engine — XLM Derivatives Co-Pilot.
Reads bot logs, detects anomalies, generates reports, proposes changes.
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...core.orchestrator import Orchestrator
    from ...core.contracts import ProjectState


def register_handlers(orch):
    """Register trading engine step handlers with the orchestrator."""
    from . import analyzer
    from . import anomaly_detector
    from . import report_generator

    def _get_slack():
        from ...core.slack_client import get_client
        return get_client()

    def handle_parse_logs(state, step: dict, project_dir: Path) -> str:
        """Step 1: Read and analyze all xlm_bot logs."""
        analysis = analyzer.full_analysis(lookback_hours=24)
        state.metadata["analysis"] = analysis
        return ""

    def handle_compute_metrics(state, step: dict, project_dir: Path) -> str:
        """Step 2: Metrics already computed in analysis — pass-through."""
        return ""

    def handle_detect_anomalies(state, step: dict, project_dir: Path) -> str:
        """Step 3: Run anomaly detection on the analysis."""
        analysis = state.metadata.get("analysis", {})
        anomalies = anomaly_detector.detect_anomalies(analysis)
        state.metadata["anomalies"] = anomalies
        return ""

    def handle_generate_report(state, step: dict, project_dir: Path) -> str:
        """Step 4: Generate the daily report with AI commentary."""
        analysis = state.metadata.get("analysis", {})
        anomalies = state.metadata.get("anomalies", [])
        result = report_generator.generate_daily_report(analysis, anomalies)
        state.metadata["report_result"] = result
        return result.get("daily_report", "")

    def handle_post_to_slack(state, step: dict, project_dir: Path) -> str:
        """Step 5: Post report summary to Slack."""
        analysis = state.metadata.get("analysis", {})
        anomalies = state.metadata.get("anomalies", [])
        report_result = state.metadata.get("report_result", {})
        report_dir = report_result.get("report_dir", str(project_dir))

        summary = report_generator.format_slack_summary(analysis, anomalies, report_dir)
        slack = _get_slack()
        slack.post_report("XLM Bot Daily Report", summary)
        return ""

    def handle_read_state(state, step: dict, project_dir: Path) -> str:
        """Quick status: just read current state and post."""
        bot_state = analyzer.read_state()
        snapshot = analyzer.read_snapshot()

        lines = [
            "*XLM Bot Status*",
            f"*Equity:* ${bot_state.get('equity_start_usd', 0):.2f}",
            f"*PnL today:* ${bot_state.get('pnl_today_usd', 0):.2f}",
            f"*Position:* {'OPEN (' + str(bot_state.get('open_position', {}).get('direction', '?')) + ')' if bot_state.get('open_position') else 'FLAT'}",
            f"*Trades:* {bot_state.get('trades', 0)} | *Losses:* {bot_state.get('losses', 0)}",
            f"*Vol:* {bot_state.get('vol_state', '?')}",
            f"*Regime:* {snapshot.get('regime', '?')}",
            f"*Last cycle:* {bot_state.get('last_cycle_ts', '?')}",
        ]
        state.metadata["status_text"] = "\n".join(lines)
        slack = _get_slack()
        slack.post_report("XLM Bot Status", "\n".join(lines))
        return ""

    orch.register_handler("trading", "parse_logs", handle_parse_logs)
    orch.register_handler("trading", "compute_metrics", handle_compute_metrics)
    orch.register_handler("trading", "detect_anomalies", handle_detect_anomalies)
    orch.register_handler("trading", "generate_report", handle_generate_report)
    orch.register_handler("trading", "post_to_slack", handle_post_to_slack)
    orch.register_handler("trading", "read_state", handle_read_state)
