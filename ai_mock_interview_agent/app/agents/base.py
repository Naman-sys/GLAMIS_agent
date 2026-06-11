from __future__ import annotations

from app.memory.memory_manager import MemoryManager
from app.services.groq_service import GroqService


class BaseInterviewAgent:
    """Base class shared by all interview agents."""

    def __init__(self, groq_service: GroqService | None, memory: MemoryManager):
        self.groq_service = groq_service
        self.memory = memory

    @property
    def has_llm(self) -> bool:
        return self.groq_service is not None
