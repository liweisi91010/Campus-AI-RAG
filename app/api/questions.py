from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.schemas.question import AskRequest, AskResponse, StudentAnswerResponse
from app.services.pipeline import QuestionPipeline

router = APIRouter(prefix='/api', tags=['student'])


@router.post('/questions', response_model=AskResponse)
def ask(req: AskRequest, session: Annotated[Session, Depends(get_session)]) -> AskResponse:
    return QuestionPipeline(session).submit(req.student_id, req.question)


@router.get('/questions/{question_id}', response_model=StudentAnswerResponse)
def get_answer(question_id: int, student_id: str, session: Annotated[Session, Depends(get_session)]) -> StudentAnswerResponse:
    return QuestionPipeline(session).student_answer(question_id, student_id)
