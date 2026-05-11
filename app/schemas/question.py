from typing import Any, Optional

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    student_id: str = Field(min_length=1, max_length=128)
    question: str = Field(min_length=2, max_length=2000)


class AskResponse(BaseModel):
    question_id: int
    status: str
    message: str
    risk_level: str
    raw_question: str
    cleaned_question: str


class StudentAnswerResponse(BaseModel):
    question_id: int
    status: str
    message: str
    raw_question: Optional[str] = None
    cleaned_question: Optional[str] = None
    created_at: Optional[str] = None
    final_answer: Optional[str] = None
    review_reason: Optional[str] = None


class AdminQuestionItem(BaseModel):
    id: int
    student_id: str
    raw_question: str
    cleaned_question: str
    intent: str
    relevance_score: float
    status: str
    risk_level: str
    draft_answer: str
    final_answer: str
    review_reason: str
    reviewer: str
    created_at: str
    reviewed_at: Optional[str]
    keyword_hits: list[dict[str, Any]]
    vector_hits: list[dict[str, Any]]
    context: list[dict[str, Any]]
    input_safety: dict[str, Any]
    output_safety: dict[str, Any]
    campus_rule: dict[str, Any]


class ApproveRequest(BaseModel):
    reviewer: str = Field(default='admin', max_length=128)
    final_answer: str = Field(min_length=1, max_length=8000)


class RejectRequest(BaseModel):
    reviewer: str = Field(default='admin', max_length=128)
    reason: str = Field(min_length=1, max_length=2000)


class IngestUploadedResponse(BaseModel):
    saved_files: list[str]
    summary: dict[str, Any]
