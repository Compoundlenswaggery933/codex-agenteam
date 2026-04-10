"""Benchmark suite validation and reporting helpers."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import yaml


def _fail(message: str) -> None:
    print(json.dumps({"error": message}), file=sys.stderr)
    sys.exit(1)


def _load_file(path_str: str, kind: str) -> tuple[Path, Any]:
    path = Path(path_str)
    if not path.exists():
        _fail(f"{kind} file not found: {path}")

    suffix = path.suffix.lower()
    try:
        with open(path) as f:
            if suffix in {".yaml", ".yml"}:
                data = yaml.safe_load(f)
            elif suffix == ".json":
                data = json.load(f)
            else:
                _fail(f"Unsupported {kind} file format: {path.suffix or '<none>'}")
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as e:
        _fail(f"Failed to read {kind} file {path}: {e}")

    return path, data


def _require_string(value: Any, field: str, errors: list[str], context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{context}: '{field}' must be a non-empty string")
        return ""
    return value.strip()


def _require_string_list(
    value: Any,
    field: str,
    errors: list[str],
    context: str,
    *,
    allow_empty: bool = True,
) -> list[str]:
    if value is None:
        return []
    invalid_items = any(not isinstance(item, str) or not item.strip() for item in value)
    if not isinstance(value, list) or invalid_items:
        errors.append(f"{context}: '{field}' must be a list of non-empty strings")
        return []
    normalized = [item.strip() for item in value]
    if not allow_empty and not normalized:
        errors.append(f"{context}: '{field}' must not be empty")
    return normalized


def _optional_number(
    value: Any,
    field: str,
    errors: list[str],
    context: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        errors.append(f"{context}: '{field}' must be numeric")
        return None
    number = float(value)
    if minimum is not None and number < minimum:
        errors.append(f"{context}: '{field}' must be >= {minimum}")
    if maximum is not None and number > maximum:
        errors.append(f"{context}: '{field}' must be <= {maximum}")
    return number


def load_benchmark_suite(path_str: str) -> dict[str, Any]:
    path, raw = _load_file(path_str, "benchmark suite")
    if not isinstance(raw, dict):
        _fail(f"Benchmark suite must contain a top-level mapping: {path}")

    errors: list[str] = []
    suite_id = _require_string(raw.get("suite_id"), "suite_id", errors, "suite")
    description = _require_string(raw.get("description"), "description", errors, "suite")
    quality_scale = raw.get("quality_scale", "0.0-1.0")
    if quality_scale != "0.0-1.0":
        errors.append("suite: 'quality_scale' must be '0.0-1.0'")

    tasks_raw = raw.get("tasks")
    if not isinstance(tasks_raw, list) or not tasks_raw:
        errors.append("suite: 'tasks' must be a non-empty list")
        tasks_raw = []

    tasks: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for idx, task_raw in enumerate(tasks_raw, start=1):
        context = f"task[{idx}]"
        if not isinstance(task_raw, dict):
            errors.append(f"{context}: task entry must be a mapping")
            continue

        task_id = _require_string(task_raw.get("id"), "id", errors, context)
        title = _require_string(task_raw.get("title"), "title", errors, context)
        category = _require_string(task_raw.get("category"), "category", errors, context)
        prompt = _require_string(task_raw.get("prompt"), "prompt", errors, context)
        difficulty = _require_string(
            task_raw.get("difficulty", "unspecified"),
            "difficulty",
            errors,
            context,
        )
        setup = _require_string_list(task_raw.get("setup", []), "setup", errors, context)
        checks = _require_string_list(task_raw.get("checks", []), "checks", errors, context)
        acceptance = _require_string_list(
            task_raw.get("acceptance", []),
            "acceptance",
            errors,
            context,
        )
        tags = _require_string_list(task_raw.get("tags", []), "tags", errors, context)
        timeout_minutes = _optional_number(
            task_raw.get("timeout_minutes", 30),
            "timeout_minutes",
            errors,
            context,
            minimum=1,
        )

        if task_id and task_id in seen_ids:
            errors.append(f"{context}: duplicate task id '{task_id}'")
        seen_ids.add(task_id)

        tasks.append(
            {
                "id": task_id,
                "title": title,
                "category": category,
                "difficulty": difficulty,
                "prompt": prompt,
                "setup": setup,
                "checks": checks,
                "acceptance": acceptance,
                "tags": tags,
                "timeout_minutes": timeout_minutes,
            }
        )

    if errors:
        _fail("; ".join(errors))

    return {
        "path": str(path),
        "suite_id": suite_id,
        "description": description,
        "quality_scale": quality_scale,
        "tasks": tasks,
    }


def load_benchmark_results(path_str: str, suite: dict[str, Any] | None = None) -> dict[str, Any]:
    path, raw = _load_file(path_str, "benchmark results")
    if not isinstance(raw, dict):
        _fail(f"Benchmark results must contain a top-level mapping: {path}")

    errors: list[str] = []
    suite_id = _require_string(raw.get("suite_id"), "suite_id", errors, "results")
    quality_scale = raw.get("quality_scale", "0.0-1.0")
    if quality_scale != "0.0-1.0":
        errors.append("results: 'quality_scale' must be '0.0-1.0'")

    strategies = _require_string_list(
        raw.get("strategies", []),
        "strategies",
        errors,
        "results",
        allow_empty=False,
    )
    runs_raw = raw.get("runs")
    if not isinstance(runs_raw, list):
        errors.append("results: 'runs' must be a list")
        runs_raw = []

    task_ids = {task["id"] for task in suite["tasks"]} if suite else set()
    seen_pairs: set[tuple[str, str]] = set()
    runs: list[dict[str, Any]] = []

    for idx, run_raw in enumerate(runs_raw, start=1):
        context = f"run[{idx}]"
        if not isinstance(run_raw, dict):
            errors.append(f"{context}: run entry must be a mapping")
            continue

        task_id = _require_string(run_raw.get("task_id"), "task_id", errors, context)
        strategy = _require_string(run_raw.get("strategy"), "strategy", errors, context)
        status = _require_string(run_raw.get("status", "recorded"), "status", errors, context)
        if status not in {"pending", "recorded"}:
            errors.append(f"{context}: 'status' must be 'pending' or 'recorded'")

        if task_ids and task_id and task_id not in task_ids:
            errors.append(f"{context}: unknown task_id '{task_id}' for suite '{suite['suite_id']}'")
        if strategies and strategy and strategy not in set(strategies):
            errors.append(f"{context}: strategy '{strategy}' not declared in results.strategies")

        pair = (task_id, strategy)
        if task_id and strategy and pair in seen_pairs:
            errors.append(f"{context}: duplicate task/strategy pair '{task_id}' + '{strategy}'")
        seen_pairs.add(pair)

        success = run_raw.get("success")
        if success is not None and not isinstance(success, bool):
            errors.append(f"{context}: 'success' must be boolean when present")

        latency_seconds = _optional_number(
            run_raw.get("latency_seconds"),
            "latency_seconds",
            errors,
            context,
            minimum=0,
        )
        cost_usd = _optional_number(
            run_raw.get("cost_usd"),
            "cost_usd",
            errors,
            context,
            minimum=0,
        )
        quality_score = _optional_number(
            run_raw.get("quality_score"),
            "quality_score",
            errors,
            context,
            minimum=0,
            maximum=1,
        )
        notes = run_raw.get("notes", "")
        if notes is not None and not isinstance(notes, str):
            errors.append(f"{context}: 'notes' must be a string when present")
        model = run_raw.get("model")
        if model is not None and not isinstance(model, str):
            errors.append(f"{context}: 'model' must be a string when present")
        run_id = run_raw.get("run_id")
        if run_id is not None and not isinstance(run_id, str):
            errors.append(f"{context}: 'run_id' must be a string when present")

        if status == "recorded":
            if success is None:
                errors.append(f"{context}: recorded runs require 'success'")
            if latency_seconds is None:
                errors.append(f"{context}: recorded runs require 'latency_seconds'")
            if cost_usd is None:
                errors.append(f"{context}: recorded runs require 'cost_usd'")
            if quality_score is None:
                errors.append(f"{context}: recorded runs require 'quality_score'")

        runs.append(
            {
                "task_id": task_id,
                "strategy": strategy,
                "status": status,
                "success": success,
                "latency_seconds": latency_seconds,
                "cost_usd": cost_usd,
                "quality_score": quality_score,
                "notes": notes or "",
                "model": model,
                "run_id": run_id,
            }
        )

    if suite and suite_id and suite_id != suite["suite_id"]:
        errors.append(f"results: suite_id '{suite_id}' does not match suite '{suite['suite_id']}'")
    if suite and quality_scale != suite["quality_scale"]:
        errors.append(
            f"results: quality_scale '{quality_scale}' does not match suite "
            f"'{suite['quality_scale']}'"
        )

    if errors:
        _fail("; ".join(errors))

    return {
        "path": str(path),
        "suite_id": suite_id,
        "quality_scale": quality_scale,
        "strategies": strategies,
        "generated_at": raw.get("generated_at"),
        "notes": raw.get("notes", ""),
        "runs": runs,
    }


def _round(value: float) -> float:
    return round(value, 4)


def _build_strategy_summary(
    strategy: str,
    runs: list[dict[str, Any]],
    total_tasks: int,
) -> dict[str, Any]:
    recorded = [run for run in runs if run["status"] == "recorded"]
    successes = sum(1 for run in recorded if run["success"] is True)
    task_coverage = len({run["task_id"] for run in recorded}) / total_tasks if total_tasks else 0.0
    latency_values = [
        run["latency_seconds"] for run in recorded if run["latency_seconds"] is not None
    ]
    cost_values = [run["cost_usd"] for run in recorded if run["cost_usd"] is not None]
    quality_values = [run["quality_score"] for run in recorded if run["quality_score"] is not None]

    run_count = len(recorded)
    return {
        "strategy": strategy,
        "recorded_runs": run_count,
        "pending_runs": sum(1 for run in runs if run["status"] == "pending"),
        "task_coverage": _round(task_coverage),
        "success_rate": _round(successes / run_count) if run_count else 0.0,
        "avg_latency_seconds": _round(sum(latency_values) / len(latency_values))
        if latency_values
        else None,
        "avg_cost_usd": _round(sum(cost_values) / len(cost_values)) if cost_values else None,
        "total_cost_usd": _round(sum(cost_values)) if cost_values else 0.0,
        "avg_quality_score": _round(sum(quality_values) / len(quality_values))
        if quality_values
        else None,
    }


def build_benchmark_report(suite: dict[str, Any], results: dict[str, Any]) -> dict[str, Any]:
    total_tasks = len(suite["tasks"])
    task_map = {task["id"]: task for task in suite["tasks"]}
    strategies = results["strategies"]

    all_runs_by_strategy: dict[str, list[dict[str, Any]]] = {
        strategy: [] for strategy in strategies
    }
    category_pairs: dict[tuple[str, str], list[dict[str, Any]]] = {}
    missing_runs: list[dict[str, str]] = []

    for run in results["runs"]:
        if run["strategy"] in all_runs_by_strategy:
            all_runs_by_strategy[run["strategy"]].append(run)

    run_lookup = {(run["task_id"], run["strategy"]): run for run in results["runs"]}
    for task in suite["tasks"]:
        for strategy in strategies:
            run = run_lookup.get((task["id"], strategy))
            if run is None or run["status"] != "recorded":
                missing_runs.append(
                    {
                        "task_id": task["id"],
                        "strategy": strategy,
                        "status": "missing" if run is None else run["status"],
                    }
                )
                continue
            category_pairs.setdefault((strategy, task["category"]), []).append(run)

    strategy_summary = [
        _build_strategy_summary(strategy, all_runs_by_strategy[strategy], total_tasks)
        for strategy in strategies
    ]
    strategy_summary.sort(
        key=lambda row: (
            -row["success_rate"],
            -(row["avg_quality_score"] or 0.0),
            row["avg_cost_usd"] if row["avg_cost_usd"] is not None else float("inf"),
            row["avg_latency_seconds"] if row["avg_latency_seconds"] is not None else float("inf"),
            -row["task_coverage"],
            row["strategy"],
        )
    )
    for idx, row in enumerate(strategy_summary, start=1):
        row["rank"] = idx

    category_breakdown: list[dict[str, Any]] = []
    for strategy in strategies:
        categories = sorted({task["category"] for task in suite["tasks"]})
        for category in categories:
            runs = category_pairs.get((strategy, category), [])
            successes = sum(1 for run in runs if run["success"] is True)
            category_breakdown.append(
                {
                    "strategy": strategy,
                    "category": category,
                    "recorded_runs": len(runs),
                    "success_rate": _round(successes / len(runs)) if runs else 0.0,
                    "avg_latency_seconds": _round(
                        sum(
                            run["latency_seconds"]
                            for run in runs
                            if run["latency_seconds"] is not None
                        )
                        / len(runs)
                    )
                    if runs
                    else None,
                    "avg_cost_usd": _round(
                        sum(run["cost_usd"] for run in runs if run["cost_usd"] is not None)
                        / len(runs)
                    )
                    if runs
                    else None,
                    "avg_quality_score": _round(
                        sum(
                            run["quality_score"] for run in runs if run["quality_score"] is not None
                        )
                        / len(runs)
                    )
                    if runs
                    else None,
                }
            )

    recorded_runs = [run for run in results["runs"] if run["status"] == "recorded"]
    report = {
        "suite_id": suite["suite_id"],
        "suite_description": suite["description"],
        "quality_scale": suite["quality_scale"],
        "task_count": total_tasks,
        "strategy_count": len(strategies),
        "expected_run_count": total_tasks * len(strategies),
        "recorded_run_count": len(recorded_runs),
        "pending_run_count": len(missing_runs),
        "strategies": strategy_summary,
        "category_breakdown": category_breakdown,
        "missing_runs": missing_runs,
        "tasks": list(task_map.values()),
    }
    return report


def _format_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _format_number(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{decimals}f}"


def render_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        f"# Benchmark Report: {report['suite_id']}",
        "",
        report["suite_description"],
        "",
        "## Summary",
        "",
        f"- Tasks: {report['task_count']}",
        f"- Strategies: {report['strategy_count']}",
        f"- Recorded runs: {report['recorded_run_count']} / {report['expected_run_count']}",
        f"- Pending or missing runs: {report['pending_run_count']}",
        f"- Quality scale: {report['quality_scale']}",
        "",
        "## Strategy Comparison",
        "",
        (
            "| Rank | Strategy | Success Rate | Avg Quality | "
            "Avg Latency (s) | Avg Cost ($) | Coverage |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    for row in report["strategies"]:
        lines.append(
            "| "
            f"{row['rank']} | "
            f"{row['strategy']} | "
            f"{_format_percent(row['success_rate'])} | "
            f"{_format_number(row['avg_quality_score'])} | "
            f"{_format_number(row['avg_latency_seconds'])} | "
            f"{_format_number(row['avg_cost_usd'])} | "
            f"{_format_percent(row['task_coverage'])} |"
        )

    lines.extend(
        [
            "",
            "## Category Breakdown",
            "",
            (
                "| Strategy | Category | Recorded Runs | Success Rate | "
                "Avg Quality | Avg Latency (s) | Avg Cost ($) |"
            ),
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in report["category_breakdown"]:
        lines.append(
            "| "
            f"{row['strategy']} | "
            f"{row['category']} | "
            f"{row['recorded_runs']} | "
            f"{_format_percent(row['success_rate'])} | "
            f"{_format_number(row['avg_quality_score'])} | "
            f"{_format_number(row['avg_latency_seconds'])} | "
            f"{_format_number(row['avg_cost_usd'])} |"
        )

    if report["missing_runs"]:
        lines.extend(["", "## Missing Runs", ""])
        for row in report["missing_runs"]:
            lines.append(f"- `{row['strategy']}` on `{row['task_id']}` ({row['status']})")

    return "\n".join(lines) + "\n"


def cmd_benchmark_validate(args) -> None:
    """Validate a benchmark suite and optional results file."""
    suite = load_benchmark_suite(args.suite)
    output = {
        "valid": True,
        "suite_id": suite["suite_id"],
        "task_count": len(suite["tasks"]),
        "quality_scale": suite["quality_scale"],
    }

    if getattr(args, "results", None):
        results = load_benchmark_results(args.results, suite)
        recorded_runs = sum(1 for run in results["runs"] if run["status"] == "recorded")
        output.update(
            {
                "results_valid": True,
                "strategy_count": len(results["strategies"]),
                "recorded_run_count": recorded_runs,
                "pending_run_count": len(results["runs"]) - recorded_runs,
            }
        )

    print(json.dumps(output))


def cmd_benchmark_init_results(args) -> None:
    """Create a benchmark results template for a suite."""
    suite = load_benchmark_suite(args.suite)
    strategies = []
    for strategy in args.strategy:
        name = strategy.strip()
        if name and name not in strategies:
            strategies.append(name)
    if not strategies:
        _fail("At least one --strategy value is required")

    payload = {
        "suite_id": suite["suite_id"],
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "quality_scale": suite["quality_scale"],
        "strategies": strategies,
        "notes": (
            "Fill in each run entry after executing the task with the named strategy. "
            "Set status=recorded once success, latency_seconds, cost_usd, and "
            "quality_score have been collected."
        ),
        "runs": [
            {
                "task_id": task["id"],
                "strategy": strategy,
                "status": "pending",
                "success": None,
                "latency_seconds": None,
                "cost_usd": None,
                "quality_score": None,
                "notes": "",
                "model": None,
                "run_id": None,
            }
            for task in suite["tasks"]
            for strategy in strategies
        ],
    }

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(payload, f, indent=2)
        print(
            json.dumps(
                {
                    "created": True,
                    "output_path": str(output_path),
                    "suite_id": suite["suite_id"],
                    "strategy_count": len(strategies),
                    "run_count": len(payload["runs"]),
                }
            )
        )
        return

    print(json.dumps(payload, indent=2))


def cmd_benchmark_report(args) -> None:
    """Aggregate recorded runs into benchmark summary metrics."""
    suite = load_benchmark_suite(args.suite)
    results = load_benchmark_results(args.results, suite)
    report = build_benchmark_report(suite, results)

    if args.markdown_out:
        markdown_path = Path(args.markdown_out)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        with open(markdown_path, "w") as f:
            f.write(render_markdown_report(report))
        report["markdown_path"] = str(markdown_path)

    print(json.dumps(report))
