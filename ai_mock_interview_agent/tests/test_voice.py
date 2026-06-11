from __future__ import annotations

import io
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.services.speech_to_text_service import get_stt_service


class MockSpeechToTextService:
    def __init__(self) -> None:
        self.is_loaded = True

    def initialize(self, model_name: str, device: str | None = None) -> None:
        pass

    def validate_audio(self, file_path: str) -> float:
        with open(file_path, "rb") as f:
            content = f.read().decode("utf-8", errors="ignore")
        if "invalid header data" in content:
            raise ValueError("Uploaded audio file is corrupted, empty, or invalid.")
        if "too much audio content" in content:
            raise ValueError("Audio duration exceeds the maximum limit.")
        if "silent bytes" in content:
            raise ValueError("Audio file contains no length or is silent.")
        return 5.0

    def transcribe(self, file_path: str) -> str:
        with open(file_path, "rb") as f:
            content = f.read().decode("utf-8", errors="ignore")
        if "no speech" in content:
            return ""
        return "This is a mock transcribed answer about FastAPI."


@pytest.fixture()
def voice_client(client) -> TestClient:
    mock_service = MockSpeechToTextService()
    app.dependency_overrides[get_stt_service] = lambda: mock_service
    yield client
    app.dependency_overrides.clear()


def test_submit_voice_unsupported_format(voice_client) -> None:
    # 1. Unsupported extension (.txt)
    response = voice_client.post(
        "/api/v1/submit-voice-answer",
        data={"session_id": "test-session"},
        files={"audio_file": ("test.txt", io.BytesIO(b"dummy content"), "text/plain")}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Unsupported audio format" in response.json()["detail"]


def test_submit_voice_missing_file(voice_client) -> None:
    # 2. Missing form fields or missing file entirely (raises 400 or 422 validation)
    response = voice_client.post(
        "/api/v1/submit-voice-answer",
        data={"session_id": "test-session"},
        files={"audio_file": ("", io.BytesIO(b""), "")}
    )
    assert response.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY)


def test_submit_voice_corrupted_audio(voice_client) -> None:
    # 3. Validation failure: Corrupt file
    response = voice_client.post(
        "/api/v1/submit-voice-answer",
        data={"session_id": "test-session"},
        files={"audio_file": ("corrupt.wav", io.BytesIO(b"invalid header data"), "audio/wav")}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "corrupted, empty, or invalid" in response.json()["detail"]


def test_submit_voice_duration_exceeded(voice_client) -> None:
    # 4. Validation failure: Too long audio
    response = voice_client.post(
        "/api/v1/submit-voice-answer",
        data={"session_id": "test-session"},
        files={"audio_file": ("long.mp3", io.BytesIO(b"too much audio content"), "audio/mpeg")}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "exceeds the maximum limit" in response.json()["detail"]


def test_submit_voice_empty_silent(voice_client) -> None:
    # 5. Validation failure: Empty/silent audio
    response = voice_client.post(
        "/api/v1/submit-voice-answer",
        data={"session_id": "test-session"},
        files={"audio_file": ("empty_silent.webm", io.BytesIO(b"silent bytes"), "audio/webm")}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "contains no length or is silent" in response.json()["detail"]


def test_submit_voice_blank_transcription(voice_client) -> None:
    # 6. Transcription produces no text
    response = voice_client.post(
        "/api/v1/submit-voice-answer",
        data={"session_id": "test-session"},
        files={"audio_file": ("blank.m4a", io.BytesIO(b"no speech"), "audio/x-m4a")}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "produced no text" in response.json()["detail"]


def test_submit_voice_success(voice_client) -> None:
    # 7. Successful transcription and interview workflow submission
    start_payload = {
        "candidate_name": "Bob",
        "role": "Python Developer",
        "experience": "Mid",
        "skills": ["Python", "FastAPI"],
    }
    start_res = voice_client.post("/api/v1/start-interview", json=start_payload)
    session_id = start_res.json()["session_id"]

    response = voice_client.post(
        "/api/v1/submit-voice-answer",
        data={"session_id": session_id},
        files={"audio_file": ("good.wav", io.BytesIO(b"valid audio bytes here"), "audio/wav")}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["transcript"] == "This is a mock transcribed answer about FastAPI."
    assert "evaluation" in data
    assert "next_question" in data
    assert data["difficulty"] in {"Easy", "Medium", "Hard"}
    assert data["interview_complete"] is False
