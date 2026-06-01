from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from mcp_camera.config import AppConfig, CameraConfig
from mcp_camera.server import CameraMcpServer


class ServerTests(TestCase):
    def test_initialize_includes_credit(self) -> None:
        server = CameraMcpServer(AppConfig(storage_dir=Path(".frames"), cameras=[]))

        response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})

        self.assertEqual(response["result"]["serverInfo"]["credits"], "Steve Villari and Villocity Labs")

    def test_tools_list_exposes_camera_tools(self) -> None:
        server = CameraMcpServer(AppConfig(storage_dir=Path(".frames"), cameras=[]))

        response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        tool_names = {tool["name"] for tool in response["result"]["tools"]}

        self.assertIn("camera_evaluate_once", tool_names)
        self.assertIn("camera_describe", tool_names)
        self.assertIn("camera_watch_create", tool_names)

    def test_camera_list_returns_configured_cameras(self) -> None:
        server = CameraMcpServer(
            AppConfig(
                storage_dir=Path(".frames"),
                cameras=[CameraConfig(id="printer-cam", name="Printer Camera", type="file", path="fixture.jpg")],
            )
        )

        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "camera_list", "arguments": {}},
            }
        )

        self.assertIn("Printer Camera", response["result"]["content"][0]["text"])

    def test_evaluate_once_returns_false_until_evaluator_configured(self) -> None:
        with TemporaryDirectory() as temp_dir:
            fixture = Path(temp_dir) / "fixture.jpg"
            fixture.write_bytes(b"fake image bytes")
            server = CameraMcpServer(
                AppConfig(
                    storage_dir=Path(temp_dir) / "frames",
                    cameras=[CameraConfig(id="fixture", name="Fixture", type="file", path=str(fixture))],
                )
            )

            response = server.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "camera_evaluate_once",
                        "arguments": {
                            "camera_id": "fixture",
                            "instruction": "Is the print failing?",
                        },
                    },
                }
            )

            self.assertIn('"met": false', response["result"]["content"][0]["text"])

    def test_describe_returns_placeholder_until_evaluator_configured(self) -> None:
        with TemporaryDirectory() as temp_dir:
            fixture = Path(temp_dir) / "fixture.jpg"
            fixture.write_bytes(b"fake image bytes")
            server = CameraMcpServer(
                AppConfig(
                    storage_dir=Path(temp_dir) / "frames",
                    cameras=[CameraConfig(id="fixture", name="Fixture", type="file", path=str(fixture))],
                )
            )

            response = server.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "camera_describe",
                        "arguments": {
                            "camera_id": "fixture",
                            "prompt": "Describe the printer bed.",
                            "detail": "brief",
                        },
                    },
                }
            )

            text = response["result"]["content"][0]["text"]
            self.assertIn("visual description is not available", text)
            self.assertIn("Describe the printer bed", text)
