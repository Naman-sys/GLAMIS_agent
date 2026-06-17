from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.adapters.glamis_adapter import GLAMISAdapter
from app.api.deps import get_interview_orchestrator
from app.schemas.glamis import GLAMISRequest, GLAMISResponse, GLAMISReportResponse
from app.schemas.interview import (
    HealthResponse,
    InterviewReportResponse,
    StartInterviewRequest,
    StartInterviewResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    SubmitVoiceAnswerResponse,
    SpeechGenerationRequest,
    SpeechGenerationResponse,
)
from app.services.interview_service import InterviewOrchestrator
from app.services.speech_to_text_service import get_stt_service, SpeechToTextService
from app.services.text_to_speech_service import get_tts_service, TextToSpeechService
from app.schemas.admin_task import AdminTaskRequest, AdminTaskResponse
from app.agents.admin_task_agent import AdminTaskAgent

router = APIRouter(tags=["interview"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@router.post("/start-interview", response_model=StartInterviewResponse)
def start_interview(
    payload: StartInterviewRequest,
    orchestrator: InterviewOrchestrator = Depends(get_interview_orchestrator),
    tts_service: TextToSpeechService = Depends(get_tts_service),
) -> StartInterviewResponse:
    try:
        response = orchestrator.start_interview(payload)
        audio_url = tts_service.generate_audio(response.first_question)
        return StartInterviewResponse(
            session_id=response.session_id,
            first_question=response.first_question,
            audio_url=audio_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/submit-answer", response_model=SubmitAnswerResponse)
def submit_answer(
    payload: SubmitAnswerRequest,
    orchestrator: InterviewOrchestrator = Depends(get_interview_orchestrator),
    tts_service: TextToSpeechService = Depends(get_tts_service),
) -> SubmitAnswerResponse:
    try:
        response = orchestrator.submit_answer(payload)
        audio_url = tts_service.generate_audio(response.next_question)
        return SubmitAnswerResponse(
            evaluation=response.evaluation,
            next_question=response.next_question,
            difficulty=response.difficulty,
            interview_complete=response.interview_complete,
            audio_url=audio_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/interview-report/{session_id}", response_model=InterviewReportResponse)
def interview_report(
    session_id: str,
    orchestrator: InterviewOrchestrator = Depends(get_interview_orchestrator),
) -> InterviewReportResponse:
    try:
        report = orchestrator.get_report(session_id)
        return InterviewReportResponse(session_id=session_id, report=report)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/submit-voice-answer", response_model=SubmitVoiceAnswerResponse)
def submit_voice_answer(
    session_id: str = Form(...),
    audio_file: UploadFile = File(...),
    orchestrator: InterviewOrchestrator = Depends(get_interview_orchestrator),
    stt_service: SpeechToTextService = Depends(get_stt_service),
    tts_service: TextToSpeechService = Depends(get_tts_service),
) -> SubmitVoiceAnswerResponse:
    if not audio_file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No audio file uploaded.")

    ext = os.path.splitext(audio_file.filename)[1].lower()
    allowed_extensions = {".mp3", ".wav", ".m4a", ".webm"}
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format. Supported formats are: {', '.join(sorted(allowed_extensions))}"
        )

    fd, temp_path = tempfile.mkstemp(suffix=ext)
    try:
        with os.fdopen(fd, "wb") as temp_file:
            while chunk := audio_file.file.read(1024 * 1024):
                temp_file.write(chunk)

        try:
            stt_service.validate_audio(temp_path)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        try:
            transcript = stt_service.transcribe(temp_path)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to transcribe audio file: {exc}"
            ) from exc

        if not transcript.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio transcription produced no text. Please answer clearly."
            )

        submit_payload = SubmitAnswerRequest(session_id=session_id, answer=transcript)
        try:
            session_response = orchestrator.submit_answer(submit_payload)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

        audio_url = tts_service.generate_audio(session_response.next_question)

        return SubmitVoiceAnswerResponse(
            transcript=transcript,
            evaluation=session_response.evaluation,
            next_question=session_response.next_question,
            difficulty=session_response.difficulty,
            interview_complete=session_response.interview_complete,
            audio_url=audio_url,
        )

    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@router.post("/glamis/start-interview", response_model=GLAMISResponse)
def glamis_start_interview(
    payload: GLAMISRequest,
    orchestrator: InterviewOrchestrator = Depends(get_interview_orchestrator),
    tts_service: TextToSpeechService = Depends(get_tts_service),
) -> GLAMISResponse:
    try:
        internal_request = GLAMISAdapter.convert_request_to_internal(payload)
        interview_type = GLAMISAdapter.get_interview_type(payload)

        session = orchestrator.memory.create_glamis_session(
            candidate_name=payload.metadata.get("candidate_name", "Candidate"),
            role=payload.metadata.get("role", "Software Engineer"),
            experience=payload.metadata.get("experience", "0-2 years"),
            skills=payload.metadata.get("skills", []),
            interview_type=interview_type.value,
            subject=internal_request.get("subject"),
            company=internal_request.get("company"),
            job_title=internal_request.get("job_title"),
            jd_details=internal_request.get("jd_details"),
            svar_type=internal_request.get("svar_type"),
        )

        first_question_result = orchestrator.generate_first_question(session.id, interview_type)
        first_question = orchestrator.store_generated_question(session.id, first_question_result, is_follow_up=False)
        audio_url = tts_service.generate_audio(first_question)

        return GLAMISAdapter.convert_response_to_glamis(
            session_id=session.id,
            next_question=first_question,
            audio_url=audio_url,
            interview_type=interview_type.value,
            metadata=payload.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/glamis/submit-answer", response_model=GLAMISResponse)
def glamis_submit_answer(
    payload: GLAMISRequest,
    orchestrator: InterviewOrchestrator = Depends(get_interview_orchestrator),
    tts_service: TextToSpeechService = Depends(get_tts_service),
) -> GLAMISResponse:
    try:
        session_id = payload.interviewId
        if not session_id:
            raise ValueError("interviewId is required")

        session = orchestrator.memory.get_session(session_id)
        interview_type = GLAMISAdapter.get_interview_type(payload)

        evaluation = orchestrator.evaluate_answer_for_glamis(
            session_id=session_id,
            answer=payload.answer or "",
            interview_type=interview_type,
        )

        if evaluation.get("overall_score", 0) < 6:
            for weakness in evaluation.get("weaknesses", []):
                orchestrator.memory.update_weak_areas(session_id, weakness)
        else:
            for strength in evaluation.get("strengths", []):
                orchestrator.memory.update_strong_areas(session_id, strength)

        adjusted_difficulty = orchestrator.adjust_difficulty_for_glamis(
            session_id=session_id,
            score=evaluation.get("overall_score", 0),
        )

        follow_up_needed = GLAMISAdapter.should_generate_followup(
            interview_type=interview_type,
            score=evaluation.get("overall_score", 0),
            evaluation=evaluation,
        )

        if follow_up_needed and evaluation.get("follow_up_needed", False):
            next_result = orchestrator.generate_followup_question(session_id)
            is_follow_up = True
        else:
            next_result = orchestrator.generate_next_question(session_id, interview_type)
            is_follow_up = False

        next_question = orchestrator.store_generated_question(session_id, next_result, is_follow_up=is_follow_up)
        audio_url = tts_service.generate_audio(next_question) if next_question else None
        follow_up_question = next_question if is_follow_up else None

        return GLAMISAdapter.convert_response_to_glamis(
            session_id=session_id,
            next_question=next_question,
            evaluation=evaluation,
            difficulty=adjusted_difficulty,
            interview_complete=False,
            audio_url=audio_url,
            follow_up_question=follow_up_question,
            interview_type=interview_type.value,
            metadata=payload.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/glamis/report/{session_id}", response_model=GLAMISReportResponse)
def glamis_interview_report(
    session_id: str,
    orchestrator: InterviewOrchestrator = Depends(get_interview_orchestrator),
) -> GLAMISReportResponse:
    try:
        session = orchestrator.memory.get_session(session_id)
        report = orchestrator.get_report(session_id)

        weak_areas = orchestrator.memory.get_weak_areas(session_id, top_n=5)
        strong_areas = orchestrator.memory.get_strong_areas(session_id, top_n=5)

        return GLAMISReportResponse(
            interviewId=session_id,
            candidate_name=session.candidate_name,
            subject=session.subject,
            interview_type=session.interview_type,
            total_questions=session.questions_asked,
            average_score=report.get("overall_score", 0),
            technical_score=report.get("technical_score", 0),
            communication_score=report.get("communication_score", 0),
            overall_score=report.get("overall_score", 0),
            strengths=list(strong_areas.keys()),
            weaknesses=list(weak_areas.keys()),
            recommendations=report.get("recommendations", []),
            summary=report.get("summary", ""),
            interview_outcome=report.get("interview_outcome", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/generate-speech", response_model=SpeechGenerationResponse)
def generate_speech(
    payload: SpeechGenerationRequest,
    tts_service: TextToSpeechService = Depends(get_tts_service),
) -> SpeechGenerationResponse:
    audio_url = tts_service.generate_audio(payload.text)
    if audio_url is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate speech for the requested text."
        )
    return SpeechGenerationResponse(audio_url=audio_url)


@router.post("/agent/admin-task", response_model=AdminTaskResponse)
def execute_admin_task(
    payload: AdminTaskRequest,
    orchestrator: InterviewOrchestrator = Depends(get_interview_orchestrator),
) -> AdminTaskResponse:
    agent = AdminTaskAgent(orchestrator.openai_service, orchestrator.memory)
    return agent.execute_task(payload.task)

