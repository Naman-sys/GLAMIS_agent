from __future__ import annotations

import logging
import subprocess
from typing import Any

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class SpeechToTextService:
    """Singleton service to load OpenAI Whisper locally and transcribe audio files."""

    _instance: SpeechToTextService | None = None
    _model: Any = None
    _model_name: str | None = None
    _device: str | None = None

    def __new__(cls, *args: Any, **kwargs: Any) -> SpeechToTextService:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, model_name: str = "base", device: str | None = None) -> None:
        """Load the Whisper model once at startup."""

        if self._model is not None:
            if self._model_name == model_name and self._device == device:
                return
            logger.info("Re-initializing Whisper model from %s to %s", self._model_name, model_name)

        logger.info("Loading local Whisper model '%s'...", model_name)
        try:
            import torch
            import whisper

            if device is None:
                device = "cuda" if torch.cuda.is_available() else "cpu"

            self._model = whisper.load_model(model_name, device=device)
            self._model_name = model_name
            self._device = device
            logger.info("Whisper model '%s' successfully loaded on device: %s", model_name, device)
        except Exception as exc:
            logger.error("Failed to load Whisper model locally: %s", str(exc), exc_info=True)
            raise RuntimeError(f"Failed to initialize local Whisper service: {exc}") from exc

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

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
                file_path
            ]
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
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
        """Transcribe a validated local audio file.

        Raises RuntimeError if model is not initialized.
        """
        if self._model is None:
            raise RuntimeError("SpeechToTextService is not initialized. Call initialize() at startup first.")

        logger.info("Transcribing audio file: %s", file_path)
        try:
            result = self._model.transcribe(file_path)
            transcript = result.get("text", "").strip()
            return transcript
        except Exception as exc:
            logger.error("Failed to transcribe audio file %s: %s", file_path, str(exc), exc_info=True)
            raise RuntimeError(f"Transcription execution failed: {exc}") from exc


def get_stt_service() -> SpeechToTextService:
    """Dependency helper to retrieve the initialized SpeechToTextService singleton."""
    return SpeechToTextService()
