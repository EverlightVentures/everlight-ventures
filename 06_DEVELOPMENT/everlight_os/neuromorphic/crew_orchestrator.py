"""
CrewAI Orchestrator -- Maps Everlight's 63 agents to CrewAI crews.

Provides pre-built crews for common Hive operations:
  - BrokerCrew: Rex + Filter + Piper + Hammer (deal pipeline)
  - TradingCrew: Rex Thornton + Cipher + Penny (market analysis)
  - ContentCrew: Viktor + Kira + Justine (content factory)
  - ConsultingCrew: Forge + Ada + Neon (client delivery)

Each crew uses local ML models (no paid API required for core logic).
LLM calls are optional -- crews can run in "local" mode using only
scikit-learn models, FAISS search, and spaCy NLP.

Uses: CrewAI (MIT license) -- free, open source.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


# =====================================================================
# Agent Definitions (mapped from roster.yaml fire teams)
# =====================================================================

AGENT_PROFILES = {
    # Alpha Squad: Claude Corp (Marcus Cole)
    "marcus_cole": {
        "role": "Chief of Staff & Dispatcher",
        "goal": "Route every query to the right agents and ensure delivery",
        "backstory": "Former army logistics officer. Runs the Hive like a military operation. Never drops a task.",
    },
    "rex_blackwell": {
        "role": "Wholesale Deal Scout",
        "goal": "Find distressed properties and motivated sellers before anyone else",
        "backstory": "Texas-born real estate hustler with a drawl. Knows every county assessor site by heart.",
    },
    "filter_banks": {
        "role": "Lead Qualification Analyst",
        "goal": "Score and rank every lead so the team focuses on the highest-value targets",
        "backstory": "Data-obsessed analyst. Speaks in numbers. Reports with spreadsheet precision.",
    },
    "piper_reeves": {
        "role": "Outreach Specialist",
        "goal": "Craft personalized outreach that gets replies and builds relationships",
        "backstory": "Nashville warmth meets Silicon Valley hustle. Every email feels like a friend writing.",
    },
    "hammer_kovacs": {
        "role": "Deal Closer",
        "goal": "Move qualified leads from proposal to signed contract",
        "backstory": "Brooklyn negotiator. Calls everyone 'champ'. Closes deals over coffee and handshakes.",
    },
    # Bravo Squad: Gemini Ops (Major Dex)
    "rex_thornton": {
        "role": "Trading Strategist",
        "goal": "Identify high-probability trade setups and manage risk",
        "backstory": "Former prop trader. Thinks in risk:reward ratios. Never chases a trade.",
    },
    "cipher_wolfe": {
        "role": "Market Intelligence Analyst",
        "goal": "Decode on-chain data, sentiment, and macro signals into actionable intel",
        "backstory": "Crypto-native analyst. Reads blockchain data like others read newspapers.",
    },
    "penny_nakamura": {
        "role": "Risk & P&L Manager",
        "goal": "Protect capital and ensure every trade has defined risk parameters",
        "backstory": "Japanese-American risk manager. Meticulous. Never lets a position exceed limits.",
    },
    # Charlie Squad: Codex Labs (Forge)
    "forge_blackwood": {
        "role": "Lead Engineer & Architect",
        "goal": "Build and maintain all technical infrastructure for Everlight",
        "backstory": "Full-stack engineer who builds production systems in his sleep.",
    },
    "ada_chen": {
        "role": "AI/ML Engineer",
        "goal": "Train, deploy, and monitor all ML models across the Hive",
        "backstory": "Stanford ML grad. Obsessed with model accuracy and feature engineering.",
    },
    # Delta Squad: Perplexity Intel (Cipher)
    "viktor_lore": {
        "role": "Content Director",
        "goal": "Create compelling content that drives traffic and conversions",
        "backstory": "Former journalist turned content strategist. Words are his weapons.",
    },
    "justine_park": {
        "role": "Compliance & Legal Review",
        "goal": "Ensure all operations comply with regulations and reduce legal risk",
        "backstory": "Harvard Law background. Catches compliance issues before they become problems.",
    },
}


def create_broker_crew_config() -> dict:
    """Configuration for the Broker Pipeline crew.

    Agents: Rex Blackwell (scout), Filter Banks (score), Piper Reeves (outreach), Hammer Kovacs (close)
    Process: Sequential -- scout -> score -> outreach -> close
    """
    return {
        "name": "Broker Pipeline Crew",
        "agents": [
            {**AGENT_PROFILES["rex_blackwell"], "tools": ["web_scraper", "property_search"]},
            {**AGENT_PROFILES["filter_banks"], "tools": ["lead_scorer", "faiss_search"]},
            {**AGENT_PROFILES["piper_reeves"], "tools": ["email_sender", "nlp_analyzer"]},
            {**AGENT_PROFILES["hammer_kovacs"], "tools": ["contract_generator", "calendar"]},
        ],
        "tasks": [
            {"description": "Scout new leads from public sources", "agent": "rex_blackwell"},
            {"description": "Score and qualify leads using ML model", "agent": "filter_banks"},
            {"description": "Draft and send personalized outreach", "agent": "piper_reeves"},
            {"description": "Follow up on warm leads and close deals", "agent": "hammer_kovacs"},
        ],
        "process": "sequential",
    }


def create_trading_crew_config() -> dict:
    """Configuration for the Trading Analysis crew."""
    return {
        "name": "Trading Analysis Crew",
        "agents": [
            {**AGENT_PROFILES["cipher_wolfe"], "tools": ["market_data", "on_chain"]},
            {**AGENT_PROFILES["rex_thornton"], "tools": ["trade_predictor", "chart_analysis"]},
            {**AGENT_PROFILES["penny_nakamura"], "tools": ["risk_calculator", "portfolio"]},
        ],
        "tasks": [
            {"description": "Analyze market conditions and sentiment", "agent": "cipher_wolfe"},
            {"description": "Identify trade setups and entry/exit points", "agent": "rex_thornton"},
            {"description": "Validate risk parameters and position sizing", "agent": "penny_nakamura"},
        ],
        "process": "sequential",
    }


def create_consulting_crew_config() -> dict:
    """Configuration for the AI Consulting crew."""
    return {
        "name": "AI Consulting Crew",
        "agents": [
            {**AGENT_PROFILES["forge_blackwood"], "tools": ["code_builder", "deploy"]},
            {**AGENT_PROFILES["ada_chen"], "tools": ["ml_trainer", "model_eval"]},
            {**AGENT_PROFILES["justine_park"], "tools": ["compliance_check", "contract_review"]},
        ],
        "tasks": [
            {"description": "Architect and build client solution", "agent": "forge_blackwood"},
            {"description": "Train and deploy ML models for client", "agent": "ada_chen"},
            {"description": "Review deliverables for compliance", "agent": "justine_park"},
        ],
        "process": "sequential",
    }


class LocalCrew:
    """Lightweight crew execution without LLM API calls.

    Uses local ML models, FAISS memory, and spaCy NLP instead of
    sending prompts to an LLM. This enables the Hive to operate
    even without API credits.

    For full CrewAI execution with LLMs, use run_with_llm().
    """

    def __init__(self, config: dict):
        self.config = config
        self.name = config["name"]
        self.results: list[dict] = []

    def run_local(self, context: dict) -> dict:
        """Execute crew tasks using local ML models only."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent))

        from ml_models import get_toolkit
        from nlp_engine import analyze_text, extract_lead_features
        from vector_memory import get_memory

        toolkit = get_toolkit()
        memory = get_memory("crew_" + self.name.lower().replace(" ", "_"))
        results = []

        for task in self.config["tasks"]:
            agent_name = task["agent"]
            profile = AGENT_PROFILES.get(agent_name, {})
            task_result = {
                "agent": agent_name,
                "role": profile.get("role", ""),
                "task": task["description"],
            }

            # Route to appropriate ML model based on agent role
            if "scout" in task["description"].lower():
                task_result["output"] = f"[{agent_name}] Scouting leads... (local mode)"
                if context.get("leads"):
                    for lead in context["leads"][:5]:
                        features = extract_lead_features(str(lead))
                        score = toolkit.score_lead(features)
                        task_result.setdefault("scored_leads", []).append({
                            "lead": lead, "score": round(score, 1)
                        })

            elif "score" in task["description"].lower() or "qualify" in task["description"].lower():
                task_result["output"] = f"[{agent_name}] Scoring leads with ML model..."
                if context.get("lead_text"):
                    features = extract_lead_features(context["lead_text"])
                    task_result["score"] = toolkit.score_lead(features)
                    task_result["features"] = features

            elif "outreach" in task["description"].lower():
                task_result["output"] = f"[{agent_name}] Analyzing outreach timing..."
                outreach = toolkit.should_outreach(context.get("outreach_context", {}))
                task_result["recommendation"] = outreach

            elif "trade" in task["description"].lower() or "market" in task["description"].lower():
                task_result["output"] = f"[{agent_name}] Analyzing market conditions..."
                if context.get("trade_data"):
                    prediction = toolkit.predict_trade(context["trade_data"])
                    task_result["prediction"] = prediction

            elif "risk" in task["description"].lower():
                task_result["output"] = f"[{agent_name}] Validating risk parameters..."
                if context.get("trade_data"):
                    rr = float(context["trade_data"].get("rr_ratio", 0))
                    task_result["risk_assessment"] = {
                        "rr_ratio": rr,
                        "approved": rr >= 1.5,
                        "reason": "R:R meets minimum" if rr >= 1.5 else "R:R too low",
                    }

            else:
                task_result["output"] = f"[{agent_name}] Processing task locally..."

            # Store in vector memory
            memory.add(
                f"{agent_name}: {task['description']} -> {task_result.get('output', '')}",
                {"agent": agent_name, "task": task["description"]},
            )
            results.append(task_result)

        memory.save()
        self.results = results
        return {
            "crew": self.name,
            "mode": "local",
            "tasks_completed": len(results),
            "results": results,
        }


# Pre-built crews
def get_broker_crew() -> LocalCrew:
    return LocalCrew(create_broker_crew_config())

def get_trading_crew() -> LocalCrew:
    return LocalCrew(create_trading_crew_config())

def get_consulting_crew() -> LocalCrew:
    return LocalCrew(create_consulting_crew_config())
