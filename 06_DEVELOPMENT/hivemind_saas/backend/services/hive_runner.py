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

import httpx

from core.config import settings
from services.slack_audit import post_audit, AuditEvent

logger = logging.getLogger(__name__)

# -- Provider API endpoints and defaults --
_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
_OPENAI_URL = "https://api.openai.com/v1/chat/completions"
_GOOGLE_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
_PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"

_AGENT_MODELS = {
    "claude": "claude-sonnet-4-20250514",
    "gemini": "gemini-2.0-flash",
    "codex": "gpt-4o",
    "perplexity": "sonar",
}

_AGENT_SYSTEM_PROMPTS = {
    "claude": (
        "You are the Chief Operator for an AI war room. "
        "Analyze the user's prompt and provide a strategic plan with risks, "
        "recommended next actions, and priorities. Be direct and actionable."
    ),
    "gemini": (
        "You are a Logistics Commander and research specialist. "
        "Provide a research summary with evidence, data points, and gaps to verify. "
        "Focus on practical execution steps and workflow automation."
    ),
    "codex": (
        "You are an Engineering Foreman and profit maximizer. "
        "Provide an implementation outline with systems impact, code architecture, "
        "and automation steps. Focus on ROI and buildable deliverables."
    ),
    "perplexity": (
        "You are an Intelligence Anchor providing real-time research. "
        "Provide sourced findings, external validation, market data, and open questions. "
        "Always cite your sources."
    ),
}


async def _call_anthropic(prompt: str, api_key: str) -> tuple[str, int]:
    """Call Claude -- via API key if available, otherwise via Claude CLI (OAuth)."""
    if api_key and api_key.startswith("sk-ant-"):
        # Direct API call with key
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                _ANTHROPIC_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": _AGENT_MODELS["claude"],
                    "max_tokens": 2000,
                    "system": _AGENT_SYSTEM_PROMPTS["claude"],
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            text = data.get("content", [{}])[0].get("text", "")
            tokens = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
            return text, tokens
    else:
        # Use Claude CLI (OAuth-authenticated) -- same as the local hive
        import shutil
        claude_bin = shutil.which("claude")
        if not claude_bin:
            raise RuntimeError("Claude CLI not installed. Run: npm install -g @anthropic-ai/claude-code")
        full_prompt = f"{_AGENT_SYSTEM_PROMPTS['claude']}\n\n{prompt}"
        env = {k: v for k, v in __import__('os').environ.items()
               if k not in ('CLAUDECODE', 'CLAUDE_CODE', 'CLAUDE_CODE_ENTRY_POINT')}
        proc = await asyncio.create_subprocess_exec(
            claude_bin, "-p", "--model", "sonnet",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(full_prompt.encode()), timeout=120)
        text = stdout.decode().strip()
        if not text and proc.returncode != 0:
            raise RuntimeError(f"Claude CLI error: {stderr.decode()[:300]}")
        return text, len(text) // 4  # estimate tokens


async def _call_openai(prompt: str, api_key: str, model: str = "gpt-4o") -> tuple[str, int]:
    """Call OpenAI-compatible API (used for Codex agent)."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            _OPENAI_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 2000,
                "messages": [
                    {"role": "system", "content": _AGENT_SYSTEM_PROMPTS["codex"]},
                    {"role": "user", "content": prompt},
                ],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        tokens = data.get("usage", {}).get("total_tokens", 0)
        return text, tokens


async def _call_gemini(prompt: str, api_key: str) -> tuple[str, int]:
    """Call Gemini -- via API key if available, otherwise via Gemini CLI (OAuth)."""
    if api_key and len(api_key) > 20:
        # Direct API call with key
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{_AGENT_MODELS['gemini']}:generateContent?key={api_key}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": f"{_AGENT_SYSTEM_PROMPTS['gemini']}\n\n{prompt}"}]}],
                    "generationConfig": {"maxOutputTokens": 2000},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)
            return text, tokens
    else:
        # Use Gemini CLI (OAuth-authenticated)
        import shutil
        gemini_bin = shutil.which("gemini")
        if not gemini_bin:
            raise RuntimeError("Gemini CLI not installed.")
        full_prompt = f"{_AGENT_SYSTEM_PROMPTS['gemini']}\n\n{prompt}"
        proc = await asyncio.create_subprocess_exec(
            gemini_bin, "-y", "-p", full_prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        text = stdout.decode().strip()
        if not text and proc.returncode != 0:
            raise RuntimeError(f"Gemini CLI error: {stderr.decode()[:300]}")
        return text, len(text) // 4


async def _call_perplexity(prompt: str, api_key: str) -> tuple[str, int]:
    """Call Perplexity API for real-time research."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            _PERPLEXITY_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": _AGENT_MODELS["perplexity"],
                "max_tokens": 1500,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": _AGENT_SYSTEM_PROMPTS["perplexity"]},
                    {"role": "user", "content": prompt},
                ],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        tokens = data.get("usage", {}).get("total_tokens", 0)
        return text, tokens


# Map agent names to their call functions
_AGENT_CALLERS = {
    "claude": _call_anthropic,
    "gemini": _call_gemini,
    "codex": _call_openai,
    "perplexity": _call_perplexity,
}

# Map agent names to their platform-level config key
_PLATFORM_KEY_ATTRS = {
    "claude": "anthropic_api_key",
    "codex": "openai_api_key",
    "gemini": "google_api_key",
    "perplexity": "",  # loaded from env PERPLEXITY_API_KEY
}


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
        """Run a real AI API call for the given agent. Falls back to a status message if no key."""
        import os

        start = time.time()

        # Resolve API key: tenant key > platform key > env var > CLI fallback
        resolved_key = api_key
        if not resolved_key:
            attr = _PLATFORM_KEY_ATTRS.get(agent, "")
            if attr:
                resolved_key = getattr(settings, attr, "")
            if not resolved_key and agent == "perplexity":
                resolved_key = os.environ.get("PERPLEXITY_API_KEY", "")
            if not resolved_key and agent == "claude":
                resolved_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not resolved_key and agent == "codex":
                resolved_key = os.environ.get("OPENAI_API_KEY", "")
            if not resolved_key and agent == "gemini":
                resolved_key = os.environ.get("GOOGLE_API_KEY", "")

        # Claude and Gemini can fall back to their CLI tools (OAuth)
        # so missing key is OK for those agents
        cli_capable = agent in ("claude", "gemini")

        if not resolved_key and not cli_capable:
            return AgentResult(
                agent=agent,
                output=f"[{agent.upper()}] No API key configured. Set the key in your integration settings or contact support.",
                duration_s=round(time.time() - start, 2),
                tokens_used=0,
            )

        caller = _AGENT_CALLERS.get(agent)
        if not caller:
            return AgentResult(
                agent=agent,
                output=f"[{agent.upper()}] Unknown agent type.",
                duration_s=round(time.time() - start, 2),
                tokens_used=0,
            )

        try:
            text, tokens = await caller(self.prompt, resolved_key)
            return AgentResult(
                agent=agent,
                output=text,
                duration_s=round(time.time() - start, 2),
                tokens_used=tokens,
            )
        except httpx.HTTPStatusError as e:
            error_body = e.response.text[:300] if e.response else str(e)
            logger.error(f"Agent {agent} HTTP error: {e.response.status_code} - {error_body}")
            return AgentResult(
                agent=agent,
                output=f"[{agent.upper()}] API error ({e.response.status_code}). Check your API key and quota.",
                duration_s=round(time.time() - start, 2),
                tokens_used=0,
            )
        except Exception as e:
            logger.error(f"Agent {agent} failed: {e}")
            return AgentResult(
                agent=agent,
                output=f"[{agent.upper()}] Error: {str(e)[:200]}",
                duration_s=round(time.time() - start, 2),
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
        duration_s = round((datetime.now(timezone.utc) - self.started_at).total_seconds(), 2)
        return {
            "session_id": self.session_id,
            "tenant_id": self.tenant_id,
            "prompt": self.prompt,
            "agents": self.agents,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "duration_s": duration_s,
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
