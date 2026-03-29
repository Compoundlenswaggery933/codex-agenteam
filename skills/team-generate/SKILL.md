---
name: team-generate
description: Regenerate .codex/agents/*.toml from codex-team.yaml and plugin defaults.
---

# Team Generate

Regenerate Codex-native agent files from the current configuration.

## When to Use

- After editing `codex-team.yaml` manually
- After adding or removing roles
- After updating the plugin (new default role templates)
- To verify generated agents match the config

## Process

### 1. Validate Config

```bash
python3 <runtime>/codex_team_rt.py roles list
```

If this fails, the config has errors — show them and stop.

### 2. Generate Agents

```bash
python3 <runtime>/codex_team_rt.py generate
```

### 3. Report Results

Show what was generated:

```
Generated agents:
  .codex/agents/architect.toml      (updated)
  .codex/agents/implementer.toml    (updated)
  .codex/agents/reviewer.toml       (updated)
  .codex/agents/test_writer.toml    (updated)
```

If custom roles were included, highlight them:
```
  .codex/agents/security_auditor.toml  (custom role)
```

### 4. Verify

Optionally show a summary of each generated agent's key fields
(name, model, can_write, participates_in) for user verification.
