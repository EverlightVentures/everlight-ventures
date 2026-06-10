"""slack_sonar_answer.py - Sonar fallback for hive-slack-agent.

Source: 05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/09_Research_and_Perplexity/perplexity_computer_clearly_explained.txt

When a user in Slack asks a factual/research question that Blinko cannot answer,
this module calls Perplexity Sonar and returns a sourced answer. Caller decides
whether to post to the thread.

The hive-slack-agent.service should import `answer_question()` and call it in
its question-handler when the local RAG (Blinko MoCs) yields insufficient results.

Usage:
    from slack_sonar_answer import answer_question
    result = answer_question("What is today's XLM circulating supply?")
    # {answer: str, citations: [urls], confidence: float}

CLI:
    python3 slack_sonar_answer.py --question "What moved XLM this week?"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

SONAR_URL = "https://api.perplexity.ai/chat/completions"
SONAR_MODEL = "sonar-pro"

_loaded = False
_key = ""


def _load() -> str:
    global _loaded, _key
    if _loaded:
        return _key
    _key = os.environ.get("PERPLEXITY_API_KEY", "")
    if not _key:
        env = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("PERPLEXITY_API_KEY="):
                    _key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    _loaded = True
    return _key


def answer_question(question: str, system_hint: str = "") -> dict[str, Any]:
    """Return {answer, citations, confidence, error}."""
    key = _load()
    if not key:
        return {"answer": "", "citations": [], "confidence": 0.0, "error": "no perplexity key"}

    hint = system_hint or (
        "You are answering a question for Lucrex's Hive Mind in Slack. "
        "Be concise (under 180 words). Cite your sources inline as [1][2]. "
        "If the question requires recent data (prices, news), prioritize the last 7 days. "
        "If you don't know, say 'I don't know' rather than guess."
    )

    body = json.dumps({
        "model": SONAR_MODEL,
        "messages": [
            {"role": "system", "content": hint},
            {"role": "user", "content": question},
        ],
        "max_tokens": 600,
        "return_citations": True,
    }).encode()

    req = urllib.request.Request(
        SONAR_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"answer": "", "citations": [], "confidence": 0.0, "error": f"HTTP {e.code}"}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        return {"answer": "", "citations": [], "confidence": 0.0, "error": str(e)}

    ans = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    citations = data.get("citations", []) or []
    # Heuristic confidence: citations + length
    confidence = min(1.0, 0.2 + 0.15 * len(citations) + min(0.4, len(ans) / 800))
    return {"answer": ans, "citations": citations, "confidence": round(confidence, 2), "error": ""}


def format_for_slack(result: dict[str, Any]) -> str:
    if result.get("error"):
        return f"(research failed: {result['error']})"
    if not result.get("answer"):
        return "(no answer returned)"
    ans = result["answer"]
    citations = result.get("citations", [])
    if citations:
        refs = "\n\n*Sources:*\n" + "\n".join(f"[{i+1}] {c}" for i, c in enumerate(citations[:8]))
        return ans + refs
    return ans


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", required=True)
    args = ap.parse_args()
    res = answer_question(args.question)
    print(format_for_slack(res))
    return 0 if not res.get("error") else 1


if __name__ == "__main__":
    sys.exit(main())
