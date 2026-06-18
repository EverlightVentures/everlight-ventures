"""
Shared markdown parsing/stripping utilities for the publishing pipeline.

Consolidates duplicated functions from:
  - build_books.py::strip_md, parse_md
  - build_audiobooks.py::clean_for_narration
"""

import re
from typing import List, Tuple


# Metadata prefixes to skip when parsing book manuscripts
SKIP_PREFIXES = (
    "**Document Status:",
    "**Date:",
    "**Format:",
    "**Page Layout:",
    "**Phonics Focus:",
    "**Core Value:",
    "**CASEL",
    "**CCSS",
    "**Superpower Unlocked:",
    "**Target Age:",
    "**Series Position:",
)

# Regex patterns for metadata lines (used in narration cleaning)
METADATA_PATTERNS = [
    r"^\*\*Document Status:.*$",
    r"^\*\*Date:.*$",
    r"^\*\*Format:.*$",
    r"^\*\*Page Layout:.*$",
    r"^\*\*Phonics Focus:.*$",
    r"^\*\*Core Value:.*$",
    r"^\*\*CASEL.*$",
    r"^\*\*CCSS.*$",
    r"^\*\*Superpower Unlocked:.*$",
    r"^\*\*Target Age:.*$",
    r"^\*\*Series Position:.*$",
    r"^End of Master Manuscript.*$",
    r"^Next steps:.*$",
    r"^\> \[ASSISTANT NOTE.*$",
]


def strip_md(text: str) -> str:
    """Remove markdown bold/italic formatting from text."""
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    return text


def clean_for_narration(text: str) -> str:
    """Strip markdown, images, metadata for TTS narration."""
    # Remove image references
    text = re.sub(r"!\[[^\]]*\]\([^\)]*\)", "", text)
    # Remove horizontal rules
    text = re.sub(r"^---+\s*$", "", text, flags=re.MULTILINE)
    # Remove markdown headers (keep the text)
    text = re.sub(r"^#{1,4}\s+", "", text, flags=re.MULTILINE)
    # Convert bold/italic to plain
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    # Remove metadata lines
    for pat in METADATA_PATTERNS:
        text = re.sub(pat, "", text, flags=re.MULTILINE)
    # Clean up multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_md(md_path: str) -> List[dict]:
    """Parse a MASTER.md manuscript into structured blocks.

    Returns list of dicts with keys: type, content, image (optional).
    Types: chapter_title, section_title, image_color, image_bw,
           interactive, qa, text.
    """
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    blocks: List[dict] = []
    i = 0
    in_back_matter = False

    while i < len(lines):
        line = lines[i].rstrip("\n")
        if not line.strip():
            i += 1
            continue
        if line.strip() == "---":
            i += 1
            continue

        img_match = re.match(r"!\[([^\]]+)\]\(images/([^\)]+)\)", line.strip())
        if img_match:
            filename = img_match.group(2)
            btype = "image_bw" if "_bw" in filename else "image_color"
            blocks.append({"type": btype, "content": "", "image": filename})
            i += 1
            continue

        if line.startswith("## CHAPTER"):
            blocks.append({"type": "chapter_title", "content": line.lstrip("# ").strip()})
            i += 1
            continue

        if line.startswith("## BACK MATTER"):
            in_back_matter = True
            i += 1
            continue

        if line.startswith("### ") and in_back_matter:
            blocks.append({"type": "section_title", "content": line.lstrip("# ").strip()})
            i += 1
            continue

        if line.startswith("## "):
            blocks.append({"type": "section_title", "content": line.lstrip("# ").strip()})
            i += 1
            continue

        if line.startswith("**Interactive Moment:**"):
            blocks.append({"type": "interactive", "content": line.replace("**Interactive Moment:**", "").strip()})
            i += 1
            continue

        if line.startswith("**Question:**"):
            q = line.replace("**Question:**", "").strip()
            a = ""
            if i + 1 < len(lines) and lines[i + 1].startswith("**Answer:**"):
                a = lines[i + 1].replace("**Answer:**", "").strip()
                i += 1
            blocks.append({"type": "qa", "content": f"Q: {q}\nA: {a}"})
            i += 1
            continue

        if line.startswith("# Sam") or line.startswith("### Everlight"):
            i += 1
            continue
        if any(line.startswith(p) for p in SKIP_PREFIXES):
            i += 1
            continue
        if line.startswith("End of Master Manuscript") or line.startswith("Next steps:"):
            i += 1
            continue

        blocks.append({"type": "text", "content": line.strip()})
        i += 1

    return blocks


def extract_chapters_from_md(md_path: str) -> List[Tuple[str, str]]:
    """Parse MASTER.md into (title, narration_text) chapter pairs for audiobook."""
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    chapter_pattern = re.compile(
        r"(?:^|\n)(?:#{1,3}\s+)?(CHAPTER \d+[:\s].*?|SERIES RECAP.*?|BACK MATTER.*?|THE LEARNING CORNER.*?|THE VALUES MOMENT.*?)(?:\n|$)",
        re.IGNORECASE,
    )

    sections: List[Tuple[str, str]] = []
    matches = list(chapter_pattern.finditer(content))

    if not matches:
        sections.append(("Full Story", clean_for_narration(content)))
    else:
        first_match_pos = matches[0].start()
        intro = content[:first_match_pos].strip()
        if intro and len(intro) > 100:
            cleaned_intro = clean_for_narration(intro)
            if cleaned_intro:
                sections.append(("Introduction", cleaned_intro))

        for i, m in enumerate(matches):
            title = m.group(1).strip()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            section_text = content[start:end]
            cleaned = clean_for_narration(section_text)

            if len(cleaned) < 50:
                continue

            # Convert interactive moments for narration
            cleaned = re.sub(
                r"Interactive Moment:\s*",
                "Here's an interactive moment for you! ",
                cleaned,
            )
            cleaned = re.sub(r"Question:\s*", "Here's a question to think about: ", cleaned)
            cleaned = re.sub(r"Answer:\s*", "The answer is: ", cleaned)

            sections.append((title, cleaned))

    return sections
