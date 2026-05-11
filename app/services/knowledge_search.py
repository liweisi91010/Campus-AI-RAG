from __future__ import annotations

import json
from typing import Any

from sqlalchemy import or_
from sqlmodel import Session, select

from app.models.knowledge import KnowledgeChunk
from app.services.keyword_service import CampusKeywordService, parse_keywords_json


class KnowledgeSearchService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.keyword_service = CampusKeywordService()

    def keyword_search(self, question: str, top_k: int = 5) -> list[dict[str, Any]]:
        keyword_info = self.keyword_service.keyword_json(question)
        terms = keyword_info.get('keywords') or self.keyword_service.extract_terms(question)
        terms = [t for t in terms if len(t) >= 2][:8]
        if not terms:
            return []
        clauses = []
        for term in terms:
            clauses.append(KnowledgeChunk.content.contains(term))
            clauses.append(KnowledgeChunk.keywords_json.contains(term))
        stmt = select(KnowledgeChunk).where(or_(*clauses)).limit(80)
        rows = list(self.session.exec(stmt).all())
        scored: list[dict[str, Any]] = []
        for row in rows:
            row_terms = parse_keywords_json(row.keywords_json)
            content_hits = sum(1 for term in terms if term in row.content)
            keyword_overlap = CampusKeywordService.overlap_score(terms, row_terms)
            intent_bonus = 0.08 if row.intent == keyword_info.get('intent') and row.intent != '其他' else 0.0
            score = min(0.45 + content_hits * 0.08 + keyword_overlap * 0.25 + intent_bonus, 0.92)
            scored.append({
                'id': row.id,
                'score': round(score, 4),
                'doc_title': row.doc_title,
                'source_file': row.source_file,
                'section_title': row.section_title,
                'intent': row.intent,
                'keywords': json.dumps(row_terms, ensure_ascii=False),
                'content': row.content,
                'match_type': 'keyword',
            })
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:top_k]
