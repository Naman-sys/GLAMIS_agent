from __future__ import annotations

import logging
from statistics import mean

from app.agents.base import BaseInterviewAgent
from app.config.settings import get_settings
from app.schemas.interview import FinalReportResult
from app.utils.json_utils import safe_json_dumps

logger = logging.getLogger(__name__)
settings = get_settings()


class ReportGeneratorAgent(BaseInterviewAgent):
    """Builds the final interview report from stored session data."""

    def generate(self, session_id: str) -> FinalReportResult:
        context = self.memory.get_recent_context(session_id, limit=20)
        summary = self.memory.get_evaluation_summary(session_id)
        evaluations = summary["evaluations"]
        session = self.memory.get_session(session_id)

        prompt_payload = {
            "candidate_name": session.candidate_name,
            "role": session.role,
            "experience": session.experience,
            "skills": ", ".join(session.skills_json or []),
            "session_summary": safe_json_dumps(summary | {"context": context}),
            "evaluations": safe_json_dumps(evaluations),
        }

        if self.has_llm:
            try:
                result = self.openai_service.generate_structured(
                    "report_generator.txt",
                    prompt_payload,
                    FinalReportResult,
                )
                return result
            except Exception:
                logger.warning("LLM report generation failed, falling back to heuristic report", exc_info=True)

        return self._fallback_report(session_id)

    def _fallback_report(self, session_id: str) -> FinalReportResult:
        session = self.memory.get_session(session_id)
        evaluations = self.memory.get_evaluation_summary(session_id)["evaluations"]
        if evaluations:
            technical_score = int(round(mean(item.get("technical_score", 0) for item in evaluations)))
            communication_score = int(round(mean(item.get("communication_score", 0) for item in evaluations)))
            problem_solving_score = int(round(mean(item.get("problem_solving_score", 0) for item in evaluations)))
            overall_score = int(round(mean(item.get("overall_score", 0) for item in evaluations)))
            strengths = self.memory.get_evaluation_summary(session_id)["strengths"]
            weaknesses = self.memory.get_evaluation_summary(session_id)["weaknesses"]
        else:
            technical_score = communication_score = problem_solving_score = overall_score = 0
            strengths = []
            weaknesses = ["No interview answers were evaluated."]

        recommendations = []
        if technical_score < settings.interview_success_threshold:
            recommendations.append("Reinforce core technical concepts and practice explaining implementation details.")
        if communication_score < settings.interview_success_threshold:
            recommendations.append("Practice answering in a more structured and concise way.")
        if problem_solving_score < settings.interview_success_threshold:
            recommendations.append("Use step-by-step reasoning and explain trade-offs more clearly.")
        if not recommendations:
            recommendations.append("Continue practicing with more advanced scenario-based questions.")

        outcome = "Strong hire signal" if overall_score >= settings.hard_score_threshold else "Needs more preparation" if overall_score < settings.interview_success_threshold else "Potential hire with follow-up"
        summary_text = (
            f"The candidate completed a mock interview for the {session.role} role. "
            f"Performance was {'strong' if overall_score >= settings.interview_success_threshold else 'mixed'} across the evaluated dimensions."
        )

        return FinalReportResult(
            candidate_name=session.candidate_name,
            role=session.role,
            technical_score=technical_score,
            communication_score=communication_score,
            problem_solving_score=problem_solving_score,
            overall_score=overall_score,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            summary=summary_text,
            interview_outcome=outcome,
        )
