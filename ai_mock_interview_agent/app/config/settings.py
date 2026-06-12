from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Mock Interview Agent"
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(default="sqlite:///./ai_mock_interview_agent.db")

    openai_api_key: str = Field(default="", env=["OPENAI_API_KEY", "GROQ_API_KEY"])
    openai_model: str = Field(default="gpt-4o-mini", env=["OPENAI_MODEL", "GROQ_MODEL"])
    openai_temperature: float = Field(default=0.2, env=["OPENAI_TEMPERATURE", "GROQ_TEMPERATURE"])
    openai_timeout_seconds: int = Field(default=60, env=["OPENAI_TIMEOUT_SECONDS", "GROQ_TIMEOUT_SECONDS"])
    openai_max_retries: int = Field(default=3, env=["OPENAI_MAX_RETRIES", "GROQ_MAX_RETRIES"])

    interview_success_threshold: int = Field(default=7)
    interview_max_questions: int = Field(default=10)
    easy_score_threshold: int = Field(default=5)
    hard_score_threshold: int = Field(default=8)

    log_level: str = Field(default="INFO")

    whisper_model: str = Field(default="whisper-1", env=["OPENAI_WHISPER_MODEL", "WHISPER_MODEL"])
    whisper_device: str | None = Field(default=None)
    whisper_max_duration_seconds: int = Field(default=300)

    tts_enabled: bool = Field(default=True)
    tts_model: str = Field(default="gpt-4o-mini-tts", env=["OPENAI_TTS_MODEL", "TTS_MODEL"])
    tts_voice: str = Field(default="alloy", env=["OPENAI_TTS_VOICE", "TTS_VOICE"])
    tts_voice_language: str = Field(default="en")
    tts_response_format: str = Field(default="mp3", env=["OPENAI_TTS_RESPONSE_FORMAT", "TTS_RESPONSE_FORMAT"])
    tts_audio_dir: str = Field(default="static/audio")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings instance."""

    return Settings()
