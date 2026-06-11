from __future__ import annotations

from typing import Any, TypedDict


class InterviewState(TypedDict, total=False):
    session_id: str
    candidate_name: str
    role: str
    experience: str
    skills: list[str]
    current_difficulty: str
    question_count: int
    current_question: str
    current_question_id: int
    candidate_answer: str
    evaluation: dict[str, Any]
    next_question: str
    report: dict[str, Any]
    interview_complete: bool
    session_context: dict[str, Any]
    recent_questions: list[dict[str, Any]]
    recent_answers: list[dict[str, Any]]
