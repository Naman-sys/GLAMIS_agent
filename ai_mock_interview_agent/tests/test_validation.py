from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.interview import (
    AnswerEvaluationResult,
    DifficultyAdjustmentResult,
    QuestionGenerationResult,
    FollowUpGenerationResult,
    FinalReportResult,
)
from app.utils.enums import DifficultyLevel, QuestionCategory


def test_answer_evaluation_result_score_coercion() -> None:
    # Verify that floats are rounded to closest integer and float-strings are resolved
    payload = {
        "technical_score": 7.4,         # Expected: 7
        "communication_score": "8.6",     # Expected: 9
        "relevance_score": 6.6,          # Expected: 7
        "problem_solving_score": 5.0,    # Expected: 5
        "completeness_score": 4.2,       # Expected: 4
        "overall_score": 6.8,            # Expected: 7
        "feedback": "Good answer.",
        "strengths": ["Clear explain"],
        "weaknesses": [],
        "follow_up_needed": False,
    }
    result = AnswerEvaluationResult(**payload)
    assert result.technical_score == 7
    assert result.communication_score == 9
    assert result.relevance_score == 7
    assert result.problem_solving_score == 5
    assert result.completeness_score == 4
    assert result.overall_score == 7


def test_difficulty_adjustment_result_normalization() -> None:
    # Test lowercase difficulty normalization and action normalization
    payload = {
        "difficulty": "easy ",           # Expected: DifficultyLevel.EASY ("Easy")
        "action": " INCREASE ",          # Expected: "increase"
        "reason": "Consistent strengths",
    }
    result = DifficultyAdjustmentResult(**payload)
    assert result.difficulty == DifficultyLevel.EASY
    assert result.action == "increase"


def test_question_generation_result_normalization() -> None:
    # Test lowercase category and casing variants
    payload = {
        "question": "Explain inheritance.",
        "category": "technical",         # Expected: QuestionCategory.TECHNICAL ("Technical")
        "difficulty": "medium",          # Expected: DifficultyLevel.MEDIUM ("Medium")
        "rationale": "Base check",
    }
    result = QuestionGenerationResult(**payload)
    assert result.category == QuestionCategory.TECHNICAL
    assert result.difficulty == DifficultyLevel.MEDIUM

    payload_problem = {
        "question": "Design a rate limiter.",
        "category": "problem-solving",   # Expected: QuestionCategory.PROBLEM_SOLVING ("Problem Solving")
        "difficulty": "HARD",            # Expected: DifficultyLevel.HARD ("Hard")
        "rationale": "Advanced scenario",
    }
    result_problem = QuestionGenerationResult(**payload_problem)
    assert result_problem.category == QuestionCategory.PROBLEM_SOLVING
    assert result_problem.difficulty == DifficultyLevel.HARD

    payload_hr = {
        "question": "Tell me about a conflict.",
        "category": "hr",                # Expected: QuestionCategory.HR ("HR")
        "difficulty": "easy",            # Expected: DifficultyLevel.EASY ("Easy")
        "rationale": "HR check",
    }
    result_hr = QuestionGenerationResult(**payload_hr)
    assert result_hr.category == QuestionCategory.HR
    assert result_hr.difficulty == DifficultyLevel.EASY


def test_final_report_result_score_coercion() -> None:
    payload = {
        "candidate_name": "Alice",
        "role": "Engineer",
        "technical_score": 8.4,
        "communication_score": 7.5,
        "problem_solving_score": 6.6,
        "overall_score": 7.3,
        "strengths": [],
        "weaknesses": [],
        "recommendations": [],
        "summary": "Summary",
        "interview_outcome": "Outcome",
    }
    result = FinalReportResult(**payload)
    assert result.technical_score == 8
    assert result.communication_score == 8
    assert result.problem_solving_score == 7
    assert result.overall_score == 7
