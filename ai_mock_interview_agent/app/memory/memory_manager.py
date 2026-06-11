from __future__ import annotations

import hashlib
from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.interview import Answer, InterviewReport, InterviewSession, Question
from app.utils.enums import DifficultyLevel


class MemoryManager:
    """Handles interview persistence and context reconstruction."""

    def __init__(self, db: Session):
        self.db = db

    def create_session(
        self,
        candidate_name: str,
        role: str,
        experience: str,
        skills: list[str],
        difficulty: str = DifficultyLevel.MEDIUM.value,
    ) -> InterviewSession:
        session = InterviewSession(
            candidate_name=candidate_name,
            role=role,
            experience=experience,
            difficulty=difficulty,
            skills_json=skills,
            candidate_profile_json={
                "candidate_name": candidate_name,
                "role": role,
                "experience": experience,
                "skills": skills,
            },
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(self, session_id: str) -> InterviewSession:
        session = self.db.get(InterviewSession, session_id)
        if session is None:
            raise ValueError(f"Interview session not found: {session_id}")
        return session

    def get_latest_question(self, session_id: str) -> Question:
        statement = (
            select(Question)
            .where(Question.session_id == session_id)
            .order_by(Question.created_at.desc(), Question.id.desc())
            .limit(1)
        )
        question = self.db.scalars(statement).first()
        if question is None:
            raise ValueError(f"No question found for session: {session_id}")
        return question

    def get_recent_questions(self, session_id: str, limit: int = 5) -> list[Question]:
        statement = (
            select(Question)
            .where(Question.session_id == session_id)
            .order_by(Question.created_at.desc(), Question.id.desc())
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def get_recent_answers(self, session_id: str, limit: int = 5) -> list[Answer]:
        statement = (
            select(Answer)
            .where(Answer.session_id == session_id)
            .order_by(Answer.created_at.desc(), Answer.id.desc())
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def get_recent_context(self, session_id: str, limit: int = 5) -> dict[str, Any]:
        session = self.get_session(session_id)
        questions = self.get_recent_questions(session_id, limit=limit)
        answers = self.get_recent_answers(session_id, limit=limit)

        return {
            "session_id": session.id,
            "candidate_name": session.candidate_name,
            "role": session.role,
            "experience": session.experience,
            "skills": session.skills_json or [],
            "difficulty": session.difficulty,
            "questions_asked": session.questions_asked,
            "recent_questions": [
                {
                    "id": question.id,
                    "question": question.question,
                    "category": question.category,
                    "difficulty": question.difficulty,
                    "is_follow_up": question.is_follow_up,
                }
                for question in questions
            ],
            "recent_answers": [
                {
                    "id": answer.id,
                    "question_id": answer.question_id,
                    "answer": answer.answer,
                    "evaluation": answer.evaluation_json,
                }
                for answer in answers
            ],
        }

    def question_exists(self, session_id: str, question_text: str) -> bool:
        normalized = question_text.strip().lower()
        statement = select(Question.question).where(Question.session_id == session_id)
        for value in self.db.scalars(statement):
            if value.strip().lower() == normalized:
                return True
        return False

    def store_question(
        self,
        session_id: str,
        question: str,
        category: str,
        difficulty: str,
        is_follow_up: bool = False,
    ) -> Question:
        question_row = Question(
            session_id=session_id,
            question=question,
            category=category,
            difficulty=difficulty,
            is_follow_up=is_follow_up,
        )
        self.db.add(question_row)
        session = self.get_session(session_id)
        session.questions_asked += 1
        session.difficulty = difficulty

        question_hash = self._hash_question(question)
        current_hashes = list(session.asked_questions_hash or [])
        if question_hash not in current_hashes:
            current_hashes.append(question_hash)
            session.asked_questions_hash = current_hashes

        self.db.commit()
        self.db.refresh(question_row)
        self.db.refresh(session)
        return question_row

    def store_answer(self, session_id: str, question_id: int, answer: str, evaluation_json: dict[str, Any]) -> Answer:
        answer_row = Answer(
            session_id=session_id,
            question_id=question_id,
            answer=answer,
            evaluation_json=evaluation_json,
        )
        self.db.add(answer_row)
        self.db.commit()
        self.db.refresh(answer_row)
        return answer_row

    def store_report(self, session_id: str, report_json: dict[str, Any]) -> InterviewReport:
        existing = self.get_report(session_id)
        if existing is None:
            report_row = InterviewReport(session_id=session_id, report_json=report_json)
            self.db.add(report_row)
        else:
            existing.report_json = report_json
            report_row = existing
        session = self.get_session(session_id)
        session.status = "completed"
        self.db.commit()
        self.db.refresh(report_row)
        self.db.refresh(session)
        return report_row

    def get_report(self, session_id: str) -> InterviewReport | None:
        statement = select(InterviewReport).where(InterviewReport.session_id == session_id)
        return self.db.scalars(statement).first()

    def get_evaluation_summary(self, session_id: str) -> dict[str, Any]:
        answers = self.get_recent_answers(session_id, limit=1000)
        scores = [answer.evaluation_json for answer in answers if answer.evaluation_json]
        strengths: list[str] = []
        weaknesses: list[str] = []
        for evaluation in scores:
            strengths.extend(evaluation.get("strengths", []))
            weaknesses.extend(evaluation.get("weaknesses", []))
        return {"evaluations": scores, "strengths": list(dict.fromkeys(strengths)), "weaknesses": list(dict.fromkeys(weaknesses))}

    def get_previous_question_texts(self, session_id: str, limit: int = 10) -> list[str]:
        return [question.question for question in self.get_recent_questions(session_id, limit=limit)]

    # GLAMIS Enhancement Methods
    
    def create_glamis_session(
        self,
        candidate_name: str,
        role: str,
        experience: str,
        skills: list[str],
        interview_type: str = "subject",
        subject: str | None = None,
        company: str | None = None,
        job_title: str | None = None,
        jd_details: str | None = None,
        svar_type: str | None = None,
        difficulty: str = DifficultyLevel.MEDIUM.value,
    ) -> InterviewSession:
        """
        Create a GLAMIS-specific interview session.
        
        Args:
            candidate_name: Candidate's name
            role: Role being interviewed for
            experience: Candidate's experience level
            skills: List of skills
            interview_type: Type of interview (subject, verbal, written, company, svar)
            subject: Subject (for subject-based interviews)
            company: Company (for company interviews)
            job_title: Job title (for company interviews)
            jd_details: JD details (for company interviews)
            svar_type: SVAR type (for SVAR interviews)
            difficulty: Initial difficulty level
        
        Returns:
            Created InterviewSession
        """
        session = InterviewSession(
            candidate_name=candidate_name,
            role=role,
            experience=experience,
            difficulty=difficulty,
            skills_json=skills,
            interview_type=interview_type,
            subject=subject,
            company=company,
            job_title=job_title,
            jd_details=jd_details,
            svar_type=svar_type,
            candidate_profile_json={
                "candidate_name": candidate_name,
                "role": role,
                "experience": experience,
                "skills": skills,
                "interview_type": interview_type,
            },
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def _hash_question(self, question: str) -> str:
        """
        Generate a hash for a question to detect duplicates.
        
        Args:
            question: Question text
        
        Returns:
            SHA256 hash of normalized question
        """
        normalized = question.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()

    def has_asked_question(self, session_id: str, question: str) -> bool:
        """
        Check if a question has been asked before in this session.
        
        Args:
            session_id: Interview session ID
            question: Question text to check
        
        Returns:
            True if question has been asked, False otherwise
        """
        session = self.get_session(session_id)
        question_hash = self._hash_question(question)
        return question_hash in (session.asked_questions_hash or [])

    def mark_question_asked(self, session_id: str, question: str) -> None:
        """
        Mark a question as asked in this session.
        
        Args:
            session_id: Interview session ID
            question: Question text
        """
        session = self.get_session(session_id)
        question_hash = self._hash_question(question)
        
        if question_hash not in (session.asked_questions_hash or []):
            if session.asked_questions_hash is None:
                session.asked_questions_hash = []
            session.asked_questions_hash.append(question_hash)
            self.db.commit()
            self.db.refresh(session)

    def update_weak_areas(self, session_id: str, area: str, frequency: int = 1) -> None:
        """
        Update weak areas for a session.
        
        Args:
            session_id: Interview session ID
            area: Weak area/topic
            frequency: How many times this area appeared as weak
        """
        session = self.get_session(session_id)
        weak_areas = dict(session.weak_areas_json or {})
        
        if area in weak_areas:
            weak_areas[area] += frequency
        else:
            weak_areas[area] = frequency
        
        session.weak_areas_json = weak_areas
        self.db.commit()
        self.db.refresh(session)

    def update_strong_areas(self, session_id: str, area: str, frequency: int = 1) -> None:
        """
        Update strong areas for a session.
        
        Args:
            session_id: Interview session ID
            area: Strong area/topic
            frequency: How many times this area appeared as strong
        """
        session = self.get_session(session_id)
        strong_areas = dict(session.strong_areas_json or {})
        
        if area in strong_areas:
            strong_areas[area] += frequency
        else:
            strong_areas[area] = frequency
        
        session.strong_areas_json = strong_areas
        self.db.commit()
        self.db.refresh(session)

    def get_weak_areas(self, session_id: str, top_n: int = 5) -> dict[str, int]:
        """
        Get top weak areas for a session.
        
        Args:
            session_id: Interview session ID
            top_n: Number of top weak areas to return
        
        Returns:
            Dictionary of weak areas and their frequencies
        """
        session = self.get_session(session_id)
        weak_areas = session.weak_areas_json or {}
        
        # Sort by frequency and return top N
        sorted_areas = sorted(weak_areas.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_areas[:top_n])

    def get_strong_areas(self, session_id: str, top_n: int = 5) -> dict[str, int]:
        """
        Get top strong areas for a session.
        
        Args:
            session_id: Interview session ID
            top_n: Number of top strong areas to return
        
        Returns:
            Dictionary of strong areas and their frequencies
        """
        session = self.get_session(session_id)
        strong_areas = session.strong_areas_json or {}
        
        # Sort by frequency and return top N
        sorted_areas = sorted(strong_areas.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_areas[:top_n])
