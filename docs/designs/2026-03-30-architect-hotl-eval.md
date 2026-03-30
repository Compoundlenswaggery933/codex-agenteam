# Minimal Plugin-Health Dashboard for AgenTeam

## Overview

This design proposes a deliberately small "plugin-health dashboard" for
AgenTeam. The goal is to give a user one place to answer:

- Is the plugin installed and configured correctly?
- Is the team runnable in this project?
- Are the key artifacts and state files present and fresh?
- Is the current workflow on-track, at-risk, or blocked?

The dashboard should stay read-heavy and low-risk. It should reuse existing
runtime state and artifact conventions instead of introducing a new long-lived
service, background process, or browser app.

This aligns with the current roadmap direction in
`docs/strategies/roadmap.md`, which already defines a lightweight health
indicator for `standup`, and with the plugin-compliance audit in
`docs/research/2026-03-29-plugin-compliance-audit.md`, which highlights
installability and packaging gaps as a practical health concern.

## Problem Statement

Today, a user has to inspect multiple places to understand whether AgenTeam is
"healthy":

- plugin packaging metadata in `.codex-plugin/`
- team config in `.agenteam/config.yaml`
- generated agent state in `.codex/agents/`
- pipeline progress in `.agenteam/state/`
- project artifacts in `docs/research/`, `docs/strategies/`, `docs/designs/`,
  and `docs/plans/`

That fragmentation is acceptable for contributors but too manual for regular
use. A compact dashboard should surface health without requiring the user to
read raw files or infer state.

## Constraints

- Keep scope intentionally tight. This is a v1 observability feature, not a
  full control plane.
- Prefer existing runtime JSON and artifact paths over new persistence.
- Avoid introducing a browser-only dependency or long-running process.
- Preserve the current separation of concerns:
  - runtime returns structured data
  - skill layer renders user-facing output
- Do not require HOTL to be active, but show HOTL availability and whether it
  is active in the current project.

## Non-Goals

- No live-updating web app
- No telemetry backend, analytics pipeline, or historical trend storage
- No background health daemon
- No auto-remediation of broken configuration
- No attempt to manage subagent execution from the dashboard itself

Those ideas are YAGNI for the current plugin maturity. The immediate need is
fast visibility, not an operational platform.

## Design Options

### Option A: Extend Standup into a Markdown Dashboard

Add a focused "plugin health" view to the existing standup-oriented runtime
data model and render it as structured Markdown.

#### Pros

- Lowest implementation cost; builds on the existing roadmap direction
- Fits AgenTeam's current architecture: runtime emits JSON, skill renders
- Works in Codex chat and as a saved artifact without extra UI infrastructure
- Easy to gate on existing files and runtime checks

#### Cons

- Not visually rich
- Limited interactivity
- May overlap conceptually with `standup` unless naming stays clear

### Option B: Generate a Static Local HTML Dashboard

Produce a single HTML file from runtime JSON and open or save it locally.

#### Pros

- Better visual hierarchy for health sections and status badges
- Still compatible with a snapshot model; no server required
- Can be shared as an artifact

#### Cons

- Adds frontend surface area and styling work before the core feature is proven
- Raises questions about asset generation, output location, and browser opening
- More moving parts for a plugin that currently operates through skills and docs

### Option C: Build a Live Interactive Dashboard

Create a continuously refreshed TUI or local web app that reads project state
and reflects changes in near real time.

#### Pros

- Best operator experience
- Strong foundation for future queue, lock, and multi-run visibility

#### Cons

- Highest complexity by far
- Conflicts with the current lightweight plugin architecture
- Forces decisions about process lifecycle, refresh cadence, and portability
- Premature before the core health model is validated

## Recommendation

Choose **Option A**.

The project already has the right primitives for a read-only health summary:
state files, resolved artifact paths, HOTL detection, and the roadmap's planned
health indicator. Extending that into a clearly named dashboard keeps the
feature useful and cheap. Option B can be added later if users actually need a
visual artifact. Option C is unjustified at this stage.

## Proposed Shape

### User Entry Point

Expose the dashboard through a lightweight team-level entry point, for example:

- `@ATeam health`
- or a dedicated skill alias that resolves to the same runtime data path

The feature should be explicitly team-level, not tied to a single specialist
role. The architect role may help design it, but the runtime owns the data and
the skill layer owns the presentation.

### Output Format

Return a concise Markdown dashboard and optionally save it to:

- `docs/meetings/<timestamp>-health.md`

That keeps consistency with the planned reporting flow instead of creating a
new top-level artifact family prematurely.

### Health Sections

The dashboard should include:

1. **Installation Health**
   - plugin manifest present
   - required plugin metadata present
   - runtime dependencies available

2. **Configuration Health**
   - `.agenteam/config.yaml` present
   - pipeline mode
   - write policy mode
   - role overrides that fail validation

3. **Agent Materialization Health**
   - expected generated agents exist in `.codex/agents/`
   - stale or missing generated agents

4. **Workflow Health**
   - latest run id, current stage, gate status
   - active write lock holder
   - blocked roles, if any

5. **Artifact Health**
   - latest research, strategy, design, and plan artifacts
   - missing handoff artifacts for the active stage

6. **HOTL Status**
   - HOTL installed?
   - HOTL active in project?
   - configured pipeline mode vs detected HOTL state

### Health States

Use three states only:

- `on-track`
- `at-risk`
- `off-track`

This matches the roadmap direction and avoids overfitting a more complex
scoring system too early.

## Data Model

The runtime should compute a single JSON payload that merges:

- current config summary
- HOTL detection result
- latest run-state summary
- resolved artifact paths
- existence/freshness checks for key files

The skill layer should not recompute business rules. It should format and
present the runtime output.

## Decision Rules

Examples of practical heuristics:

- **on-track**
  - config exists
  - required agents exist
  - no blocked write lock
  - current stage has expected upstream artifacts

- **at-risk**
  - HOTL available but config likely mismatched with user expectations
  - generated agents missing for one or more configured roles
  - expected artifacts are stale or missing, but the workflow is still
    recoverable

- **off-track**
  - no usable config
  - runtime validation fails
  - active run references missing artifacts or irreconcilable role config

## Risks

- **Feature overlap risk:** If this becomes a renamed copy of `standup`, the UX
  gets muddy. The dashboard must emphasize plugin health, not general project
  narration.
- **Rule drift risk:** If health logic is split between runtime and skills, the
  reported state will become inconsistent.
- **False confidence risk:** A green dashboard must not imply code correctness.
  It indicates workflow readiness and artifact continuity only.

## Scope-Creep Warnings

The following should be explicitly deferred:

- sparkline/history views
- browser dashboards
- GitHub or external service integrations
- push notifications
- automatic repair actions
- per-role performance scoring

Each of those can wait until the core dashboard proves that users consult it
regularly.

## Decisions

- Use a read-only dashboard model backed by runtime JSON.
- Reuse the standup/reporting shape rather than creating a new subsystem.
- Keep health scoring coarse: `on-track`, `at-risk`, `off-track`.
- Treat HOTL state as a first-class health signal, but do not make HOTL a
  requirement.

## Next Steps

1. Define the runtime JSON contract for plugin health.
2. Decide whether to implement this as a dedicated runtime command or an
   extension of the planned standup command.
3. Add a skill-level entry point that renders the dashboard and optionally
   writes a Markdown artifact.
4. Add unit coverage for health classification and missing-artifact scenarios.
