"""
Hive Runner - executes a multi-agent session for a tenant.

Coordinates Claude + Gemini + Codex + Perplexity in parallel,
stores results, builds mindmap graph, fires Slack audit events.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from services.slack_audit import post_audit, AuditEvent

logger = logging.getLogger(__name__)


class AgentResult:
    def __init__(self, agent: str, output: str, duration_s: float, tokens_used: int = 0):
        self.agent = agent
        self.output = output
        self.duration_s = duration_s
        self.tokens_used = tokens_used
        self.node_id = str(uuid.uuid4())[:8]


class HiveSession:
    """
    Represents one multi-agent session.
    Tenant provides their own API keys via integrations; we decrypt and use them.
    """

    def __init__(self, session_id: str, tenant_id: str, tenant_name: str, prompt: str, agents: list[str]):
        self.session_id = session_id
        self.tenant_id = tenant_id
        self.tenant_name = tenant_name
        self.prompt = prompt
        self.agents = agents  # e.g. ["claude", "gemini", "codex", "perplexity"]
        self.results: list[AgentResult] = []
        self.started_at = datetime.now(timezone.utc)
        self.status = "pending"

    async def run(self, tenant_keys: dict[str, str]) -> dict:
        """
        Run agents in parallel. tenant_keys maps provider -> decrypted API key.
        Returns session result dict for storage.
        """
        self.status = "running"
        start = time.time()

        await post_audit(
            AuditEvent.SESSION_STARTED,
            tenant_name=self.tenant_name,
            tenant_id=self.tenant_id,
            summary=f"Hive session started with {len(self.agents)} agents.",
            details={"prompt_preview": self.prompt[:120], "agents": ", ".join(self.agents)},
            session_id=self.session_id,
        )

        tasks = []
        for agent in self.agents:
            key = tenant_keys.get(agent, "")
            tasks.append(self._run_agent(agent, key))

        try:
            agent_results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in agent_results:
                if isinstance(r, Exception):
                    logger.error(f"Agent error in session {self.session_id}: {r}")
                else:
                    self.results.append(r)

            self.status = "completed"
            duration = round(time.time() - start, 1)

            await post_audit(
                AuditEvent.SESSION_COMPLETED,
                tenant_name=self.tenant_name,
                tenant_id=self.tenant_id,
                summary=f"Session completed in {duration}s. {len(self.results)}/{len(self.agents)} agents responded.",
                details={
                    "duration_s": duration,
                    "agents_succeeded": len(self.results),
                    "total_tokens": sum(r.tokens_used for r in self.results),
                },
                session_id=self.session_id,
            )

        except Exception as e:
            self.status = "failed"
            await post_audit(
                AuditEvent.SESSION_FAILED,
                tenant_name=self.tenant_name,
                tenant_id=self.tenant_id,
                summary=f"Session failed: {e}",
                session_id=self.session_id,
            )
            raise

        return self._to_dict()

    async def _run_agent(self, agent: str, api_key: str) -> AgentResult:
        """Placeholder: calls the appropriate AI provider."""
        # In production this calls the real provider SDK
        # using the tenant's decrypted API key
        await asyncio.sleep(0.1)  # simulate network
        return AgentResult(
            agent=agent,
            output=f"[{agent}] Response placeholder for: {self.prompt[:60]}",
            duration_s=0.1,
            tokens_used=0,
        )

    def build_mindmap(self) -> dict:
        """
        Build a React Flow compatible mindmap graph from session results.
        Root node = prompt, branches = agent results.
        """
        root_id = f"root_{self.session_id[:8]}"
        nodes = [
            {
                "id": root_id,
                "type": "root",
                "data": {"label": self.prompt[:80], "type": "query"},
                "position": {"x": 0, "y": 0},
            }
        ]
        edges = []
        x_offset = -300

        for i, result in enumerate(self.results):
            node_id = f"agent_{result.agent}_{result.node_id}"
            nodes.append({
                "id": node_id,
                "type": "agent",
                "data": {
                    "label": result.agent.upper(),
                    "output_preview": result.output[:100],
                    "duration_s": result.duration_s,
                    "tokens": result.tokens_used,
                },
                "position": {"x": x_offset + (i * 200), "y": 200},
            })
            edges.append({
                "id": f"e_{root_id}_{node_id}",
                "source": root_id,
                "target": node_id,
                "type": "smoothstep",
            })

        return {"nodes": nodes, "edges": edges}

    def _to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "tenant_id": self.tenant_id,
            "prompt": self.prompt,
            "agents": self.agents,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "results": [
                {
                    "agent": r.agent,
                    "output": r.output,
                    "duration_s": r.duration_s,
                    "tokens_used": r.tokens_used,
                }
                for r in self.results
            ],
            "mindmap": self.build_mindmap(),
        }
