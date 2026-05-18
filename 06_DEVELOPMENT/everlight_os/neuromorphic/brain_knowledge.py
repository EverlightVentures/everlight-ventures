"""Transcript-backed knowledge ingestion for the Everlight AI brain."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .vector_memory import VectorMemory
except ImportError:
    from vector_memory import VectorMemory

STATE_DIR = Path(__file__).parent / "state"
STATE_DIR.mkdir(exist_ok=True)

STATUS_PATH = STATE_DIR / "ai_brain_knowledge.json"
MEMORY_NAME = "ai_brain"
ROOT_DIR = Path(__file__).resolve().parent.parent
REPO_STACK_PATH = ROOT_DIR / "hive_mind" / "open_source_repo_stack.yaml"
SLACK_ROUTING_PATH = ROOT_DIR / "hive_mind" / "slack_routing.yaml"

TOPIC_KEYWORDS = {
    "plasticity": [
        "plasticity", "hebbian", "synaptic", "stdp", "learning rule", "triplet connectivity",
    ],
    "continual_learning": [
        "continual learning", "catastrophic forgetting", "assembly", "assemblies", "dendrite",
        "preserve", "multi-task", "lifelong learning",
    ],
    "state_regulation": [
        "internal state", "arousal", "modulate", "regulation", "behavioral context",
        "state modulation", "stability", "homeostasis",
    ],
    "event_based_sensing": [
        "event-based", "ego motion", "sensor", "vision", "audition", "touch", "time difference encoder",
    ],
    "neuromorphic_hardware": [
        "hardware", "loihi", "cmos", "analog", "asynchronous", "sub-threshold", "chip",
    ],
    "spiking_control": [
        "spiking neural network", "spiking neuron", "leaky integrate-and-fire", "delay learning",
        "spike response model", "quadcopter", "control",
    ],
    "efficient_ai": [
        "language model", "llm", "attention", "token mixing", "channel mixing",
        "cost", "efficiency", "quadratic scaling",
    ],
    "representation_learning": [
        "embedding", "recurrent", "population activity", "representation", "shared variability",
        "latent", "sequence",
    ],
}


def _candidate_source_dirs() -> list[Path]:
    candidates: list[Path] = []
    env_dir = os.environ.get("AI_BRAIN_SOURCE_DIR", "").strip()
    if env_dir:
        candidates.append(Path(env_dir).expanduser())

    here = Path(__file__).resolve()
    suffixes = [
        Path("05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/Ai_Brain"),
        Path("05_PERSONAL/A_Personal_Notebook/NOTEPAD/Transcripts/Ai_Brain"),
    ]
    for parent in here.parents:
        for suffix in suffixes:
            candidates.append(parent / suffix)

    seen: set[str] = set()
    unique = []
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def resolve_source_dir() -> Path | None:
    for path in _candidate_source_dirs():
        if path.exists() and path.is_dir():
            return path
    return None


def _source_files(source_dir: Path | None) -> list[Path]:
    if source_dir is None:
        return []
    return sorted(path for path in source_dir.rglob("*.txt") if path.is_file())


def _clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _chunk_text(text: str, chunk_size: int = 1100, overlap: int = 150) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)
            tail = current[-overlap:] if overlap > 0 else ""
            current = f"{tail}\n\n{paragraph}".strip()
        else:
            for idx in range(0, len(paragraph), max(chunk_size - overlap, 200)):
                chunk = paragraph[idx:idx + chunk_size].strip()
                if chunk:
                    chunks.append(chunk)
            current = ""

    if current:
        chunks.append(current)

    return chunks


def _infer_topics(text: str) -> dict[str, int]:
    lowered = text.lower()
    counts: dict[str, int] = {}
    for topic, keywords in TOPIC_KEYWORDS.items():
        hit_count = sum(lowered.count(keyword) for keyword in keywords)
        if hit_count:
            counts[topic] = hit_count
    return counts


def _derive_traits(topic_totals: Counter) -> dict[str, int]:
    def pick(*keys: str) -> int:
        return sum(int(topic_totals.get(key, 0)) for key in keys)

    adaptability = pick("continual_learning", "plasticity", "representation_learning")
    emotional = pick("state_regulation", "plasticity")
    decisive = pick("spiking_control", "event_based_sensing", "neuromorphic_hardware")
    logical = pick("representation_learning", "efficient_ai", "spiking_control")
    self_healing = pick("continual_learning", "plasticity", "state_regulation")

    raw = {
        "adaptability": adaptability,
        "emotional_regulation": emotional,
        "decisiveness": decisive,
        "logical_rigor": logical,
        "self_healing": self_healing,
    }
    ceiling = max(max(raw.values()), 1)
    return {key: int(round(min(100, (value / ceiling) * 100))) for key, value in raw.items()}


def _knowledge_mode(traits: dict[str, int], top_topics: list[dict[str, Any]]) -> str:
    if not top_topics:
        return "knowledge pending"

    leader = top_topics[0]["topic"].replace("_", " ")
    if traits.get("self_healing", 0) >= 70 and traits.get("logical_rigor", 0) >= 70:
        return f"adaptive, self-healing, logic-forward ({leader})"
    if traits.get("decisiveness", 0) >= 70:
        return f"decisive neuromorphic operator ({leader})"
    return f"safety-first learning brain ({leader})"


def _build_manifest(files: list[Path], source_dir: Path | None) -> dict[str, Any]:
    base = source_dir or Path(".")
    items = []
    for file_path in files:
        stat = file_path.stat()
        items.append({
            "path": str(file_path.relative_to(base)),
            "size": int(stat.st_size),
            "mtime_ns": int(stat.st_mtime_ns),
        })
    digest = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()
    return {"digest": digest, "files": items}


def _existing_status() -> dict[str, Any]:
    if not STATUS_PATH.exists():
        return {}
    try:
        return json.loads(STATUS_PATH.read_text())
    except Exception:
        return {}


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        import yaml
    except Exception:
        return {}
    try:
        return yaml.safe_load(path.read_text()) or {}
    except Exception:
        return {}


def _detect_repo_installation(repo: dict[str, Any]) -> dict[str, Any]:
    detection = repo.get("detection") or {}
    module_hits = {}
    for name in (detection.get("python_modules") or []):
        try:
            module_hits[name] = importlib.util.find_spec(name) is not None
        except Exception:
            module_hits[name] = False
    binary_hits = {
        name: shutil.which(name) is not None
        for name in (detection.get("binaries") or [])
    }
    installed = bool(module_hits or binary_hits) and (
        all(module_hits.values()) if module_hits else True
    ) and (
        all(binary_hits.values()) if binary_hits else True
    )
    return {
        "installed": installed,
        "module_hits": module_hits,
        "binary_hits": binary_hits,
    }


def _repo_stack_status() -> dict[str, Any]:
    stack = _load_yaml(REPO_STACK_PATH)
    repos = list(stack.get("repos") or [])
    if not repos:
        return {"available": False, "repos_total": 0}

    phase_1 = [repo for repo in repos if repo.get("phase") == "phase_1"]
    installed = []
    missing = []
    for repo in repos:
        detection = _detect_repo_installation(repo)
        record = {
            "id": repo.get("id", ""),
            "phase": repo.get("phase", ""),
            "owner_agent": repo.get("owner_agent", ""),
            "category": repo.get("category", ""),
            "installed": detection["installed"],
        }
        if detection["installed"]:
            installed.append(record)
        else:
            missing.append(record)

    recommended_next = [
        {
            "id": repo.get("id", ""),
            "owner_agent": repo.get("owner_agent", ""),
            "category": repo.get("category", ""),
            "install": (
                (repo.get("install") or {}).get("docker")
                or (repo.get("install") or {}).get("shell")
                or (repo.get("install") or {}).get("pip")
                or (repo.get("install") or {}).get("conda")
                or "manual"
            ),
        }
        for repo in sorted(phase_1, key=lambda item: (item.get("priority", 999), item.get("id", "")))
        if not _detect_repo_installation(repo)["installed"]
    ][:5]

    workflows: Counter = Counter()
    owners: Counter = Counter()
    for repo in repos:
        for workflow in repo.get("workflows") or []:
            workflows.update([workflow])
        owner = repo.get("owner_agent", "")
        if owner:
            owners.update([owner])

    return {
        "available": True,
        "repos_total": len(repos),
        "installed_total": len(installed),
        "missing_total": len(missing),
        "phase_1_total": len(phase_1),
        "phase_1_ready": len(recommended_next) < len(phase_1),
        "top_workflows": [
            {"workflow": workflow, "count": count}
            for workflow, count in workflows.most_common(5)
        ],
        "recommended_next": recommended_next,
        "owner_agents": [name for name, _ in owners.most_common(6)],
        "already_in_stack": [repo["id"] for repo in installed[:8]],
    }


def _slack_routing_status() -> dict[str, Any]:
    routing_bundle = _load_yaml(SLACK_ROUTING_PATH)
    routing = routing_bundle.get("routing") or {}
    channels = routing_bundle.get("channels") or {}
    if not routing:
        return {"available": False, "routes_total": 0}

    formal_agents = []
    for route_name, route in routing.items():
        agent_name = str(route.get("agent", "")).strip()
        if agent_name:
            formal_agents.append({
                "route": route_name,
                "agent": agent_name,
                "channel": route.get("channel", ""),
            })

    unique_agent_names = list(dict.fromkeys(item["agent"] for item in formal_agents))

    return {
        "available": True,
        "routes_total": len(routing),
        "channels_total": len(channels),
        "formal_agents": formal_agents[:8],
        "agent_names": unique_agent_names[:8],
    }


def _repo_stack_memory_entries(repo_status: dict[str, Any], routing_status: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    for item in repo_status.get("recommended_next") or []:
        entries.append({
            "text": (
                f"Recommended Everlight upgrade: {item['id']} owned by {item['owner_agent']} "
                f"for category {item['category']}. Preferred install path: {item['install']}."
            ),
            "metadata": {
                "source": "repo_stack",
                "kind": "recommended_upgrade",
                "repo_id": item["id"],
                "owner_agent": item["owner_agent"],
                "category": item["category"],
            },
        })

    for workflow in repo_status.get("top_workflows") or []:
        entries.append({
            "text": (
                f"Everlight workflow emphasis: {workflow['workflow']} appears across "
                f"{workflow['count']} curated open-source integrations."
            ),
            "metadata": {
                "source": "repo_stack",
                "kind": "workflow_priority",
                "workflow": workflow["workflow"],
            },
        })

    for route in routing_status.get("formal_agents") or []:
        entries.append({
            "text": (
                f"Formal Everlight agent {route['agent']} owns route {route['route']} "
                f"through Slack channel {route['channel']}."
            ),
            "metadata": {
                "source": "slack_routing",
                "kind": "agent_route",
                "agent": route["agent"],
                "route": route["route"],
            },
        })

    return entries


def ingest_ai_brain_corpus(force: bool = False) -> dict[str, Any]:
    source_dir = resolve_source_dir()
    files = _source_files(source_dir)
    manifest = _build_manifest(files, source_dir)
    existing = _existing_status()

    if not force and existing.get("manifest", {}).get("digest") == manifest["digest"]:
        return existing

    memory = VectorMemory(MEMORY_NAME)
    memory.entries = []
    memory.index = None
    memory._is_fitted = False

    topic_totals: Counter = Counter()
    entries: list[dict[str, Any]] = []
    doc_summaries: list[dict[str, Any]] = []

    for file_path in files:
        raw_text = _clean_text(file_path.read_text(errors="ignore"))
        if not raw_text:
            continue

        kind = "summary" if "summary" in file_path.as_posix().lower() else "transcript"
        topics = _infer_topics(raw_text)
        topic_totals.update(topics)
        chunks = _chunk_text(raw_text)
        title = file_path.stem
        relative_path = str(file_path.relative_to(source_dir)) if source_dir else str(file_path)

        doc_summaries.append({
            "title": title,
            "kind": kind,
            "path": relative_path,
            "chars": len(raw_text),
            "chunks": len(chunks),
            "topics": sorted(topics, key=topics.get, reverse=True)[:4],
        })

        for idx, chunk in enumerate(chunks):
            entries.append({
                "text": chunk,
                "metadata": {
                    "source": "ai_brain_transcript",
                    "kind": kind,
                    "title": title,
                    "path": relative_path,
                    "chunk_index": idx,
                    "topics": sorted(topics, key=topics.get, reverse=True)[:4],
                },
            })

    repo_status = _repo_stack_status()
    routing_status = _slack_routing_status()
    stack_entries = _repo_stack_memory_entries(repo_status, routing_status)
    if stack_entries:
        entries.extend(stack_entries)

    memory.add_batch(entries)
    memory.save()

    top_topics = [
        {"topic": topic, "count": count}
        for topic, count in topic_totals.most_common(6)
    ]
    traits = _derive_traits(topic_totals)
    highlights = sorted(
        doc_summaries,
        key=lambda item: (len(item["topics"]), item["chunks"], item["chars"]),
        reverse=True,
    )[:5]

    status = {
        "available": bool(entries),
        "source_dir": str(source_dir) if source_dir else "",
        "documents": len(doc_summaries),
        "chunks": len(entries),
        "indexed": bool(entries),
        "last_ingested_at": datetime.now(timezone.utc).isoformat(),
        "top_topics": top_topics,
        "cognitive_profile": traits,
        "knowledge_mode": _knowledge_mode(traits, top_topics),
        "highlights": highlights,
        "manifest": manifest,
        "memory": memory.get_stats(),
        "repo_stack": repo_status,
        "slack_routing": routing_status,
    }
    STATUS_PATH.write_text(json.dumps(status, indent=2, default=str))
    return status


def get_ai_brain_status(refresh: bool = False) -> dict[str, Any]:
    if refresh or not STATUS_PATH.exists():
        return ingest_ai_brain_corpus(force=refresh)

    source_dir = resolve_source_dir()
    files = _source_files(source_dir)
    manifest = _build_manifest(files, source_dir)
    existing = _existing_status()
    if existing.get("manifest", {}).get("digest") != manifest["digest"]:
        return ingest_ai_brain_corpus(force=True)
    return existing


def search_ai_brain(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    get_ai_brain_status()
    memory = VectorMemory(MEMORY_NAME)
    results = memory.search(query, top_k=top_k)
    if not results:
        return memory._substring_search(query, top_k)
    if max(float(item.get("similarity", 0)) for item in results) <= 0:
        return memory._substring_search(query, top_k)
    return results


if __name__ == "__main__":
    refresh = "--refresh" in sys.argv
    print(json.dumps(get_ai_brain_status(refresh=refresh), indent=2, default=str))
