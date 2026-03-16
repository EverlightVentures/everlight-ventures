"""
SaaS Factory Engine — Idea to Spec Pack Factory.
Intake > Scope > Stack > Spec (9 docs) > Gate > [Build stub] > [Launch stub] > [Ops stub]
"""

from pathlib import Path


def register_handlers(orch):
    """Register saas engine step handlers with the orchestrator."""
    from . import scoper
    from . import stack_picker
    from . import spec_writer
    from . import saas_gate
    from . import builder
    from . import launcher
    from . import ops_writer

    def _get_slack():
        from ...core.slack_client import get_client
        return get_client()

    # --- Phase 0: Spec ---

    def handle_scope_idea(state, step: dict, project_dir: Path) -> str:
        idea = state.metadata.get("idea", state.request)
        scope = scoper.validate_and_scope(idea, project_dir)
        state.metadata["scope"] = scope
        state.metadata["slug"] = scope.get("slug", state.metadata.get("slug", "untitled"))
        return str(project_dir / "scope.json")

    def handle_pick_stack(state, step: dict, project_dir: Path) -> str:
        scope = state.metadata.get("scope", {})
        stack = stack_picker.pick_stack(scope, project_dir)
        state.metadata["stack"] = stack
        return str(project_dir / "stack.json")

    def handle_write_spec(state, step: dict, project_dir: Path) -> str:
        scope = state.metadata.get("scope", {})
        stack = state.metadata.get("stack", {})
        paths = spec_writer.write_all_spec_docs(scope, stack, project_dir)
        state.metadata["spec_paths"] = paths
        return str(project_dir / "spec" / "01_PRD.md")

    def handle_spec_gate(state, step: dict, project_dir: Path) -> str:
        result = saas_gate.run_spec_gate(project_dir)
        state.metadata["spec_gate_result"] = result
        return str(project_dir / "spec_approval.json")

    def handle_post_to_slack(state, step: dict, project_dir: Path) -> str:
        scope = state.metadata.get("scope", {})
        gate = state.metadata.get("spec_gate_result", {})
        approved = gate.get("approved", False)

        summary = (
            f"*SaaS Factory — Spec Pack Ready*\n\n"
            f"*Idea:* {scope.get('one_liner', state.request)}\n"
            f"*Slug:* `{scope.get('slug', '?')}`\n"
            f"*ICP:* {scope.get('icp', '?')}\n"
            f"*Revenue model:* {scope.get('revenue_model', '?')}\n"
            f"*Stack:* {state.metadata.get('stack', {}).get('summary', '?')}\n\n"
            f"*Spec gate:* {'PASSED' if approved else 'FAILED — review required'}\n"
            f"*Docs written:* 9/9 spec documents in `spec/`\n\n"
            f"_Review output: `{project_dir}`_\n"
            f"_Approve to proceed to Phase 1 (Build)_"
        )

        slack = _get_slack()
        slack.post_approval(state.id, summary, "saas_factory")
        return ""

    # --- Phase 1: Build (stubs) ---

    def handle_scaffold_repo(state, step: dict, project_dir: Path) -> str:
        return builder.scaffold(
            state.metadata.get("scope", {}),
            state.metadata.get("stack", {}),
            project_dir,
        )

    def handle_write_tests(state, step: dict, project_dir: Path) -> str:
        return builder.write_test_plan(state.metadata.get("scope", {}), project_dir)

    def handle_build_gate(state, step: dict, project_dir: Path) -> str:
        return saas_gate.run_build_gate(project_dir)

    # --- Phase 2: Launch (stubs) ---

    def handle_write_launch(state, step: dict, project_dir: Path) -> str:
        return launcher.write_launch_pack(state.metadata.get("scope", {}), project_dir)

    def handle_write_ops(state, step: dict, project_dir: Path) -> str:
        return ops_writer.write_ops_pack(state.metadata.get("scope", {}), project_dir)

    def handle_launch_gate(state, step: dict, project_dir: Path) -> str:
        return saas_gate.run_launch_gate(project_dir)

    # --- Register all handlers ---
    orch.register_handler("saas", "scope_idea", handle_scope_idea)
    orch.register_handler("saas", "pick_stack", handle_pick_stack)
    orch.register_handler("saas", "write_spec", handle_write_spec)
    orch.register_handler("saas", "spec_gate", handle_spec_gate)
    orch.register_handler("saas", "post_to_slack", handle_post_to_slack)
    orch.register_handler("saas", "scaffold_repo", handle_scaffold_repo)
    orch.register_handler("saas", "write_tests", handle_write_tests)
    orch.register_handler("saas", "build_gate", handle_build_gate)
    orch.register_handler("saas", "write_launch", handle_write_launch)
    orch.register_handler("saas", "write_ops", handle_write_ops)
    orch.register_handler("saas", "launch_gate", handle_launch_gate)
