from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from mcp_camera.__main__ import clawbot_config
from mcp_camera.config import load_config


class ConfigTests(TestCase):
    def test_load_config_parses_file_camera(self) -> None:
        config = Path(self.create_temp_file())
        config.write_text(
            """
            {
              "storage_dir": ".frames",
              "cameras": [
                {
                  "id": "fixture",
                  "name": "Fixture",
                  "type": "file",
                  "path": "examples/fixture.jpg"
                }
              ]
            }
            """,
            encoding="utf-8",
        )

        app_config = load_config(config)

        self.assertEqual(app_config.cameras[0].id, "fixture")
        self.assertEqual(app_config.cameras[0].type, "file")

    def test_load_config_rejects_unknown_camera_type(self) -> None:
        config = Path(self.create_temp_file())
        config.write_text(
            """
            {
              "cameras": [
                {
                  "id": "bad",
                  "type": "magic"
                }
              ]
            }
            """,
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "Unsupported camera type"):
            load_config(config)

    def test_load_config_parses_openai_evaluator(self) -> None:
        config = Path(self.create_temp_file())
        config.write_text(
            """
            {
              "storage_dir": ".frames",
              "evaluator": {
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "api_key_env": "OPENAI_API_KEY",
                "detail": "high"
              },
              "cameras": [
                {
                  "id": "fixture",
                  "type": "file",
                  "path": "examples/fixture.jpg"
                }
              ]
            }
            """,
            encoding="utf-8",
        )

        app_config = load_config(config)

        self.assertEqual(app_config.evaluator.provider, "openai")
        self.assertEqual(app_config.evaluator.detail, "high")

    def test_clawbot_config_points_at_camera_config(self) -> None:
        config = Path(self.create_temp_file())

        server_config = clawbot_config(config)

        command = str(server_config["command"])
        args = server_config["args"]
        self.assertTrue("mcp-camera-watch" in command or args[:2] == ["-m", "mcp_camera"])
        self.assertIn(str(config.resolve()), server_config["args"])
        self.assertIn("cwd", server_config)

    def test_clawbot_config_includes_openai_env_when_available(self) -> None:
        config = Path(self.create_temp_file())

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            server_config = clawbot_config(config)

        self.assertEqual(server_config["env"]["OPENAI_API_KEY"], "test-key")

    def create_temp_file(self) -> str:
        import tempfile

        handle = tempfile.NamedTemporaryFile(delete=False)
        handle.close()
        return handle.name
