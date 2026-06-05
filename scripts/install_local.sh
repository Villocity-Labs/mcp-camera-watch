#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests

if [[ "$(uname -s)" == "Darwin" ]] && command -v xcrun >/dev/null 2>&1; then
  mkdir -p .camera-mcp/bin
  xcrun swiftc \
    scripts/capture_macos_camera.swift \
    -framework AppKit \
    -framework AVFoundation \
    -framework CoreImage \
    -framework Foundation \
    -Xlinker -sectcreate \
    -Xlinker __TEXT \
    -Xlinker __info_plist \
    -Xlinker scripts/macos-camera-info.plist \
    -o .camera-mcp/bin/capture-macos-camera
fi

if [[ ! -f cameras.json ]]; then
  .venv/bin/mcp-camera-watch --init-config --config ./cameras.json
fi

.venv/bin/mcp-camera-watch --print-clawbot-config --config ./cameras.json > ./clawbot-mcp-camera-watch.server.json

cat <<'EOF'
MCP Camera Watch local setup is ready.

Next files:
- cameras.json: edit this with your camera snapshot URL, laptop camera, or local fixture path.
- clawbot-mcp-camera-watch.server.json: generated OpenClaw/Clawbot MCP server definition.

To smoke test:
  scripts/smoke_mcp.sh

To install into a running OpenClaw/Clawbot setup and verify end to end:
  scripts/install_openclaw_e2e.sh --restart-gateway
EOF
