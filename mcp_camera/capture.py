from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib import request

from .config import CameraConfig


class CaptureService:
    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir

    def snapshot(self, camera: CameraConfig) -> dict[str, str]:
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        captured_at = datetime.now(timezone.utc).isoformat()
        frame_path = self.storage_dir / f"{camera.id}-{captured_at.replace(':', '-')}.jpg"

        if camera.type == "snapshot_url":
            if not camera.url:
                raise ValueError(f"Camera {camera.id} is missing url.")
            with request.urlopen(camera.url, timeout=20) as response:
                frame_path.write_bytes(response.read())
        elif camera.type == "file":
            if not camera.path:
                raise ValueError(f"Camera {camera.id} is missing path.")
            shutil.copyfile(Path(camera.path).expanduser(), frame_path)
        elif camera.type == "macos_camera":
            self.capture_macos_camera(camera, frame_path)
        else:
            raise ValueError(f"Unsupported camera type: {camera.type}")

        return {
            "camera_id": camera.id,
            "frame_path": str(frame_path),
            "captured_at": captured_at,
        }

    def capture_macos_camera(self, camera: CameraConfig, frame_path: Path) -> None:
        helper = Path(
            os.environ.get(
                "MCP_CAMERA_MACOS_CAPTURE_BIN",
                Path(__file__).resolve().parent.parent / ".camera-mcp" / "bin" / "capture-macos-camera",
            )
        ).expanduser()
        if not helper.is_file():
            raise ValueError(
                "macos_camera capture helper is missing. Run scripts/install_local.sh on macOS, then try again."
            )

        command = [str(helper), "--output", str(frame_path)]
        if camera.device_name:
            command.extend(["--device", camera.device_name])

        try:
            subprocess.run(command, check=True, capture_output=True, text=True, timeout=30)
        except subprocess.CalledProcessError as exc:
            message = exc.stderr.strip() or exc.stdout.strip() or str(exc)
            raise RuntimeError(f"macos_camera capture failed: {message}") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("macos_camera capture timed out.") from exc
