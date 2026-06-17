from __future__ import annotations

import json
import logging

from app.agents.base import BaseInterviewAgent
from app.config.settings import get_settings
from app.evaluators.scoring import heuristic_evaluate_answer
from app.schemas.interview import AnswerEvaluationResult
from app.utils.json_utils import safe_json_dumps

logger = logging.getLogger(__name__)
settings = get_settings()


class AnswerEvaluatorAgent(BaseInterviewAgent):
    """Scores candidate answers using OpenAI, with a deterministic fallback."""

    def evaluate(
        self,
        session_id: str,
        question: str,
        answer: str,
        interview_type: str = "subject",
    ) -> AnswerEvaluationResult:
        context = self.memory.get_recent_context(session_id)
        session = self.memory.get_session(session_id)
        
        # Get type-specific evaluation criteria
        eval_criteria = {}
        if interview_type == "subject":
            eval_criteria = {
                "technical_knowledge": "depth of understanding",
                "accuracy": "correctness of answer",
                "completeness": "coverage of topic",
            }
        elif interview_type == "verbal":
            eval_criteria = {
                "communication": "clarity and fluency",
                "grammar": "grammatical correctness",
                "vocabulary": "word choice and range",
            }
        elif interview_type == "written":
            eval_criteria = {
                "grammar": "writing grammar",
                "structure": "logical organization",
                "clarity": "clarity of expression",
            }
        elif interview_type == "company":
            eval_criteria = {
                "role_fit": "fit for the position",
                "jd_alignment": "alignment with job description",
                "experience_relevance": "relevance to role",
            }
        elif interview_type == "svar":
            eval_criteria = {
                "pronunciation": "correct pronunciation",
                "vocabulary": "vocabulary usage",
                "fluency": "speech fluency",
            }
        
        prompt_payload = {
            "candidate_name": context["candidate_name"],
            "role": context["role"],
            "experience": context["experience"],
            "skills": ", ".join(context["skills"]),
            "difficulty": context["difficulty"],
            "question": question,
            "answer": answer,
            "session_context": safe_json_dumps(context),
            "evaluation_criteria": json.dumps(eval_criteria),
        }

        if self.has_llm:
            try:
                result = self.openai_service.generate_structured(
                    "answer_evaluator.txt",
                    prompt_payload,
                    AnswerEvaluationResult,
                )
                return self._normalize_result(result, interview_type)
            except Exception:
                logger.warning("LLM evaluation failed, falling back to heuristic scoring", exc_info=True)

        heuristic_result = heuristic_evaluate_answer(question, answer, context["role"], context.get("skills", []), context["experience"])
        return self._normalize_result(heuristic_result, interview_type)

    def _normalize_result(self, result: AnswerEvaluationResult, interview_type: str) -> AnswerEvaluationResult:
        scores = [
            result.technical_score,
            result.communication_score,
            result.relevance_score,
            result.problem_solving_score,
            result.completeness_score,
        ]
        if result.overall_score == 0:
            result.overall_score = int(round(sum(scores) / len(scores)))

        if interview_type == "verbal":
            result.grammar_score = result.communication_score
            result.vocabulary_score = min(10, result.communication_score + 1)
        elif interview_type == "written":
            result.grammar_score = result.communication_score
            result.content_structure_score = result.relevance_score
            result.accuracy_score = result.overall_score
        elif interview_type == "company":
            result.accuracy_score = result.relevance_score
        elif interview_type == "svar":
            result.pronunciation_score = result.communication_score
            result.correctness_score = result.overall_score
            result.accuracy_score = result.relevance_score

        result.follow_up_needed = result.follow_up_needed or result.overall_score < settings.interview_success_threshold or result.completeness_score < 6
        return result
