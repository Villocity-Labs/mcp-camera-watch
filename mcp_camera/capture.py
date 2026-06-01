from __future__ import annotations

import shutil
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
        else:
            raise ValueError(f"Unsupported camera type: {camera.type}")

        return {
            "camera_id": camera.id,
            "frame_path": str(frame_path),
            "captured_at": captured_at,
        }
