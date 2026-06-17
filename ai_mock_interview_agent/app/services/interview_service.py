from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session

from app.agents import (
    AnswerEvaluatorAgent,
    DifficultyControllerAgent,
    FollowUpQuestionGeneratorAgent,
    QuestionGeneratorAgent,
    ReportGeneratorAgent,
)
from app.config.settings import get_settings
from app.graph.workflow import build_interview_graph
from app.memory.memory_manager import MemoryManager
from app.schemas.interview import (
    FinalReportResult,
    HealthResponse,
    QuestionGenerationResult,
    StartInterviewRequest,
    StartInterviewResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from app.services.openai_service import OpenAIConfigurationError, OpenAIService
from app.utils.enums import DifficultyLevel, InterviewType


class InterviewOrchestrator:
    """Coordinates database, agents, and the LangGraph workflow."""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.memory = MemoryManager(db)
        self.openai_service = self._build_openai_service()
        self.question_agent = QuestionGeneratorAgent(self.openai_service, self.memory)
        self.answer_evaluator = AnswerEvaluatorAgent(self.openai_service, self.memory)
        self.followup_agent = FollowUpQuestionGeneratorAgent(self.openai_service, self.memory)
        self.difficulty_agent = DifficultyControllerAgent(self.openai_service, self.memory)
        self.report_agent = ReportGeneratorAgent(self.openai_service, self.memory)
        self.workflow = build_interview_graph(self)

    def _build_openai_service(self) -> OpenAIService | None:
        if not self.settings.openai_api_key:
            return None
        try:
            return OpenAIService(self.settings)
        except OpenAIConfigurationError:
            return None

    def health(self) -> HealthResponse:
        return HealthResponse()

    def start_interview(self, request: StartInterviewRequest) -> StartInterviewResponse:
        session = self.memory.create_session(
            candidate_name=request.candidate_name,
            role=request.role,
            experience=request.experience,
            skills=request.skills,
            difficulty=DifficultyLevel.MEDIUM.value,
        )
        state = self.workflow.invoke(
            {
                "session_id": session.id,
                "candidate_name": request.candidate_name,
                "role": request.role,
                "experience": request.experience,
                "skills": request.skills,
            }
        )
        return StartInterviewResponse(session_id=session.id, first_question=state.get("next_question", ""))

    def submit_answer(self, request: SubmitAnswerRequest) -> SubmitAnswerResponse:
        session = self.memory.get_session(request.session_id)
        if session.questions_asked <= 0:
            raise ValueError("The interview session has not been started correctly.")
        state = self.workflow.invoke(
            {
                "session_id": session.id,
                "candidate_answer": request.answer,
            }
        )
        evaluation = state.get("evaluation", {})
        next_question = state.get("next_question", "")
        return SubmitAnswerResponse(
            evaluation=evaluation,
            next_question=next_question,
            difficulty=state.get("current_difficulty", session.difficulty),
            interview_complete=state.get("interview_complete", False),
        )

    def get_report(self, session_id: str) -> dict[str, Any]:
        report = self.memory.get_report(session_id)
        if report is None:
            result = self.report_agent.generate(session_id)
            report = self.memory.store_report(session_id, result.model_dump())
        return report.report_json

    def load_context(self, state: dict[str, Any]) -> dict[str, Any]:
        session_id = state["session_id"]
        context = self.memory.get_recent_context(session_id)
        return {
            **state,
            "candidate_name": context["candidate_name"],
            "role": context["role"],
            "experience": context["experience"],
            "skills": context["skills"],
            "current_difficulty": context["difficulty"],
            "question_count": context["questions_asked"],
            "session_context": context,
            "recent_questions": context["recent_questions"],
            "recent_answers": context["recent_answers"],
        }

    def evaluate_answer(self, state: dict[str, Any]) -> dict[str, Any]:
        session_id = state["session_id"]
        question = self.memory.get_latest_question(session_id)
        evaluation = self.answer_evaluator.evaluate(session_id, question.question, state["candidate_answer"])
        self.memory.store_answer(session_id, question.id, state["candidate_answer"], evaluation.model_dump())
        return {
            **state,
            "current_question": question.question,
            "current_question_id": question.id,
            "evaluation": evaluation.model_dump(),
        }

    def adjust_difficulty(self, state: dict[str, Any]) -> dict[str, Any]:
        session = self.memory.get_session(state["session_id"])
        evaluation = state.get("evaluation", {})
        adjusted = self.difficulty_agent.adjust(session.id, evaluation, session.difficulty)
        session.difficulty = adjusted.difficulty.value
        self.db.commit()
        return {
            **state,
            "current_difficulty": adjusted.difficulty.value,
            "difficulty_adjustment": adjusted.model_dump(),
        }

    def generate_followup(self, state: dict[str, Any]) -> dict[str, Any]:
        session_id = state["session_id"]
        question = self.memory.get_latest_question(session_id)
        evaluation = state.get("evaluation", {})
        result = self.followup_agent.generate(session_id, question.question, state["candidate_answer"], evaluation)
        stored = self.memory.store_question(session_id, result.question, result.category.value, result.difficulty.value, True)
        return {
            **state,
            "next_question": stored.question,
            "current_question": stored.question,
            "current_question_id": stored.id,
        }

    def generate_question(self, state: dict[str, Any]) -> dict[str, Any]:
        session_id = state["session_id"]
        context = self.memory.get_recent_context(session_id)
        result = self.question_agent.generate(session_id)
        stored = self.memory.store_question(session_id, result.question, result.category.value, result.difficulty.value, False)
        return {
            **state,
            "next_question": stored.question,
            "current_question": stored.question,
            "current_question_id": stored.id,
            "current_difficulty": stored.difficulty,
            "question_count": context["questions_asked"] + 1,
        }

    def generate_report(self, state: dict[str, Any]) -> dict[str, Any]:
        report = self.report_agent.generate(state["session_id"])
        report_row = self.memory.store_report(state["session_id"], report.model_dump())
        return {
            **state,
            "report": report_row.report_json,
            "interview_complete": True,
            "next_question": "",
        }

    def evaluate_answer_for_glamis(self, session_id: str, answer: str, interview_type: InterviewType) -> dict[str, Any]:
        question = self.memory.get_latest_question(session_id)
        evaluation_result = self.answer_evaluator.evaluate(
            session_id,
            question.question,
            answer,
            interview_type.value,
        )
        self.memory.store_answer(session_id, question.id, answer, evaluation_result.model_dump())
        return evaluation_result.model_dump()

    def adjust_difficulty_for_glamis(self, session_id: str, score: int) -> str:
        session = self.memory.get_session(session_id)
        adjusted = self.difficulty_agent.adjust(session_id, {"overall_score": score}, session.difficulty)
        session.difficulty = adjusted.difficulty.value
        self.db.commit()
        return session.difficulty

    def generate_first_question(self, session_id: str, interview_type: InterviewType) -> QuestionGenerationResult:
        session = self.memory.get_session(session_id)
        subject = session.subject if interview_type == InterviewType.SUBJECT else None
        result = self.question_agent.generate(
            session_id,
            interview_type=interview_type.value,
            subject=subject,
        )
        if not result.question:
            raise ValueError("Failed to generate the first GLAMIS interview question.")
        return result

    def generate_next_question(self, session_id: str, interview_type: InterviewType) -> QuestionGenerationResult:
        return self.generate_first_question(session_id, interview_type)

    def generate_followup_question(self, session_id: str) -> QuestionGenerationResult:
        session = self.memory.get_session(session_id)
        latest_question = self.memory.get_latest_question(session_id)
        recent_answers = self.memory.get_recent_answers(session_id, limit=1)
        last_answer = recent_answers[0].answer if recent_answers else ""
        evaluation = recent_answers[0].evaluation_json if recent_answers else {}
        result = self.followup_agent.generate(
            session_id,
            latest_question.question,
            last_answer,
            evaluation,
            interview_type=session.interview_type,
        )
        return result

    def store_generated_question(self, session_id: str, result: QuestionGenerationResult, is_follow_up: bool = False) -> str:
        stored = self.memory.store_question(
            session_id,
            result.question,
            result.category.value,
            result.difficulty.value,
            is_follow_up,
        )
        return stored.question

    def route_from_context(self, state: dict[str, Any]) -> str:
        return "evaluate_answer" if state.get("candidate_answer") else "generate_question"

    def route_after_adjustment(self, state: dict[str, Any]) -> str:
        session = self.memory.get_session(state["session_id"])
        evaluation = state.get("evaluation", {})
        if session.questions_asked >= self.settings.interview_max_questions:
            return "generate_report"
        if evaluation.get("follow_up_needed") or evaluation.get("overall_score", 0) < self.settings.interview_success_threshold:
            return "generate_followup"
        return "generate_question"
