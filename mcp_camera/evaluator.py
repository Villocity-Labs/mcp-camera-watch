from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class PlaceholderEvaluator:
    """Evaluator placeholder until a vision backend is configured."""

    def describe(self, *, frame_path: str, prompt: str, detail: str) -> dict[str, Any]:
        return {
            "description": (
                "No vision evaluator is configured yet. The frame was captured, "
                "but visual description is not available."
            ),
            "prompt": prompt,
            "detail": detail,
            "evidence_frame_path": frame_path,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }

    def evaluate(self, *, instruction: str, frame_path: str, threshold: float) -> dict[str, Any]:
        return {
            "met": False,
            "confidence": 0.0,
            "threshold": threshold,
            "summary": (
                "No vision evaluator is configured yet. The frame was captured, "
                "but the condition was not evaluated."
            ),
            "instruction": instruction,
            "evidence_frame_path": frame_path,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
