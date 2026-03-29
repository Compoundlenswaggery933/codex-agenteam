---
name: ateam-add-role
description: Add a custom role to the project's agenteam.yaml config.
---

# AgenTeam Add Role

Add a new custom role to the project configuration.

## Process

### 1. Gather Role Details

Ask the user for each field, one at a time:

1. **Name:** Role identifier (kebab or snake_case, e.g., `security_auditor`)
2. **Description:** What does this role do? (1-2 sentences)
3. **Responsibilities:** List of specific duties (3-5 items)
4. **Stages:** Which pipeline stages does this role participate in?
   Options: design, plan, implement, test, review
5. **Can write?** Does this role need to modify files? (yes/no)
   - If yes: **Write scope** — which file patterns? (e.g., `docs/**`)
6. **Model:** Which model? (default: o3-mini)
7. **Reasoning effort:** low, medium, or high? (default: medium)

### 2. Add to Config

Read the current `agenteam.yaml` and add the new role under `roles:`.

If the role participates in a pipeline stage, add it to the appropriate
stage in the `pipeline.stages` section.

### 3. Regenerate Agents

```bash
python3 <runtime>/agenteam_rt.py generate
```

### 4. Confirm

Show the user:
- The new role's config as it appears in agenteam.yaml
- The generated agent file path (`.codex/agents/<name>.toml`)
- How to use it: `$ateam-dispatch <name> "<task>"`
