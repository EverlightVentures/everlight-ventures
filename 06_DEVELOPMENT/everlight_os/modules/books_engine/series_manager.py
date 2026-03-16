"""
Books Engine — Series manager.
Loads/creates series bibles, maintains character continuity.
"""

from pathlib import Path
from ...core.ai_worker import call_openai
from ...core.filesystem import write_text, read_text

EXISTING_BOOKS_PATH = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Publishing/Ebook_Sells/ADVENTURES_WITH_SAM")

# Known series info (from existing books)
SERIES_INFO = {
    "adventures_with_sam": {
        "title": "Adventures with Sam",
        "characters": {
            "Sam": "A curious, brave young kid who discovers superpowers. Each book reveals a new superpower connected to emotional intelligence and life skills.",
            "Robo": "Sam's robot companion. Loyal, helpful, and sometimes clumsy. Provides comic relief and asks questions that help Sam (and the reader) learn.",
        },
        "themes": [
            "Emotional intelligence",
            "Life skills through adventure",
            "Friendship and teamwork",
            "Problem solving",
        ],
        "visual_style": "Vibrant, colorful, kid-friendly digital art. Characters have expressive faces and dynamic poses.",
        "age_range": "4-8 years",
        "existing_books": [
            "Sam's First Superpower (Book 1)",
            "Sam's Second Superpower (Book 2)",
            "Sam's Third Superpower (Book 3)",
            "Sam's 4th Superpower (Book 4)",
        ],
        "format": "Picture book, ~24-32 pages, large illustrations with short text per page",
    },
    "sam_and_luna": {
        "title": "Adventures with Sam and Luna",
        "characters": {
            "Sam": "Same Sam from Adventures with Sam, slightly older.",
            "Luna": "A new friend with her own unique abilities. Complements Sam's strengths.",
        },
        "themes": ["Collaboration", "New friendships", "Combined strengths"],
        "visual_style": "Same vibrant style as Adventures with Sam",
        "age_range": "4-8 years",
        "existing_books": [],
        "format": "Picture book, ~24-32 pages",
    },
}


def get_or_create_bible(series: str, project_dir: Path) -> str:
    """
    Load existing series bible or create one.
    Returns the bible text.
    """
    bible_path = project_dir / "series_bible.md"
    if bible_path.exists():
        return read_text(bible_path)

    info = SERIES_INFO.get(series, SERIES_INFO["adventures_with_sam"])

    # Check if there's a bible in the series root
    series_root = Path("/mnt/sdcard/AA_MY_DRIVE/books") / series
    root_bible = series_root / "series_bible.md"
    if root_bible.exists():
        bible = read_text(root_bible)
        write_text(bible_path, bible)
        return bible

    # Generate new bible from known info
    bible = _generate_bible(info)
    write_text(bible_path, bible)

    # Also save to series root for future books
    series_root.mkdir(parents=True, exist_ok=True)
    write_text(root_bible, bible)

    return bible


def _generate_bible(info: dict) -> str:
    """Generate a series bible from known series info."""
    chars = "\n".join(f"- **{name}**: {desc}" for name, desc in info["characters"].items())
    themes = "\n".join(f"- {t}" for t in info["themes"])
    books = "\n".join(f"- {b}" for b in info["existing_books"]) if info["existing_books"] else "- None yet"

    prompt = f"""Create a detailed children's book series bible.

Series: {info['title']}
Age range: {info['age_range']}
Format: {info['format']}

Characters:
{chars}

Core themes:
{themes}

Existing books:
{books}

Visual style: {info['visual_style']}

Create a comprehensive series bible that includes:
1. Series overview and mission
2. Character profiles (personality, appearance, speech patterns, quirks)
3. World rules (what's possible, what's not)
4. Visual style guide (color palette, character proportions, backgrounds)
5. Story structure template (how each book should flow)
6. Tone guide (vocabulary level, humor style, emotional beats)
7. Continuity notes (what readers should recognize across books)

Write in markdown format. Be specific enough that any illustrator or writer could maintain consistency."""

    system = "You are a children's book series developer. Create detailed, practical series bibles."
    return call_openai(prompt, system=system, temperature=0.6, max_tokens=3000)
