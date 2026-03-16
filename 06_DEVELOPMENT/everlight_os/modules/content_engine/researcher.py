"""
Content Engine — Research step.
Uses Perplexity API to gather facts, sources, and key points on a topic.
"""

import json
from pathlib import Path
from ...core.ai_worker import call_perplexity
from ...core.filesystem import write_json, write_text


def research_topic(topic: str, intent: str, url: str = None, project_dir: Path = None) -> dict:
    """
    Research a topic using Perplexity.
    Returns research packet dict and saves to project_dir if provided.
    """
    query = _build_research_query(topic, intent, url)
    raw = call_perplexity(query)

    packet = {
        "topic": topic,
        "intent": intent,
        "url": url,
        "raw_research": raw,
    }

    # Parse structured data from the research
    structured = _extract_structured(raw, topic)
    packet.update(structured)

    if project_dir:
        write_json(project_dir / "research_packet.json", packet)
        write_text(project_dir / "sources.md", _format_sources(packet))

    return packet


def _build_research_query(topic: str, intent: str, url: str = None) -> str:
    """Build the research query based on intent type."""
    base = f"Research this topic thoroughly: {topic}\n\n"

    if intent == "howto":
        base += "Focus on: step-by-step instructions, common mistakes, tools needed, prerequisites, best practices."
    elif intent == "comparison":
        base += "Focus on: key differences, pros/cons of each option, pricing, use cases, who each is best for."
    elif intent == "news":
        base += "Focus on: what happened, when, who's involved, impact, what's next, reactions."
    elif intent == "listicle":
        base += "Focus on: comprehensive list of options/items, brief description of each, key features, pricing if applicable."
    else:  # explainer
        base += "Focus on: clear explanation, history, how it works, why it matters, examples, common misconceptions."

    if url:
        base += f"\n\nAlso reference this URL for additional context: {url}"

    base += "\n\nProvide specific facts, numbers, and cite your sources."
    return base


def _extract_structured(raw: str, topic: str) -> dict:
    """Extract structured data from raw research text."""
    # Simple extraction — key points and sources
    lines = raw.split("\n")
    key_points = []
    sources = []

    in_sources = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "source" in line.lower() or "reference" in line.lower() or "citation" in line.lower():
            in_sources = True
            continue
        if in_sources and (line.startswith("http") or line[0].isdigit()):
            sources.append(line)
        elif line.startswith(("-", "*", "•")) and not in_sources:
            key_points.append(line.lstrip("-*• "))

    return {
        "key_points": key_points[:15],
        "sources": sources[:10],
    }


def _format_sources(packet: dict) -> str:
    """Format sources as markdown."""
    lines = [f"# Sources — {packet['topic']}", ""]
    sources = packet.get("sources", [])
    if sources:
        for i, s in enumerate(sources, 1):
            lines.append(f"{i}. {s}")
    else:
        lines.append("*Sources embedded in research packet*")
    return "\n".join(lines)
