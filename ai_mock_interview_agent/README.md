# AI Mock Interview Agent

A production-oriented AI mock interview backend built with FastAPI, LangGraph, LangChain, SQLAlchemy, SQLite, and the OpenAI API.

## What it does

- Conducts mock interviews end to end.
- Generates interview questions dynamically.
- Evaluates candidate answers with structured scoring.
- Produces intelligent follow-up questions.
- Adjusts difficulty based on performance.
- Stores interview context in SQLite.
- Generates a final interview report.
- Exposes APIs for web, mobile, or desktop clients.

## Tech Stack

- Python 3.12+
- FastAPI
- LangGraph
- LangChain
- OpenAI API
- SQLite
- SQLAlchemy
- Pydantic
- python-dotenv
- Pytest

## Project Structure

```text
ai_mock_interview_agent/
├── app/
│   ├── api/
│   ├── agents/
│   ├── graph/
│   ├── services/
│   │   └── openai_service.py
│   ├── memory/
│   ├── prompts/
│   ├── evaluators/
│   ├── database/
│   ├── models/
│   ├── schemas/
│   ├── utils/
│   └── config/
├── tests/
├── requirements.txt
├── .env.example
├── README.md
└── main.py
```

## Setup

1. Create and activate a Python 3.12+ virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file from `.env.example` and set your OpenAI API key.
4. Start the API:

```bash
uvicorn main:app --reload
```

## Environment Variables

- `OPENAI_API_KEY`: OpenAI API key.
- `OPENAI_MODEL`: OpenAI model name, default is `gpt-4o-mini`.
- `OPENAI_WHISPER_MODEL`: OpenAI speech-to-text model, default is `whisper-1`.
- `OPENAI_TTS_MODEL`: OpenAI TTS model, default is `gpt-4o-mini-tts`.
- `DATABASE_URL`: SQLite connection string.

## API Endpoints

### `POST /api/v1/start-interview`

Request:

```json
{
  "candidate_name": "Naman",
  "role": "Software Engineer",
  "experience": "Fresher",
  "skills": ["Java", "SQL", "DSA"]
}
```

Response:

```json
{
  "session_id": "c0b1f...",
  "first_question": "Explain how you would..."
}
```

### `POST /api/v1/submit-answer`

Request:

```json
{
  "session_id": "c0b1f...",
  "answer": "HashMap stores key-value pairs..."
}
```

Response:

```json
{
  "evaluation": {
    "technical_score": 8,
    "communication_score": 7,
    "relevance_score": 9,
    "problem_solving_score": 8,
    "completeness_score": 8,
    "overall_score": 8,
    "feedback": "Detailed feedback",
    "strengths": ["..."],
    "weaknesses": ["..."]
  },
  "next_question": "Can you explain...",
  "difficulty": "Medium",
  "interview_complete": false
}
```

### `GET /api/v1/interview-report/{session_id}`

Returns the final report for the session.

### `GET /api/v1/health`

Response:

```json
{
  "status": "healthy"
}
```

## Notes

- If `OPENAI_API_KEY` is missing, the system falls back to deterministic heuristics so the backend still works for local testing.
- The interview flow is orchestrated with LangGraph, and the OpenAI layer is reusable across agents.
- SQLite is used by default for fast local development and easy integration.
