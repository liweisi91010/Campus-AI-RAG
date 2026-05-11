from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

settings = get_settings()
engine = create_engine(
    settings.sqlalchemy_url,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=280,
)


def create_db_and_tables() -> None:
    # Import models so SQLModel metadata knows them.
    from app.models.question import QuestionRecord  # noqa: F401
    from app.models.knowledge import KnowledgeChunk  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
