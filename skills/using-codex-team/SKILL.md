---
name: using-codex-team
description: Router skill for codex-team plugin. Maps user intent to the appropriate team skill.
---

# codex-team Router

You have the **codex-team** plugin installed. It provides role-based team
collaboration for AI-assisted development.

## Available Skills

| Skill | Invoke | When to Use |
|-------|--------|-------------|
| team-init | `$team-init` | Set up team config for a project |
| team-run | `$team-run` | Run a full pipeline (standalone or HOTL) |
| team-dispatch | `$team-dispatch` | Dispatch a specific role for a task |
| team-status | `$team-status` | Show current team state and progress |
| team-add-role | `$team-add-role` | Add a custom role to the project |
| team-generate | `$team-generate` | Regenerate .codex/agents/*.toml from config |

## Intent Routing

Match user intent to the right skill:

- **"Set up team" / "Initialize team" / "Configure roles"** -> `$team-init`
- **"Run this task" / "Build feature X" / "Work on this"** -> `$team-run`
- **"Send to reviewer" / "Get architect input" / "Run implementer"** -> `$team-dispatch`
- **"Show status" / "What's the team doing?" / "Progress?"** -> `$team-status`
- **"Add a security auditor" / "New role" / "Custom role"** -> `$team-add-role`
- **"Regenerate agents" / "Update TOML" / "Sync agents"** -> `$team-generate`

## Quick Reference

**Default roles:** architect (design/plan/review), implementer (implement),
test_writer (test), reviewer (review).

**Config file:** `codex-team.yaml` in project root.

**Generated agents:** `.codex/agents/*.toml` — Codex-native custom agents.

**Pipeline modes:** standalone (built-in), hotl (explicit opt-in), dispatch-only (ad-hoc).
