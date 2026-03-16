#!/usr/bin/env python3
"""Example Slack logger usage for one task lifecycle."""

from everlight_os.slack_org.logger import SlackLogger


def main() -> None:
    logger = SlackLogger()

    task_obj = {
        "task_id": "launch-book-004",
        "parent_task_id": None,
        "task_type": "book_launch",
        "priority": "high",
        "status": "running",
        "owner_agent": "agent-book-showrunner",
        "assigned_llm": "claude",
        "requested_by": "user",
        "title": "Launch Sam Book 4 campaign",
        "objective": "Prepare and release launch assets for Amazon listing + social + affiliate tie-in",
        "blockers": ["Awaiting final cover image"],
        "delegations": [
            {
                "to_agent": "agent-seo-keywords",
                "reason": "keyword mapping needed before listing finalization",
                "status": "sent",
            }
        ],
        "next_action": "Finalize listing after keyword map and cover approval",
        "risk_level": "medium",
        "eta": "2h",
    }

    logger.post_agent_log(
        channel="book_team.book_showrunner",
        task_obj=task_obj,
        actions=[
            "Built launch brief and assigned specialists",
            "Prepared first draft of listing strategy",
            "Queued social copy variants",
        ],
        decisions=[
            "Use unified launch packet with per-platform copy variants",
            "Hold final listing publish until cover image arrives",
        ],
        blockers=task_obj["blockers"],
        artifacts=[
            "/outputs/launches/book-004/listing_strategy_v2.md",
            "/outputs/launches/book-004/social_posts_pack.md",
        ],
    )

    logger.post_war_room_update(
        task_obj=task_obj,
        summary="Kickoff complete, delegation sent, draft assets in progress.",
    )

    logger.post_approval_request(
        channel="shared_ops.approvals",
        payload={
            "agent_slug": "agent-book-showrunner",
            "task_id": "launch-book-004",
            "decision_needed": "Approve final campaign angle for listing and social",
            "option_1": "Mystery adventure emphasis",
            "option_2": "Educational blends emphasis",
            "recommended_option": "Mystery adventure emphasis",
            "impact_note": "Faster launch and stronger conversion likelihood",
            "deadline": "2026-02-25T10:00:00-08:00",
        },
    )


if __name__ == "__main__":
    main()

