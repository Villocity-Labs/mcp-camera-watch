from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from mcp_camera.config import AppConfig, CameraConfig, EvaluatorConfig
from mcp_camera.web import CameraWebApi


class WebApiTests(TestCase):
    def test_camera_list_returns_ui_metadata(self) -> None:
        api = CameraWebApi(
            AppConfig(
                storage_dir=Path(".frames"),
                cameras=[CameraConfig(id="laptop-camera", name="Laptop Camera", type="macos_camera")],
                evaluator=EvaluatorConfig(provider="openai", model="gpt-4.1-mini"),
            )
        )

        result = api.camera_list()

        self.assertEqual(result["cameras"][0]["id"], "laptop-camera")
        self.assertEqual(result["model"], "gpt-4.1-mini")

    def test_snapshot_returns_displayable_frame(self) -> None:
        with TemporaryDirectory() as temp_dir:
            fixture = Path(temp_dir) / "fixture.jpg"
            fixture.write_bytes(b"fake image bytes")
            api = CameraWebApi(
                AppConfig(
                    storage_dir=Path(temp_dir) / "frames",
                    cameras=[CameraConfig(id="fixture", name="Fixture", type="file", path=str(fixture))],
                )
            )

            result = api.snapshot("fixture")

        self.assertTrue(result["frame_data_url"].startswith("data:image/jpeg;base64,"))

    def test_describe_uses_request_key_and_prompt(self) -> None:
        with TemporaryDirectory() as temp_dir:
            fixture = Path(temp_dir) / "fixture.jpg"
            fixture.write_bytes(b"fake image bytes")
            api = CameraWebApi(
                AppConfig(
                    storage_dir=Path(temp_dir) / "frames",
                    cameras=[CameraConfig(id="fixture", name="Fixture", type="file", path=str(fixture))],
                    evaluator=EvaluatorConfig(provider="openai", model="gpt-4.1-mini"),
                )
            )

            with patch("mcp_camera.web.OpenAIEvaluator.describe") as describe:
                describe.return_value = {
                    "description": "A blue test fixture.",
                    "provider": "openai",
                    "model": "gpt-4.1-mini",
                    "observed_at": "2026-06-05T12:00:00+00:00",
                }
                result = api.describe(
                    camera_id="fixture",
                    prompt="What color is visible?",
                    detail="brief",
                    api_key="request-key",
                    model="gpt-4.1-mini",
                )

        self.assertEqual(result["description"], "A blue test fixture.")
        self.assertEqual(describe.call_args.kwargs["prompt"], "What color is visible?")
