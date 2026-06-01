from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any, Callable
from uuid import uuid4

from .capture import CaptureService
from .config import AppConfig, CameraConfig
from .evaluator import PlaceholderEvaluator

JsonObject = dict[str, Any]


@dataclass
class Watch:
    id: str
    camera_id: str
    instruction: str
    roi: JsonObject | None = None
    cadence_seconds: int = 30
    confidence_threshold: float = 0.8
    cooldown_seconds: int = 300
    status: str = "created"
    latest_result: JsonObject | None = None
    alerts: list[JsonObject] = field(default_factory=list)


class CameraMcpServer:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.cameras = {camera.id: camera for camera in config.cameras}
        self.capture = CaptureService(config.storage_dir)
        self.evaluator = PlaceholderEvaluator()
        self.watches: dict[str, Watch] = {}
        self.tools: dict[str, Callable[[JsonObject], Any]] = {
            "camera_list": self.camera_list,
            "camera_snapshot": self.camera_snapshot,
            "camera_describe": self.camera_describe,
            "camera_evaluate_once": self.camera_evaluate_once,
            "camera_watch_create": self.camera_watch_create,
            "camera_watch_start": self.camera_watch_start,
            "camera_watch_stop": self.camera_watch_stop,
            "camera_watch_status": self.camera_watch_status,
            "camera_alerts_list": self.camera_alerts_list,
        }

    def run(self) -> None:
        for line in sys.stdin:
            try:
                message = json.loads(line)
                response = self.handle(message)
            except Exception as exc:
                response = self.error(None, -32603, str(exc))
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

    def handle(self, message: JsonObject) -> JsonObject | None:
        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params") or {}

        if method == "initialize":
            return self.result(
                request_id,
                {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "mcp-camera-watch",
                        "version": "0.1.0",
                        "credits": "Steve Villari and Villocity Labs",
                    },
                    "capabilities": {"tools": {}},
                },
            )
        if method == "notifications/initialized":
            return None
        if method == "tools/list":
            return self.result(request_id, {"tools": tool_definitions()})
        if method == "tools/call":
            return self.call_tool(request_id, params)

        return self.error(request_id, -32601, f"Unknown method: {method}")

    def call_tool(self, request_id: Any, params: JsonObject) -> JsonObject:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name not in self.tools:
            return self.error(request_id, -32602, f"Unknown tool: {name}")
        try:
            payload = self.tools[name](arguments)
            return self.result(request_id, {"content": [{"type": "text", "text": json.dumps(payload, indent=2)}]})
        except Exception as exc:
            return self.error(request_id, -32000, str(exc))

    def camera_list(self, _: JsonObject) -> list[JsonObject]:
        return [
            {"id": camera.id, "name": camera.name, "type": camera.type}
            for camera in self.cameras.values()
        ]

    def camera_snapshot(self, args: JsonObject) -> JsonObject:
        return self.capture.snapshot(self.camera(args))

    def camera_describe(self, args: JsonObject) -> JsonObject:
        camera = self.camera(args)
        snapshot = self.capture.snapshot(camera)
        return self.evaluator.describe(
            frame_path=snapshot["frame_path"],
            prompt=str(args.get("prompt") or "Describe what is visible in this camera frame."),
            detail=str(args.get("detail") or "normal"),
        )

    def camera_evaluate_once(self, args: JsonObject) -> JsonObject:
        camera = self.camera(args)
        snapshot = self.capture.snapshot(camera)
        return self.evaluator.evaluate(
            instruction=required(args, "instruction"),
            frame_path=snapshot["frame_path"],
            threshold=float(args.get("confidence_threshold", 0.8)),
        )

    def camera_watch_create(self, args: JsonObject) -> JsonObject:
        camera_id = required(args, "camera_id")
        if camera_id not in self.cameras:
            raise ValueError(f"Unknown camera_id: {camera_id}")
        watch_id = str(args.get("watch_id") or f"watch-{uuid4().hex[:8]}")
        watch = Watch(
            id=watch_id,
            camera_id=camera_id,
            instruction=required(args, "instruction"),
            roi=args.get("roi") if isinstance(args.get("roi"), dict) else None,
            cadence_seconds=int(args.get("cadence_seconds", 30)),
            confidence_threshold=float(args.get("confidence_threshold", 0.8)),
            cooldown_seconds=int(args.get("cooldown_seconds", 300)),
        )
        self.watches[watch.id] = watch
        return {"watch_id": watch.id, "status": watch.status}

    def camera_watch_start(self, args: JsonObject) -> JsonObject:
        watch = self.watch(args)
        watch.status = "running"
        watch.latest_result = self.camera_evaluate_once(
            {
                "camera_id": watch.camera_id,
                "instruction": watch.instruction,
                "confidence_threshold": watch.confidence_threshold,
            }
        )
        if watch.latest_result.get("met") is True:
            watch.alerts.append(watch.latest_result)
        return {"watch_id": watch.id, "status": watch.status, "latest_result": watch.latest_result}

    def camera_watch_stop(self, args: JsonObject) -> JsonObject:
        watch = self.watch(args)
        watch.status = "stopped"
        return {"watch_id": watch.id, "status": watch.status}

    def camera_watch_status(self, args: JsonObject) -> JsonObject:
        watch = self.watch(args)
        return {
            "watch_id": watch.id,
            "status": watch.status,
            "latest_result": watch.latest_result,
            "alerts": watch.alerts,
        }

    def camera_alerts_list(self, _: JsonObject) -> list[JsonObject]:
        alerts: list[JsonObject] = []
        for watch in self.watches.values():
            alerts.extend(watch.alerts)
        return alerts

    def camera(self, args: JsonObject) -> CameraConfig:
        camera_id = required(args, "camera_id")
        if camera_id not in self.cameras:
            raise ValueError(f"Unknown camera_id: {camera_id}")
        return self.cameras[camera_id]

    def watch(self, args: JsonObject) -> Watch:
        watch_id = required(args, "watch_id")
        if watch_id not in self.watches:
            raise ValueError(f"Unknown watch_id: {watch_id}")
        return self.watches[watch_id]

    @staticmethod
    def result(request_id: Any, result: JsonObject) -> JsonObject:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def error(request_id: Any, code: int, message: str) -> JsonObject:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def required(args: JsonObject, name: str) -> str:
    value = args.get(name)
    if not value:
        raise ValueError(f"Missing required argument: {name}")
    return str(value)


def tool_definitions() -> list[JsonObject]:
    camera_id_schema = {
        "type": "object",
        "properties": {"camera_id": {"type": "string"}},
        "required": ["camera_id"],
        "additionalProperties": False,
    }
    watch_id_schema = {
        "type": "object",
        "properties": {"watch_id": {"type": "string"}},
        "required": ["watch_id"],
        "additionalProperties": False,
    }
    return [
        {
            "name": "camera_list",
            "description": "List configured cameras.",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "camera_snapshot",
            "description": "Capture one frame from a camera.",
            "inputSchema": camera_id_schema,
        },
        {
            "name": "camera_describe",
            "description": "Describe what is visible in the current camera frame.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "camera_id": {"type": "string"},
                    "prompt": {"type": "string", "default": "Describe what is visible in this camera frame."},
                    "detail": {"type": "string", "enum": ["brief", "normal", "detailed"], "default": "normal"},
                    "roi": {"type": "object"},
                },
                "required": ["camera_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "camera_evaluate_once",
            "description": "Evaluate one visual instruction against the current camera frame.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "camera_id": {"type": "string"},
                    "instruction": {"type": "string"},
                    "roi": {"type": "object"},
                    "confidence_threshold": {"type": "number", "default": 0.8},
                },
                "required": ["camera_id", "instruction"],
                "additionalProperties": False,
            },
        },
        {
            "name": "camera_watch_create",
            "description": "Create a visual watch instruction.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "camera_id": {"type": "string"},
                    "watch_id": {"type": "string"},
                    "instruction": {"type": "string"},
                    "roi": {"type": "object"},
                    "cadence_seconds": {"type": "integer", "default": 30},
                    "confidence_threshold": {"type": "number", "default": 0.8},
                    "cooldown_seconds": {"type": "integer", "default": 300},
                },
                "required": ["camera_id", "instruction"],
                "additionalProperties": False,
            },
        },
        {
            "name": "camera_watch_start",
            "description": "Start a visual watch.",
            "inputSchema": watch_id_schema,
        },
        {
            "name": "camera_watch_stop",
            "description": "Stop a visual watch.",
            "inputSchema": watch_id_schema,
        },
        {
            "name": "camera_watch_status",
            "description": "Get watch state and latest result.",
            "inputSchema": watch_id_schema,
        },
        {
            "name": "camera_alerts_list",
            "description": "List true-condition camera alerts.",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    ]
