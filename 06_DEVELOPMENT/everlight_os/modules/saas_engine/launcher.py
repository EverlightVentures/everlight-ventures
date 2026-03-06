"""
SaaS Factory — Go-to-market pack writer. STUB — Phase 2.
"""

from pathlib import Path
from ...core.filesystem import write_text


def write_launch_pack(scope: dict, project_dir: Path) -> str:
    launch_dir = project_dir / "launch"
    launch_dir.mkdir(exist_ok=True)
    stub = f"# {scope.get('product_name', 'Product')} — [STUB] Phase 2 expansion needed.\n"
    for fname in [
        "landing_page_copy.md", "pricing.md", "onboarding_email_sequence.md",
        "affiliate_program_plan.md", "seedance_prompts.txt", "socials.md",
    ]:
        write_text(launch_dir / fname, stub)
    return str(launch_dir / "landing_page_copy.md")
