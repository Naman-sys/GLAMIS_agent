from __future__ import annotations

from app.agents.interview_type_router import InterviewTypeRouter
from app.evaluators.scoring import heuristic_evaluate_answer, heuristic_difficulty_adjustment
from app.utils.enums import SubjectType


def test_heuristic_evaluation_produces_structured_scores() -> None:
    result = heuristic_evaluate_answer(
        question="Explain HashMap.",
        answer="HashMap stores key-value pairs and resolves collisions using buckets.",
        role="Software Engineer",
        skills=["Java", "DSA"],
        experience="Fresher",
    )
    assert 0 <= result.overall_score <= 10
    assert result.feedback
    assert isinstance(result.strengths, list)


def test_interview_type_router_subject_name_mapping() -> None:
    assert InterviewTypeRouter.get_subject_type("Data Structures and Algorithms") == SubjectType.DSA
    assert InterviewTypeRouter.get_subject_type("Operating Systems") == SubjectType.OS
    assert InterviewTypeRouter.get_subject_type("Computer Networks") == SubjectType.CN
    assert InterviewTypeRouter.get_subject_type("Machine Learning") == SubjectType.ML
    assert InterviewTypeRouter.get_subject_type("Cyber Security") == SubjectType.CYBERSECURITY


def test_heuristic_difficulty_adjustment_moves_expected_direction() -> None:
    harder = heuristic_difficulty_adjustment("Medium", 9)
    easier = heuristic_difficulty_adjustment("Medium", 2)
    assert harder.difficulty.value in {"Medium", "Hard"}
    assert easier.difficulty.value == "Easy"


def test_heuristic_difficulty_adjustment_accepts_0_100_scale() -> None:
    assert heuristic_difficulty_adjustment("Medium", 20).difficulty.value == "Easy"
    assert heuristic_difficulty_adjustment("Medium", 55).difficulty.value == "Medium"
    assert heuristic_difficulty_adjustment("Medium", 85).difficulty.value == "Hard"
