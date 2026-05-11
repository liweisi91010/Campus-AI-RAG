from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Float, String, Text
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class QuestionRecord(SQLModel, table=True):
    __tablename__ = 'question_records'

    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: str = Field(sa_column=Column(String(128), index=True, nullable=False))

    raw_question: str = Field(sa_column=Column(Text, nullable=False))
    cleaned_question: str = Field(sa_column=Column(Text, nullable=False))
    intent: str = Field(default='其他', sa_column=Column(String(128), index=True))

    keyword_hits_json: str = Field(default='[]', sa_column=Column(Text, nullable=False))
    vector_hits_json: str = Field(default='[]', sa_column=Column(Text, nullable=False))
    context_json: str = Field(default='[]', sa_column=Column(Text, nullable=False))

    input_safety_json: str = Field(default='{}', sa_column=Column(Text, nullable=False))
    output_safety_json: str = Field(default='{}', sa_column=Column(Text, nullable=False))
    campus_rule_json: str = Field(default='{}', sa_column=Column(Text, nullable=False))

    relevance_score: float = Field(default=0.0, sa_column=Column(Float, nullable=False))
    draft_answer: str = Field(default='', sa_column=Column(Text, nullable=False))
    final_answer: str = Field(default='', sa_column=Column(Text, nullable=False))

    status: str = Field(default='PENDING_REVIEW', sa_column=Column(String(64), index=True, nullable=False))
    risk_level: str = Field(default='LOW', sa_column=Column(String(64), index=True, nullable=False))
    review_reason: str = Field(default='', sa_column=Column(Text, nullable=False))
    reviewer: str = Field(default='', sa_column=Column(String(128), nullable=False))
    reviewed_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))

    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(DateTime(timezone=True), index=True, nullable=False))
    updated_at: datetime = Field(default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))
