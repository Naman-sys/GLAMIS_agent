from __future__ import annotations

import hashlib
import logging
import os
from typing import Any

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class TextToSpeechService:
    """Singleton service to convert text to speech using gTTS with local caching."""

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
        # Ensure static audio directory exists
        os.makedirs(settings.tts_audio_dir, exist_ok=True)
        self._initialized = True

    def generate_audio(self, text: str) -> str | None:
        """Convert text to speech and return the static URL of the generated MP3.

        Uses MD5 hashing to cache files and avoid redundant generation.
        Returns None if TTS is disabled or generation fails.
        """
        settings = get_settings()
        if not settings.tts_enabled:
            return None

        clean_text = text.strip()
        if not clean_text:
            return None

        # Compute hash of the text to use as a cache key
        text_hash = hashlib.md5(clean_text.encode("utf-8")).hexdigest()
        filename = f"{text_hash}.mp3"
        filepath = os.path.join(settings.tts_audio_dir, filename)
        relative_url = f"/static/audio/{filename}"

        # Check cache: if file exists, reuse it
        if os.path.exists(filepath):
            logger.info("TTS cache hit for text hash %s: %s", text_hash, relative_url)
            return relative_url

        logger.info("Generating new TTS audio for text hash %s...", text_hash)
        try:
            from gtts import gTTS

            # Generate speech locally
            tts = gTTS(text=clean_text, lang=settings.tts_voice_language)
            
            # Ensure the directory exists just in case
            os.makedirs(settings.tts_audio_dir, exist_ok=True)
            
            tts.save(filepath)
            logger.info("Successfully generated TTS audio file: %s", filepath)
            return relative_url
        except Exception as exc:
            logger.warning("Failed to generate TTS audio for '%s': %s", clean_text[:30], str(exc), exc_info=True)
            return None


def get_tts_service() -> TextToSpeechService:
    """Dependency helper to retrieve the TextToSpeechService singleton."""
    return TextToSpeechService()
