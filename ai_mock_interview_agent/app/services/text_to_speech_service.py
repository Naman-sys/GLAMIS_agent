from __future__ import annotations

import hashlib
import logging
import os
from typing import Any

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class TextToSpeechService:
    """Singleton service to convert text to speech with OpenAI TTS and cached local audio."""

    _instance: TextToSpeechService | None = None
    _initialized: bool = False

    def __new__(cls, *args: Any, **kwargs: Any) -> TextToSpeechService:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        settings = get_settings()
        os.makedirs(settings.tts_audio_dir, exist_ok=True)
        self._initialized = True

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

    def _save_openai_audio(self, response: Any, filepath: str) -> None:
        if hasattr(response, "read"):
            audio_bytes = response.read()
        elif isinstance(response, (bytes, bytearray)):
            audio_bytes = bytes(response)
        elif isinstance(response, str):
            audio_bytes = response.encode("utf-8")
        else:
            audio_bytes = bytes(response)

        with open(filepath, "wb") as audio_file:
            audio_file.write(audio_bytes)

    def generate_audio(self, text: str) -> str | None:
        """Convert text to speech and return the static URL of the generated MP3."""
        settings = get_settings()
        if not settings.tts_enabled:
            return None

        clean_text = text.strip()
        if not clean_text:
            return None

        text_hash = hashlib.md5(clean_text.encode("utf-8")).hexdigest()
        filename = f"{text_hash}.mp3"
        filepath = os.path.join(settings.tts_audio_dir, filename)
        relative_url = f"/static/audio/{filename}"

        if os.path.exists(filepath):
            logger.info("TTS cache hit for text hash %s: %s", text_hash, relative_url)
            return relative_url

        logger.info("Generating new TTS audio for text hash %s...", text_hash)
        try:
            client = self._get_openai_client()
            response = client.audio.speech.create(
                input=clean_text,
                model=settings.tts_model,
                voice=settings.tts_voice,
                response_format=settings.tts_response_format,
            )
            self._save_openai_audio(response, filepath)
            logger.info("Successfully generated OpenAI TTS audio file: %s", filepath)
            return relative_url
        except Exception as exc:
            logger.warning("OpenAI TTS generation failed for '%s': %s", clean_text[:30], str(exc), exc_info=True)

        try:
            from gtts import gTTS

            tts = gTTS(text=clean_text, lang=settings.tts_voice_language)
            os.makedirs(settings.tts_audio_dir, exist_ok=True)
            tts.save(filepath)
            logger.info("Successfully generated fallback TTS audio file: %s", filepath)
            return relative_url
        except Exception as exc:
            logger.warning("Failed to generate fallback TTS audio for '%s': %s", clean_text[:30], str(exc), exc_info=True)
            return None


def get_tts_service() -> TextToSpeechService:
    """Dependency helper to retrieve the TextToSpeechService singleton."""
    return TextToSpeechService()
