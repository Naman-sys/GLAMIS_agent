from __future__ import annotations

import os
import shutil
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

import gtts
from app.config.settings import get_settings

# Mock gTTS.save to write a dummy file locally instead of making an HTTP request
def mock_gtts_save(self, savefile: str) -> None:
    with open(savefile, "wb") as f:
        f.write(b"dummy mp3 data")

gtts.gTTS.save = mock_gtts_save


@pytest.fixture(autouse=True)
def cleanup_audio_dir() -> None:
    settings = get_settings()
    if os.path.exists(settings.tts_audio_dir):
        shutil.rmtree(settings.tts_audio_dir)
    os.makedirs(settings.tts_audio_dir, exist_ok=True)
    yield
    if os.path.exists(settings.tts_audio_dir):
        shutil.rmtree(settings.tts_audio_dir)


def test_generate_speech_success(client) -> None:
    # 1. Verify successful speech generation
    payload = {"text": "Explain HashMap in Java."}
    response = client.post("/api/v1/generate-speech", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "audio_url" in data
    assert data["audio_url"].startswith("/static/audio/")
    assert data["audio_url"].endswith(".mp3")
    
    # Verify file was created on disk
    settings = get_settings()
    filename = data["audio_url"].split("/")[-1]
    filepath = os.path.join(settings.tts_audio_dir, filename)
    assert os.path.exists(filepath)


def test_generate_speech_caching(client) -> None:
    # 2. Verify that duplicate text requests hit the MD5 cache and reuse the file
    payload = {"text": "What is dependency injection?"}
    
    response_1 = client.post("/api/v1/generate-speech", json=payload)
    assert response_1.status_code == status.HTTP_200_OK
    url_1 = response_1.json()["audio_url"]
    
    response_2 = client.post("/api/v1/generate-speech", json=payload)
    assert response_2.status_code == status.HTTP_200_OK
    url_2 = response_2.json()["audio_url"]
    
    # Both URLs must be identical
    assert url_1 == url_2


def test_generate_speech_validation_error(client) -> None:
    # 3. Verify that empty text returns validation error
    payload = {"text": ""}
    response = client.post("/api/v1/generate-speech", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_interview_responses_contain_audio_url(client) -> None:
    # 4. Verify start-interview and submit-answer return audio_url
    start_payload = {
        "candidate_name": "Charlie",
        "role": "Python Backend Developer",
        "experience": "Mid",
        "skills": ["FastAPI", "PostgreSQL"],
    }
    
    # Start interview
    response = client.post("/api/v1/start-interview", json=start_payload)
    assert response.status_code == status.HTTP_200_OK
    start_data = response.json()
    assert "audio_url" in start_data
    assert start_data["audio_url"] is not None
    assert start_data["audio_url"].startswith("/static/audio/")
    
    session_id = start_data["session_id"]
    
    # Submit answer
    answer_payload = {
        "session_id": session_id,
        "answer": "A connection pool keeps database connections open to reuse them.",
    }
    ans_res = client.post("/api/v1/submit-answer", json=answer_payload)
    assert ans_res.status_code == status.HTTP_200_OK
    ans_data = ans_res.json()
    assert "audio_url" in ans_data
    assert ans_data["audio_url"] is not None
    assert ans_data["audio_url"].startswith("/static/audio/")
