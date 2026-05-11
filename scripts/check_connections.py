from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from sqlmodel import Session

from app.core.config import get_settings
from app.db.session import create_db_and_tables, engine
from app.services.embedding_service import EmbeddingService
from app.services.milvus_store import MilvusKnowledgeStore


def main() -> None:
    settings = get_settings()
    print('DATABASE_URL:', settings.sqlalchemy_url.replace(settings.mysql_password, '***'))
    create_db_and_tables()
    with Session(engine) as session:
        result = session.exec(text('SELECT 1')).one()
        print('MySQL OK:', result)
    store = MilvusKnowledgeStore()
    store.ensure_collection(recreate=False)
    print('Milvus OK:', settings.milvus_uri, 'collection:', settings.milvus_collection)
    emb = EmbeddingService()
    vec = emb.embed_one('校园卡丢失如何补办？')
    print('Embedding provider:', settings.embedding_provider, 'dimension:', len(vec))
    print('Manual review enabled:', settings.manual_review_enabled)
    print('Banned words file:', settings.banned_words_file)


if __name__ == '__main__':
    main()
