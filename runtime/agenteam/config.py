"""Config loading, validation, and team config resolution."""

import json
import sys
from pathlib import Path

import yaml

from .constants import (
    ISOLATION_MAP,
    VALID_ISOLATION,
    VALID_PIPELINES,
    VALID_WRITE_MODES,
)


def resolve_team_config(config: dict) -> tuple[str | None, str]:
    """Resolve (pipeline_mode, isolation_mode) from either new or legacy schema.

    New schema (flat keys):
      isolation: branch | worktree | none
      pipeline: hotl  (top-level string, optional -- only "hotl" is meaningful)

    Legacy schema (nested team block):
      team.pipeline: standalone | hotl | dispatch-only | auto
      team.parallel_writes.mode: serial | scoped | worktree

    Returns:
      (pipeline_mode, isolation_mode)
      pipeline_mode is None for auto-detect, or "hotl" for explicit HOTL.
      isolation_mode is "branch" (default), "worktree", or "none".
    """
    # New schema (flat keys)
    isolation = config.get("isolation")
    # "pipeline" can be either a string (mode) or a dict (stages).
    # Only treat it as a mode if it's a string.
    pipeline_val = config.get("pipeline")
    pipeline = pipeline_val if isinstance(pipeline_val, str) else None

    # Legacy schema (nested team block)
    team = config.get("team", {})
    if isinstance(team, dict):
        if not pipeline:
            legacy_pipeline = team.get("pipeline")
            if legacy_pipeline == "hotl":
                pipeline = "hotl"
            # standalone, auto, dispatch-only all resolve to None (auto-detect)

        if not isolation:
            pw = team.get("parallel_writes", {})
            if isinstance(pw, dict):
                legacy_mode = pw.get("mode")
                if legacy_mode:
                    isolation = ISOLATION_MAP.get(legacy_mode, legacy_mode)

    # Defaults
    isolation = isolation or "branch"
    # pipeline: None means auto-detect at runtime
    return pipeline, isolation


def find_config(path_or_dir: str | None = None) -> Path:
    """Locate config file. Accepts a direct file path or a directory to search."""
    if path_or_dir:
        p = Path(path_or_dir)
        # If it's a file path, use it directly
        if p.is_file():
            return p
        # If it's a directory, search within it
        if p.is_dir():
            preferred = p / ".agenteam" / "config.yaml"
            if preferred.exists():
                return preferred
            legacy = p / "agenteam.yaml"
            if legacy.exists():
                return legacy
            raise FileNotFoundError(
                f"Config not found in {p}. Expected .agenteam/config.yaml or agenteam.yaml"
            )
        raise FileNotFoundError(f"Config path does not exist: {p}")

    # Default: search current directory
    d = Path.cwd()
    preferred = d / ".agenteam" / "config.yaml"
    if preferred.exists():
        return preferred
    legacy = d / "agenteam.yaml"
    if legacy.exists():
        return legacy
    raise FileNotFoundError(
        f"Config not found in {d}. Expected .agenteam/config.yaml or agenteam.yaml"
    )


def load_config(path: Path) -> dict:
    """Load and validate config file."""
    with open(path) as f:
        config: dict = yaml.safe_load(f)
    validate_config(config)
    return config


def validate_config(config: dict) -> None:
    """Validate required fields and enum values (new + legacy schema)."""
    errors = []

    if not isinstance(config, dict):
        raise ValueError("Config must be a YAML mapping")

    if "version" not in config:
        errors.append("Missing required field: version")

    # --- New schema validation (flat keys) ---
    isolation = config.get("isolation")
    if isolation and isolation not in VALID_ISOLATION:
        errors.append(
            f"Invalid isolation: '{isolation}'. "
            f"Must be one of: {', '.join(sorted(VALID_ISOLATION))}"
        )

    # Top-level "pipeline" can be a string (mode) or dict (stages).
    # Only validate if it's a string.
    pipeline_val = config.get("pipeline")
    if isinstance(pipeline_val, str) and pipeline_val != "hotl":
        errors.append(
            f"Invalid pipeline: '{pipeline_val}'. "
            "Only 'hotl' is valid as a top-level string. "
            "Omit for auto-detect, or use pipeline.stages for stage definitions."
        )

    # --- Legacy schema validation (nested team block) ---
    team = config.get("team", {})
    if not isinstance(team, dict):
        errors.append("'team' must be a mapping")
    elif team:
        # Emit deprecation warnings for legacy keys
        legacy_pipeline = team.get("pipeline")
        if legacy_pipeline:
            if legacy_pipeline not in VALID_PIPELINES:
                errors.append(
                    f"Invalid team.pipeline: '{legacy_pipeline}'. "
                    f"Must be one of: {', '.join(sorted(VALID_PIPELINES))}"
                )
            else:
                print(
                    json.dumps(
                        {
                            "warning": (
                                f"Legacy config key 'team.pipeline: {legacy_pipeline}' found. "
                                "Consider using top-level 'pipeline: hotl' "
                                "or omitting for auto-detect."
                            )
                        }
                    ),
                    file=sys.stderr,
                )

        pw = team.get("parallel_writes", {})
        if isinstance(pw, dict) and pw:
            mode = pw.get("mode")
            if mode:
                if mode not in VALID_WRITE_MODES:
                    errors.append(
                        f"Invalid team.parallel_writes.mode: '{mode}'. "
                        f"Must be one of: {', '.join(sorted(VALID_WRITE_MODES))}"
                    )
                else:
                    print(
                        json.dumps(
                            {
                                "warning": (
                                    f"Legacy config key 'team.parallel_writes.mode: {mode}' found. "
                                    "Consider using top-level "
                                    f"'isolation: {ISOLATION_MAP.get(mode, mode)}'."
                                )
                            }
                        ),
                        file=sys.stderr,
                    )

    # --- Profile validation ---
    pipeline_dict = config.get("pipeline", {})
    if isinstance(pipeline_dict, dict):
        profiles = pipeline_dict.get("profiles", {})
        if isinstance(profiles, dict) and profiles:
            # Collect valid stage names from pipeline.stages
            pipeline_stages = pipeline_dict.get("stages", [])
            valid_stage_names = set()
            stage_rework_map: dict[str, str | None] = {}
            if isinstance(pipeline_stages, list):
                for s in pipeline_stages:
                    if isinstance(s, dict) and "name" in s:
                        valid_stage_names.add(s["name"])
                        stage_rework_map[s["name"]] = s.get("rework_to")

            for profile_name, profile_def in profiles.items():
                if not isinstance(profile_def, dict):
                    errors.append(f"Profile '{profile_name}' must be a mapping")
                    continue

                stages_list = profile_def.get("stages")
                if not stages_list or not isinstance(stages_list, list):
                    errors.append(f"Profile '{profile_name}': 'stages' must be a non-empty list")
                    continue

                # Check for unknown stage names
                profile_stage_set = set()
                for sname in stages_list:
                    if not isinstance(sname, str):
                        errors.append(
                            f"Profile '{profile_name}': stage names must be strings, got {type(sname).__name__}"
                        )
                    elif sname not in valid_stage_names:
                        errors.append(
                            f"Profile '{profile_name}': unknown stage '{sname}'"
                        )
                    elif sname in profile_stage_set:
                        errors.append(
                            f"Profile '{profile_name}': duplicate stage '{sname}'"
                        )
                    else:
                        profile_stage_set.add(sname)

                # Cross-stage rework validation
                for sname in profile_stage_set:
                    rework_target = stage_rework_map.get(sname)
                    if rework_target and rework_target not in profile_stage_set:
                        errors.append(
                            f"Profile '{profile_name}': stage '{sname}' has rework_to "
                            f"'{rework_target}' which is not in this profile"
                        )

                # Hints type check
                hints = profile_def.get("hints")
                if hints is not None:
                    if not isinstance(hints, list) or not all(isinstance(h, str) for h in hints):
                        errors.append(
                            f"Profile '{profile_name}': 'hints' must be a list of strings"
                        )

    if errors:
        raise ValueError("; ".join(errors))
