from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "storage_dir": ".camera-mcp/frames",
    "evaluator": {
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "api_key_env": "OPENAI_API_KEY",
        "detail": "low",
    },
    "cameras": [
        {
            "id": "printer-cam",
            "name": "Printer Camera",
            "type": "snapshot_url",
            "url": "http://octopi.local/webcam/?action=snapshot",
        }
    ],
}


@dataclass(frozen=True)
class CameraConfig:
    id: str
    name: str
    type: str
    url: str | None = None
    path: str | None = None


@dataclass(frozen=True)
class EvaluatorConfig:
    provider: str = "placeholder"
    model: str = "gpt-4.1-mini"
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str = "https://api.openai.com/v1"
    detail: str = "low"
    timeout_seconds: int = 60


@dataclass(frozen=True)
class AppConfig:
    storage_dir: Path
    cameras: list[CameraConfig]
    evaluator: EvaluatorConfig = field(default_factory=EvaluatorConfig)


def load_config(path: Path) -> AppConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    storage_dir = Path(str(raw.get("storage_dir", ".camera-mcp/frames"))).expanduser()
    cameras = raw.get("cameras", [])
    if not isinstance(cameras, list):
        raise ValueError("Config field 'cameras' must be a list.")
    return AppConfig(
        storage_dir=storage_dir,
        cameras=[_parse_camera(item) for item in cameras],
        evaluator=_parse_evaluator(raw.get("evaluator", {})),
    )


def write_default_config(path: Path) -> None:
    path.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n", encoding="utf-8")


def _parse_camera(item: Any) -> CameraConfig:
    if not isinstance(item, dict):
        raise ValueError("Each camera config must be an object.")

    camera_id = item.get("id")
    camera_type = str(item.get("type", "")).lower()
    if not camera_id:
        raise ValueError("Camera config is missing required field: id")
    if camera_type not in {"snapshot_url", "file"}:
        raise ValueError(f"Unsupported camera type: {camera_type}")
    if camera_type == "snapshot_url" and not item.get("url"):
        raise ValueError("snapshot_url camera requires url")
    if camera_type == "file" and not item.get("path"):
        raise ValueError("file camera requires path")

    return CameraConfig(
        id=str(camera_id),
        name=str(item.get("name") or camera_id),
        type=camera_type,
        url=str(item["url"]) if item.get("url") else None,
        path=str(item["path"]) if item.get("path") else None,
    )


def _parse_evaluator(item: Any) -> EvaluatorConfig:
    if item is None:
        item = {}
    if not isinstance(item, dict):
        raise ValueError("Config field 'evaluator' must be an object.")

    provider = str(item.get("provider", "placeholder")).lower()
    if provider not in {"placeholder", "openai"}:
        raise ValueError(f"Unsupported evaluator provider: {provider}")

    detail = str(item.get("detail", "low")).lower()
    if detail not in {"low", "high", "auto"}:
        raise ValueError("Evaluator detail must be one of: low, high, auto")

    timeout_seconds = int(item.get("timeout_seconds", 60))
    if timeout_seconds <= 0:
        raise ValueError("Evaluator timeout_seconds must be positive.")

    return EvaluatorConfig(
        provider=provider,
        model=str(item.get("model", "gpt-4.1-mini")),
        api_key_env=str(item.get("api_key_env", "OPENAI_API_KEY")),
        base_url=str(item.get("base_url", "https://api.openai.com/v1")).rstrip("/"),
        detail=detail,
        timeout_seconds=timeout_seconds,
    )
