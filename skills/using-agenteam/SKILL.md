---
name: using-agenteam
description: Router skill for AgenTeam plugin. Maps user intent to the appropriate skill.
---

# AgenTeam Router

You have the **AgenTeam** plugin installed. It provides role-based team
collaboration for AI-assisted development. You are the lead; the plugin
organizes your specialist roles.

## Available Skills

| Skill | Invoke | When to Use |
|-------|--------|-------------|
| ateam-init | `$ateam-init` | Set up team config for a project |
| ateam-run | `$ateam-run` | Run a full pipeline (standalone or HOTL) |
| ateam-dispatch | `$ateam-dispatch` | Dispatch a specific role for a task |
| ateam-status | `$ateam-status` | Show current team state and progress |
| ateam-add-role | `$ateam-add-role` | Add a custom role to the project |
| ateam-generate | `$ateam-generate` | Regenerate .codex/agents/*.toml from config |

## Intent Routing

Match user intent to the right skill:

- **"Set up team" / "Initialize team" / "Configure roles"** -> `$ateam-init`
- **"Run this task" / "Build feature X" / "Work on this"** -> `$ateam-run`
- **"Send to reviewer" / "Get architect input" / "Run implementer"** -> `$ateam-dispatch`
- **"Show status" / "What's the team doing?" / "Progress?"** -> `$ateam-status`
- **"Add a security auditor" / "New role" / "Custom role"** -> `$ateam-add-role`
- **"Regenerate agents" / "Update TOML" / "Sync agents"** -> `$ateam-generate`

## Quick Reference

**Default roles:** architect (design/plan/review), implementer (implement),
test_writer (test), reviewer (review).

**Config file:** `agenteam.yaml` in project root.

**Generated agents:** `.codex/agents/*.toml` — Codex-native custom agents.

**Pipeline modes:** standalone (built-in), hotl (explicit opt-in), dispatch-only (ad-hoc).
