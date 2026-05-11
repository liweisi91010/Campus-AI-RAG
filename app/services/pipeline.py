from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.config import get_settings
from app.models.question import QuestionRecord
from app.schemas.question import AskResponse, StudentAnswerResponse
from app.services.cleaner import TextCleaner
from app.services.keyword_service import CampusKeywordService
from app.services.embedding_service import EmbeddingService
from app.services.knowledge_search import KnowledgeSearchService
from app.services.milvus_store import MilvusKnowledgeStore
from app.services.openai_gateway import OpenAIGateway
from app.services.safety import BannedWordFastReview, CampusRuleSafety
from app.utils.jsonx import dumps, loads


class QuestionPipeline:
    def __init__(self, session: Session) -> None:
        self.settings = get_settings()
        self.session = session
        self.cleaner = TextCleaner()
        self.keyword_service = CampusKeywordService()
        self.knowledge_search = KnowledgeSearchService(session)
        self.embedding = EmbeddingService()
        self.openai = OpenAIGateway()
        self.milvus = MilvusKnowledgeStore()
        self.rule_safety = CampusRuleSafety()
        self.fast_review = BannedWordFastReview(self.settings.banned_words_file)

    def submit(self, student_id: str, raw_question: str) -> AskResponse:
        cleaned = self.cleaner.clean(raw_question)
        keyword_info = self.keyword_service.keyword_json(cleaned)
        intent = keyword_info.get('intent', '其他')

        input_moderation = self.openai.moderate(cleaned)
        campus_rule = self.rule_safety.check(cleaned).to_dict()

        keyword_hits: list[dict[str, Any]] = []
        vector_hits: list[dict[str, Any]] = []
        context: list[dict[str, Any]] = []
        relevance = 0.0

        if input_moderation.get('safe', True) and campus_rule.get('safe', True):
            keyword_hits = self.knowledge_search.keyword_search(cleaned, top_k=self.settings.top_k)
            query_vector = self.embedding.embed_one(query_embedding_input(cleaned, intent, keyword_info))
            vector_hits = self.milvus.search(query_vector, top_k=self.settings.top_k)
            context = self._merge_hits(keyword_hits, vector_hits, keyword_info)
            relevance = max([h.get('score', 0.0) for h in context] or [0.0])

        if not input_moderation.get('safe', True) or not campus_rule.get('safe', True):
            draft = '该问题触发安全或隐私规则，需要人工老师处理。'
        elif relevance < self.settings.min_relevance_score:
            draft = '我暂时没有在学工手册/教务知识库中找到足够可靠的依据。建议联系辅导员、学院办公室或对应业务部门确认。'
        else:
            draft = self.openai.draft_answer(cleaned, intent, context, keyword_info)

        output_moderation = self.openai.moderate(draft)
        answer_fast_review = self.fast_review.check(draft, target_name='answer').to_dict()
        if self.settings.quick_review_check_question:
            question_fast_review = self.fast_review.check(cleaned, target_name='question').to_dict()
        else:
            question_fast_review = {'safe': True, 'risk_level': 'LOW', 'reasons': []}

        quick_review = {
            'manual_review_enabled': self.settings.manual_review_enabled,
            'banned_words_file': str(self.settings.banned_words_file),
            'question_checked': self.settings.quick_review_check_question,
            'question': question_fast_review,
            'answer': answer_fast_review,
        }
        campus_rule['quick_review'] = quick_review

        risk_level = self._risk_level(input_moderation, campus_rule, relevance, output_moderation, quick_review)
        now = datetime.now(timezone.utc)

        status = 'PENDING_REVIEW'
        final_answer = ''
        reviewer = ''
        reviewed_at = None
        review_reason = ''
        message = '问题已生成草稿并进入人工审核。审核通过后学生端才能看到最终答复。'

        if not self.settings.manual_review_enabled:
            fast_ok, fast_reasons = self._fast_review_decision(
                input_moderation=input_moderation,
                output_moderation=output_moderation,
                campus_rule=campus_rule,
                answer_fast_review=answer_fast_review,
                question_fast_review=question_fast_review,
            )
            reviewer = 'fast_review'
            reviewed_at = now
            if fast_ok:
                status = 'APPROVED'
                final_answer = draft
                message = '已通过违禁词快速审核，答案已直接返回学生。'
            else:
                status = 'REJECTED'
                final_answer = ''
                review_reason = '快速审核未通过：' + '；'.join(fast_reasons)
                message = '快速审核未通过，答案未返回学生。'

        record = QuestionRecord(
            student_id=student_id,
            raw_question=raw_question,
            cleaned_question=cleaned,
            intent=intent,
            keyword_hits_json=dumps(keyword_hits),
            vector_hits_json=dumps(vector_hits),
            context_json=dumps(context),
            input_safety_json=dumps(input_moderation),
            output_safety_json=dumps(output_moderation),
            campus_rule_json=dumps(campus_rule),
            relevance_score=float(relevance),
            draft_answer=draft,
            final_answer=final_answer,
            status=status,
            risk_level=risk_level,
            review_reason=review_reason,
            reviewer=reviewer,
            reviewed_at=reviewed_at,
            updated_at=now,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return AskResponse(
            question_id=record.id or 0,
            status=record.status,
            risk_level=record.risk_level,
            message=message,
            raw_question=record.raw_question,
            cleaned_question=record.cleaned_question,
        )

    def student_answer(self, question_id: int, student_id: str) -> StudentAnswerResponse:
        record = self.session.get(QuestionRecord, question_id)
        if not record or record.student_id != student_id:
            raise HTTPException(status_code=404, detail='Question not found')

        base = {
            'question_id': record.id or 0,
            'status': record.status,
            'raw_question': record.raw_question,
            'cleaned_question': record.cleaned_question,
            'created_at': record.created_at.isoformat() if record.created_at else None,
        }

        if record.status == 'APPROVED':
            return StudentAnswerResponse(
                **base,
                message='审核已通过。' if record.reviewer != 'fast_review' else '快速审核已通过。',
                final_answer=record.final_answer,
            )
        if record.status == 'REJECTED':
            return StudentAnswerResponse(
                **base,
                message='该问题未通过审核，请联系辅导员或相关部门。',
                review_reason=record.review_reason,
            )
        return StudentAnswerResponse(
            **base,
            message='问题仍在人工审核中。',
        )

    def list_admin_questions(self, status: str = 'PENDING_REVIEW', limit: int = 50) -> list[QuestionRecord]:
        stmt = select(QuestionRecord).where(QuestionRecord.status == status).order_by(QuestionRecord.created_at.desc()).limit(limit)
        return list(self.session.exec(stmt).all())

    def approve(self, question_id: int, reviewer: str, final_answer: str) -> QuestionRecord:
        record = self.session.get(QuestionRecord, question_id)
        if not record:
            raise HTTPException(status_code=404, detail='Question not found')
        record.status = 'APPROVED'
        record.final_answer = final_answer
        record.reviewer = reviewer
        record.reviewed_at = datetime.now(timezone.utc)
        record.updated_at = datetime.now(timezone.utc)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def reject(self, question_id: int, reviewer: str, reason: str) -> QuestionRecord:
        record = self.session.get(QuestionRecord, question_id)
        if not record:
            raise HTTPException(status_code=404, detail='Question not found')
        record.status = 'REJECTED'
        record.review_reason = reason
        record.reviewer = reviewer
        record.reviewed_at = datetime.now(timezone.utc)
        record.updated_at = datetime.now(timezone.utc)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def _merge_hits(self, keyword_hits: list[dict[str, Any]], vector_hits: list[dict[str, Any]], keyword_info: dict[str, Any]) -> list[dict[str, Any]]:
        by_id: dict[str, dict[str, Any]] = {}
        query_terms = keyword_info.get('keywords', [])
        query_intent = keyword_info.get('intent', '其他')
        for hit in keyword_hits + vector_hits:
            hid = str(hit.get('id'))
            if not hid:
                continue
            score = float(hit.get('score', 0.0) or 0.0)
            hit_terms = []
            try:
                raw = hit.get('keywords', '[]')
                hit_terms = json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                hit_terms = []
            score += CampusKeywordService.overlap_score(query_terms, hit_terms) * 0.05
            if query_intent != '其他' and hit.get('intent') == query_intent:
                score += 0.04
            hit = dict(hit)
            hit['score'] = round(min(score, 0.99), 4)
            if hid not in by_id or hit['score'] > by_id[hid]['score']:
                by_id[hid] = hit
        merged = list(by_id.values())
        merged.sort(key=lambda x: x.get('score', 0.0), reverse=True)
        return merged[:self.settings.top_k]

    def _risk_level(
        self,
        input_mod: dict[str, Any],
        campus_rule: dict[str, Any],
        relevance: float,
        output_mod: dict[str, Any] | None = None,
        quick_review: dict[str, Any] | None = None,
    ) -> str:
        if not input_mod.get('safe', True) or not campus_rule.get('safe', True):
            return 'HIGH'
        if output_mod and not output_mod.get('safe', True):
            return 'HIGH'
        if quick_review:
            answer = quick_review.get('answer', {})
            question = quick_review.get('question', {})
            if not answer.get('safe', True) or not question.get('safe', True):
                return 'HIGH'
        if campus_rule.get('risk_level') == 'MEDIUM':
            return 'MEDIUM'
        if relevance and relevance < self.settings.min_relevance_score:
            return 'MEDIUM'
        return 'LOW'

    @staticmethod
    def _fast_review_decision(
        input_moderation: dict[str, Any],
        output_moderation: dict[str, Any],
        campus_rule: dict[str, Any],
        answer_fast_review: dict[str, Any],
        question_fast_review: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        if not input_moderation.get('safe', True):
            reasons.append('输入触发模型安全审核')
        if not output_moderation.get('safe', True):
            reasons.append('输出触发模型安全审核')
        if not campus_rule.get('safe', True):
            reasons.extend(campus_rule.get('reasons') or ['输入触发校园本地安全规则'])
        if not question_fast_review.get('safe', True):
            reasons.extend(question_fast_review.get('reasons') or ['问题命中违禁词'])
        if not answer_fast_review.get('safe', True):
            reasons.extend(answer_fast_review.get('reasons') or ['答案命中违禁词'])
        return (not reasons, reasons)


def record_to_admin_item(record: QuestionRecord) -> dict[str, Any]:
    return {
        'id': record.id,
        'student_id': record.student_id,
        'raw_question': record.raw_question,
        'cleaned_question': record.cleaned_question,
        'intent': record.intent,
        'relevance_score': record.relevance_score,
        'status': record.status,
        'risk_level': record.risk_level,
        'draft_answer': record.draft_answer,
        'final_answer': record.final_answer,
        'review_reason': record.review_reason,
        'reviewer': record.reviewer,
        'created_at': record.created_at.isoformat() if record.created_at else '',
        'reviewed_at': record.reviewed_at.isoformat() if record.reviewed_at else None,
        'keyword_hits': loads(record.keyword_hits_json, []),
        'vector_hits': loads(record.vector_hits_json, []),
        'context': loads(record.context_json, []),
        'input_safety': loads(record.input_safety_json, {}),
        'output_safety': loads(record.output_safety_json, {}),
        'campus_rule': loads(record.campus_rule_json, {}),
    }


def query_embedding_input(question: str, intent: str, keyword_info: dict[str, Any]) -> str:
    keywords = ' '.join(str(x) for x in keyword_info.get('keywords', []) if str(x).strip())
    return f'学生问题：{question}\n意图：{intent}\n关键词：{keywords}'
