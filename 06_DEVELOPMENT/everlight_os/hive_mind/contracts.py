"""
Hive Mind data contracts.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Dict, Any
import json
import uuid


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


@dataclass
class ManagerResult:
    """Result from one manager's deliberation."""
    manager: str = ""           # "claude", "gemini", "codex", "perplexity"
    role: str = ""              # "Chief Operator / Strategist"
    status: str = "pending"     # pending | running | done | failed | timeout
    response_text: str = ""
    started_at: str = ""
    finished_at: str = ""
    duration_s: float = 0.0
    error: str = ""
    employees_consulted: List[str] = field(default_factory=list)
    output_file: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HiveSession:
    """One hive deliberation session."""
    id: str = field(default_factory=_new_id)
    prompt: str = ""
    mode: str = "full"          # "full" | "lite" | "all"
    status: str = "pending"     # pending | running | done | partial
    routed_to: List[str] = field(default_factory=list)
    intel_summary: str = ""     # Perplexity intel (phase 1)
    managers: List[ManagerResult] = field(default_factory=list)
    combined_summary: str = ""
    war_room_dir: str = ""
    created: str = field(default_factory=_now)
    finished: str = ""
    total_duration_s: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class FireTeamResult:
    """Result from a fire team's execution."""
    squad: str = ""
    fire_team: str = ""
    team_leader: str = ""
    agents_activated: List[str] = field(default_factory=list)
    buddy_failovers: int = 0
    status: str = "pending"
    response_text: str = ""
    duration_s: float = 0.0
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "HiveSession":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
