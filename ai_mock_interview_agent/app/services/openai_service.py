from __future__ import annotations

import json
from typing import Any, TypeVar

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

try:
    from openai import OpenAI
except ImportError as exc:  # pragma: no cover - dependency issues are surfaced clearly
    OpenAI = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

from pydantic import BaseModel

from app.config.settings import Settings, get_settings
from app.utils.json_utils import extract_json
from app.utils.prompt_loader import render_prompt

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


class OpenAIServiceError(RuntimeError):
    """Base class for OpenAI service failures."""


class OpenAIConfigurationError(OpenAIServiceError):
    """Raised when the OpenAI client cannot be initialized."""


class OpenAIService:
    """Reusable OpenAI service with retry, prompt loading, and structured parsing."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        if OpenAI is None:
            raise OpenAIConfigurationError(
                "openai is not installed correctly. "
                "Install the dependency before using the OpenAI service."
            ) from _IMPORT_ERROR
        if not self.settings.openai_api_key:
            raise OpenAIConfigurationError("OPENAI_API_KEY is not configured in the environment.")

        self.client = OpenAI(
            api_key=self.settings.openai_api_key,
            timeout=self.settings.openai_timeout_seconds,
            max_retries=self.settings.openai_max_retries,
        )

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=6),
        retry=retry_if_exception_type(Exception),
    )
    def _invoke(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.settings.openai_model,
            temperature=self.settings.openai_temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = ""
        if hasattr(response, "choices") and response.choices:
            choice = response.choices[0]
            message = getattr(choice, "message", None)
            if isinstance(message, dict):
                content = message.get("content", "")
            else:
                content = getattr(message, "content", "")

        if isinstance(content, dict):
            return json.dumps(content)

        if not isinstance(content, str) or not content.strip():
            raise OpenAIServiceError("The model returned an empty response.")
        return content

    def generate_structured(
        self,
        prompt_name: str,
        variables: dict[str, Any],
        response_model: type[ResponseModel],
        *,
        user_prompt_prefix: str = "Return only valid JSON.",
        subdirectory: str = "",
    ) -> ResponseModel:
        """Render a prompt template, invoke OpenAI, and parse the structured response."""

        system_prompt = "You are a precise production AI interviewer. Follow the instructions exactly and output JSON only."
        user_prompt = f"{user_prompt_prefix}\n\n{render_prompt(prompt_name, variables, subdirectory)}"
        raw_response = self._invoke(system_prompt=system_prompt, user_prompt=user_prompt)
        parsed = extract_json(raw_response)
        parsed = self._normalize_structured_response(parsed, response_model)
        if hasattr(response_model, "model_validate"):
            return response_model.model_validate(parsed)
        return response_model.parse_obj(parsed)  # type: ignore[return-value]

    def _normalize_structured_response(self, parsed: Any, response_model: type[ResponseModel]) -> Any:
        if not isinstance(parsed, dict):
            return parsed

        model_keys = set(
            response_model.model_fields.keys()
            if hasattr(response_model, "model_fields")
            else response_model.__fields__.keys()
        )

        if model_keys.issubset(parsed.keys()):
            return parsed

        if "questions" in parsed and isinstance(parsed["questions"], list) and len(parsed["questions"]) > 0:
            candidate = parsed["questions"][0]
            if isinstance(candidate, dict) and model_keys.issubset(candidate.keys()):
                return candidate

        if "output" in parsed and isinstance(parsed["output"], dict) and model_keys.issubset(parsed["output"].keys()):
            return parsed["output"]

        if len(parsed) == 1:
            only_value = next(iter(parsed.values()))
            if isinstance(only_value, dict) and model_keys.issubset(only_value.keys()):
                return only_value

        for value in parsed.values():
            if isinstance(value, dict) and model_keys.issubset(value.keys()):
                return value

        return parsed

    def generate_text(self, prompt_name: str, variables: dict[str, Any], subdirectory: str = "") -> str:
        system_prompt = "You are a precise production AI interviewer. Follow the instructions exactly."
        user_prompt = render_prompt(prompt_name, variables, subdirectory)
        return self._invoke(system_prompt=system_prompt, user_prompt=user_prompt)
