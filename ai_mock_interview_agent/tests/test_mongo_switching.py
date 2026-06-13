from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest
from app.memory.memory_manager import MemoryManager, MongoObject
from app.config.settings import get_settings


def test_mongo_object_wrapper() -> None:
    data = {"_id": "test-uuid-123", "candidate_name": "Dave", "role": "Backend dev"}
    obj = MongoObject(data)
    assert obj.id == "test-uuid-123"
    assert obj.candidate_name == "Dave"
    assert obj.role == "Backend dev"
    assert obj.non_existent is None  # Resilient fallback returns None


def test_memory_manager_sqlite_fallback() -> None:
    # By default, settings.mongodb_url is None
    orig_url = get_settings().mongodb_url
    try:
        get_settings().mongodb_url = None
        db = MagicMock()
        manager = MemoryManager(db)
        assert not manager.use_mongo
        assert manager.db == db
    finally:
        get_settings().mongodb_url = orig_url


@patch("pymongo.MongoClient")
def test_memory_manager_mongo_mode_crud(mock_mongo_client) -> None:
    # Setup mock Mongo Client and DB structure
    mock_db = MagicMock()
    mock_client_inst = MagicMock()
    mock_client_inst.__getitem__.return_value = mock_db
    mock_mongo_client.return_value = mock_client_inst

    # We mock the collections
    mock_sessions = MagicMock()
    mock_questions = MagicMock()
    mock_answers = MagicMock()
    mock_reports = MagicMock()

    def get_collection(name):
        if name == "sessions":
            return mock_sessions
        elif name == "questions":
            return mock_questions
        elif name == "answers":
            return mock_answers
        elif name == "reports":
            return mock_reports
        return MagicMock()

    mock_db.__getitem__.side_effect = get_collection

    orig_url = get_settings().mongodb_url
    try:
        get_settings().mongodb_url = "mongodb://localhost:27017/test_db"
        manager = MemoryManager()
        assert manager.use_mongo
        assert manager.mongo_db == mock_db

        # 1. Test create_session
        session = manager.create_session("John Doe", "Software Engineer", "3 years", ["Python"])
        assert session.candidate_name == "John Doe"
        assert session.role == "Software Engineer"
        mock_sessions.insert_one.assert_called_once()
        inserted_doc = mock_sessions.insert_one.call_args[0][0]
        assert inserted_doc["_id"] == session.id

        # 2. Test get_session
        mock_sessions.find_one.return_value = inserted_doc
        fetched = manager.get_session(session.id)
        assert fetched.id == session.id
        mock_sessions.find_one.assert_called_with({"_id": session.id})

        # 3. Test store_question
        mock_sessions.find_one.return_value = inserted_doc
        question = manager.store_question(session.id, "Explain Python list comprehension", "Technical", "Medium")
        assert question.question == "Explain Python list comprehension"
        mock_questions.insert_one.assert_called_once()
        mock_sessions.update_one.assert_called_once()

        # 4. Test store_answer
        answer = manager.store_answer(session.id, question.id, "It is a concise way to create lists", {"overall_score": 8})
        assert answer.answer == "It is a concise way to create lists"
        mock_answers.insert_one.assert_called_once()

        # 5. Test store_report
        mock_reports.find_one.return_value = None
        report = manager.store_report(session.id, {"overall_score": 8, "outcome": "Hire"})
        mock_reports.insert_one.assert_called_once()
    finally:
        get_settings().mongodb_url = orig_url
