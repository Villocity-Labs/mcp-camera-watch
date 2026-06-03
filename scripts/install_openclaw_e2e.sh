#!/usr/bin/env bash
set -euo pipefail

ORIGINAL_CWD="$(pwd)"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="$ROOT_DIR/cameras.json"
MODE="auto"
FORCE=0
RESTART_GATEWAY=0
OPENCLAW_BIN="${OPENCLAW_BIN:-}"
OPENCLAW_PROFILE=""
OPENCLAW_DEV=0
OPENCLAW_TIMEOUT_MS="${OPENCLAW_TIMEOUT_MS:-10000}"
OPENCLAW_CMD=()
WORK_DIR=""
REGISTER_CHANGED=0
SERVER_NAME="mcp-camera-watch"

usage() {
  cat <<'EOF'
Usage: scripts/install_openclaw_e2e.sh [options]

Install MCP Camera Watch locally, smoke test the MCP stdio server, detect
OpenClaw, and safely register it with a running OpenClaw/Clawbot setup.

Options:
  --mode auto|server|plugin   Registration path. Default: auto.
                              auto uses the standard MCP server in this repo.
  --config PATH               Camera config path. Default: ./cameras.json.
  --force                     Replace a conflicting existing registration.
  --restart-gateway           Run openclaw gateway restart --safe after changes.
  --openclaw-bin PATH         OpenClaw CLI path. Default: first openclaw in PATH.
  --openclaw-profile NAME     Pass --profile NAME to OpenClaw.
  --openclaw-dev              Pass --dev to OpenClaw.
  -h, --help                  Show this help.

Environment:
  OPENCLAW_BIN                Alternate OpenClaw CLI path.
  OPENCLAW_TIMEOUT_MS         OpenClaw probe timeout in milliseconds.
EOF
}

log() {
  printf '\n==> %s\n' "$*"
}

warn() {
  printf 'WARN: %s\n' "$*" >&2
}

die() {
  local message="$1"
  local code="${2:-1}"
  printf 'ERROR: %s\n' "$message" >&2
  exit "$code"
}

cleanup() {
  if [[ -n "$WORK_DIR" && -d "$WORK_DIR" ]]; then
    rm -rf "$WORK_DIR"
  fi
}

trap cleanup EXIT

abs_path() {
  local input="$1"
  local path
  if [[ "$input" = /* ]]; then
    path="$input"
  else
    path="$ORIGINAL_CWD/$input"
  fi

  local dir
  local base
  dir="$(dirname "$path")"
  base="$(basename "$path")"

  if [[ -d "$dir" ]]; then
    (cd "$dir" && printf '%s/%s\n' "$PWD" "$base")
  else
    printf '%s\n' "$path"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      [[ $# -ge 2 ]] || die "--mode requires auto, server, or plugin."
      MODE="$2"
      shift 2
      ;;
    --config)
      [[ $# -ge 2 ]] || die "--config requires a path."
      CONFIG_PATH="$(abs_path "$2")"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --restart-gateway)
      RESTART_GATEWAY=1
      shift
      ;;
    --openclaw-bin)
      [[ $# -ge 2 ]] || die "--openclaw-bin requires a path."
      OPENCLAW_BIN="$2"
      shift 2
      ;;
    --openclaw-profile)
      [[ $# -ge 2 ]] || die "--openclaw-profile requires a profile name."
      OPENCLAW_PROFILE="$2"
      shift 2
      ;;
    --openclaw-dev)
      OPENCLAW_DEV=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown option: $1"
      ;;
  esac
done

case "$MODE" in
  auto|server|plugin)
    ;;
  *)
    die "--mode must be auto, server, or plugin."
    ;;
esac

WORK_DIR="$(mktemp -d)"

python_bin() {
  if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    printf '%s\n' "$ROOT_DIR/.venv/bin/python"
  else
    printf '%s\n' "python3"
  fi
}

detect_openclaw() {
  local bin="$OPENCLAW_BIN"
  if [[ -z "$bin" ]]; then
    bin="$(command -v openclaw || true)"
  fi

  [[ -n "$bin" ]] || die "OpenClaw CLI was not found in PATH. Install or start OpenClaw, then rerun this script." 2
  [[ -x "$bin" || "$bin" == "openclaw" ]] || die "OpenClaw CLI is not executable: $bin" 2

  OPENCLAW_CMD=("$bin")
  if [[ "$OPENCLAW_DEV" == "1" ]]; then
    OPENCLAW_CMD+=("--dev")
  fi
  if [[ -n "$OPENCLAW_PROFILE" ]]; then
    OPENCLAW_CMD+=("--profile" "$OPENCLAW_PROFILE")
  fi
}

oc() {
  "${OPENCLAW_CMD[@]}" "$@"
}

supports_openclaw_command() {
  oc "$@" --help >/dev/null 2>&1
}

json_files_equal() {
  "$(python_bin)" - "$1" "$2" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as left_file:
    left = json.load(left_file)
with open(sys.argv[2], encoding="utf-8") as right_file:
    right = json.load(right_file)

sys.exit(0 if left == right else 1)
PY
}

ensure_openclaw_running() {
  local quiet="${1:-0}"
  local status_json="$WORK_DIR/openclaw-gateway-status.json"
  local status_err="$WORK_DIR/openclaw-gateway-status.err"
  local health_json="$WORK_DIR/openclaw-health.json"
  local health_err="$WORK_DIR/openclaw-health.err"

  if oc gateway status --json --require-rpc --timeout "$OPENCLAW_TIMEOUT_MS" >"$status_json" 2>"$status_err"; then
    return 0
  fi

  if oc health --json --timeout "$OPENCLAW_TIMEOUT_MS" >"$health_json" 2>"$health_err"; then
    return 0
  fi

  if [[ "$quiet" == "1" ]]; then
    return 1
  fi

  if [[ -s "$status_err" ]]; then
    sed 's/^/  /' "$status_err" >&2
  fi
  if [[ -s "$health_err" ]]; then
    sed 's/^/  /' "$health_err" >&2
  fi
  return 1
}

wait_for_openclaw_running() {
  local deadline=$((SECONDS + 60))

  while (( SECONDS < deadline )); do
    if ensure_openclaw_running 1; then
      return 0
    fi
    sleep 2
  done

  ensure_openclaw_running
}

select_mode() {
  case "$MODE" in
    server)
      supports_openclaw_command mcp set && supports_openclaw_command mcp show \
        || die "This OpenClaw CLI does not support 'openclaw mcp set/show'." 2
      printf '%s\n' "server"
      ;;
    plugin)
      die "Plugin mode is not available yet: this repository does not include an OpenClaw plugin package. Use --mode server or --mode auto." 2
      ;;
    auto)
      if supports_openclaw_command mcp set && supports_openclaw_command mcp show; then
        printf '%s\n' "server"
      else
        die "OpenClaw was detected, but MCP registration commands are not available." 2
      fi
      ;;
  esac
}

register_server() {
  local server_json="$WORK_DIR/$SERVER_NAME.server.json"
  local existing_json="$WORK_DIR/existing-$SERVER_NAME.server.json"
  local actual_json="$WORK_DIR/actual-$SERVER_NAME.server.json"

  log "Generating MCP server definition"
  "$ROOT_DIR/.venv/bin/mcp-camera-watch" --print-clawbot-config --config "$CONFIG_PATH" >"$server_json"

  if [[ "$CONFIG_PATH" == "$ROOT_DIR/cameras.json" ]]; then
    cp "$server_json" "$ROOT_DIR/clawbot-mcp-camera-watch.server.json"
  fi

  if oc mcp show "$SERVER_NAME" --json >"$existing_json" 2>/dev/null; then
    if json_files_equal "$existing_json" "$server_json"; then
      log "OpenClaw already has the matching $SERVER_NAME server registration"
    elif [[ "$FORCE" == "1" ]]; then
      log "Replacing existing OpenClaw $SERVER_NAME server registration"
      oc mcp set "$SERVER_NAME" "$(<"$server_json")"
      REGISTER_CHANGED=1
    else
      die "OpenClaw already has a $SERVER_NAME MCP server with different settings. Rerun with --force to replace it, or inspect it with 'openclaw mcp show $SERVER_NAME --json'." 3
    fi
  else
    log "Registering $SERVER_NAME with OpenClaw MCP config"
    oc mcp set "$SERVER_NAME" "$(<"$server_json")"
    REGISTER_CHANGED=1
  fi

  oc mcp show "$SERVER_NAME" --json >"$actual_json"
  json_files_equal "$actual_json" "$server_json" \
    || die "OpenClaw MCP registration did not match the generated server definition." 1

  log "OpenClaw MCP server registration verified"
}

restart_gateway_if_requested() {
  if [[ "$RESTART_GATEWAY" != "1" ]]; then
    if [[ "$REGISTER_CHANGED" == "1" ]]; then
      warn "OpenClaw config changed. Restart the gateway if your setup does not hot-reload config, or rerun this script with --restart-gateway."
    fi
    return 0
  fi

  supports_openclaw_command gateway restart \
    || die "This OpenClaw CLI does not support 'openclaw gateway restart'." 2

  log "Restarting OpenClaw gateway safely"
  oc gateway restart --safe --json >"$WORK_DIR/openclaw-gateway-restart.json"

  log "Verifying OpenClaw gateway after restart"
  wait_for_openclaw_running \
    || die "OpenClaw gateway did not become reachable after restart." 2
}

main() {
  cd "$ROOT_DIR"

  local config_dir
  config_dir="$(dirname "$CONFIG_PATH")"
  [[ -d "$config_dir" ]] || die "Config directory does not exist: $config_dir"

  log "Installing MCP Camera Watch locally"
  "$ROOT_DIR/scripts/install_local.sh"

  if [[ ! -f "$CONFIG_PATH" ]]; then
    log "Creating camera config at $CONFIG_PATH"
    "$ROOT_DIR/.venv/bin/mcp-camera-watch" --init-config --config "$CONFIG_PATH"
  fi

  log "Running local MCP smoke test"
  "$ROOT_DIR/scripts/smoke_mcp.sh" "$CONFIG_PATH"

  detect_openclaw
  log "Detected OpenClaw CLI: ${OPENCLAW_CMD[*]}"
  oc --version

  log "Checking for a running OpenClaw gateway"
  ensure_openclaw_running \
    || die "OpenClaw CLI was found, but the gateway is not reachable. Start OpenClaw/Clawbot, then rerun this script." 2

  local selected_mode
  selected_mode="$(select_mode)"
  log "Using OpenClaw registration mode: $selected_mode"

  register_server
  restart_gateway_if_requested

  cat <<EOF

MCP Camera Watch OpenClaw end-to-end check passed.

Mode: $selected_mode
Config: $CONFIG_PATH
OpenClaw: ${OPENCLAW_CMD[*]}

Next safe prompt for Clawbot/OpenClaw:
  List my configured cameras.
EOF
}

main "$@"
