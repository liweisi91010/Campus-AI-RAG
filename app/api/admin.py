from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlmodel import Session

from app.api.deps import verify_admin_token
from app.core.config import get_settings
from app.db.session import get_session
from app.schemas.question import AdminQuestionItem, ApproveRequest, IngestUploadedResponse, RejectRequest
from app.services.markdown_ingestor import MarkdownIngestor
from app.services.pipeline import QuestionPipeline, record_to_admin_item

router = APIRouter(prefix='/api/admin', tags=['admin'], dependencies=[Depends(verify_admin_token)])


@router.get('/questions', response_model=list[AdminQuestionItem])
def list_questions(
    session: Annotated[Session, Depends(get_session)],
    status: str = 'PENDING_REVIEW',
    limit: int = 50,
) -> list[dict]:
    records = QuestionPipeline(session).list_admin_questions(status=status, limit=limit)
    return [record_to_admin_item(r) for r in records]


@router.post('/questions/{question_id}/approve', response_model=AdminQuestionItem)
def approve_question(
    question_id: int,
    req: ApproveRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    record = QuestionPipeline(session).approve(question_id, req.reviewer, req.final_answer)
    return record_to_admin_item(record)


@router.post('/questions/{question_id}/reject', response_model=AdminQuestionItem)
def reject_question(
    question_id: int,
    req: RejectRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    record = QuestionPipeline(session).reject(question_id, req.reviewer, req.reason)
    return record_to_admin_item(record)


@router.post('/knowledge/upload-md', response_model=IngestUploadedResponse)
async def upload_markdown(
    session: Annotated[Session, Depends(get_session)],
    files: Annotated[list[UploadFile], File(description='Markdown files')],
    rebuild: bool = False,
) -> IngestUploadedResponse:
    settings = get_settings()
    upload_dir = Path(settings.knowledge_dir) / 'uploads'
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for f in files:
        safe_name = Path(f.filename or 'uploaded.md').name
        if not safe_name.lower().endswith('.md'):
            continue
        target = upload_dir / safe_name
        data = await f.read()
        target.write_bytes(data)
        saved.append(str(target))
    summary = MarkdownIngestor(session).ingest_files([Path(x) for x in saved], rebuild=rebuild).to_dict()
    return IngestUploadedResponse(saved_files=saved, summary=summary)


@router.post('/knowledge/rebuild-from-dir')
def rebuild_from_dir(session: Annotated[Session, Depends(get_session)]) -> dict:
    settings = get_settings()
    summary = MarkdownIngestor(session).ingest_directory(settings.knowledge_dir, rebuild=True)
    return summary.to_dict()
