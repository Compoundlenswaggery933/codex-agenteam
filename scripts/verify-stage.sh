#!/usr/bin/env bash
set -euo pipefail

# verify-stage.sh — Execute a verification command and return structured JSON.
# Called by the run skill after each stage dispatch.
#
# Usage:
#   verify-stage.sh run <command> --cwd <path>

MAX_OUTPUT=4000  # Truncate stdout/stderr to this many chars

cmd="${1:-}"
shift || true

case "$cmd" in
  run)
    # Parse arguments
    command=""
    cwd=""
    while [ $# -gt 0 ]; do
      case "$1" in
        --cwd)
          cwd="${2:?--cwd requires a path}"
          shift 2
          ;;
        *)
          if [ -z "$command" ]; then
            command="$1"
          else
            command="$command $1"
          fi
          shift
          ;;
      esac
    done

    if [ -z "$command" ]; then
      echo '{"error": "No command provided"}' >&2
      exit 1
    fi

    if [ -z "$cwd" ]; then
      echo '{"error": "--cwd is required"}' >&2
      exit 1
    fi

    if [ ! -d "$cwd" ]; then
      echo "{\"error\": \"cwd does not exist: $cwd\"}" >&2
      exit 1
    fi

    # Execute the command in the specified directory
    stdout_file="$(mktemp)"
    stderr_file="$(mktemp)"
    trap 'rm -f "$stdout_file" "$stderr_file"' EXIT

    set +e
    (cd "$cwd" && eval "$command") >"$stdout_file" 2>"$stderr_file"
    exit_code=$?
    set -e

    # Truncate output
    stdout="$(head -c "$MAX_OUTPUT" "$stdout_file")"
    stderr="$(head -c "$MAX_OUTPUT" "$stderr_file")"

    # Escape for JSON
    stdout_escaped="$(printf '%s' "$stdout" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()), end="")' 2>/dev/null || echo '""')"
    stderr_escaped="$(printf '%s' "$stderr" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()), end="")' 2>/dev/null || echo '""')"

    if [ "$exit_code" -eq 0 ]; then
      passed="true"
    else
      passed="false"
    fi

    cat <<EOF
{"exit_code": $exit_code, "stdout": $stdout_escaped, "stderr": $stderr_escaped, "passed": $passed}
EOF
    ;;
  *)
    echo "Usage: verify-stage.sh run <command> --cwd <path>" >&2
    exit 1
    ;;
esac
