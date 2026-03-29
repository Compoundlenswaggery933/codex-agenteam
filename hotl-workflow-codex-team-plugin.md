---
intent: Build a Codex plugin that provides role-based team collaboration for AI-assisted development
success_criteria: Plugin installs, default roles generate valid TOML agents, standalone pipeline runs all stages, HOTL integration works via explicit opt-in, serial write policy enforces one writer at a time
risk_level: medium
auto_approve: true
---

## Steps

- [x] **Step 1: Scaffold plugin directory structure and manifest**
action: Create the plugin directory tree: .codex-plugin/, skills/ (7 subdirs), roles/, runtime/, scripts/, templates/, docs/, test/. Create .codex-plugin/plugin.json with name "codex-team", version "1.0.0", and skills directory reference. Create runtime/requirements.txt with PyYAML and toml pinned versions.
loop: false
verify: test -f .codex-plugin/plugin.json && python3 -c "import json; json.load(open('.codex-plugin/plugin.json'))" && test -f runtime/requirements.txt
gate: auto

- [x] **Step 2: Create architect role template**
action: Create roles/architect.yaml with all fields from the design doc: name, base_agent (default), description, responsibilities (4 items), participates_in (design, plan, review), model (o3), reasoning_effort (high), sandbox_mode (network-read), can_write (false), write_scope ([]), parallel_safe (true), handoff_contract, and system_instructions.
loop: false
verify: python3 -c "import yaml; d=yaml.safe_load(open('roles/architect.yaml')); assert d['name']=='architect'; assert d['can_write']==False; assert 'design' in d['participates_in']"

- [x] **Step 3: Create implementer role template**
action: Create roles/implementer.yaml. Key fields: participates_in [implement], can_write true, write_scope ["src/**", "lib/**"], parallel_safe false, sandbox_mode (network-none or appropriate). System instructions emphasize writing clean code, following existing patterns, and respecting write scope.
loop: false
verify: python3 -c "import yaml; d=yaml.safe_load(open('roles/implementer.yaml')); assert d['can_write']==True; assert d['parallel_safe']==False"

- [x] **Step 4: Create reviewer and test-writer role templates**
action: Create roles/reviewer.yaml (can_write false, participates_in [review], parallel_safe true, focus on correctness/security/regressions) and roles/test-writer.yaml (can_write true, write_scope ["tests/**", "**/*.test.*"], participates_in [test], parallel_safe true when scoped).
loop: false
verify: python3 -c "import yaml; r=yaml.safe_load(open('roles/reviewer.yaml')); t=yaml.safe_load(open('roles/test-writer.yaml')); assert r['can_write']==False; assert t['can_write']==True; assert 'tests/**' in t['write_scope']"

- [x] **Step 5: Create codex-team.yaml.template**
action: Create templates/codex-team.yaml.template matching the design doc's Project Configuration section. Include version "1", team settings (name, pipeline: standalone, parallel_writes mode: serial), role overrides section with comments, custom role example (commented out), and standalone pipeline stages (design, plan, implement, test, review) with gates.
loop: false
verify: python3 -c "import yaml; d=yaml.safe_load(open('templates/codex-team.yaml.template')); assert d['version']=='1'; assert d['team']['pipeline']=='standalone'; assert len(d['pipeline']['stages'])==5"

- [x] **Step 6: Implement runtime core — config loading and validation**
action: Create runtime/codex_team_rt.py. Implement the CLI entry point (argparse with subcommands: init, generate, dispatch, status, run, policy, roles). Implement config loading: find codex-team.yaml in current directory, parse with PyYAML, validate required fields (version, team, team.pipeline, team.parallel_writes.mode). Implement schema validation that checks pipeline is one of [standalone, hotl, dispatch-only, auto] and parallel_writes.mode is one of [serial, scoped, worktree]. Output errors as JSON to stderr.
loop: until tests pass
max_iterations: 3
verify: python3 -c "import subprocess, json; r=subprocess.run(['python3','runtime/codex_team_rt.py','--help'], capture_output=True, text=True); assert r.returncode==0; assert 'init' in r.stdout"

- [x] **Step 7: Implement runtime — role resolution and config merge**
action: Add role resolution to codex_team_rt.py. Implement: load plugin default roles from roles/*.yaml, load project overrides from codex-team.yaml roles section, deep-merge (project overrides win on leaf values, lists replace not append). For custom roles (not in plugin defaults), use project config as sole source. Add "roles list" and "roles show <name>" subcommands that output resolved roles as JSON.
loop: until tests pass
max_iterations: 3
verify: cd /Users/yimwu/Documents/workspace/codex-team && cp templates/codex-team.yaml.template codex-team.yaml && python3 runtime/codex_team_rt.py roles list | python3 -c "import sys,json; roles=json.load(sys.stdin); assert 'architect' in roles; assert 'implementer' in roles" && rm codex-team.yaml

- [x] **Step 8: Implement runtime — TOML agent generation**
action: Add "generate" subcommand to codex_team_rt.py. For each resolved role, produce a .codex/agents/<name>.toml file with flat top-level keys: name, description, model, model_reasoning_effort, sandbox_mode, developer_instructions. The developer_instructions field combines system_instructions with role metadata (participates_in, can_write, parallel_safe). Create .codex/agents/ directory if it doesn't exist. Output list of generated files as JSON.
loop: until tests pass
max_iterations: 3
verify: cd /Users/yimwu/Documents/workspace/codex-team && cp templates/codex-team.yaml.template codex-team.yaml && python3 runtime/codex_team_rt.py generate && test -f .codex/agents/architect.toml && python3 -c "import toml; d=toml.load('.codex/agents/architect.toml'); assert 'name' in d; assert 'developer_instructions' in d" && rm -rf .codex/agents codex-team.yaml

- [x] **Step 9: Implement runtime — init and state management**
action: Add "init" subcommand: validate codex-team.yaml, create .codex-team/state/ directory, generate a run-id (timestamp-based), create initial state JSON with all stages set to "pending", write_locks empty. Add "status" subcommand: read latest state file, output formatted JSON with current stage, active roles, write locks.
loop: until tests pass
max_iterations: 3
verify: cd /Users/yimwu/Documents/workspace/codex-team && cp templates/codex-team.yaml.template codex-team.yaml && python3 runtime/codex_team_rt.py init --task "test task" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'run_id' in d; assert d['stages']['design']['status']=='pending'" && rm -rf .codex-team codex-team.yaml

- [x] **Step 10: Implement runtime — dispatch with write policy**
action: Add "dispatch" subcommand: accept stage name, --task, --run-id. Resolve roles for the stage from pipeline config. Separate into writers and readers. Apply write policy (serial mode for v1): if a write lock is active, put writer in blocked list. Return dispatch plan as JSON with fields: stage, dispatch (list of role assignments with agent path, mode, write_lock), policy, gate, blocked. Add "policy check" subcommand that validates write_scope disjointness across all writing roles.
loop: until tests pass
max_iterations: 3
verify: cd /Users/yimwu/Documents/workspace/codex-team && cp templates/codex-team.yaml.template codex-team.yaml && python3 runtime/codex_team_rt.py init --task "test" > /dev/null && python3 runtime/codex_team_rt.py dispatch implement --task "test" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['stage']=='implement'; assert len(d['dispatch'])>0; assert d['policy']=='serial'" && rm -rf .codex-team codex-team.yaml

- [x] **Step 11: Implement runtime — HOTL detection**
action: Add hotl_available() function to codex_team_rt.py that checks common install locations (~/.codex/plugins/hotl, ~/.claude/plugins/cache/hotl-plugin). Add a "hotl check" subcommand that returns JSON {available: bool, path: string|null}. This is used by team-init and team-run skills.
loop: false
verify: python3 runtime/codex_team_rt.py hotl check | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'available' in d"

- [x] **Step 12: Write runtime unit tests**
action: Create test/test_runtime.py with pytest tests covering: config loading and validation (valid config, missing fields, invalid pipeline mode), role resolution and merge (default only, with overrides, custom role), TOML generation (correct fields, flat structure), init and state creation, dispatch plan generation (serial policy, correct role selection), write policy enforcement (blocks second writer). Use tmp_path fixture for isolation.
loop: until tests pass
max_iterations: 5
verify: cd /Users/yimwu/Documents/workspace/codex-team && pip install pytest pyyaml toml -q 2>/dev/null && python3 -m pytest test/test_runtime.py -v

- [x] **Step 13: Write using-codex-team router skill**
action: Create skills/using-codex-team/SKILL.md. This is the router skill that maps user intent to the appropriate skill. Include: skill metadata (name, description), routing table (set up team -> team-init, run task -> team-run, dispatch role -> team-dispatch, show status -> team-status, add role -> team-add-role, regenerate agents -> team-generate), and instructions for how Codex should interpret user requests.
loop: false
verify: test -f skills/using-codex-team/SKILL.md && test -s skills/using-codex-team/SKILL.md

- [x] **Step 14: Write team-init skill**
action: Create skills/team-init/SKILL.md. Steps: check for Python 3 and deps (offer pip install if missing), check for existing codex-team.yaml, copy template if absent, prompt for customization (team name, pipeline mode), run codex-team-rt init to validate, run codex-team-rt generate to produce .codex/agents/*.toml, check for HOTL and suggest pipeline: hotl if found.
loop: false
verify: test -f skills/team-init/SKILL.md && test -s skills/team-init/SKILL.md

- [x] **Step 15: Write team-run skill**
action: Create skills/team-run/SKILL.md. The main orchestration skill. Standalone mode: iterate pipeline stages, call codex-team-rt dispatch per stage, launch role agents as Codex subagents per dispatch plan, enforce gates between stages. HOTL mode (wrapper): for each stage resolve roles via dispatch, invoke corresponding HOTL skill with role agents as workers, manage handoffs between phases. dispatch-only mode: tell user to use team-dispatch directly.
loop: false
verify: test -f skills/team-run/SKILL.md && test -s skills/team-run/SKILL.md

- [x] **Step 16: Write team-dispatch, team-status, team-add-role, team-generate skills**
action: Create the remaining 4 skill files. team-dispatch: accept role + task, validate, check write policy, launch as subagent. team-status: read state, display formatted output. team-add-role: prompt for fields, write to codex-team.yaml, regenerate agents. team-generate: run codex-team-rt generate, report results.
loop: false
verify: test -f skills/team-dispatch/SKILL.md && test -f skills/team-status/SKILL.md && test -f skills/team-add-role/SKILL.md && test -f skills/team-generate/SKILL.md

- [x] **Step 17: Write smoke tests**
action: Create test/smoke.bats using BATS framework. Tests: plugin.json is valid JSON, all 7 SKILL.md files exist and are non-empty, all 4 role YAML files exist and are valid YAML, codex-team.yaml.template is valid YAML, codex_team_rt.py --help returns 0, requirements.txt exists.
loop: until tests pass
max_iterations: 3
verify: cd /Users/yimwu/Documents/workspace/codex-team && bats test/smoke.bats

- [x] **Step 18: Write check-update.sh script**
action: Create scripts/check-update.sh. Simple bash script that checks GitHub API for latest release/tag, compares with current version from plugin.json, outputs update suggestion to stderr if newer version available. Best-effort, never fails hard.
loop: false
verify: bash scripts/check-update.sh 2>&1; test $? -eq 0 || test $? -eq 1

- [x] **Step 19: Create setup documentation**
action: Create docs/setup.md covering: prerequisites (Python 3.8+, PyYAML, toml), installation methods (Codex plugin install, manual clone), quick start (team-init, team-run), configuration reference (codex-team.yaml fields), HOTL integration (how to enable, what changes), and available skills with invocation syntax (/skills, $team-run).
loop: false
verify: test -f docs/setup.md && test -s docs/setup.md

- [x] **Step 20: Integration verification**
action: Run full integration check. Verify plugin.json is valid. Run all smoke tests. Run all runtime unit tests. Do a manual walkthrough: copy template to codex-team.yaml, run init, run generate, verify TOML agents are correct, run dispatch for each stage, verify state transitions. Clean up test artifacts.
loop: until all checks pass
max_iterations: 3
verify:
  - type: shell
    command: cd /Users/yimwu/Documents/workspace/codex-team && python3 -c "import json; json.load(open('.codex-plugin/plugin.json'))"
  - type: shell
    command: cd /Users/yimwu/Documents/workspace/codex-team && python3 -m pytest test/test_runtime.py -v
  - type: shell
    command: cd /Users/yimwu/Documents/workspace/codex-team && bats test/smoke.bats
gate: human
