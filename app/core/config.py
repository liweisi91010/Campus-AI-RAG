from functools import lru_cache
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    mysql_host: str = '127.0.0.1'
    mysql_port: int = 3306
    mysql_user: str = 'campus_ai'
    mysql_password: str = 'campus_ai_pwd'
    mysql_database: str = 'campus_ai'
    mysql_charset: str = 'utf8mb4'
    database_url: Optional[str] = None

    milvus_uri: str = 'http://127.0.0.1:19530'
    milvus_token: str = ''
    milvus_collection: str = 'campus_student_handbook'
    # local_hash uses a deterministic local vector, so no external embedding API is required.
    # If you switch EMBEDDING_PROVIDER to openai, set this to the provider's embedding dimension.
    milvus_dimension: int = 1024
    milvus_metric: str = 'COSINE'

    openai_api_key: str = Field(default='replace_me')
    openai_base_url: str = 'https://api.longcat.chat/openai/v1'
    openai_chat_model: str = 'LongCat-Flash-Lite'
    openai_embedding_model: str = ''
    # local_hash: local deterministic Chinese lexical embedding. No embedding API needed.
    # openai: call an OpenAI-compatible /embeddings endpoint.
    embedding_provider: str = 'local_hash'
    openai_moderation_model: str = 'omni-moderation-latest'
    use_responses_api: bool = False
    enable_openai_moderation: bool = False

    # Review mode
    # True: every generated draft goes to admin review.
    # False: use local banned-word fast review; pass => APPROVED, fail => REJECTED.
    manual_review_enabled: bool = True
    banned_words_file: Path = Path('./data/banned_words.txt')
    quick_review_check_question: bool = False

    knowledge_dir: Path = Path('./knowledge')
    keyword_file: Path = Path('./data/campus_keywords.yml')
    typo_file: Path = Path('./data/typo_map.yml')
    top_k: int = 5
    min_relevance_score: float = 0.55
    chunk_max_chars: int = 900
    chunk_overlap_chars: int = 120

    api_host: str = '0.0.0.0'
    api_port: int = 8000
    streamlit_api_base: str = 'http://127.0.0.1:8000'
    admin_token: str = 'change_this_admin_token'

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        user = quote_plus(self.mysql_user)
        pwd = quote_plus(self.mysql_password)
        host = self.mysql_host
        port = self.mysql_port
        db = self.mysql_database
        charset = self.mysql_charset
        return f'mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}?charset={charset}'


@lru_cache
def get_settings() -> Settings:
    return Settings()
