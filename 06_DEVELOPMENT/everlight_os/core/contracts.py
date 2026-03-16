"""
Everlight OS — Shared data contracts.
All engines use these schemas for state, steps, and log entries.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import json
import uuid


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


@dataclass
class StepDef:
    """One planned step in a pipeline."""
    name: str
    worker: str  # "openai", "perplexity", "local", "slack"
    description: str = ""
    status: str = "pending"  # pending | running | done | failed
    output_path: str = ""
    started_at: str = ""
    finished_at: str = ""
    duration_s: float = 0.0
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProjectState:
    """Tracks a project through its pipeline steps."""
    id: str = field(default_factory=_new_id)
    engine: str = ""  # "trading", "content", "books"
    intent: str = ""  # "daily_report", "howto", "new_book", etc.
    request: str = ""  # original user input
    status: str = "pending"  # pending | running | done | failed
    current_step: int = 0
    steps: List[Dict] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    project_dir: str = ""
    created: str = field(default_factory=_now)
    updated: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, d: dict) -> "ProjectState":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_json(cls, path: str) -> "ProjectState":
        with open(path) as f:
            return cls.from_dict(json.load(f))

    def save(self, path: str):
        self.updated = _now()
        with open(path, "w") as f:
            f.write(self.to_json())


@dataclass
class RunLogEntry:
    """One line in everlight_runs.jsonl."""
    timestamp: str = field(default_factory=_now)
    project_id: str = ""
    engine: str = ""
    intent: str = ""
    request: str = ""
    classification: Dict = field(default_factory=dict)
    steps_completed: int = 0
    steps_total: int = 0
    artifacts: List[str] = field(default_factory=list)
    status: str = ""  # ok | fail
    errors: List[str] = field(default_factory=list)
    duration_s: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    def to_jsonl(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class RouterResult:
    """Output of the router classification."""
    engine: str = ""  # "trading", "content", "books", "status"
    intent: str = ""  # subtype within engine
    confidence: float = 0.0
    steps: List[StepDef] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["steps"] = [s.to_dict() if isinstance(s, StepDef) else s for s in self.steps]
        return d

    def generate_tickets(self) -> List[Dict]:
        """Generate role-based work tickets from the step plan."""
        tickets = []
        for step in self.steps:
            s = step if isinstance(step, StepDef) else StepDef(**step) if isinstance(step, dict) else step
            name = s.name if isinstance(s, StepDef) else step.get("name", "")
            worker = s.worker if isinstance(s, StepDef) else step.get("worker", "")
            desc = s.description if isinstance(s, StepDef) else step.get("description", "")
            tickets.append({
                "role": _WORKER_ROLE_MAP.get(worker, worker),
                "task": desc or name,
                "inputs": [f"engine: {self.engine}", f"intent: {self.intent}"],
                "outputs": _STEP_OUTPUTS.get(name, []),
                "definition_of_done": _STEP_DOD.get(name, "Step completed successfully"),
            })
        return tickets


# --- Role ticket mappings ---

_WORKER_ROLE_MAP = {
    "openai": "gpt_content_director",
    "perplexity": "perplexity_researcher",
    "local": "local_processor",
    "slack": "slack_notifier",
}

_STEP_OUTPUTS = {
    "research": ["research_packet.json", "sources.md"],
    "outline": ["outline.md"],
    "draft": ["blog.md", "socials.md", "email.md", "video_script.md", "image_prompts.txt", "seedance_prompts.txt"],
    "seo": ["seo.json"],
    "monetize": ["monetization.md"],
    "quality_gate": ["publish_checklist.md", "qa_report.md", "approval_status.json"],
    "parse_logs": ["metrics.json"],
    "detect_anomalies": ["anomalies.json"],
    "generate_report": ["daily_report.md", "recommended_changes.md"],
    "series_bible": ["series_bible.md"],
    "manuscript": ["manuscript.md"],
    "illustrations": ["illustration_prompts.txt", "coloring_page_prompts.txt", "cover_prompt.txt"],
    "kdp_metadata": ["kdp_metadata.json"],
    "launch_pack": ["launch_socials.md", "launch_email.md", "video_script.md", "seedance_prompts.txt"],
    # SaaS Factory steps
    "scope_idea": ["scope.json"],
    "pick_stack": ["stack.json"],
    "write_spec": [
        "spec/01_PRD.md", "spec/02_USER_STORIES.md", "spec/03_ACCEPTANCE_CRITERIA.md",
        "spec/04_NONFUNCTIONAL_REQUIREMENTS.md", "spec/05_DATA_MODEL.md", "spec/06_API_SPEC.md",
        "spec/07_UI_MAP.md", "spec/08_RISK_REGISTER.md", "spec/09_ROADMAP.md",
    ],
    "spec_gate": ["spec_gate_report.md", "spec_approval.json"],
    "scaffold_repo": ["build/RUNBOOK.md", "build/.env.example"],
    "write_tests": ["build/TEST_PLAN.md"],
    "write_launch": [
        "launch/landing_page_copy.md", "launch/pricing.md", "launch/onboarding_email_sequence.md",
        "launch/affiliate_program_plan.md", "launch/seedance_prompts.txt", "launch/socials.md",
    ],
    "write_ops": [
        "ops/support_sop.md", "ops/incident_sop.md", "ops/backup_restore.md",
        "ops/privacy_policy_draft.md", "ops/terms_draft.md", "ops/analytics_plan.md",
    ],
}

_STEP_DOD = {
    "research": "10+ facts with sources, ranked by relevance",
    "outline": "Structured H1/H2 outline matching template, all sections filled",
    "draft": "Blog 1200-1800 words, 3-7 social posts, email under 300 words, video script 15-45s",
    "seo": "Valid JSON with title_tag, meta_description, keywords, schema markup",
    "monetize": "Affiliate slot guidance, CTA variants, disclaimer flags",
    "quality_gate": "All checks passed or fixes documented, approval_status.json written",
    "parse_logs": "All JSONL logs parsed, metrics computed",
    "detect_anomalies": "Anomalies flagged with severity levels",
    "generate_report": "Plain English daily report with metrics and outlook",
    "series_bible": "Character profiles, world rules, visual style guide loaded/created",
    "manuscript": "Full page-by-page manuscript with illustration notes",
    "illustrations": "Cover prompt + per-page interior prompts + coloring page prompts",
    "kdp_metadata": "Valid JSON with title, keywords, categories, pricing",
    "launch_pack": "Social posts, email, video script, seedance prompts for book launch",
    # SaaS Factory steps
    "scope_idea": "scope.json with slug, one_liner, ICP, revenue_model, moat, competitors, mvp_scope",
    "pick_stack": "stack.json with frontend, backend, database, hosting, auth, payments, rationale",
    "write_spec": "All 9 spec docs in spec/ subfolder, each 300+ words with headings",
    "spec_gate": "spec_approval.json written, approved=true only if all 9 docs exist and pass length check",
    "scaffold_repo": "build/ folder with RUNBOOK.md and .env.example",
    "write_tests": "TEST_PLAN.md with unit, integration, and e2e test cases",
    "build_gate": "All build files present, build_approval.json written",
    "write_launch": "All 6 launch files in launch/ subfolder",
    "write_ops": "All 6 ops files in ops/ subfolder",
    "launch_gate": "launch_approval.json written, all launch materials reviewed",
}
