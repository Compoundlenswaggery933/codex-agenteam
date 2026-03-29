---
name: ateam-dispatch
description: Dispatch a specific role for an ad-hoc task outside the pipeline.
---

# AgenTeam Dispatch

Launch a specific role agent for a focused task, independent of the pipeline.

## Process

### 1. Accept Input

Get the role name and task from the user. Examples:
- `$ateam-dispatch architect "Review this API design"`
- `$ateam-dispatch reviewer "Check auth logic in src/auth.py"`

If role or task is missing, ask.

### 2. Validate Role

```bash
python3 <runtime>/agenteam_rt.py roles show <role-name>
```

If the role doesn't exist, show available roles:
```bash
python3 <runtime>/agenteam_rt.py roles list
```

### 3. Check Write Policy

If the role has `can_write: true`, check for active write locks:

```bash
python3 <runtime>/agenteam_rt.py status
```

If a write lock is active and the role needs to write:
- Inform the user: "Write lock held by <active_role>. Wait for completion or
  override with confirmation."
- Do not proceed without user approval.

### 4. Launch Agent

Launch the role as a Codex subagent using the generated agent file:
- Agent file: `.codex/agents/<role-name>.toml`
- Pass the task description as the prompt
- Pass relevant project context (current branch, recent changes, etc.)

### 5. Collect Output

Present the agent's output to the user with the role name as context:
"**[architect]:** <output>"

## Notes

- Dispatch mode works regardless of pipeline setting
- Multiple read-only roles can be dispatched in parallel
- Write roles follow the configured write policy
