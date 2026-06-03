#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${1:-"$ROOT_DIR/cameras.json"}"
SERVER_BIN="${ROOT_DIR}/.venv/bin/mcp-camera-watch"
SERVER_ARGS=()
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"

if [[ ! -x "$SERVER_BIN" ]]; then
  SERVER_BIN="python3"
  SERVER_ARGS=(-m mcp_camera)
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

OUTPUT="$(
  printf '%s\n' \
    '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
    '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
    | "$SERVER_BIN" "${SERVER_ARGS[@]+"${SERVER_ARGS[@]}"}" --config "$CONFIG_PATH"
)"

printf '%s\n' "$OUTPUT"

SMOKE_OUTPUT="$OUTPUT" "$PYTHON_BIN" - <<'PY'
import json
import os
import sys

required_tools = {
    "camera_list",
    "camera_snapshot",
    "camera_describe",
    "camera_evaluate_once",
    "camera_watch_create",
}

try:
    responses = [json.loads(line) for line in os.environ["SMOKE_OUTPUT"].splitlines() if line.strip()]
except Exception as exc:
    print(f"Smoke test failed: MCP output was not valid JSON: {exc}", file=sys.stderr)
    sys.exit(1)

if len(responses) != 2:
    print(f"Smoke test failed: expected 2 MCP responses, got {len(responses)}.", file=sys.stderr)
    sys.exit(1)

initialize = responses[0].get("result", {})
server_info = initialize.get("serverInfo", {})
if server_info.get("name") != "mcp-camera-watch":
    print("Smoke test failed: initialize response did not identify mcp-camera-watch.", file=sys.stderr)
    sys.exit(1)

tools = responses[1].get("result", {}).get("tools", [])
tool_names = {tool.get("name") for tool in tools if isinstance(tool, dict)}
missing = sorted(required_tools - tool_names)
if missing:
    print(f"Smoke test failed: missing expected tools: {', '.join(missing)}.", file=sys.stderr)
    sys.exit(1)

print("MCP smoke test passed.", file=sys.stderr)
PY
