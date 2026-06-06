#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

NEEDS_INSTALL=0
if [[ ! -x .venv/bin/mcp-camera-watch ]]; then
  NEEDS_INSTALL=1
elif [[ "$(uname -s)" == "Darwin" && ! -x .camera-mcp/bin/capture-macos-camera ]]; then
  NEEDS_INSTALL=1
fi

if [[ "$NEEDS_INSTALL" == "1" ]]; then
  scripts/install_local.sh
fi

exec .venv/bin/mcp-camera-watch --web --config "${MCP_CAMERA_CONFIG:-./cameras.json}" "$@"
