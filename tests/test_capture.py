from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from mcp_camera.capture import CaptureService
from mcp_camera.config import CameraConfig


class CaptureTests(TestCase):
    def test_macos_camera_invokes_capture_helper(self) -> None:
        with TemporaryDirectory() as temp_dir:
            helper = Path(temp_dir) / "capture-macos-camera"
            helper.write_text("#!/bin/sh\n", encoding="utf-8")
            helper.chmod(0o755)
            service = CaptureService(Path(temp_dir) / "frames")
            camera = CameraConfig(
                id="laptop-camera",
                name="Laptop Camera",
                type="macos_camera",
                device_name="FaceTime HD Camera",
            )

            with patch.dict("os.environ", {"MCP_CAMERA_MACOS_CAPTURE_BIN": str(helper)}):
                with patch("mcp_camera.capture.subprocess.run") as run:
                    result = service.snapshot(camera)

            command = run.call_args.args[0]
            self.assertIn("--device", command)
            self.assertIn("FaceTime HD Camera", command)
            self.assertEqual(result["camera_id"], "laptop-camera")
