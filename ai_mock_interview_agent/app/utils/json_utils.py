from __future__ import annotations

import json
import re
from typing import Any


_JSON_BLOCK_PATTERN = re.compile(r"```json\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)
_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


def extract_json(text: Any) -> Any:
    """Extract and parse JSON from an LLM response."""

    if isinstance(text, (dict, list)):
        return text

    if not text:
        raise ValueError("Empty response received from the model.")

    cleaned_text = str(text).strip()
    block_match = _JSON_BLOCK_PATTERN.search(cleaned_text)
    if block_match:
        cleaned_text = block_match.group(1).strip()

    object_match = _OBJECT_PATTERN.search(cleaned_text)
    if object_match:
        cleaned_text = object_match.group(0)

    return json.loads(cleaned_text)


def safe_json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)
