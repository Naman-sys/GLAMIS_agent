import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TTS_AUDIO_DIR = os.path.join(PROJECT_ROOT, "static", "audio")



class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Mock Interview Agent"
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(default="sqlite:///./ai_mock_interview_agent.db")

    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    openai_temperature: float = Field(default=0.2, env="OPENAI_TEMPERATURE")
    openai_timeout_seconds: int = Field(default=60, env="OPENAI_TIMEOUT_SECONDS")
    openai_max_retries: int = Field(default=3, env="OPENAI_MAX_RETRIES")

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
    tts_audio_dir: str = Field(default=DEFAULT_TTS_AUDIO_DIR)

    # GLAMIS Admin Automation Integration settings
    glamis_backend_url: str = Field(default="http://localhost:8001")
    glamis_admin_email: str = Field(default="admin@glamis.in")
    glamis_admin_password: str = Field(default="demo123")
    mongodb_url: str | None = Field(default=None)



@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings instance."""

    return Settings()
