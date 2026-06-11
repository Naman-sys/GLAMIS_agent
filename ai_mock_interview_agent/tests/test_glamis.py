from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.interview import InterviewSession


def get_session(session_id: str) -> InterviewSession | None:
    with SessionLocal() as db:
        return db.get(InterviewSession, session_id)


def test_glamis_subject_interview_end_to_end(client) -> None:
    start_payload = {
        "interview_type": "subject",
        "subject": "DSA",
        "metadata": {
            "candidate_name": "Alice",
            "role": "Software Engineer",
            "experience": "Fresher",
            "skills": ["Python", "DSA"],
        },
    }

    start_response = client.post("/api/v1/glamis/start-interview", json=start_payload)
    assert start_response.status_code == 200
    start_data = start_response.json()
    assert start_data["status"] == "success"
    assert start_data["interviewId"]
    assert start_data["question"]
    assert start_data["audioFileName"].startswith("/static/audio/")

    session_id = start_data["interviewId"]

    submit_payload = {
        "interview_type": "subject",
        "subject": "DSA",
        "interviewId": session_id,
        "answer": "I would choose an efficient data structure like a hash map for fast lookup and consider amortized complexity.",
    }
    submit_response = client.post("/api/v1/glamis/submit-answer", json=submit_payload)
    assert submit_response.status_code == 200
    submit_data = submit_response.json()

    assert submit_data["status"] == "success"
    assert submit_data["interviewId"] == session_id
    assert submit_data["question"]
    assert submit_data["evaluation"]["overallScore"] >= 0
    assert submit_data["difficulty"] in {"Easy", "Medium", "Hard"}
    assert submit_data["audioFileName"] is not None

    session = get_session(session_id)
    assert session is not None
    assert session.interview_type == "subject"
    assert session.questions_asked >= 1
    assert isinstance(session.asked_questions_hash, list)
    assert session.asked_questions_hash


def test_glamis_company_interview_end_to_end(client) -> None:
    start_payload = {
        "interview_type": "company",
        "selectedCompany": "Acme Corp",
        "jobTitle": "Backend Engineer",
        "jdDetails": "Design scalable APIs and ensure strong data consistency.",
        "metadata": {
            "candidate_name": "Eve",
            "role": "Backend Engineer",
            "experience": "Senior",
            "skills": ["APIs", "Databases"],
        },
    }

    start_response = client.post("/api/v1/glamis/start-interview", json=start_payload)
    assert start_response.status_code == 200
    start_data = start_response.json()
    assert start_data["status"] == "success"
    assert start_data["question"]

    session_id = start_data["interviewId"]
    submit_payload = {
        "interview_type": "company",
        "interviewId": session_id,
        "answer": "I have designed and scaled backend APIs for multiple teams, focusing on reliability and observability.",
    }
    submit_response = client.post("/api/v1/glamis/submit-answer", json=submit_payload)
    assert submit_response.status_code == 200
    submit_data = submit_response.json()

    assert submit_data["interviewId"] == session_id
    assert submit_data["evaluation"]["overallScore"] >= 0
    assert submit_data["difficulty"] in {"Easy", "Medium", "Hard"}

    session = get_session(session_id)
    assert session is not None
    assert session.interview_type == "company"
    assert session.company == "Acme Corp"
    assert session.job_title == "Backend Engineer"


def test_glamis_written_interview_end_to_end(client) -> None:
    start_payload = {
        "interview_type": "written",
        "subject": "ML",
        "metadata": {
            "candidate_name": "James",
            "role": "Data Scientist",
            "experience": "Junior",
            "skills": ["ML", "Python"],
        },
    }

    start_response = client.post("/api/v1/glamis/start-interview", json=start_payload)
    assert start_response.status_code == 200
    start_data = start_response.json()
    assert start_data["status"] == "success"
    assert start_data["question"]

    session_id = start_data["interviewId"]
    submit_payload = {
        "interview_type": "written",
        "subject": "ML",
        "interviewId": session_id,
        "answer": "Machine learning models benefit from clean data preparation and feature engineering.",
    }
    submit_response = client.post("/api/v1/glamis/submit-answer", json=submit_payload)
    assert submit_response.status_code == 200
    submit_data = submit_response.json()

    assert submit_data["status"] == "success"
    assert submit_data["question"]
    assert submit_data["difficulty"] in {"Easy", "Medium", "Hard"}

    session = get_session(session_id)
    assert session is not None
    assert session.interview_type == "written"
    assert session.subject == "ML"


def test_glamis_verbal_interview_end_to_end(client) -> None:
    start_payload = {
        "interview_type": "verbal",
        "subject": "General",
        "metadata": {
            "candidate_name": "Natalie",
            "role": "Product Manager",
            "experience": "Mid",
            "skills": ["Communication", "Leadership"],
        },
    }

    start_response = client.post("/api/v1/glamis/start-interview", json=start_payload)
    assert start_response.status_code == 200
    start_data = start_response.json()
    assert start_data["status"] == "success"
    assert start_data["question"]

    session_id = start_data["interviewId"]
    submit_payload = {
        "interview_type": "verbal",
        "subject": "General",
        "interviewId": session_id,
        "answer": "I explain my ideas clearly and provide examples that make the strategy easy to understand.",
    }
    submit_response = client.post("/api/v1/glamis/submit-answer", json=submit_payload)
    assert submit_response.status_code == 200
    submit_data = submit_response.json()

    assert submit_data["status"] == "success"
    assert submit_data["evaluation"]["overallScore"] >= 0
    assert submit_data["difficulty"] in {"Easy", "Medium", "Hard"}

    session = get_session(session_id)
    assert session is not None
    assert session.interview_type == "verbal"


def test_glamis_svar_interview_end_to_end(client) -> None:
    start_payload = {
        "interview_type": "svar",
        "difficulty": "reading",
        "metadata": {
            "candidate_name": "Maya",
            "role": "Speech Analyst",
            "experience": "Entry",
            "skills": ["Speech", "Audio"],
        },
    }

    start_response = client.post("/api/v1/glamis/start-interview", json=start_payload)
    assert start_response.status_code == 200
    start_data = start_response.json()
    assert start_data["status"] == "success"
    assert start_data["question"]

    session_id = start_data["interviewId"]
    submit_payload = {
        "interview_type": "svar",
        "difficulty": "reading",
        "interviewId": session_id,
        "answer": "I would slowly read each sentence and repeat it accurately in the same order.",
    }
    submit_response = client.post("/api/v1/glamis/submit-answer", json=submit_payload)
    assert submit_response.status_code == 200
    submit_data = submit_response.json()

    assert submit_data["status"] == "success"
    assert submit_data["evaluation"]["overallScore"] >= 0
    assert submit_data["question"]

    session = get_session(session_id)
    assert session is not None
    assert session.interview_type == "svar"
    assert session.svar_type == "reading"


def test_glamis_followup_and_difficulty_adjustment(client) -> None:
    start_payload = {
        "interview_type": "subject",
        "subject": "CN",
        "metadata": {
            "candidate_name": "Ravi",
            "role": "Network Engineer",
            "experience": "Junior",
            "skills": ["Networks", "TCP/IP"],
        },
    }

    start_response = client.post("/api/v1/glamis/start-interview", json=start_payload)
    assert start_response.status_code == 200
    session_id = start_response.json()["interviewId"]

    submit_payload = {
        "interview_type": "subject",
        "subject": "CN",
        "interviewId": session_id,
        "answer": "No idea.",
    }
    submit_response = client.post("/api/v1/glamis/submit-answer", json=submit_payload)
    assert submit_response.status_code == 200
    submit_data = submit_response.json()

    assert submit_data["difficulty"] == "Easy"
    assert submit_data["evaluation"]["overallScore"] <= 5
    assert submit_data["evaluation"]["followUpNeeded"] is True
    assert submit_data["followUpQuestion"]
    assert submit_data["audioFileName"] is not None

    session = get_session(session_id)
    assert session is not None
    assert session.weak_areas_json or session.strong_areas_json


def test_glamis_subject_exact_name_and_camel_case_response(client) -> None:
    start_payload = {
        "interview_type": "subject",
        "subject": "Operating Systems",
        "metadata": {
            "candidate_name": "Leo",
            "role": "System Engineer",
            "experience": "Junior",
            "skills": ["OS", "Concurrency"],
        },
    }

    start_response = client.post("/api/v1/glamis/start-interview", json=start_payload)
    assert start_response.status_code == 200
    start_data = start_response.json()
    assert start_data["status"] == "success"
    assert start_data["question"]
    assert start_data["audioFileName"] is not None
    assert start_data["interviewId"]


def test_followup_generator_handles_normalization_question() -> None:
    from app.agents.followup_generator import FollowUpQuestionGeneratorAgent
    from app.database.session import SessionLocal
    from app.memory.memory_manager import MemoryManager

    with SessionLocal() as db:
        memory = MemoryManager(db)
        session = memory.create_session(
            candidate_name="Zoe",
            role="Software Engineer",
            experience="Fresher",
            skills=["DBMS"],
        )

        agent = FollowUpQuestionGeneratorAgent(None, memory)
        result = agent.generate(
            session.id,
            question="What is Normalization?",
            answer="Reduces redundancy.",
            evaluation={"technical_score": 3, "overall_score": 3},
            interview_type="subject",
        )

        assert any(term in result.question for term in ["1NF", "2NF", "3NF"])


def test_glamis_submit_answer_returns_camel_case_evaluation_keys(client) -> None:
    start_payload = {
        "interview_type": "subject",
        "subject": "Operating Systems",
        "metadata": {
            "candidate_name": "Maya",
            "role": "System Engineer",
            "experience": "Junior",
            "skills": ["OS", "Memory Management"],
        },
    }

    start_response = client.post("/api/v1/glamis/start-interview", json=start_payload)
    assert start_response.status_code == 200
    session_id = start_response.json()["interviewId"]

    submit_payload = {
        "interview_type": "subject",
        "subject": "Operating Systems",
        "interviewId": session_id,
        "answer": "It manages processes and memory.",
    }
    submit_response = client.post("/api/v1/glamis/submit-answer", json=submit_payload)
    assert submit_response.status_code == 200
    submit_data = submit_response.json()
    assert submit_data["evaluation"]["overallScore"] >= 0
    assert "grammarScore" in submit_data["evaluation"]
    assert "accuracyScore" in submit_data["evaluation"]
    assert "audioFileName" in submit_data


def test_glamis_report_endpoint(client) -> None:
    start_payload = {
        "interview_type": "subject",
        "subject": "OS",
        "metadata": {
            "candidate_name": "Frank",
            "role": "Systems Engineer",
            "experience": "Mid",
            "skills": ["OS", "Memory Management"],
        },
    }

    start_data = client.post("/api/v1/glamis/start-interview", json=start_payload).json()
    session_id = start_data["interviewId"]

    submit_payload = {
        "interview_type": "subject",
        "subject": "OS",
        "interviewId": session_id,
        "answer": "The operating system manages memory, processes, and scheduling to ensure stable execution.",
    }
    client.post("/api/v1/glamis/submit-answer", json=submit_payload)

    report_response = client.get(f"/api/v1/glamis/report/{session_id}")
    assert report_response.status_code == 200
    report_data = report_response.json()

    assert report_data["interviewId"] == session_id
    assert report_data["interviewType"] == "subject"
    assert report_data["candidateName"] == "Frank"
    assert isinstance(report_data["strengths"], list)
    assert isinstance(report_data["weaknesses"], list)
    assert "recommendations" in report_data
