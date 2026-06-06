from __future__ import annotations

import base64
import json
import mimetypes
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError

from .config import EvaluatorConfig

JsonObject = dict[str, Any]


class PlaceholderEvaluator:
    """Evaluator placeholder until a vision backend is configured."""

    def describe(self, *, frame_path: str, prompt: str, detail: str) -> JsonObject:
        return {
            "description": (
                "No vision evaluator is configured yet. The frame was captured, "
                "but visual description is not available."
            ),
            "provider": "placeholder",
            "prompt": prompt,
            "detail": detail,
            "evidence_frame_path": frame_path,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }

    def evaluate(self, *, instruction: str, frame_path: str, threshold: float) -> JsonObject:
        return {
            "met": False,
            "confidence": 0.0,
            "threshold": threshold,
            "provider": "placeholder",
            "summary": (
                "No vision evaluator is configured yet. The frame was captured, "
                "but the condition was not evaluated."
            ),
            "instruction": instruction,
            "evidence_frame_path": frame_path,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }


@dataclass(frozen=True)
class OpenAIEvaluator:
    model: str
    api_key_env: str
    base_url: str
    image_detail: str
    timeout_seconds: int
    api_key: str | None = None

    def describe(self, *, frame_path: str, prompt: str, detail: str) -> JsonObject:
        api_key = self.api_key or os.environ.get(self.api_key_env)
        if is_missing_api_key(api_key):
            return self.missing_api_key(frame_path, prompt=prompt, detail=detail)

        text_prompt = (
            "You are MCP Camera Watch, a careful visual assistant for real-world camera frames. "
            "Describe only what is visible. Mention uncertainty when the view is unclear. "
            "If asked about 3D printing, pay attention to filament color, spool/nozzle/bed state, "
            "detachment, spaghetti-like extrusion, layer shifts, and obvious print quality issues.\n\n"
            f"Detail level requested by the user: {detail}.\n"
            f"User request: {prompt}"
        )

        output_text = self.call_responses_api(
            api_key=api_key,
            frame_path=frame_path,
            prompt=text_prompt,
            max_output_tokens=700,
        )
        return {
            "description": output_text,
            "provider": "openai",
            "model": self.model,
            "prompt": prompt,
            "detail": detail,
            "evidence_frame_path": frame_path,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }

    def evaluate(self, *, instruction: str, frame_path: str, threshold: float) -> JsonObject:
        api_key = self.api_key or os.environ.get(self.api_key_env)
        if is_missing_api_key(api_key):
            response = self.missing_api_key(frame_path, prompt=instruction, detail="evaluation")
            return {
                "met": False,
                "confidence": 0.0,
                "threshold": threshold,
                "provider": "openai",
                "model": self.model,
                "summary": response["description"],
                "instruction": instruction,
                "evidence_frame_path": frame_path,
                "observed_at": response["observed_at"],
            }

        text_prompt = (
            "You are MCP Camera Watch, evaluating one visual condition against a camera frame. "
            "Use only visible evidence from the image. If the image is unclear or the condition "
            "cannot be verified, set met to false and use a low confidence. "
            "Return only a JSON object with these keys: met, confidence, summary. "
            "confidence must be a number from 0 to 1. "
            "For 3D-print monitoring, treat detached parts, spaghetti-like extrusion, major layer shifts, "
            "or obvious failed adhesion as print problems.\n\n"
            f"Condition: {instruction}\n"
            f"Decision threshold: {threshold}"
        )

        output_text = self.call_responses_api(
            api_key=api_key,
            frame_path=frame_path,
            prompt=text_prompt,
            max_output_tokens=350,
        )
        parsed = parse_json_object(output_text)
        raw_met = bool(parsed.get("met", False))
        confidence = clamp_float(parsed.get("confidence", 0.0))
        summary = str(parsed.get("summary") or output_text)

        return {
            "met": raw_met and confidence >= threshold,
            "raw_met": raw_met,
            "confidence": confidence,
            "threshold": threshold,
            "provider": "openai",
            "model": self.model,
            "summary": summary,
            "instruction": instruction,
            "evidence_frame_path": frame_path,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }

    def call_responses_api(self, *, api_key: str, frame_path: str, prompt: str, max_output_tokens: int) -> str:
        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": image_data_url(Path(frame_path)),
                            "detail": self.image_detail,
                        },
                    ],
                }
            ],
            "max_output_tokens": max_output_tokens,
        }
        data = json.dumps(payload).encode("utf-8")
        api_request = request.Request(
            f"{self.base_url}/responses",
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(api_request, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI vision request failed with HTTP {exc.code}: {body}") from exc
        except URLError as exc:
            raise RuntimeError(f"OpenAI vision request failed: {exc.reason}") from exc

        return extract_response_text(response_payload)

    def missing_api_key(self, frame_path: str, *, prompt: str, detail: str) -> JsonObject:
        return {
            "description": (
                f"OpenAI vision evaluator is configured, but {self.api_key_env} is not set. "
                "Provide an API key and try again."
            ),
            "provider": "openai",
            "model": self.model,
            "prompt": prompt,
            "detail": detail,
            "evidence_frame_path": frame_path,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }


def build_evaluator(config: EvaluatorConfig) -> PlaceholderEvaluator | OpenAIEvaluator:
    if config.provider == "openai":
        return OpenAIEvaluator(
            model=config.model,
            api_key_env=config.api_key_env,
            base_url=config.base_url,
            image_detail=config.detail,
            timeout_seconds=config.timeout_seconds,
        )
    return PlaceholderEvaluator()


def image_data_url(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def extract_response_text(payload: JsonObject) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    chunks: list[str] = []
    for output_item in payload.get("output", []):
        if not isinstance(output_item, dict):
            continue
        for content_item in output_item.get("content", []):
            if not isinstance(content_item, dict):
                continue
            text = content_item.get("text")
            if isinstance(text, str):
                chunks.append(text)

    if chunks:
        return "\n".join(chunks).strip()

    raise RuntimeError("OpenAI response did not include output text.")


def parse_json_object(text: str) -> JsonObject:
    stripped = text.strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return {"summary": stripped}
        try:
            parsed = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError:
            return {"summary": stripped}

    return parsed if isinstance(parsed, dict) else {"summary": stripped}


def clamp_float(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(1.0, max(0.0, number))


def is_missing_api_key(value: str | None) -> bool:
    if not value:
        return True
    normalized = value.strip().lower()
    return normalized.startswith("replace-with-") or normalized in {"your-api-key", "your-openai-api-key"}
