# Deploying MCP Camera Watch To Clawbot / OpenClaw

This guide assumes you have Clawbot/OpenClaw installed and want it to launch MCP Camera Watch as a local stdio MCP server.

MCP Camera Watch was built by Steve Villari and Villocity Labs.

## Local Browser Test

Before registering with OpenClaw, a tester can exercise the same camera capture and OpenAI vision evaluator through a local browser UI:

```bash
scripts/start_ui.sh
```

Choose a configured camera, capture a frame, optionally brighten the preview, enter an OpenAI API key, and send a custom request about the image. Preview brightening does not alter the image sent to OpenAI. An entered key stays only in the open browser tab, is cleared after submission, and is not saved by MCP Camera Watch. The UI listens only on `127.0.0.1`.

## Happy Path: One Command

Start with a running OpenClaw/Clawbot gateway, then run this from the repository root:

```bash
export OPENAI_API_KEY="your-openai-api-key"
scripts/install_openclaw_e2e.sh --restart-gateway
```

The command performs the full tester path:

- Runs [scripts/install_local.sh](scripts/install_local.sh) to create `.venv`, install MCP Camera Watch editable, run unit tests, initialize `cameras.json` when missing, and generate `clawbot-mcp-camera-watch.server.json`.
- Runs [scripts/smoke_mcp.sh](scripts/smoke_mcp.sh) and asserts that MCP `initialize` returns `serverInfo.name: "mcp-camera-watch"` and that the camera tools are present.
- Detects `openclaw`, verifies the gateway is reachable, and chooses the safest registration mode.
- In default `auto` mode, registers the standard MCP stdio server with `openclaw mcp set mcp-camera-watch ...` when the name is unused or already matches this checkout.
- If `OPENAI_API_KEY` is set when you run the installer, the generated OpenClaw MCP server entry includes that key in the server environment so the daemon can use the vision evaluator.
- Stops before replacing a different existing `mcp-camera-watch` server. Use `--force` only when you intentionally want this checkout to replace the existing entry.
- With `--restart-gateway`, asks OpenClaw to restart safely after registration and verifies the gateway is reachable again.

The smoke test does not capture a camera frame or call an external vision service. It verifies install, MCP protocol startup, tool discovery, OpenClaw detection, and OpenClaw registration.

On macOS, the installer also compiles a native camera capture helper at `.camera-mcp/bin/capture-macos-camera`. To use the built-in laptop camera, add this entry to `cameras.json` before running the happy-path command:

```json
{
  "id": "laptop-camera",
  "name": "Laptop Camera",
  "type": "macos_camera",
  "device_name": "FaceTime HD Camera"
}
```

List the exact camera names available on the Mac with:

```bash
.camera-mcp/bin/capture-macos-camera --list
```

The first live snapshot may display a macOS Camera permission prompt. Allow access for the process running MCP Camera Watch, then ask OpenClaw:

```text
Take a snapshot from laptop-camera.
```

```text
Describe what laptop-camera sees right now.
```

If you previously registered MCP Camera Watch before setting `OPENAI_API_KEY`, rerun:

```bash
scripts/install_openclaw_e2e.sh --force --restart-gateway
```

After the command passes, ask Clawbot/OpenClaw:

```text
List my configured cameras.
```

Then, after confirming your `cameras.json` points at a reachable camera or local image file:

```text
Describe what printer-cam sees.
```

Useful printer-camera prompts:

```text
Look at printer-cam and tell me what color filament is visible.
```

```text
Check printer-cam and tell me if the print looks detached, spaghetti-like, shifted, or otherwise messed up.
```

```text
Watch printer-cam and alert me if the print starts looking detached, spaghetti-like, shifted, or messy.
```

If your OpenClaw install uses a named profile, add:

```bash
scripts/install_openclaw_e2e.sh --openclaw-profile your-profile --restart-gateway
```

Plugin mode is reserved for a future native OpenClaw plugin package. This repository currently installs through the standard MCP stdio server path.

## Manual Setup

From this folder:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests
```

Generate a local config:

```bash
.venv/bin/mcp-camera-watch --init-config --config ./cameras.json
```

Edit `cameras.json` with your camera details and evaluator settings. Supported `type` values:

- `snapshot_url`
- `file`
- `macos_camera` on macOS; optionally set `device_name` to choose a specific camera

The default evaluator config uses OpenAI:

```json
{
  "evaluator": {
    "provider": "openai",
    "model": "gpt-4.1-mini",
    "api_key_env": "OPENAI_API_KEY",
    "detail": "low"
  }
}
```

Run the local smoke test:

```bash
scripts/smoke_mcp.sh
```

Generate the exact OpenClaw server JSON:

```bash
.venv/bin/mcp-camera-watch --print-clawbot-config --config ./cameras.json
```

Register it manually:

```bash
openclaw mcp set mcp-camera-watch "$(.venv/bin/mcp-camera-watch --print-clawbot-config --config ./cameras.json)"
```

Restart Clawbot/OpenClaw after adding the server if your setup does not hot-reload MCP config.

## Troubleshooting

- If Clawbot says the server is missing, verify the absolute `command` path in `openclaw mcp show mcp-camera-watch --json`.
- If a snapshot URL fails, open the configured `url` in a browser from the same machine.
- If a file camera fails, verify the configured `path` exists.
- If a macOS camera fails, rerun `scripts/install_local.sh`, verify its name with `.camera-mcp/bin/capture-macos-camera --list`, and allow Camera access in System Settings > Privacy & Security > Camera.
- If descriptions or evaluations say `OPENAI_API_KEY` is not set, export it and rerun `scripts/install_openclaw_e2e.sh --force --restart-gateway`.
