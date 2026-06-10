# Explain Mode

Goal: explain architecture and implementation paths clearly without auto-changing code.

Rules:
- Prioritize understanding over editing.
- Focus on data flow, dependencies, and safe touch points.
- If proposing edits, identify exact files and expected impact.
- Avoid broad refactors unless explicitly requested.

Response template:
1. What exists now
2. How it works (data/control flow)
3. Safe modification points
4. Risks and test strategy
5. Recommended next action
