"""Load hive mind configuration from roster.yaml."""

from pathlib import Path

import yaml

ROSTER_PATH = Path(__file__).parent / "roster.yaml"
WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
AI_WORKERS = WORKSPACE / "03_AUTOMATION_CORE" / "01_Scripts" / "ai_workers"
AGENT_DIR = WORKSPACE / ".claude" / "agents"


def load_roster() -> dict:
    with open(ROSTER_PATH) as f:
        return yaml.safe_load(f)


def get_wrapper_path(name: str) -> str:
    """Get the full path to an AI worker wrapper script."""
    paths = {
        "clx_delegate": str(AI_WORKERS / "clx_delegate.py"),
        "gmx_delegate": str(AI_WORKERS / "gemx_delegate.py"),
        "ppx_terminal": str(AI_WORKERS / "ppx_terminal.py"),
        "cx_terminal": str(AI_WORKERS / "cx_terminal.py"),
    }
    return paths.get(name, name)


# ---------------------------------------------------------------------------
# Fire Team Doctrine v2 -- Hierarchy helpers
# ---------------------------------------------------------------------------

def get_fire_team(roster: dict, squad_key: str, team_name: str) -> dict:
    """Get a specific fire team from the roster.

    Returns dict with keys: mission, callsign, team_leader, specialist_1,
    specialist_2, verifier, assistant (each a dict with name, id, etc.)
    """
    squads = roster.get("squads", {})
    squad = squads.get(squad_key, {})
    return squad.get("fire_teams", {}).get(team_name, {})


def get_fire_team_agent_ids(fire_team: dict) -> list[str]:
    """Extract all agent IDs from a fire team dict."""
    ids = []
    for role in ("team_leader", "specialist_1", "specialist_2", "verifier", "assistant"):
        agent = fire_team.get(role)
        if isinstance(agent, dict) and agent.get("id"):
            ids.append(agent["id"])
    return ids


def get_squad_agents(roster: dict, squad_key: str) -> list[str]:
    """Get all agent IDs in a squad (across all fire teams)."""
    agents = []
    squads = roster.get("squads", {})
    squad = squads.get(squad_key, {})
    # Include squad leader
    sl = squad.get("squad_leader", {})
    if isinstance(sl, dict) and sl.get("id"):
        agents.append(sl["id"])
    for team in squad.get("fire_teams", {}).values():
        agents.extend(get_fire_team_agent_ids(team))
    return agents


def get_buddy(roster: dict, agent_name: str) -> str | None:
    """Find an agent's buddy from the buddy_pairs registry."""
    for pair in roster.get("buddy_pairs", []):
        if pair.get("primary") == agent_name:
            return pair.get("backup")
        if pair.get("backup") == agent_name:
            return pair.get("primary")
    return None


def resolve_fire_teams_for_category(roster: dict, category: str) -> dict:
    """Given a routing category, return which fire teams to activate per squad.

    Returns: {squad_key: fire_team_name} mapping.
    """
    rules = roster.get("routing_rules", {})
    rule = rules.get(category, {})
    return rule.get("fire_teams", {})
