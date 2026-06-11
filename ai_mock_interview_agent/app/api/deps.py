from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.interview_service import InterviewOrchestrator


def get_interview_orchestrator(db: Session = Depends(get_db)) -> InterviewOrchestrator:
    """Create an orchestrator bound to the request database session."""

    return InterviewOrchestrator(db)
