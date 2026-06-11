from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Mock Interview Agent"
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(default="sqlite:///./ai_mock_interview_agent.db")

    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="llama-3.3-70b-versatile")
    groq_temperature: float = Field(default=0.2)
    groq_timeout_seconds: int = Field(default=60)
    groq_max_retries: int = Field(default=3)

    interview_success_threshold: int = Field(default=7)
    interview_max_questions: int = Field(default=10)
    easy_score_threshold: int = Field(default=5)
    hard_score_threshold: int = Field(default=8)

    log_level: str = Field(default="INFO")

    whisper_model: str = Field(default="base")
    whisper_device: str | None = Field(default=None)
    whisper_max_duration_seconds: int = Field(default=300)

    tts_enabled: bool = Field(default=True)
    tts_voice_language: str = Field(default="en")
    tts_audio_dir: str = Field(default="static/audio")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings instance."""

    return Settings()
