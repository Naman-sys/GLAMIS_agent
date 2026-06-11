from __future__ import annotations

import json
import logging
from itertools import cycle
from typing import Any

from app.agents.base import BaseInterviewAgent
from app.agents.interview_type_router import InterviewTypeRouter
from app.config.settings import get_settings
from app.evaluators.scoring import heuristic_evaluate_answer
from app.schemas.interview import QuestionGenerationResult
from app.utils.enums import DifficultyLevel, QuestionCategory
from app.utils.json_utils import safe_json_dumps

logger = logging.getLogger(__name__)
settings = get_settings()


class QuestionGeneratorAgent(BaseInterviewAgent):
    """Generates the next interview question and avoids duplicates."""

    def generate(
        self,
        session_id: str,
        *,
        category_hint: str | None = None,
        interview_type: str = "subject",
        subject: str | None = None,
    ) -> QuestionGenerationResult:
        context = self.memory.get_recent_context(session_id)
        recent_questions = self.memory.get_previous_question_texts(session_id, limit=10)
        
        # Get session for GLAMIS fields
        session = self.memory.get_session(session_id)
        
        # Prepare prompt based on interview type
        if interview_type == "subject":
            subject_type = InterviewTypeRouter.get_subject_type(subject or "")
            prompt_name = f"subject_{subject_type.value}"
            subdirectory = "subjects"
        else:
            prompt_name = interview_type
            subdirectory = ""
        
        prompt_payload = {
            "candidate_name": context["candidate_name"],
            "role": context["role"],
            "experience": context["experience"],
            "skills": ", ".join(context["skills"]),
            "difficulty": context["difficulty"],
            "category_hint": category_hint or self._suggest_category(context),
            "recent_questions": safe_json_dumps(recent_questions),
            "session_context": safe_json_dumps(context),
            # GLAMIS-specific fields
            "subject": subject or getattr(session, "subject", None) or "",
            "company": getattr(session, "company", None) or "",
            "job_title": getattr(session, "job_title", None) or "",
            "jd_details": getattr(session, "jd_details", None) or "",
            "svar_type": getattr(session, "svar_type", None) or "",
        }

        if self.has_llm:
            try:
                result = self.groq_service.generate_structured(
                    prompt_name if prompt_name != "subject_none" else "question_generator.txt",
                    prompt_payload,
                    QuestionGenerationResult,
                    subdirectory=subdirectory,
                )
                # Check for duplicates using new hashing mechanism
                if not self.memory.has_asked_question(session_id, result.question):
                    self.memory.mark_question_asked(session_id, result.question)
                    return result
                # If duplicate, try fallback
                logger.info(f"Question already asked, generating fallback for session {session_id}")
            except Exception:
                logger.warning("LLM question generation failed, falling back to heuristic question", exc_info=True)

        return self._fallback_question(context, recent_questions)

    def _suggest_category(self, context: dict[str, Any]) -> str:
        difficulty = context.get("difficulty", DifficultyLevel.MEDIUM.value)
        questions_asked = int(context.get("questions_asked", 0))
        pattern = [
            QuestionCategory.TECHNICAL.value,
            QuestionCategory.BEHAVIORAL.value,
            QuestionCategory.PROBLEM_SOLVING.value,
            QuestionCategory.HR.value,
        ]
        if difficulty == DifficultyLevel.HARD.value:
            return QuestionCategory.PROBLEM_SOLVING.value
        if difficulty == DifficultyLevel.EASY.value:
            return QuestionCategory.BEHAVIORAL.value if questions_asked % 2 else QuestionCategory.TECHNICAL.value
        return pattern[questions_asked % len(pattern)]

    def _fallback_question(self, context: dict[str, Any], recent_questions: list[str]) -> QuestionGenerationResult:
        role = context["role"]
        skills = context.get("skills", [])
        difficulty = context.get("difficulty", DifficultyLevel.MEDIUM.value)
        category = self._suggest_category(context)

        if category == QuestionCategory.TECHNICAL.value:
            focus = skills[0] if skills else role
            question = f"Explain how you would solve a real-world {focus} problem in this role, and what trade-offs you would consider."
        elif category == QuestionCategory.BEHAVIORAL.value:
            question = f"Tell me about a time you had to learn something quickly for a project related to {role}. How did you approach it?"
        elif category == QuestionCategory.HR.value:
            question = f"Why are you interested in the {role} role, and what kind of team environment helps you do your best work?"
        else:
            question = f"Walk me through how you would approach a difficult {role} problem from first principles."

        if question in recent_questions:
            question = f"What is one concrete example of how you would apply your {', '.join(skills[:2]) or role} knowledge in this role?"

        return QuestionGenerationResult(
            question=question,
            category=QuestionCategory(category),
            difficulty=DifficultyLevel(difficulty),
            rationale="Fallback question generated from the candidate profile and recent interview context.",
        )
