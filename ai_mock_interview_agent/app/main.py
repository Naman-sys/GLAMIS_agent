from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config.settings import get_settings
from app.database.session import init_db
from app.services.speech_to_text_service import get_stt_service

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    # Ensure static audio directory exists
    os.makedirs(settings.tts_audio_dir, exist_ok=True)

    # Configure remote OpenAI transcription model at startup
    get_stt_service().initialize(settings.whisper_model, settings.whisper_device)

    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Ensure static directory exists before mounting
    from pathlib import Path
    package_root = Path(__file__).resolve().parent.parent
    static_dir = os.path.join(package_root, "static")
    os.makedirs(static_dir, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    app.include_router(router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
