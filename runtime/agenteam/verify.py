"""Verification planning, recording, and gate management for the verified pipeline."""

import json
import os
import sys
from pathlib import Path

from .config import resolve_team_config
from .state import get_pipeline_stages


def detect_verify_command(cwd: str | None = None) -> str | None:
    """Auto-detect a verification command from repo signals in the given directory.

    Checks for:
      - pytest.ini, pyproject.toml with [tool.pytest], or tests/ dir -> "python3 -m pytest -v"
      - package.json with test script -> "npm test"
      - go.mod -> "go test ./..."
      - Cargo.toml -> "cargo test"
      - Makefile with test target -> "make test"

    Returns the verify command string, or None if nothing detected.
    """
    d = Path(cwd) if cwd else Path.cwd()

    # Python / pytest
    if (d / "pytest.ini").exists():
        return "python3 -m pytest -v"

    pyproject = d / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text()
            if "[tool.pytest" in content:
                return "python3 -m pytest -v"
        except OSError:
            pass

    if (d / "tests").is_dir():
        return "python3 -m pytest -v"

    # Node.js / npm
    pkg_json = d / "package.json"
    if pkg_json.exists():
        try:
            import json as _json

            pkg = _json.loads(pkg_json.read_text())
            scripts = pkg.get("scripts", {})
            if "test" in scripts:
                return "npm test"
        except (OSError, json.JSONDecodeError):
            pass

    # Go
    if (d / "go.mod").exists():
        return "go test ./..."

    # Rust
    if (d / "Cargo.toml").exists():
        return "cargo test"

    # Makefile
    makefile = d / "Makefile"
    if makefile.exists():
        try:
            content = makefile.read_text()
            for line in content.splitlines():
                stripped = line.strip()
                if stripped == "test:" or stripped.startswith("test:"):
                    return "make test"
        except OSError:
            pass

    return None


def _resolve_cwd(config: dict, run_id: str | None) -> str:
    """Resolve the working directory for verification.

    In worktree mode, returns the worktree path. Otherwise returns cwd.
    """
    _, isolation_mode = resolve_team_config(config)

    if isolation_mode == "worktree" and run_id:
        # Check state for worktree path
        state_path = Path.cwd() / ".agenteam" / "state" / f"{run_id}.json"
        if state_path.exists():
            with open(state_path) as f:
                state = json.load(f)
            wt = state.get("worktree_path")
            if wt:
                return str(Path.cwd() / wt)

    return str(Path.cwd())


def _load_state(run_id: str) -> dict:
    """Load a run state file by run_id."""
    state_path = Path.cwd() / ".agenteam" / "state" / f"{run_id}.json"
    if not state_path.exists():
        print(
            json.dumps({"error": f"Run {run_id} not found"}),
            file=sys.stderr,
        )
        sys.exit(1)
    with open(state_path) as f:
        return json.load(f)


def _save_state(run_id: str, state: dict) -> None:
    """Save a run state file."""
    state_path = Path.cwd() / ".agenteam" / "state" / f"{run_id}.json"
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)


def cmd_verify_plan(args, config: dict) -> None:
    """Return a verification plan for a pipeline stage.

    Arguments: <stage> --run-id <id>
    Returns JSON with: stage, verify, source, max_retries, attempt, cwd
    """
    stage_name = args.stage
    run_id = getattr(args, "run_id", None)

    stages = get_pipeline_stages(config)
    stage_config = None
    for s in stages:
        if s["name"] == stage_name:
            stage_config = s
            break

    if not stage_config:
        print(
            json.dumps({"error": f"Stage '{stage_name}' not found in pipeline"}),
            file=sys.stderr,
        )
        sys.exit(1)

    # Determine verify command and source
    verify = stage_config.get("verify")
    source = "config" if verify else None
    max_retries = stage_config.get("max_retries", 0)

    if verify is None:
        # Auto-detect
        cwd = _resolve_cwd(config, run_id)
        detected = detect_verify_command(cwd)
        if detected:
            verify = detected
            source = "auto-detected"
        else:
            source = "none"

    # Determine current attempt from state
    attempt = 0
    if run_id and verify:
        state_path = Path.cwd() / ".agenteam" / "state" / f"{run_id}.json"
        if state_path.exists():
            with open(state_path) as f:
                state = json.load(f)
            stage_state = state.get("stages", {}).get(stage_name, {})
            attempts = stage_state.get("verify_attempts", [])
            attempt = len(attempts) + 1
        else:
            attempt = 1
    elif verify:
        attempt = 1

    result: dict = {
        "stage": stage_name,
        "verify": verify,
        "source": source,
        "max_retries": max_retries,
        "attempt": attempt,
    }

    # Include cwd only when there is a verify command
    if verify:
        result["cwd"] = _resolve_cwd(config, run_id)

    print(json.dumps(result))


def cmd_record_verify(args, config: dict) -> None:
    """Record a verification result for a stage.

    Arguments: --run-id <id> --stage <stage> --result pass|fail [--output "..."]
    """
    run_id = args.run_id
    stage_name = args.stage
    result_val = args.result
    output = getattr(args, "output", None) or ""

    state = _load_state(run_id)

    stages = state.get("stages", {})
    if stage_name not in stages:
        print(
            json.dumps({"error": f"Stage '{stage_name}' not found in state"}),
            file=sys.stderr,
        )
        sys.exit(1)

    stage_state = stages[stage_name]

    # Initialize verify_attempts if needed
    if "verify_attempts" not in stage_state:
        stage_state["verify_attempts"] = []

    attempt_num = len(stage_state["verify_attempts"]) + 1
    entry: dict = {
        "attempt": attempt_num,
        "result": result_val,
    }
    if output:
        entry["output"] = output

    stage_state["verify_attempts"].append(entry)
    stage_state["verify_result"] = result_val

    _save_state(run_id, state)

    print(json.dumps({"recorded": True, "stage": stage_name, "attempt": attempt_num, "result": result_val}))


def cmd_final_verify_plan(args, config: dict) -> None:
    """Return a final verification plan for the run.

    Arguments: --run-id <id>
    Returns JSON with: commands, policy, max_retries, source, cwd
    """
    run_id = getattr(args, "run_id", None)

    # Read from config
    commands = config.get("final_verify")
    policy = config.get("final_verify_policy", "block")
    max_retries = config.get("final_verify_max_retries", 1)

    if commands:
        # Ensure commands is a list
        if isinstance(commands, str):
            commands = [commands]
        source = "config"
    else:
        # Auto-detect
        cwd = _resolve_cwd(config, run_id)
        detected = detect_verify_command(cwd)
        if detected:
            commands = [detected]
            source = "auto-detected"
        else:
            commands = []
            source = "none"
            policy = "unverified"

    result: dict = {
        "commands": commands,
        "policy": policy,
        "max_retries": max_retries,
        "source": source,
    }

    # Include cwd only when there are commands
    if commands:
        result["cwd"] = _resolve_cwd(config, run_id)

    print(json.dumps(result))


def cmd_record_gate(args, config: dict) -> None:
    """Record a gate decision for a stage.

    Arguments: --run-id <id> --stage <stage> --gate-type <type> --result <approved|rejected> [--verdict "..."]
    """
    run_id = args.run_id
    stage_name = args.stage
    gate_type = args.gate_type
    result_val = args.result
    verdict = getattr(args, "verdict", None) or ""

    state = _load_state(run_id)

    stages = state.get("stages", {})
    if stage_name not in stages:
        print(
            json.dumps({"error": f"Stage '{stage_name}' not found in state"}),
            file=sys.stderr,
        )
        sys.exit(1)

    stage_state = stages[stage_name]

    stage_state["gate"] = gate_type
    stage_state["gate_result"] = result_val

    # For agent gates, record which agent type approved
    if gate_type in ("reviewer", "qa"):
        stage_state["gate_agent"] = gate_type

    if verdict:
        stage_state["gate_verdict"] = verdict

    _save_state(run_id, state)

    response: dict = {
        "recorded": True,
        "stage": stage_name,
        "gate_type": gate_type,
        "result": result_val,
    }
    if verdict:
        response["verdict"] = verdict

    print(json.dumps(response))
