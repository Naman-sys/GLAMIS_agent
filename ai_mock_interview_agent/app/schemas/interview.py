from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.enums import DifficultyLevel, QuestionCategory


class StartInterviewRequest(BaseModel):
    candidate_name: str = Field(min_length=1, max_length=255)
    role: str = Field(min_length=1, max_length=255)
    experience: str = Field(min_length=1, max_length=120)
    skills: list[str] = Field(default_factory=list)

    @field_validator("skills")
    @classmethod
    def normalize_skills(cls, value: list[str]) -> list[str]:
        return [skill.strip() for skill in value if skill and skill.strip()]


class StartInterviewResponse(BaseModel):
    session_id: str
    first_question: str
    audio_url: str | None = None


class SubmitAnswerRequest(BaseModel):
    session_id: str = Field(min_length=1)
    answer: str = Field(min_length=1)


class SubmitAnswerResponse(BaseModel):
    evaluation: dict[str, Any]
    next_question: str
    difficulty: str
    interview_complete: bool = False
    audio_url: str | None = None


class InterviewReportResponse(BaseModel):
    session_id: str
    report: dict[str, Any]


class HealthResponse(BaseModel):
    status: Literal["healthy"] = "healthy"


class QuestionGenerationResult(BaseModel):
    question: str = Field(min_length=1)
    category: QuestionCategory
    difficulty: DifficultyLevel
    rationale: str = Field(default="")

    @field_validator("difficulty", mode="before")
    @classmethod
    def normalize_difficulty(cls, v: Any) -> str:
        if isinstance(v, str):
            val = v.strip().capitalize()
            if val in ("Easy", "Medium", "Hard"):
                return val
        return v

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: Any) -> str:
        if isinstance(v, str):
            val = v.strip()
            if val.upper() == "HR":
                return "HR"
            if val.upper() == "SVAR":
                return "SVAR"
            if val.lower() in ("problem solving", "problem-solving"):
                return "Problem Solving"
            return val.title()
        return v


class AnswerEvaluationResult(BaseModel):
    technical_score: int = Field(ge=0, le=10)
    communication_score: int = Field(ge=0, le=10)
    relevance_score: int = Field(ge=0, le=10)
    problem_solving_score: int = Field(ge=0, le=10)
    completeness_score: int = Field(ge=0, le=10)
    grammar_score: int = Field(ge=0, le=10, default=0)
    vocabulary_score: int = Field(ge=0, le=10, default=0)
    content_structure_score: int = Field(ge=0, le=10, default=0)
    pronunciation_score: int = Field(ge=0, le=10, default=0)
    correctness_score: int = Field(ge=0, le=10, default=0)
    accuracy_score: int = Field(ge=0, le=10, default=0)
    overall_score: int = Field(ge=0, le=10)
    feedback: str = Field(min_length=1)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    follow_up_needed: bool = False

    @field_validator(
        "technical_score",
        "communication_score",
        "relevance_score",
        "problem_solving_score",
        "completeness_score",
        "grammar_score",
        "vocabulary_score",
        "content_structure_score",
        "pronunciation_score",
        "correctness_score",
        "accuracy_score",
        "overall_score",
        mode="before"
    )
    @classmethod
    def coerce_to_int(cls, v: Any) -> int:
        if isinstance(v, (int, float)):
            return int(round(v))
        if isinstance(v, str):
            try:
                return int(round(float(v)))
            except ValueError:
                pass
        return v


class FollowUpGenerationResult(BaseModel):
    question: str = Field(min_length=1)
    category: QuestionCategory
    difficulty: DifficultyLevel
    rationale: str = Field(default="")

    @field_validator("difficulty", mode="before")
    @classmethod
    def normalize_difficulty(cls, v: Any) -> str:
        if isinstance(v, str):
            val = v.strip().capitalize()
            if val in ("Easy", "Medium", "Hard"):
                return val
        return v

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: Any) -> str:
        if isinstance(v, str):
            val = v.strip()
            if val.upper() == "HR":
                return "HR"
            if val.upper() == "SVAR":
                return "SVAR"
            if val.lower() in ("problem solving", "problem-solving"):
                return "Problem Solving"
            return val.title()
        return v


class DifficultyAdjustmentResult(BaseModel):
    difficulty: DifficultyLevel
    action: Literal["increase", "maintain", "decrease"]
    reason: str = Field(min_length=1)

    @field_validator("difficulty", mode="before")
    @classmethod
    def normalize_difficulty(cls, v: Any) -> str:
        if isinstance(v, str):
            val = v.strip().capitalize()
            if val in ("Easy", "Medium", "Hard"):
                return val
        return v

    @field_validator("action", mode="before")
    @classmethod
    def normalize_action(cls, v: Any) -> str:
        if isinstance(v, str):
            val = v.strip().lower()
            if val in ("increase", "maintain", "decrease"):
                return val
        return v


class FinalReportResult(BaseModel):
    candidate_name: str
    role: str
    technical_score: int = Field(ge=0, le=10)
    communication_score: int = Field(ge=0, le=10)
    problem_solving_score: int = Field(ge=0, le=10)
    overall_score: int = Field(ge=0, le=10)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    summary: str = Field(default="")
    interview_outcome: str = Field(default="")
    model_config = ConfigDict(use_enum_values=True)

    @field_validator(
        "technical_score",
        "communication_score",
        "problem_solving_score",
        "overall_score",
        mode="before"
    )
    @classmethod
    def coerce_to_int(cls, v: Any) -> int:
        if isinstance(v, (int, float)):
            return int(round(v))
        if isinstance(v, str):
            try:
                return int(round(float(v)))
            except ValueError:
                pass
        return v


class SubmitVoiceAnswerResponse(BaseModel):
    transcript: str
    evaluation: dict[str, Any]
    next_question: str
    difficulty: str
    interview_complete: bool = False
    audio_url: str | None = None


class SpeechGenerationRequest(BaseModel):
    text: str = Field(min_length=1)


class SpeechGenerationResponse(BaseModel):
    audio_url: str

