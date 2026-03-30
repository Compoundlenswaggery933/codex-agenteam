#!/usr/bin/env bats
# Tests for scripts/verify-stage.sh

SCRIPT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
VERIFY="$SCRIPT_DIR/scripts/verify-stage.sh"

setup() {
  WORK_DIR="$(mktemp -d "${BATS_TEST_TMPDIR}/verify-stage-XXXXXX")"
}

teardown() {
  rm -rf "$WORK_DIR"
}

@test "passing command returns passed:true" {
  run bash "$VERIFY" run "echo hello" --cwd "$WORK_DIR"
  [ "$status" -eq 0 ]
  echo "$output" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d['passed'] == True
assert d['exit_code'] == 0
assert 'hello' in d['stdout']
"
}

@test "failing command returns passed:false" {
  run bash "$VERIFY" run "exit 1" --cwd "$WORK_DIR"
  [ "$status" -eq 0 ]  # script itself succeeds; failure is in the JSON
  echo "$output" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d['passed'] == False
assert d['exit_code'] == 1
"
}

@test "--cwd changes working directory" {
  echo "marker" > "$WORK_DIR/testfile.txt"
  run bash "$VERIFY" run "cat testfile.txt" --cwd "$WORK_DIR"
  [ "$status" -eq 0 ]
  echo "$output" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d['passed'] == True
assert 'marker' in d['stdout']
"
}

@test "missing --cwd returns error" {
  run bash "$VERIFY" run "echo test"
  [ "$status" -ne 0 ]
}

@test "stderr is captured" {
  run bash "$VERIFY" run "echo errout >&2" --cwd "$WORK_DIR"
  [ "$status" -eq 0 ]
  echo "$output" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert 'errout' in d['stderr']
"
}

@test "nonexistent cwd returns error" {
  run bash "$VERIFY" run "echo test" --cwd "/nonexistent/path"
  [ "$status" -ne 0 ]
}

@test "command with exit code 2 returns passed:false" {
  run bash "$VERIFY" run "exit 2" --cwd "$WORK_DIR"
  [ "$status" -eq 0 ]
  echo "$output" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d['passed'] == False
assert d['exit_code'] == 2
"
}
