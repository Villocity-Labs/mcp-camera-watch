from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from mcp_camera.evaluator import OpenAIEvaluator, image_data_url


class FakeOpenAIEvaluator(OpenAIEvaluator):
    def __init__(self, response_text: str) -> None:
        super().__init__(
            model="gpt-4.1-mini",
            api_key_env="OPENAI_API_KEY",
            base_url="https://api.openai.com/v1",
            image_detail="low",
            timeout_seconds=60,
        )
        object.__setattr__(self, "response_text", response_text)

    def call_responses_api(self, *, api_key: str, frame_path: str, prompt: str, max_output_tokens: int) -> str:
        return self.response_text


class EvaluatorTests(TestCase):
    def test_image_data_url_encodes_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            image = Path(temp_dir) / "fixture.jpg"
            image.write_bytes(b"fake image bytes")

            data_url = image_data_url(image)

            self.assertTrue(data_url.startswith("data:image/jpeg;base64,"))

    def test_openai_describe_returns_model_text(self) -> None:
        evaluator = FakeOpenAIEvaluator("Visible red filament on the printer bed.")
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            response = evaluator.describe(frame_path="frame.jpg", prompt="What colors are visible?", detail="normal")

        self.assertEqual(response["description"], "Visible red filament on the printer bed.")
        self.assertEqual(response["provider"], "openai")

    def test_openai_evaluate_parses_json_and_applies_threshold(self) -> None:
        evaluator = FakeOpenAIEvaluator('{"met": true, "confidence": 0.72, "summary": "Possible spaghetti."}')
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            response = evaluator.evaluate(frame_path="frame.jpg", instruction="Is this print failing?", threshold=0.8)

        self.assertFalse(response["met"])
        self.assertTrue(response["raw_met"])
        self.assertEqual(response["confidence"], 0.72)
        self.assertIn("Possible spaghetti", response["summary"])

    def test_openai_evaluator_handles_missing_api_key(self) -> None:
        evaluator = FakeOpenAIEvaluator("unused")
        with patch.dict("os.environ", {}, clear=True):
            response = evaluator.describe(frame_path="frame.jpg", prompt="What do you see?", detail="brief")

        self.assertIn("OPENAI_API_KEY is not set", response["description"])
        self.assertEqual(response["provider"], "openai")
