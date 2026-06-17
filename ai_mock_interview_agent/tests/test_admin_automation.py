from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.services.admin_api_client import AdminAPIClient
from app.agents.admin_task_agent import AdminTaskAgent
from app.schemas.admin_task import (
    AdminTaskPlan,
    AdminTaskAction,
    CompanyDetails,
    SubjectDetails,
    StudentQuestion,
)
from app.main import app


@pytest.fixture
def mock_client_auth():
    """Mock the HTTP client responses of AdminAPIClient for authentication."""
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=201,
            json=lambda: {
                "success": True,
                "statusCode": 200,
                "data": {
                    "accessToken": "mock_access_token",
                    "isAdmin": True
                },
                "message": "LoggedIn Successfully"
            }
        )
        yield mock_post


def test_admin_api_client_login(mock_client_auth) -> None:
    client = AdminAPIClient()
    client._ensure_authenticated()
    assert client.access_token == "mock_access_token"
    assert "Authorization" in client.client.headers
    assert client.client.headers["Authorization"] == "Bearer mock_access_token"


@patch("httpx.Client.post")
def test_admin_api_client_create_interview(mock_post) -> None:
    def side_effect(url, *args, **kwargs):
        if "login" in str(url):
            return MagicMock(
                status_code=201,
                json=lambda: {
                    "success": True,
                    "statusCode": 200,
                    "data": {
                        "accessToken": "mock_access_token",
                        "isAdmin": True
                    },
                    "message": "LoggedIn Successfully"
                }
            )
        else:
            return MagicMock(
                status_code=200,
                json=lambda: {
                    "message": "Company Interview Created Successfully",
                    "link": "https://glamis.in/myInterview/"
                }
            )
    mock_post.side_effect = side_effect

    client = AdminAPIClient()
    payload = {"name": "Test Company Interview"}
    result = client.create_interview("company", payload)

    assert result["message"] == "Company Interview Created Successfully"
    assert result["link"] == "https://glamis.in/myInterview/"


@patch("app.services.admin_api_client.AdminAPIClient.fetch_interview_details")
@patch("app.services.admin_api_client.AdminAPIClient.download_attendance")
@patch("app.services.admin_api_client.AdminAPIClient.create_interview")
def test_admin_task_agent_execution(
    mock_create, mock_download, mock_fetch, mock_client_auth
) -> None:
    # Setup mocks
    mock_create.return_value = {"message": "Success", "link": "link"}
    mock_download.return_value = "Email,Name\nstudent1@gla.ac.in,Student 1"
    mock_fetch.return_value = [
        {"name": "Java Subject Interview", "_id": "645abc1234567890abcdef12"}
    ]

    # Mock OpenAIService structured output
    mock_openai = MagicMock()
    mock_plan = AdminTaskPlan(
        actions=[
            AdminTaskAction(
                action_type="schedule_interview",
                interview_type="subject",
                subject_details=SubjectDetails(
                    name="Java Subject Interview",
                    subject="Java",
                    from_time="10:00",
                    to_time="12:00",
                    date="2026-06-25",
                    no_of_questions=5,
                    easy=2,
                    medium=2,
                    hard=1,
                    students=["student1@gla.ac.in"],
                    questions=[StudentQuestion(question="What is a class?", difficulty="Easy")]
                )
            ),
            AdminTaskAction(
                action_type="download_attendance",
                interview_name_or_id="Java Subject Interview"
            ),
            # Test unsupported action type
            AdminTaskAction(
                action_type="unsupported",
                message="Cancel is unsupported"
            )
        ]
    )
    mock_openai.generate_structured.return_value = mock_plan

    # Create agent and run
    memory = MagicMock()
    agent = AdminTaskAgent(mock_openai, memory)
    response = agent.execute_task("Schedule Java test and download report")

    assert not response.success  # False because we have an unsupported action in the list
    assert len(response.actions_executed) == 2
    
    # Assert scheduling action details
    sched_action = response.actions_executed[0]
    assert sched_action["action"] == "schedule_interview"
    assert sched_action["interview_type"] == "subject"
    
    # Assert download action details
    dl_action = response.actions_executed[1]
    assert dl_action["action"] == "download_attendance"
    assert dl_action["resolved_ids"] == ["645abc1234567890abcdef12"]
    assert "student1@gla.ac.in" in dl_action["csv_snippet"]


def test_api_admin_task_route(client) -> None:
    # Since OPENAI_API_KEY is empty by default in conftest, this will hit the fallback check
    response = client.post("/api/v1/agent/admin-task", json={"task": "Do everything"})
    assert response.status_code == 200
    data = response.json()
    assert not data["success"]
    assert "No LLM service configured" in data["message"]
