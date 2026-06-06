# MCP Camera Watch

[![CI](https://github.com/Villocity-Labs/mcp-camera-watch/actions/workflows/ci.yml/badge.svg)](https://github.com/Villocity-Labs/mcp-camera-watch/actions/workflows/ci.yml)

A local-first MCP companion service for camera-based monitoring and true/false visual condition alerts.

Built as a companion project for MCP Printer by Steve Villari and Villocity Labs.

## Goal

Tell the camera MCP what to look for, where to look, and how often to check. It returns structured true/false results with confidence, summaries, and evidence frame paths.
It can also describe what it sees in a camera frame, which is useful for exploratory checks before turning an observation into a persistent watch.

Example:

```text
Watch printer-cam and alert if the print appears detached or spaghetti-like extrusion is visible.
```

## Current Starter Scope

This starter project includes:

- MCP stdio server skeleton
- Camera config loading
- Snapshot capture from:
  - HTTP snapshot URL
  - Local image file
  - Built-in or attached macOS camera
- OpenAI vision evaluation through the Responses API when `OPENAI_API_KEY` is configured
- Tool definitions for:
  - `camera_list`
  - `camera_snapshot`
  - `camera_describe`
  - `camera_evaluate_once`
  - `camera_watch_create`
  - `camera_watch_start`
  - `camera_watch_stop`
  - `camera_watch_status`
  - `camera_alerts_list`
- Tests using only the Python standard library

If no OpenAI API key is available, the evaluator returns a clear setup message instead of crashing.

## Description Tool

Use `camera_describe` when you want a general description instead of a true/false condition.

Example input:

```json
{
  "camera_id": "printer-cam",
  "prompt": "Describe the print bed and any visible filament problems.",
  "detail": "normal"
}
```

Example output shape:

```json
{
  "description": "The print bed appears clear and the nozzle area is visible.",
  "prompt": "Describe the print bed and any visible filament problems.",
  "detail": "normal",
  "evidence_frame_path": ".camera-mcp/frames/printer-cam-2026-06-01T14-00-00.jpg",
  "observed_at": "2026-06-01T14:00:00Z"
}
```

## Quick Start

```bash
scripts/install_local.sh
```

Edit the generated `cameras.json` file with your camera source, then run:

```bash
scripts/smoke_mcp.sh
```

## Local Testing UI

Open the local camera testing UI with:

```bash
scripts/start_ui.sh
```

The browser UI lets a tester:

- Choose any camera from `cameras.json`.
- Capture and preview a live frame.
- Brighten a dark preview without changing the image sent to OpenAI.
- Enter an OpenAI API key without saving it to disk.
- Select the OpenAI model and response detail.
- Send a custom request about what the camera sees.

The UI binds only to `127.0.0.1`. An entered key stays only in the open browser tab and is cleared immediately after submission. Leave the field blank to use `OPENAI_API_KEY` from the process environment.

For example, select `laptop-camera`, enter:

```text
What colors are visible, and is anything unusual happening in this frame?
```

Then press **Capture and ask OpenAI**.

On macOS, `scripts/install_local.sh` also builds the native laptop-camera capture helper. Add a camera like this to `cameras.json`:

```json
{
  "id": "laptop-camera",
  "name": "Laptop Camera",
  "type": "macos_camera",
  "device_name": "FaceTime HD Camera"
}
```

On first capture, allow camera access when macOS asks. To see the exact camera names available on the Mac:

```bash
.camera-mcp/bin/capture-macos-camera --list
```

To enable real visual descriptions and condition checks, set your OpenAI API key before registering with OpenClaw:

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

For a running OpenClaw/Clawbot setup, the one-command tester path is:

```bash
scripts/install_openclaw_e2e.sh --restart-gateway
```

That command reuses [scripts/install_local.sh](scripts/install_local.sh) and [scripts/smoke_mcp.sh](scripts/smoke_mcp.sh), detects the OpenClaw CLI and running gateway, registers `mcp-camera-watch` when the name is unused or already matches this checkout, and verifies the saved OpenClaw registration. It stops before replacing a different existing `mcp-camera-watch` entry unless you pass `--force`.

If you previously registered the server before setting `OPENAI_API_KEY`, rerun with `--force --restart-gateway` so OpenClaw picks up the key in the MCP server environment.

After it passes, ask OpenClaw/Clawbot:

```text
List my configured cameras.
```

Then try:

```text
Describe what printer-cam sees right now.
```

For the built-in Mac camera, try:

```text
Take a snapshot from laptop-camera.
```

```text
Describe what laptop-camera sees right now.
```

```text
Look at printer-cam and tell me what color filament is visible.
```

```text
Watch printer-cam and alert me if the print looks detached, spaghetti-like, shifted, or otherwise messed up.
```

For the detailed happy path, see [DEPLOY.md](DEPLOY.md).

## Example Config

```json
{
  "storage_dir": ".camera-mcp/frames",
  "evaluator": {
    "provider": "openai",
    "model": "gpt-4.1-mini",
    "api_key_env": "OPENAI_API_KEY",
    "detail": "low"
  },
  "cameras": [
    {
      "id": "printer-cam",
      "name": "Printer Camera",
      "type": "snapshot_url",
      "url": "http://octopi.local/webcam/?action=snapshot"
    },
    {
      "id": "fixture",
      "name": "Fixture Image",
      "type": "file",
      "path": "examples/fixture.jpg"
    },
    {
      "id": "laptop-camera",
      "name": "Laptop Camera",
      "type": "macos_camera",
      "device_name": "FaceTime HD Camera"
    }
  ]
}
```

## Printer Integration

MCP Printer should remain separate. Agents can orchestrate both MCPs directly, and MCP Printer can later call MCP Camera Watch through an optional local HTTP bridge.

Planned printer workflow:

1. Check printer status.
2. Ask camera MCP if bed is clear.
3. Start print if checks pass.
4. Start a misprint/spaghetti watch.
5. Alert the user if a watch result becomes true.
6. Ask before pausing/canceling unless the user explicitly enables automation.

## Safety

Camera monitoring should assist, not replace supervision. Default behavior should be alert-and-ask, not automatic machine intervention.

API keys, local camera configuration, generated OpenClaw configuration, and captured frames must remain private. See [SECURITY.md](SECURITY.md) for the project security and camera-privacy guidance.
