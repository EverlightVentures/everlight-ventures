"""
Content Engine — Search → Monetize → Publish Pack.
Turns any topic into a complete content bundle.
"""

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...core.orchestrator import Orchestrator
    from ...core.contracts import ProjectState


def register_handlers(orch):
    """Register content engine step handlers with the orchestrator."""
    from . import researcher
    from . import outliner
    from . import drafter
    from . import seo_optimizer
    from . import monetizer
    from . import quality_gate

    def _get_slack():
        from ...core.slack_client import get_client
        return get_client()

    def handle_research(state, step: dict, project_dir: Path) -> str:
        """Step 1: Research the topic using Perplexity."""
        topic = state.metadata.get("topic", state.request)
        url = state.metadata.get("url")
        packet = researcher.research_topic(topic, state.intent, url=url, project_dir=project_dir)
        state.metadata["research"] = packet
        return str(project_dir / "research_packet.json")

    def handle_outline(state, step: dict, project_dir: Path) -> str:
        """Step 2: Create structured outline from template + research."""
        topic = state.metadata.get("topic", state.request)
        research = state.metadata.get("research", {})
        outline_text = outliner.create_outline(topic, state.intent, research, project_dir)
        state.metadata["outline"] = outline_text
        return str(project_dir / "outline.md")

    def handle_draft(state, step: dict, project_dir: Path) -> str:
        """Step 3: Draft blog, socials, email, video script."""
        topic = state.metadata.get("topic", state.request)
        outline_text = state.metadata.get("outline", "")
        research = state.metadata.get("research", {})
        paths = drafter.draft_all(topic, state.intent, outline_text, research, project_dir)
        state.metadata["draft_paths"] = paths
        return paths.get("blog", "")

    def handle_seo(state, step: dict, project_dir: Path) -> str:
        """Step 4: Generate SEO optimization pack."""
        topic = state.metadata.get("topic", state.request)
        blog = ""
        blog_path = project_dir / "blog.md"
        if blog_path.exists():
            blog = blog_path.read_text()
        seo_data = seo_optimizer.optimize_seo(topic, state.intent, blog, project_dir)
        state.metadata["seo"] = seo_data
        return str(project_dir / "seo.json")

    def handle_monetize(state, step: dict, project_dir: Path) -> str:
        """Step 5: Generate monetization plan."""
        topic = state.metadata.get("topic", state.request)
        blog = ""
        blog_path = project_dir / "blog.md"
        if blog_path.exists():
            blog = blog_path.read_text()
        monetizer.generate_monetization(topic, state.intent, blog, project_dir)
        return str(project_dir / "monetization.md")

    def handle_quality_gate(state, step: dict, project_dir: Path) -> str:
        """Step 6: Run quality checks."""
        topic = state.metadata.get("topic", state.request)
        result = quality_gate.run_quality_gate(topic, project_dir)
        state.metadata["quality"] = result
        return result.get("checklist_path", "")

    def handle_post_to_slack(state, step: dict, project_dir: Path) -> str:
        """Step 7: Post preview + approval to Slack."""
        topic = state.metadata.get("topic", state.request)
        quality = state.metadata.get("quality", {})
        seo = state.metadata.get("seo", {})

        status = "READY" if quality.get("all_pass") else "NEEDS REVIEW"
        checks = quality.get("checks", [])
        passed = sum(1 for c in checks if c.get("pass"))

        # Build content pack manifest
        manifest = {
            "topic": topic,
            "intent": state.intent,
            "project_id": state.id,
            "status": status,
            "quality_score": next((c.get("score") for c in checks if c.get("name") == "ai_quality_review"), None),
            "seo_title": seo.get("title_tag", ""),
            "primary_keyword": seo.get("primary_keyword", ""),
            "artifacts": state.artifacts,
            "project_dir": str(project_dir),
        }
        from ...core.filesystem import write_json
        write_json(project_dir / "content_pack.json", manifest)

        # Slack summary
        summary = f"""*Content Pack — {topic}*

*Status:* {status} ({passed}/{len(checks)} checks passed)
*Type:* {state.intent}
*SEO Title:* {seo.get('title_tag', 'N/A')}
*Keyword:* {seo.get('primary_keyword', 'N/A')}

*Files created:*
- blog.md
- socials.md ({5} platform posts)
- email.md
- video_script.md
- seo.json
- monetization.md
- image_prompts.txt
- seedance_prompts.txt
- publish_checklist.md

_Output: `{project_dir}`_"""

        slack = _get_slack()
        slack.post_approval(state.id, summary, "content")
        return str(project_dir / "content_pack.json")

    # Register all handlers
    orch.register_handler("content", "research", handle_research)
    orch.register_handler("content", "outline", handle_outline)
    orch.register_handler("content", "draft", handle_draft)
    orch.register_handler("content", "seo", handle_seo)
    orch.register_handler("content", "monetize", handle_monetize)
    orch.register_handler("content", "quality_gate", handle_quality_gate)
    orch.register_handler("content", "post_to_slack", handle_post_to_slack)
