from __future__ import annotations

import datetime
import hashlib
import logging
import uuid
from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.models.interview import Answer, InterviewReport, InterviewSession, Question
from app.utils.enums import DifficultyLevel

logger = logging.getLogger(__name__)


class MongoObject:
    """A wrapper class around MongoDB dictionaries to mimic SQLAlchemy model attribute access."""

    def __init__(self, data: dict[str, Any]):
        self.__dict__.update(data)

    @property
    def id(self) -> Any:
        val = self.__dict__.get("_id")
        if val is not None and not isinstance(val, (int, str)):
            return str(val)
        return val

    def __getattr__(self, name: str) -> Any:
        try:
            return self.__dict__[name]
        except KeyError:
            return None


class MemoryManager:
    """Handles interview persistence and context reconstruction using either SQLite (SQLAlchemy) or MongoDB."""

    def __init__(self, db: Session | None = None):
        self.db = db
        self.settings = get_settings()
        self.use_mongo = bool(self.settings.mongodb_url)

        if self.use_mongo:
            try:
                import pymongo
                mongo_url = self.settings.mongodb_url
                logger.info("Initializing MongoDB memory manager with URL: %s", mongo_url)
                
                # Parse DB name from URI
                parsed = pymongo.uri_parser.parse_uri(mongo_url)
                db_name = parsed.get("database") or "glamis_agent"
                
                self.mongo_client = pymongo.MongoClient(mongo_url)
                self.mongo_db = self.mongo_client[db_name]
                
                self.col_sessions = self.mongo_db["sessions"]
                self.col_questions = self.mongo_db["questions"]
                self.col_answers = self.mongo_db["answers"]
                self.col_reports = self.mongo_db["reports"]
                
                logger.info("MongoDB client connected successfully to database: %s", db_name)
            except Exception as exc:
                logger.exception("Failed to connect to MongoDB. Falling back to SQL mode.")
                self.use_mongo = False

    def create_session(
        self,
        candidate_name: str,
        role: str,
        experience: str,
        skills: list[str],
        difficulty: str = DifficultyLevel.MEDIUM.value,
    ) -> Any:
        if self.use_mongo:
            session_id = str(uuid.uuid4())
            doc = {
                "_id": session_id,
                "candidate_name": candidate_name,
                "role": role,
                "experience": experience,
                "difficulty": difficulty,
                "skills_json": skills,
                "candidate_profile_json": {
                    "candidate_name": candidate_name,
                    "role": role,
                    "experience": experience,
                    "skills": skills,
                },
                "questions_asked": 0,
                "status": "pending",
                "subject": None,
                "company": None,
                "job_title": None,
                "jd_details": None,
                "svar_type": None,
                "weak_areas_json": {},
                "strong_areas_json": {},
                "asked_questions_hash": [],
                "created_at": datetime.datetime.utcnow(),
                "updated_at": datetime.datetime.utcnow(),
            }
            self.col_sessions.insert_one(doc)
            return MongoObject(doc)

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

    def get_session(self, session_id: str) -> Any:
        if self.use_mongo:
            doc = self.col_sessions.find_one({"_id": session_id})
            if doc is None:
                raise ValueError(f"Interview session not found: {session_id}")
            return MongoObject(doc)

        session = self.db.get(InterviewSession, session_id)
        if session is None:
            raise ValueError(f"Interview session not found: {session_id}")
        return session

    def get_latest_question(self, session_id: str) -> Any:
        if self.use_mongo:
            doc = self.col_questions.find_one(
                {"session_id": session_id},
                sort=[("created_at", -1), ("_id", -1)]
            )
            if doc is None:
                raise ValueError(f"No question found for session: {session_id}")
            return MongoObject(doc)

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

    def get_recent_questions(self, session_id: str, limit: int = 5) -> list[Any]:
        if self.use_mongo:
            cursor = self.col_questions.find({"session_id": session_id}).sort([("created_at", -1), ("_id", -1)]).limit(limit)
            return [MongoObject(doc) for doc in cursor]

        statement = (
            select(Question)
            .where(Question.session_id == session_id)
            .order_by(Question.created_at.desc(), Question.id.desc())
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def get_recent_answers(self, session_id: str, limit: int = 5) -> list[Any]:
        if self.use_mongo:
            cursor = self.col_answers.find({"session_id": session_id}).sort([("created_at", -1), ("_id", -1)]).limit(limit)
            return [MongoObject(doc) for doc in cursor]

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
        if self.use_mongo:
            cursor = self.col_questions.find({"session_id": session_id})
            for doc in cursor:
                if doc.get("question", "").strip().lower() == normalized:
                    return True
            return False

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
    ) -> Any:
        if self.use_mongo:
            question_id = int(hashlib.md5(f"{session_id}-{question}".encode()).hexdigest(), 16) % 100000000
            q_doc = {
                "_id": question_id,
                "session_id": session_id,
                "question": question,
                "category": category,
                "difficulty": difficulty,
                "is_follow_up": is_follow_up,
                "created_at": datetime.datetime.utcnow(),
            }
            self.col_questions.insert_one(q_doc)
            
            # Update session details
            session = self.get_session(session_id)
            question_hash = self._hash_question(question)
            current_hashes = list(session.asked_questions_hash or [])
            if question_hash not in current_hashes:
                current_hashes.append(question_hash)
            
            self.col_sessions.update_one(
                {"_id": session_id},
                {
                    "$inc": {"questions_asked": 1},
                    "$set": {
                        "difficulty": difficulty,
                        "asked_questions_hash": current_hashes,
                        "updated_at": datetime.datetime.utcnow(),
                    }
                }
            )
            return MongoObject(q_doc)

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

    def store_answer(self, session_id: str, question_id: int, answer: str, evaluation_json: dict[str, Any]) -> Any:
        if self.use_mongo:
            answer_id = int(hashlib.md5(f"{session_id}-{question_id}".encode()).hexdigest(), 16) % 100000000
            a_doc = {
                "_id": answer_id,
                "session_id": session_id,
                "question_id": question_id,
                "answer": answer,
                "evaluation_json": evaluation_json,
                "created_at": datetime.datetime.utcnow(),
            }
            self.col_answers.insert_one(a_doc)
            return MongoObject(a_doc)

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

    def store_report(self, session_id: str, report_json: dict[str, Any]) -> Any:
        if self.use_mongo:
            existing = self.col_reports.find_one({"session_id": session_id})
            if existing is None:
                r_doc = {
                    "_id": str(uuid.uuid4()),
                    "session_id": session_id,
                    "report_json": report_json,
                    "created_at": datetime.datetime.utcnow(),
                }
                self.col_reports.insert_one(r_doc)
            else:
                self.col_reports.update_one(
                    {"session_id": session_id},
                    {"$set": {"report_json": report_json}}
                )
                r_doc = self.col_reports.find_one({"session_id": session_id})

            self.col_sessions.update_one(
                {"_id": session_id},
                {"$set": {"status": "completed", "updated_at": datetime.datetime.utcnow()}}
            )
            return MongoObject(r_doc)

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

    def get_report(self, session_id: str) -> Any | None:
        if self.use_mongo:
            doc = self.col_reports.find_one({"session_id": session_id})
            return MongoObject(doc) if doc else None

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
    ) -> Any:
        if self.use_mongo:
            session_id = str(uuid.uuid4())
            doc = {
                "_id": session_id,
                "candidate_name": candidate_name,
                "role": role,
                "experience": experience,
                "difficulty": difficulty,
                "skills_json": skills,
                "interview_type": interview_type,
                "subject": subject,
                "company": company,
                "job_title": job_title,
                "jd_details": jd_details,
                "svar_type": svar_type,
                "candidate_profile_json": {
                    "candidate_name": candidate_name,
                    "role": role,
                    "experience": experience,
                    "skills": skills,
                    "interview_type": interview_type,
                },
                "questions_asked": 0,
                "status": "pending",
                "weak_areas_json": {},
                "strong_areas_json": {},
                "asked_questions_hash": [],
                "created_at": datetime.datetime.utcnow(),
                "updated_at": datetime.datetime.utcnow(),
            }
            self.col_sessions.insert_one(doc)
            return MongoObject(doc)

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
        normalized = question.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()

    def has_asked_question(self, session_id: str, question: str) -> bool:
        session = self.get_session(session_id)
        question_hash = self._hash_question(question)
        return question_hash in (session.asked_questions_hash or [])

    def mark_question_asked(self, session_id: str, question: str) -> None:
        if self.use_mongo:
            session = self.get_session(session_id)
            question_hash = self._hash_question(question)
            current_hashes = list(session.asked_questions_hash or [])
            if question_hash not in current_hashes:
                current_hashes.append(question_hash)
                self.col_sessions.update_one(
                    {"_id": session_id},
                    {"$set": {"asked_questions_hash": current_hashes, "updated_at": datetime.datetime.utcnow()}}
                )
            return

        session = self.get_session(session_id)
        question_hash = self._hash_question(question)
        
        if question_hash not in (session.asked_questions_hash or []):
            if session.asked_questions_hash is None:
                session.asked_questions_hash = []
            session.asked_questions_hash.append(question_hash)
            self.db.commit()
            self.db.refresh(session)

    def update_weak_areas(self, session_id: str, area: str, frequency: int = 1) -> None:
        if self.use_mongo:
            session = self.get_session(session_id)
            weak_areas = dict(session.weak_areas_json or {})
            weak_areas[area] = weak_areas.get(area, 0) + frequency
            self.col_sessions.update_one(
                {"_id": session_id},
                {"$set": {"weak_areas_json": weak_areas, "updated_at": datetime.datetime.utcnow()}}
            )
            return

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
        if self.use_mongo:
            session = self.get_session(session_id)
            strong_areas = dict(session.strong_areas_json or {})
            strong_areas[area] = strong_areas.get(area, 0) + frequency
            self.col_sessions.update_one(
                {"_id": session_id},
                {"$set": {"strong_areas_json": strong_areas, "updated_at": datetime.datetime.utcnow()}}
            )
            return

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
        session = self.get_session(session_id)
        weak_areas = session.weak_areas_json or {}
        sorted_areas = sorted(weak_areas.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_areas[:top_n])

    def get_strong_areas(self, session_id: str, top_n: int = 5) -> dict[str, int]:
        session = self.get_session(session_id)
        strong_areas = session.strong_areas_json or {}
        sorted_areas = sorted(strong_areas.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_areas[:top_n])
