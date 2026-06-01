# MCP Camera Watch Spec

## Core Contract

General descriptions return natural-language scene context:

```json
{
  "description": "The printer bed is visible, with a partially completed print near the center.",
  "prompt": "Describe the print bed.",
  "detail": "normal",
  "evidence_frame_path": "/path/to/frame.jpg",
  "observed_at": "2026-06-01T13:30:00Z"
}
```

Every visual check returns a binary result:

```json
{
  "met": true,
  "confidence": 0.87,
  "summary": "Loose filament is visible above the print bed.",
  "evidence_frame_path": "/path/to/frame.jpg",
  "observed_at": "2026-06-01T13:30:00Z"
}
```

`met` is the integration point for agents and companion services.

## MVP Tool Surface

- `camera_list`
- `camera_snapshot`
- `camera_describe`
- `camera_evaluate_once`
- `camera_watch_create`
- `camera_watch_start`
- `camera_watch_stop`
- `camera_watch_status`
- `camera_alerts_list`

## Watch Model

```json
{
  "watch_id": "watch-01",
  "camera_id": "printer-cam",
  "instruction": "Alert if the print appears detached.",
  "roi": {
    "name": "print-bed"
  },
  "cadence_seconds": 30,
  "confidence_threshold": 0.8,
  "cooldown_seconds": 300
}
```

## Camera Types

Initial:

- `snapshot_url`
- `file`

Future:

- `rtsp`
- `usb`
- `folder`
- `printer_native`

## Evaluators

The evaluator API should support multiple backends:

- no-op placeholder
- local OpenCV rules
- OpenAI-compatible vision model
- local VLM
- hybrid evaluator that combines cheap CV checks with a vision model

## Printer Link

MCP Printer can later consume this service through:

- agent-level orchestration of both MCP servers
- optional local HTTP bridge
- shared event/result JSON schema

Do not make MCP Printer depend on camera monitoring by default.
