"""
Books Engine — Multi-Series Factory.
Idea → Series Bible → Outline → Manuscript → Illustrations → KDP → Launch Pack.
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...core.orchestrator import Orchestrator
    from ...core.contracts import ProjectState


def register_handlers(orch):
    """Register books engine step handlers with the orchestrator."""
    from . import series_manager
    from . import outliner
    from . import manuscript_writer
    from . import illustration_gen
    from . import kdp_packager
    from . import launch_planner

    def _get_slack():
        from ...core.slack_client import get_client
        return get_client()

    def handle_series_bible(state, step: dict, project_dir: Path) -> str:
        """Step 1: Load or create series bible."""
        series = state.metadata.get("series", "adventures_with_sam")
        bible = series_manager.get_or_create_bible(series, project_dir)
        state.metadata["series_bible"] = bible
        return str(project_dir / "series_bible.md")

    def handle_outline(state, step: dict, project_dir: Path) -> str:
        """Step 2: Create book outline."""
        title = state.metadata.get("title", state.request)
        bible = state.metadata.get("series_bible", "")
        outline_text = outliner.create_book_outline(title, bible, project_dir)
        state.metadata["outline"] = outline_text
        return str(project_dir / "outline.md")

    def handle_manuscript(state, step: dict, project_dir: Path) -> str:
        """Step 3: Draft full manuscript."""
        title = state.metadata.get("title", state.request)
        outline_text = state.metadata.get("outline", "")
        bible = state.metadata.get("series_bible", "")
        manuscript = manuscript_writer.write_manuscript(title, outline_text, bible, project_dir)
        state.metadata["manuscript"] = manuscript
        return str(project_dir / "manuscript.md")

    def handle_illustrations(state, step: dict, project_dir: Path) -> str:
        """Step 4: Generate illustration + coloring page prompts."""
        title = state.metadata.get("title", state.request)
        manuscript = state.metadata.get("manuscript", "")
        bible = state.metadata.get("series_bible", "")
        paths = illustration_gen.generate_illustration_prompts(title, manuscript, bible, project_dir)
        state.metadata["illustration_paths"] = paths
        return paths.get("cover", "")

    def handle_kdp_metadata(state, step: dict, project_dir: Path) -> str:
        """Step 5: Generate KDP metadata."""
        title = state.metadata.get("title", state.request)
        outline_text = state.metadata.get("outline", "")
        series = state.metadata.get("series", "adventures_with_sam")
        metadata = kdp_packager.generate_kdp_metadata(title, outline_text, series, project_dir)
        state.metadata["kdp_metadata"] = metadata
        return str(project_dir / "kdp_metadata.json")

    def handle_launch_pack(state, step: dict, project_dir: Path) -> str:
        """Step 6: Create launch content pack."""
        title = state.metadata.get("title", state.request)
        metadata = state.metadata.get("kdp_metadata", {})
        outline_text = state.metadata.get("outline", "")
        paths = launch_planner.create_launch_pack(title, metadata, outline_text, project_dir)
        state.metadata["launch_paths"] = paths
        return paths.get("socials", "")

    def handle_post_to_slack(state, step: dict, project_dir: Path) -> str:
        """Step 7: Post book summary + approval to Slack."""
        title = state.metadata.get("title", state.request)
        metadata = state.metadata.get("kdp_metadata", {})

        summary = f"""*New Book Ready — {metadata.get('title', title)}*

*Series:* {metadata.get('series_name', 'Adventures with Sam')}
*Age range:* {metadata.get('age_range', '4-8')}
*Pages:* {metadata.get('page_count', '~28')}

*Files created:*
- series_bible.md
- outline.md
- manuscript.md
- illustration_prompts.txt
- coloring_page_prompts.txt
- cover_prompt.txt
- kdp_metadata.json
- launch_socials.md
- launch_email.md
- video_script.md
- seedance_prompts.txt

_Output: `{project_dir}`_"""

        slack = _get_slack()
        slack.post_approval(state.id, summary, "books")
        return ""

    # Register all handlers
    orch.register_handler("books", "series_bible", handle_series_bible)
    orch.register_handler("books", "outline", handle_outline)
    orch.register_handler("books", "manuscript", handle_manuscript)
    orch.register_handler("books", "illustrations", handle_illustrations)
    orch.register_handler("books", "kdp_metadata", handle_kdp_metadata)
    orch.register_handler("books", "launch_pack", handle_launch_pack)
    orch.register_handler("books", "post_to_slack", handle_post_to_slack)
