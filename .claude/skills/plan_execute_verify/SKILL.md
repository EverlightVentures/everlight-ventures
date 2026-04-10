---
name: plan_execute_verify
description: Enforce plan-first execution with explicit validation and rollback.
---

When to use:
- Any non-trivial engineering task.

Workflow:
1. Produce a short plan.
2. Confirm assumptions.
3. Execute minimal scoped edits.
4. Validate with direct checks.
5. Report rollback steps.

Output contract:
- Goal
- Actions taken
- Validation
- Risks
- Rollback
