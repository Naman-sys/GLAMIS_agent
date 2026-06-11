from __future__ import annotations


def test_health_endpoint(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_interview_flow_and_report(client) -> None:
    start_payload = {
        "candidate_name": "Naman",
        "role": "Software Engineer",
        "experience": "Fresher",
        "skills": ["Java", "SQL", "DSA"],
    }
    start_response = client.post("/api/v1/start-interview", json=start_payload)
    assert start_response.status_code == 200
    start_data = start_response.json()
    assert start_data["session_id"]
    assert start_data["first_question"]

    session_id = start_data["session_id"]
    answer_payload = {
        "session_id": session_id,
        "answer": "HashMap stores key-value pairs and uses hashing to provide fast average lookups."
    }
    answer_response = client.post("/api/v1/submit-answer", json=answer_payload)
    assert answer_response.status_code == 200
    answer_data = answer_response.json()
    assert "evaluation" in answer_data
    assert answer_data["evaluation"]["overall_score"] >= 0
    assert answer_data["difficulty"] in {"Easy", "Medium", "Hard"}

    report_response = client.get(f"/api/v1/interview-report/{session_id}")
    assert report_response.status_code == 200
    report_data = report_response.json()
    assert report_data["session_id"] == session_id
    assert report_data["report"]["candidate_name"] == "Naman"
    assert "overall_score" in report_data["report"]
