from __future__ import annotations

import logging
import subprocess
from typing import Any

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class SpeechToTextService:
    """Singleton service to transcribe audio with OpenAI Whisper."""

    _instance: SpeechToTextService | None = None
    _model_name: str | None = None
    _device: str | None = None

    def __new__(cls, *args: Any, **kwargs: Any) -> SpeechToTextService:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, model_name: str = "whisper-1", device: str | None = None) -> None:
        """Configure the remote OpenAI transcription model."""
        if self._model_name == model_name and self._device == device:
            return

        self._model_name = model_name
        self._device = device
        logger.info(
            "Configured remote OpenAI transcription model '%s' (device setting ignored).",
            model_name,
        )

    @property
    def is_loaded(self) -> bool:
        return self._model_name is not None

    def _get_openai_client(self):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai is not installed. Install the dependency before using the OpenAI SDK.") from exc

        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured in the environment.")

        return OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout_seconds,
            max_retries=settings.openai_max_retries,
        )

    def validate_audio(self, file_path: str) -> float:
        """Validate audio structure, duration, and integrity using ffprobe.

        Raises ValueError if audio is invalid, empty, or exceeds duration limit.
        """
        settings = get_settings()
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path,
            ]
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            output = result.stdout.strip()
            if not output:
                raise ValueError("Metadata duration missing from ffprobe output.")

            try:
                duration = float(output)
            except ValueError as val_exc:
                raise ValueError("Audio duration metadata is non-numeric.") from val_exc

            if duration <= 0:
                raise ValueError("Audio file contains no length or is silent.")

            if duration > settings.whisper_max_duration_seconds:
                raise ValueError(
                    f"Audio duration of {duration:.1f}s exceeds the maximum limit of {settings.whisper_max_duration_seconds}s."
                )

            return duration
        except (subprocess.CalledProcessError, ValueError) as exc:
            logger.warning("Audio validation failure for %s: %s", file_path, str(exc), exc_info=True)
            raise ValueError(f"Uploaded audio file is corrupted, empty, or invalid: {exc}") from exc

    def transcribe(self, file_path: str) -> str:
        """Transcribe a validated local audio file."""
        if self._model_name is None:
            raise RuntimeError("SpeechToTextService is not initialized. Call initialize() at startup first.")

        settings = get_settings()
        logger.info("Transcribing audio file %s with OpenAI model %s", file_path, self._model_name)

        try:
            client = self._get_openai_client()
            with open(file_path, "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    file=audio_file,
                    model=self._model_name,
                )

            if isinstance(response, str):
                transcript = response.strip()
            elif isinstance(response, dict):
                transcript = response.get("text", "").strip()
            else:
                transcript = getattr(response, "text", "").strip()

            return transcript
        except Exception as exc:
            logger.error("Failed to transcribe audio file %s: %s", file_path, str(exc), exc_info=True)
            raise RuntimeError(f"Transcription execution failed: {exc}") from exc


def get_stt_service() -> SpeechToTextService:
    """Dependency helper to retrieve the initialized SpeechToTextService singleton."""
    return SpeechToTextService()
