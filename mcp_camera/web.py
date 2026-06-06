from __future__ import annotations

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any

from .capture import CaptureService
from .config import AppConfig, CameraConfig
from .evaluator import OpenAIEvaluator, image_data_url

JsonObject = dict[str, Any]
ASSETS = files("mcp_camera.web_assets")
CONTENT_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
}


class CameraWebApi:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.cameras = {camera.id: camera for camera in config.cameras}
        self.capture = CaptureService(config.storage_dir)

    def camera_list(self) -> JsonObject:
        return {
            "cameras": [
                {"id": camera.id, "name": camera.name, "type": camera.type}
                for camera in self.cameras.values()
            ],
            "model": self.config.evaluator.model,
            "api_key_env": self.config.evaluator.api_key_env,
        }

    def snapshot(self, camera_id: str) -> JsonObject:
        snapshot = self.capture.snapshot(self.camera(camera_id))
        return {
            **snapshot,
            "frame_data_url": image_data_url(self.frame_path(snapshot)),
        }

    def describe(
        self,
        *,
        camera_id: str,
        prompt: str,
        detail: str,
        api_key: str | None,
        model: str | None,
    ) -> JsonObject:
        snapshot = self.capture.snapshot(self.camera(camera_id))
        evaluator = OpenAIEvaluator(
            model=(model or self.config.evaluator.model).strip() or self.config.evaluator.model,
            api_key_env=self.config.evaluator.api_key_env,
            base_url=self.config.evaluator.base_url,
            image_detail=self.config.evaluator.detail,
            timeout_seconds=self.config.evaluator.timeout_seconds,
            api_key=(api_key or "").strip() or None,
        )
        result = evaluator.describe(
            frame_path=snapshot["frame_path"],
            prompt=prompt.strip() or "Describe what is visible in this camera frame.",
            detail=detail if detail in {"brief", "normal", "detailed"} else "normal",
        )
        return {
            **result,
            "camera_id": camera_id,
            "frame_data_url": image_data_url(self.frame_path(snapshot)),
        }

    def camera(self, camera_id: str) -> CameraConfig:
        if camera_id not in self.cameras:
            raise ValueError(f"Unknown camera_id: {camera_id}")
        return self.cameras[camera_id]

    @staticmethod
    def frame_path(snapshot: JsonObject) -> Path:
        return Path(str(snapshot["frame_path"]))


def make_handler(api: CameraWebApi):
    class CameraWebHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/api/cameras":
                self.send_json(api.camera_list())
                return
            self.send_asset("index.html" if self.path in {"/", "/index.html"} else self.path.removeprefix("/"))

        def do_POST(self) -> None:
            try:
                payload = self.read_json()
                if self.path == "/api/snapshot":
                    result = api.snapshot(required_string(payload, "camera_id"))
                elif self.path == "/api/describe":
                    result = api.describe(
                        camera_id=required_string(payload, "camera_id"),
                        prompt=str(payload.get("prompt") or ""),
                        detail=str(payload.get("detail") or "normal"),
                        api_key=str(payload.get("api_key") or "") or None,
                        model=str(payload.get("model") or "") or None,
                    )
                else:
                    self.send_json({"error": "Not found."}, status=404)
                    return
                self.send_json(result)
            except ValueError as exc:
                self.send_json({"error": str(exc)}, status=400)
            except Exception as exc:
                self.send_json({"error": str(exc)}, status=500)

        def read_json(self) -> JsonObject:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 2_000_000:
                raise ValueError("Request body is missing or too large.")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("Request body must be a JSON object.")
            return payload

        def send_asset(self, asset_name: str) -> None:
            if asset_name not in {"index.html", "styles.css", "app.js"}:
                self.send_error(404)
                return
            asset = ASSETS.joinpath(asset_name)
            data = asset.read_bytes()
            suffix = "." + asset_name.rsplit(".", 1)[-1]
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPES[suffix])
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def send_json(self, payload: JsonObject, *, status: int = 200) -> None:
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format: str, *args: object) -> None:
            return

    return CameraWebHandler


def required_string(payload: JsonObject, name: str) -> str:
    value = str(payload.get(name) or "").strip()
    if not value:
        raise ValueError(f"Missing required field: {name}")
    return value


def run_web_ui(config: AppConfig, *, port: int, open_browser: bool) -> None:
    api = CameraWebApi(config)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(api))
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"MCP Camera Watch test UI: {url}")
    print("The UI is local-only. Press Ctrl-C to stop.")
    if open_browser:
        threading.Timer(0.25, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
