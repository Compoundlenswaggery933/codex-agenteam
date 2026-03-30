# Configuration Reference

AgenTeam works out of the box with zero config. Customize when you're ready.

Config lives at `.agenteam/config.yaml` in your project root.

## Minimal Config

```yaml
version: "1"
```

Everything else is inferred from defaults and auto-detection.

## Customized Config

```yaml
version: "2"
isolation: worktree       # branch (default) | worktree | none

roles:
  dev:
    write_scope:
      - "src/**"
      - "lib/**"

pipeline:
  stages:
    - name: implement
      roles: [dev]
      gate: auto
```

## Full Config Example

```yaml
version: "2"
isolation: branch              # branch (default) | worktree | none
# pipeline: hotl               # omit for auto-detect

# Override built-in roles or add custom ones
roles:
  dev:
    model: o4-mini
    reasoning_effort: high
    write_scope:
      - "src/**"
      - "lib/**"
      - "docs/plans/**"

  # Custom roles
  security_auditor:
    description: "Reviews code for security vulnerabilities"
    participates_in: [review]
    can_write: false
    system_instructions: |
      Focus on OWASP top 10, auth/authz logic, and hardcoded secrets.

# Final verification (runs after all stages)
final_verify:
  - "python3 -m pytest -v"
final_verify_policy: block     # block (default) | warn
final_verify_max_retries: 1

# Pipeline stages
pipeline:
  stages:
    - name: research
      roles: [researcher]
      gate: auto
    - name: strategy
      roles: [pm]
      gate: human
    - name: design
      roles: [architect, pm, researcher]
      gate: human
    - name: plan
      roles: [dev]
      gate: human
    - name: implement
      roles: [dev]
      gate: auto
      verify: "python3 -m pytest -v"
      max_retries: 2
      rework_to: plan
    - name: test
      roles: [qa]
      gate: auto
    - name: review
      roles: [reviewer]
      gate: human

  # Pipeline profiles — right-size the pipeline to the task
  profiles:
    quick:
      stages: [implement, test]
      hints: [typo, one-line fix, config change, version bump]
    standard:
      stages: [design, plan, implement, test, review]
      hints: [new endpoint, refactor, add feature, fix bug]
```

Use profiles with `@ATeam --profile quick fix the typo in README`.

## Built-in Roles

| Role | Participates In | Can Write | Write Scope | Parallel Safe |
|------|----------------|-----------|-------------|---------------|
| Researcher | research, design | Yes | `docs/research/**` | Yes |
| PM | strategy, design | Yes | `docs/strategies/**` | Yes |
| Architect | design | Yes | `docs/designs/**` | Yes |
| Dev | plan, implement | Yes | `src/**`, `lib/**`, `docs/plans/**` | No |
| Qa | test | Yes | `tests/**`, `**/*.test.*` | Yes |
| Reviewer | review | No | -- | Yes |

## Custom Roles

Add custom roles in the `roles:` section of your config:

```yaml
roles:
  security_auditor:
    description: "Reviews code for security vulnerabilities"
    participates_in: [review]
    can_write: false
    system_instructions: |
      Focus on OWASP top 10, auth/authz logic, and hardcoded secrets.

  docs_writer:
    description: "Maintains documentation"
    participates_in: [implement]
    can_write: true
    write_scope: ["docs/**", "README.md"]
```

Or add them interactively:

```
@ATeam add a security auditor that focuses on auth and data leaks
@ATeam add a performance engineer to profile API response times
```

## Branch Isolation

Writing agents are automatically isolated — they never touch your current branch directly.

| Mode | Behavior |
|------|----------|
| `branch` *(default)* | Creates `ateam/<role>/<task>` branch per assignment |
| `worktree` | Creates an isolated git worktree per writer |
| `none` | Stays on current branch (relies on non-overlapping write scopes) |

Set in config:

```yaml
isolation: worktree
```

## Config Migration

If you have a legacy config using `team.pipeline` or `team.parallel_writes.mode`, migrate to the canonical format:

```bash
# Preview changes
python3 runtime/agenteam_rt.py migrate --dry-run

# Apply migration
python3 runtime/agenteam_rt.py migrate
```

Migration bumps `version` to `"2"`, transforms legacy keys to flat top-level keys, and creates a timestamped backup of the original file.

## Validation

Validate your config for errors and warnings:

```bash
# Summary (default)
python3 runtime/agenteam_rt.py validate

# Full structured diagnostics
python3 runtime/agenteam_rt.py validate --format diagnostics

# Treat warnings as errors
python3 runtime/agenteam_rt.py validate --strict
```

Validation checks: required fields, enum values, stage-role cross-references, profile consistency, duplicate stage names, rework_to targets, and suggests corrections for typos.
