from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, questions
from app.db.session import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title='Campus Student Handbook AI Customer Service',
    description='Python RAG demo: MySQL8 + Milvus + Markdown knowledge base + human review.',
    version='0.1.0',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(questions.router)
app.include_router(admin.router)


@app.get('/health')
def health() -> dict:
    return {'ok': True}
