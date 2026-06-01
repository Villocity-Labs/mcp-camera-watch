from pathlib import Path
from unittest import TestCase

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

    def create_temp_file(self) -> str:
        import tempfile

        handle = tempfile.NamedTemporaryFile(delete=False)
        handle.close()
        return handle.name
