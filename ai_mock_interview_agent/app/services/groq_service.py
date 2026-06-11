from __future__ import annotations

from typing import Any, TypeVar

from langchain_core.messages import HumanMessage, SystemMessage
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

try:
    from langchain_groq import ChatGroq
except ImportError as exc:  # pragma: no cover - dependency issues are surfaced clearly
    ChatGroq = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

from pydantic import BaseModel

from app.config.settings import Settings, get_settings
from app.utils.json_utils import extract_json
from app.utils.prompt_loader import render_prompt

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


class GroqServiceError(RuntimeError):
    """Base class for Groq service failures."""


class GroqConfigurationError(GroqServiceError):
    """Raised when the Groq client cannot be initialized."""


class GroqService:
    """Reusable Groq service with retry, prompt loading, and structured parsing."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        if ChatGroq is None:
            raise GroqConfigurationError(
                "langchain-groq is not installed correctly. "
                "Install the dependency before using the Groq service."
            ) from _IMPORT_ERROR
        if not self.settings.groq_api_key:
            raise GroqConfigurationError("GROQ_API_KEY is not configured in the environment.")

        self.client = ChatGroq(
            groq_api_key=self.settings.groq_api_key,
            model=self.settings.groq_model,
            temperature=self.settings.groq_temperature,
            timeout=self.settings.groq_timeout_seconds,
        )

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=6),
        retry=retry_if_exception_type(Exception),
    )
    def _invoke(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
        content = getattr(response, "content", "")
        if not isinstance(content, str) or not content.strip():
            raise GroqServiceError("The model returned an empty response.")
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
        """Render a prompt template, invoke Groq, and parse the structured response."""

        system_prompt = "You are a precise production AI interviewer. Follow the instructions exactly and output JSON only."
        user_prompt = f"{user_prompt_prefix}\n\n{render_prompt(prompt_name, variables, subdirectory)}"
        raw_response = self._invoke(system_prompt=system_prompt, user_prompt=user_prompt)
        parsed = extract_json(raw_response)
        if hasattr(response_model, "model_validate"):
            return response_model.model_validate(parsed)
        return response_model.parse_obj(parsed)  # type: ignore[return-value]

    def generate_text(self, prompt_name: str, variables: dict[str, Any], subdirectory: str = "") -> str:
        system_prompt = "You are a precise production AI interviewer. Follow the instructions exactly."
        user_prompt = render_prompt(prompt_name, variables, subdirectory)
        return self._invoke(system_prompt=system_prompt, user_prompt=user_prompt)
