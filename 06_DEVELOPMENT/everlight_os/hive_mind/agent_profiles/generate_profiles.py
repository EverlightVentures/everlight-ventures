"""
Agent Profile Generator -- Creates full identity packages for all Hive agents.

Generates:
  - Agent profile JSON (name, title, bio, contact info, skills)
  - vCard (.vcf) files for digital business cards
  - Profile page data for everlightventures.io/team/[slug]
  - Headshot prompts for AI image generation

Run: python3 generate_profiles.py
"""
import json
import os
import re
import sys
from pathlib import Path

# Load roster
ROSTER_PATH = Path(__file__).parent.parent / "roster.yaml"
PROFILES_DIR = Path(__file__).parent
SITE_DIR = Path(__file__).parent.parent.parent.parent / "everlightventures" / "src" / "pages" / "team"

try:
    import yaml
    roster = yaml.safe_load(ROSTER_PATH.read_text())
except ImportError:
    print("PyYAML required: pip install pyyaml")
    sys.exit(1)


def extract_agents(data):
    """Recursively extract all agents from roster YAML."""
    agents = []
    if isinstance(data, dict):
        if "name" in data and isinstance(data.get("name"), str):
            agents.append(data)
        for v in data.values():
            agents.extend(extract_agents(v))
    elif isinstance(data, list):
        for item in data:
            agents.extend(extract_agents(item))
    return agents


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def generate_bio(agent):
    """Generate a professional bio from agent personality and role."""
    name = agent.get("name", "Agent")
    personality = agent.get("personality", [])
    role_id = agent.get("id", "")

    # Map role IDs to titles
    title_map = {
        "chief_of_staff": "Chief of Staff",
        "28_deal_scout": "Deal Scout",
        "29_lead_qualifier": "Lead Qualification Analyst",
        "30_match_maker": "Matchmaking Specialist",
        "31_outreach_agent": "Outreach Specialist",
        "32_deal_closer": "Deal Closer",
        "33_commission_auditor": "Commission Auditor",
        "34_compliance_gate": "Compliance Officer",
        "36_rex_wholesale": "Wholesale Operations Lead",
        "37_ace_deal_marketer": "Deal Marketing Specialist",
        "27_profit_maximizer": "P&L Analyst",
        "everlight_trading_risk": "Trading Risk Strategist",
        "51_prospect_scraper": "Prospect Research Analyst",
        "52_client_deployer": "Client Success Manager",
    }

    title = title_map.get(role_id, "Operations Specialist")
    traits = ", ".join(personality[:3]) if personality else "dedicated, detail-oriented"

    bio = (
        f"{name} is a {title} at Everlight Ventures, "
        f"known for being {traits}. "
        f"Specializing in AI-powered business automation, {name.split()[0]} "
        f"helps clients and partners achieve measurable results through "
        f"intelligent systems and data-driven strategies."
    )
    return title, bio


def generate_headshot_prompt(agent):
    """Generate a prompt for AI headshot generation."""
    name = agent.get("name", "Agent")
    personality = agent.get("personality", [])

    # Infer appearance cues from name/personality
    style = "professional corporate headshot, studio lighting, neutral background"
    if "warm" in personality or "personable" in personality:
        style += ", warm smile, approachable"
    elif "no-bs" in personality or "sharp" in personality:
        style += ", confident expression, direct gaze"
    elif "by-the-book" in personality:
        style += ", serious expression, professional demeanor"
    else:
        style += ", friendly professional expression"

    return f"Professional headshot of {name}, {style}, high quality portrait photo, 512x512"


def generate_vcard(agent, title):
    """Generate a vCard (.vcf) file for the agent."""
    name = agent.get("name", "Agent")
    email = agent.get("email", "")
    parts = name.split()
    first = parts[0] if parts else name
    last = parts[-1] if len(parts) > 1 else ""
    slug = slugify(name)

    vcard = f"""BEGIN:VCARD
VERSION:3.0
FN:{name}
N:{last};{first};;;
ORG:Everlight Ventures
TITLE:{title}
EMAIL;TYPE=WORK:{email}
URL:https://everlightventures.io/team/{slug}
NOTE:AI-Powered Operations | Everlight Ventures
END:VCARD"""
    return vcard


def generate_profile(agent):
    """Generate complete agent profile."""
    name = agent.get("name", "Agent")
    slug = slugify(name)
    email = agent.get("email", "")
    voice_id = agent.get("voice_id", "")
    personality = agent.get("personality", [])
    title, bio = generate_bio(agent)
    headshot_prompt = generate_headshot_prompt(agent)
    vcard = generate_vcard(agent, title)

    profile = {
        "name": name,
        "slug": slug,
        "title": title,
        "email": email,
        "phone": "",  # To be assigned
        "voice_id": voice_id,
        "has_voice": bool(voice_id),
        "bio": bio,
        "personality": personality,
        "headshot_prompt": headshot_prompt,
        "headshot_url": f"/team/photos/{slug}.jpg",
        "booking_url": f"https://cal.everlightventures.io/{slug}",
        "vcard_url": f"/team/vcards/{slug}.vcf",
        "profile_url": f"https://everlightventures.io/team/{slug}",
        "linkedin_url": "",
        "skills": personality[:5],
        "department": "",
        "role_id": agent.get("id", ""),
    }

    return profile, vcard


def main():
    all_agents = extract_agents(roster)

    # Deduplicate by name
    seen = set()
    unique = []
    for a in all_agents:
        if a["name"] not in seen:
            seen.add(a["name"])
            unique.append(a)

    print(f"Processing {len(unique)} agents...")

    profiles = []
    vcards_dir = PROFILES_DIR / "vcards"
    vcards_dir.mkdir(exist_ok=True)

    for agent in unique:
        profile, vcard = generate_profile(agent)
        profiles.append(profile)

        # Save individual vCard
        vcard_path = vcards_dir / f"{profile['slug']}.vcf"
        vcard_path.write_text(vcard)

    # Save master profiles JSON
    master_path = PROFILES_DIR / "all_profiles.json"
    master_path.write_text(json.dumps(profiles, indent=2))
    print(f"Saved {len(profiles)} profiles to {master_path}")
    print(f"Saved {len(profiles)} vCards to {vcards_dir}")

    # Print summary
    with_voice = sum(1 for p in profiles if p["has_voice"])
    with_email = sum(1 for p in profiles if p["email"])
    print(f"\nSummary:")
    print(f"  Total agents: {len(profiles)}")
    print(f"  With voices:  {with_voice}")
    print(f"  With emails:  {with_email}")
    print(f"  Need photos:  {len(profiles)} (all)")
    print(f"  Need phones:  {len(profiles)} (all)")


if __name__ == "__main__":
    main()
