# AI Org Communication Templates

## 1. War Room Update (#ai-war-room)
**Goal:** High-signal status for the Chief Operator.

```markdown
### 📢 [TEAM] Update: [Task ID]
- **Status:** [Active|Done|Blocked]
- **Summary:** [1-sentence achievement or blocker]
- **Next Action:** [Description] ([Owner])
- **ETA:** [Timestamp]
```

## 2. Agent Handoff Log (Specific Channel)
**Goal:** Detailed transfer of context between agents.

```markdown
### 🔄 Handoff: [From Agent] -> [To Agent]
- **Task ID:** [UUID]
- **Context:** [Links to files/drafts]
- **Requirements:** [Specific instructions for next step]
- **Priority:** [1-5]
```

## 3. Error/Escalation Log
**Goal:** Identifying failure points for the Automation Architect/Eng Foreman.

```markdown
### ⚠️ ERROR: [Workflow Name]
- **Agent:** [Reporting Agent]
- **Failure:** [Technical/Strategic description]
- **Log Path:** `_logs/[file_name].log`
- **Request:** [Help/Instruction needed]
```

## 4. Phase Gate Checklist
**Goal:** Enforce discipline at each project milestone. No work proceeds past a gate without sign-off.

### Gate 1: Scope Viable
- [ ] Problem statement written (1-2 sentences)
- [ ] Success criteria defined (measurable)
- [ ] Estimated effort: S / M / L
- [ ] Dependencies identified
- [ ] **Sign-off:** ____________ Date: ____

### Gate 2: Spec Approved
- [ ] Technical spec or plan file created
- [ ] File list (create/modify/delete) documented
- [ ] Risk assessment: what can break?
- [ ] Rollback plan documented
- [ ] **Sign-off:** ____________ Date: ____

### Gate 3: Build Approved
- [ ] All files created/modified per spec
- [ ] Tests pass (or manual verification documented)
- [ ] No regressions in existing functionality
- [ ] Code reviewed (self or peer)
- [ ] **Sign-off:** ____________ Date: ____

### Gate 4: Launch Approved
- [ ] Deployed to target environment
- [ ] Smoke test passed in production
- [ ] Monitoring/alerts configured
- [ ] Documentation updated
- [ ] **Sign-off:** ____________ Date: ____
