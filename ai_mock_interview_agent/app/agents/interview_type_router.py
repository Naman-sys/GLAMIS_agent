"""
Interview Type Router - Routes different interview types to appropriate handlers.

Responsible for:
- Detecting interview type from requests
- Selecting appropriate prompts
- Routing to specialized agents
"""
from __future__ import annotations

from app.utils.enums import InterviewType, SubjectType, SVARType


class InterviewTypeRouter:
    """Routes interview requests to appropriate handlers based on type."""

    @staticmethod
    def detect_interview_type(request_data: dict) -> InterviewType:
        """
        Detect the interview type from request data.
        
        Args:
            request_data: Request dictionary with interview parameters
            
        Returns:
            InterviewType enum value
        """
        if "interview_type" in request_data:
            raw_type = request_data["interview_type"]
            if isinstance(raw_type, str):
                raw_type = raw_type.lower().strip()
            if raw_type == "jd":
                return InterviewType.COMPANY
            try:
                return InterviewType(raw_type)
            except ValueError:
                pass

        # COMPANY interview
        if "selectedCompany" in request_data:
            return InterviewType.COMPANY

        # SVAR interview
        if "difficulty" in request_data and request_data.get("difficulty") in [
            "reading", "repeating", "jumbled_sentence", "short_question", "comprehension"
        ]:
            return InterviewType.SVAR

        # WRITTEN interview (no answer provided, only asking for question)
        if "subject" in request_data and not request_data.get("answer") and request_data.get("interview_type") == "written":
            return InterviewType.WRITTEN

        # VERBAL interview
        if "subject" in request_data and request_data.get("interview_type") == "verbal":
            return InterviewType.VERBAL

        # SUBJECT interview (default)
        if "subject" in request_data:
            return InterviewType.SUBJECT

        # Default to SUBJECT
        return InterviewType.SUBJECT

    @staticmethod
    def get_subject_type(subject: str) -> SubjectType:
        """
        Convert subject string to SubjectType enum.
        
        Args:
            subject: Subject name (case-insensitive)
            
        Returns:
            SubjectType enum value
        """
        subject_lower = subject.lower().strip()
        
        mapping = {
            "dsa": SubjectType.DSA,
            "data structures": SubjectType.DSA,
            "data structures and algorithms": SubjectType.DSA,
            "os": SubjectType.OS,
            "operating system": SubjectType.OS,
            "operating systems": SubjectType.OS,
            "cn": SubjectType.CN,
            "computer networks": SubjectType.CN,
            "networks": SubjectType.CN,
            "dbms": SubjectType.DBMS,
            "database": SubjectType.DBMS,
            "database management system": SubjectType.DBMS,
            "ml": SubjectType.ML,
            "machine learning": SubjectType.ML,
            "cybersecurity": SubjectType.CYBERSECURITY,
            "cyber security": SubjectType.CYBERSECURITY,
            "security": SubjectType.CYBERSECURITY,
        }
        
        return mapping.get(subject_lower, SubjectType.DSA)

    @staticmethod
    def get_svar_type(difficulty: str) -> SVARType:
        """
        Convert difficulty string to SVARType enum.
        
        Args:
            difficulty: SVAR difficulty type (case-insensitive)
            
        Returns:
            SVARType enum value
        """
        difficulty_lower = difficulty.lower().strip()
        
        mapping = {
            "reading": SVARType.READING,
            "repeating": SVARType.REPEATING,
            "jumbled_sentence": SVARType.JUMBLED_SENTENCE,
            "jumbled": SVARType.JUMBLED_SENTENCE,
            "short_question": SVARType.SHORT_QUESTION,
            "short": SVARType.SHORT_QUESTION,
            "comprehension": SVARType.COMPREHENSION,
        }
        
        return mapping.get(difficulty_lower, SVARType.READING)

    @staticmethod
    def get_prompt_name(interview_type: InterviewType, subject: str | None = None) -> str:
        """
        Get the prompt file name based on interview type and subject.
        
        Args:
            interview_type: Type of interview
            subject: Subject name (for subject-based interviews)
            
        Returns:
            Prompt file name (without .txt extension)
        """
        if interview_type == InterviewType.SUBJECT:
            if subject:
                subject_type = InterviewTypeRouter.get_subject_type(subject)
                return f"subject_{subject_type.value}"
            return "subject_dsa"
        
        elif interview_type == InterviewType.VERBAL:
            return "verbal"
        
        elif interview_type == InterviewType.WRITTEN:
            return "written"
        
        elif interview_type == InterviewType.COMPANY:
            return "company"
        
        elif interview_type == InterviewType.SVAR:
            return "svar"
        
        return "subject_dsa"

    @staticmethod
    def should_include_follow_up(interview_type: InterviewType, score: int) -> bool:
        """
        Determine if a follow-up question should be generated.
        
        Args:
            interview_type: Type of interview
            score: Candidate's score (0-10)
            
        Returns:
            True if follow-up question should be generated
        """
        # For subject and verbal interviews, follow up on low scores
        if interview_type in (InterviewType.SUBJECT, InterviewType.VERBAL):
            return score < 6
        
        # For written interviews, always generate follow-up
        if interview_type == InterviewType.WRITTEN:
            return True
        
        # For company interviews, follow up on low scores
        if interview_type == InterviewType.COMPANY:
            return score < 6
        
        # SVAR interviews typically don't use follow-ups
        return False

    @staticmethod
    def get_evaluation_criteria(interview_type: InterviewType) -> dict[str, str]:
        """
        Get evaluation criteria based on interview type.
        
        Args:
            interview_type: Type of interview
            
        Returns:
            Dictionary of criteria to evaluate
        """
        base_criteria = {
            "technical_accuracy": "How accurate is the technical content?",
            "completeness": "How complete is the answer?",
            "clarity": "Is the answer clear and well-structured?",
        }
        
        if interview_type == InterviewType.SUBJECT:
            return {
                **base_criteria,
                "relevance": "Is the answer relevant to the question?",
                "depth": "Does it show deep understanding?",
            }
        
        elif interview_type == InterviewType.VERBAL:
            return {
                **base_criteria,
                "communication": "Is communication clear and grammatically correct?",
                "vocabulary": "Is appropriate vocabulary used?",
                "fluency": "Is the answer fluent and natural?",
            }
        
        elif interview_type == InterviewType.WRITTEN:
            return {
                **base_criteria,
                "writing_quality": "Is the writing quality good?",
                "organization": "Is the answer well-organized?",
            }
        
        elif interview_type == InterviewType.COMPANY:
            return {
                "technical_accuracy": "Technical accuracy of answer",
                "behavioral_fit": "Does response align with company culture?",
                "problem_solving": "Problem-solving approach",
                "communication": "Communication effectiveness",
            }
        
        elif interview_type == InterviewType.SVAR:
            return {
                "pronunciation": "Pronunciation accuracy",
                "correctness": "Correctness of answer",
                "grammar": "Grammar and sentence structure",
            }
        
        return base_criteria
