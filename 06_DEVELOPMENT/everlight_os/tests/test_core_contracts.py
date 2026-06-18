"""Tests for everlight_os.core.contracts — data contracts and serialization."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.contracts import (
    StepDef,
    ProjectState,
    RunLogEntry,
    RouterResult,
    _WORKER_ROLE_MAP,
    _STEP_OUTPUTS,
    _STEP_DOD,
)


class StepDefTests(unittest.TestCase):
    def test_default_values(self):
        s = StepDef(name="research", worker="openai")
        self.assertEqual(s.name, "research")
        self.assertEqual(s.worker, "openai")
        self.assertEqual(s.status, "pending")
        self.assertEqual(s.description, "")
        self.assertEqual(s.duration_s, 0.0)
        self.assertEqual(s.error, "")

    def test_to_dict(self):
        s = StepDef(name="draft", worker="local", status="done", duration_s=1.5)
        d = s.to_dict()
        self.assertEqual(d["name"], "draft")
        self.assertEqual(d["worker"], "local")
        self.assertEqual(d["status"], "done")
        self.assertAlmostEqual(d["duration_s"], 1.5)

    def test_custom_fields(self):
        s = StepDef(
            name="seo",
            worker="openai",
            description="Generate SEO meta",
            output_path="/out/seo.json",
            error="timeout",
            status="failed",
        )
        d = s.to_dict()
        self.assertEqual(d["description"], "Generate SEO meta")
        self.assertEqual(d["output_path"], "/out/seo.json")
        self.assertEqual(d["error"], "timeout")
        self.assertEqual(d["status"], "failed")


class ProjectStateTests(unittest.TestCase):
    def test_defaults(self):
        ps = ProjectState()
        self.assertTrue(len(ps.id) > 0)
        self.assertEqual(ps.engine, "")
        self.assertEqual(ps.status, "pending")
        self.assertIsInstance(ps.steps, list)
        self.assertIsInstance(ps.artifacts, list)
        self.assertIsInstance(ps.errors, list)
        self.assertIsInstance(ps.metadata, dict)
        self.assertTrue(ps.created)
        self.assertTrue(ps.updated)

    def test_to_dict_roundtrip(self):
        ps = ProjectState(
            engine="trading",
            intent="daily_report",
            request="Generate trading report",
            status="running",
            current_step=2,
        )
        d = ps.to_dict()
        self.assertEqual(d["engine"], "trading")
        self.assertEqual(d["intent"], "daily_report")
        self.assertEqual(d["current_step"], 2)

    def test_to_json(self):
        ps = ProjectState(engine="content", intent="howto")
        j = ps.to_json()
        parsed = json.loads(j)
        self.assertEqual(parsed["engine"], "content")
        self.assertEqual(parsed["intent"], "howto")

    def test_from_dict(self):
        d = {
            "id": "abc12345",
            "engine": "books",
            "intent": "new_book",
            "status": "done",
            "current_step": 5,
            "steps": [{"name": "outline"}],
            "artifacts": ["manuscript.md"],
            "errors": [],
        }
        ps = ProjectState.from_dict(d)
        self.assertEqual(ps.id, "abc12345")
        self.assertEqual(ps.engine, "books")
        self.assertEqual(ps.status, "done")
        self.assertEqual(ps.current_step, 5)
        self.assertEqual(len(ps.steps), 1)

    def test_from_dict_ignores_extra_keys(self):
        d = {
            "id": "test1",
            "engine": "trading",
            "extra_field": "should_be_ignored",
        }
        ps = ProjectState.from_dict(d)
        self.assertEqual(ps.engine, "trading")
        self.assertFalse(hasattr(ps, "extra_field"))

    def test_save_and_from_json(self):
        ps = ProjectState(
            engine="saas",
            intent="full_build",
            request="Build SaaS app",
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            ps.save(path)
            loaded = ProjectState.from_json(path)
            self.assertEqual(loaded.engine, "saas")
            self.assertEqual(loaded.intent, "full_build")
            self.assertEqual(loaded.request, "Build SaaS app")
        finally:
            os.unlink(path)


class RunLogEntryTests(unittest.TestCase):
    def test_defaults(self):
        entry = RunLogEntry()
        self.assertTrue(entry.timestamp)
        self.assertEqual(entry.project_id, "")
        self.assertEqual(entry.status, "")
        self.assertEqual(entry.steps_completed, 0)

    def test_to_dict(self):
        entry = RunLogEntry(
            project_id="proj1",
            engine="content",
            intent="howto",
            status="ok",
            steps_completed=5,
            steps_total=7,
        )
        d = entry.to_dict()
        self.assertEqual(d["project_id"], "proj1")
        self.assertEqual(d["steps_completed"], 5)

    def test_to_jsonl(self):
        entry = RunLogEntry(project_id="proj2", engine="trading", status="fail")
        line = entry.to_jsonl()
        parsed = json.loads(line)
        self.assertEqual(parsed["project_id"], "proj2")
        self.assertEqual(parsed["status"], "fail")


class RouterResultTests(unittest.TestCase):
    def test_defaults(self):
        rr = RouterResult()
        self.assertEqual(rr.engine, "")
        self.assertEqual(rr.intent, "")
        self.assertAlmostEqual(rr.confidence, 0.0)
        self.assertIsInstance(rr.steps, list)
        self.assertIsInstance(rr.metadata, dict)

    def test_to_dict_with_stepdef(self):
        rr = RouterResult(
            engine="trading",
            intent="daily_report",
            confidence=0.85,
            steps=[StepDef(name="parse_logs", worker="local")],
        )
        d = rr.to_dict()
        self.assertEqual(d["engine"], "trading")
        self.assertEqual(len(d["steps"]), 1)
        self.assertEqual(d["steps"][0]["name"], "parse_logs")

    def test_generate_tickets_with_stepdef(self):
        steps = [
            StepDef(name="research", worker="perplexity", description="Deep research"),
            StepDef(name="draft", worker="openai", description="Write blog"),
        ]
        rr = RouterResult(engine="content", intent="howto", steps=steps)
        tickets = rr.generate_tickets()
        self.assertEqual(len(tickets), 2)
        self.assertEqual(tickets[0]["role"], "perplexity_researcher")
        self.assertEqual(tickets[0]["task"], "Deep research")
        self.assertIn("research_packet.json", tickets[0]["outputs"])
        self.assertEqual(tickets[1]["role"], "gpt_content_director")

    def test_generate_tickets_with_dict_steps(self):
        rr = RouterResult(
            engine="trading",
            intent="daily_report",
            steps=[
                {"name": "parse_logs", "worker": "local", "description": "Read logs"},
            ],
        )
        tickets = rr.generate_tickets()
        self.assertEqual(len(tickets), 1)
        self.assertEqual(tickets[0]["role"], "local_processor")

    def test_generate_tickets_empty_steps(self):
        rr = RouterResult(engine="status", intent="full_status")
        tickets = rr.generate_tickets()
        self.assertEqual(tickets, [])


class WorkerMappingsTests(unittest.TestCase):
    def test_worker_role_map_keys(self):
        expected = {"openai", "perplexity", "local", "slack"}
        self.assertEqual(set(_WORKER_ROLE_MAP.keys()), expected)

    def test_step_outputs_has_key_steps(self):
        for key in ("research", "outline", "draft", "seo", "generate_report"):
            self.assertIn(key, _STEP_OUTPUTS, f"Missing step output: {key}")
            self.assertIsInstance(_STEP_OUTPUTS[key], list)

    def test_step_dod_has_matching_keys(self):
        for key in _STEP_OUTPUTS:
            self.assertIn(key, _STEP_DOD, f"Missing DOD for step: {key}")


if __name__ == "__main__":
    unittest.main()
