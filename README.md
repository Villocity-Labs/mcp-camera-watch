# MCP Camera Watch

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
- A placeholder evaluator interface
- Tests using only the Python standard library

The starter intentionally does not claim visual intelligence yet. The first real evaluator should plug into `mcp_camera/evaluator.py`.

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

For a running OpenClaw/Clawbot setup, the one-command tester path is:

```bash
scripts/install_openclaw_e2e.sh --restart-gateway
```

That command reuses [scripts/install_local.sh](scripts/install_local.sh) and [scripts/smoke_mcp.sh](scripts/smoke_mcp.sh), detects the OpenClaw CLI and running gateway, registers `mcp-camera-watch` when the name is unused or already matches this checkout, and verifies the saved OpenClaw registration. It stops before replacing a different existing `mcp-camera-watch` entry unless you pass `--force`.

After it passes, ask OpenClaw/Clawbot:

```text
List my configured cameras.
```

For the detailed happy path, see [DEPLOY.md](DEPLOY.md).

## Example Config

```json
{
  "storage_dir": ".camera-mcp/frames",
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
