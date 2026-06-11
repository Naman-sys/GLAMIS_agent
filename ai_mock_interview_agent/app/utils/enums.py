from enum import Enum


class DifficultyLevel(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class QuestionCategory(str, Enum):
    TECHNICAL = "Technical"
    BEHAVIORAL = "Behavioral"
    HR = "HR"
    PROBLEM_SOLVING = "Problem Solving"
    SVAR = "SVAR"


class InterviewType(str, Enum):
    """Types of interviews supported by GLAMIS"""
    SUBJECT = "subject"
    VERBAL = "verbal"
    WRITTEN = "written"
    COMPANY = "company"
    SVAR = "svar"


class SubjectType(str, Enum):
    """Subject types for subject-based interviews"""
    DSA = "dsa"
    OS = "os"  # Operating System
    CN = "cn"  # Computer Networks
    DBMS = "dbms"
    ML = "ml"  # Machine Learning
    CYBERSECURITY = "cybersecurity"


class SVARType(str, Enum):
    """SVAR interview types"""
    READING = "reading"
    REPEATING = "repeating"
    JUMBLED_SENTENCE = "jumbled_sentence"
    SHORT_QUESTION = "short_question"
    COMPREHENSION = "comprehension"
