from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeChunk(SQLModel, table=True):
    __tablename__ = 'knowledge_chunks'

    id: str = Field(sa_column=Column(String(64), primary_key=True))
    source_file: str = Field(sa_column=Column(String(512), index=True, nullable=False))
    doc_title: str = Field(default='', sa_column=Column(String(512), index=True, nullable=False))
    section_title: str = Field(default='', sa_column=Column(String(512), nullable=False))
    chunk_index: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    intent: str = Field(default='其他', sa_column=Column(String(128), index=True, nullable=False))
    keywords_json: str = Field(default='[]', sa_column=Column(Text, nullable=False))
    content: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(DateTime(timezone=True), index=True, nullable=False))

