from __future__ import annotations

import hashlib
import math
import re
from typing import Iterable

import jieba
from openai import OpenAI

from app.core.config import get_settings
from app.services.keyword_service import CampusKeywordService


class EmbeddingService:
    """Embedding abstraction used by Markdown ingestion and vector search.

    Providers:
    - local_hash: local deterministic Chinese lexical embedding. No external embedding API is needed.
    - openai: call an OpenAI-compatible /embeddings endpoint.

    LongCat's public API documentation currently exposes chat/completions but not an embeddings
    endpoint, so local_hash is the recommended default for LongCat deployments.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.provider = (self.settings.embedding_provider or 'local_hash').strip().lower()
        self.keyword_service = CampusKeywordService()
        self._openai_client: OpenAI | None = None
        if self.provider in {'openai', 'api'}:
            self._openai_client = OpenAI(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
            )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self.provider in {'openai', 'api'}:
            return self._embed_texts_openai(texts)
        if self.provider in {'local_hash', 'hash', 'local'}:
            return [self._embed_text_local_hash(text) for text in texts]
        raise ValueError(
            f'Unsupported EMBEDDING_PROVIDER={self.settings.embedding_provider!r}. '
            'Use local_hash or openai.'
        )

    def embed_one(self, text: str) -> list[float]:
        vectors = self.embed_texts([text])
        return vectors[0]

    def _embed_texts_openai(self, texts: list[str]) -> list[list[float]]:
        if self._openai_client is None:
            raise RuntimeError('OpenAI client is not initialized')
        if not self.settings.openai_embedding_model:
            raise ValueError('OPENAI_EMBEDDING_MODEL is required when EMBEDDING_PROVIDER=openai')
        resp = self._openai_client.embeddings.create(
            model=self.settings.openai_embedding_model,
            input=texts,
        )
        vectors = [list(item.embedding) for item in resp.data]
        self._validate_dimension(vectors)
        return vectors

    def _embed_text_local_hash(self, text: str) -> list[float]:
        dim = int(self.settings.milvus_dimension)
        if dim <= 0:
            raise ValueError('MILVUS_DIMENSION must be a positive integer')

        vector = [0.0] * dim
        weighted_terms = self._weighted_terms(text)
        if not weighted_terms:
            weighted_terms = [(text.strip() or 'empty', 1.0)]

        for term, weight in weighted_terms:
            if not term:
                continue
            digest = hashlib.blake2b(term.encode('utf-8'), digest_size=16).digest()
            raw = int.from_bytes(digest[:8], 'big', signed=False)
            idx = raw % dim
            sign = 1.0 if (digest[8] & 1) == 0 else -1.0
            vector[idx] += sign * weight

        norm = math.sqrt(sum(x * x for x in vector))
        if norm == 0:
            return vector
        return [x / norm for x in vector]

    def _weighted_terms(self, text: str) -> list[tuple[str, float]]:
        normalized, aliases = self.keyword_service.normalize_aliases(text or '')
        normalized = normalize_text(normalized)
        keyword_info = self.keyword_service.keyword_json(normalized)
        campus_keywords = [str(x).strip() for x in keyword_info.get('keywords', []) if str(x).strip()]
        intent = str(keyword_info.get('intent') or '').strip()

        weighted: list[tuple[str, float]] = []

        # Strong signals from your university-specific vocabulary.
        for word in campus_keywords:
            weighted.append((f'kw:{word}', 3.0))
            weighted.append((word, 2.0))
        for alias, canonical in aliases.items():
            weighted.append((f'alias:{alias}->{canonical}', 2.2))
            weighted.append((canonical, 2.0))
        if intent and intent != '其他':
            weighted.append((f'intent:{intent}', 2.5))

        # Chinese word segmentation. cut_for_search yields more recall than exact mode.
        for token in jieba.cut_for_search(normalized):
            token = token.strip().lower()
            if useful_token(token):
                weighted.append((token, token_weight(token)))

        # Character n-grams help when jieba does not know school-specific names yet.
        compact = re.sub(r'\s+', '', normalized)
        for n, weight in ((2, 0.55), (3, 0.35)):
            for gram in char_ngrams(compact, n):
                weighted.append((f'g{n}:{gram}', weight))

        # Deduplicate while preserving cumulative weights.
        acc: dict[str, float] = {}
        for term, weight in weighted:
            if not term:
                continue
            acc[term] = acc.get(term, 0.0) + float(weight)
        return list(acc.items())

    def _validate_dimension(self, vectors: list[list[float]]) -> None:
        if not vectors:
            return
        expected = self.settings.milvus_dimension
        actual = len(vectors[0])
        if actual != expected:
            raise ValueError(
                f'Embedding dimension mismatch: provider returned {actual}, '
                f'but MILVUS_DIMENSION={expected}. Change .env and recreate the Milvus collection.'
            )


def normalize_text(text: str) -> str:
    text = text.replace('\u3000', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip().lower()


def useful_token(token: str) -> bool:
    if not token or len(token) < 2:
        return False
    if token in STOPWORDS:
        return False
    if re.fullmatch(r'[\W_]+', token):
        return False
    return True


def token_weight(token: str) -> float:
    if re.search(r'[\u4e00-\u9fff]', token):
        return 1.0 + min(len(token), 8) * 0.08
    if token.isdigit():
        return 0.6
    return 0.9 + min(len(token), 12) * 0.04


def char_ngrams(text: str, n: int) -> Iterable[str]:
    if len(text) < n:
        return []
    return (text[i:i + n] for i in range(0, len(text) - n + 1))


STOPWORDS = {
    '一个', '一下', '一些', '这个', '那个', '怎么', '如何', '什么', '是否', '可以', '需要',
    '办理', '进行', '有关', '关于', '如果', '因为', '所以', '以及', '或者', '但是', '没有',
    'the', 'and', 'for', 'with', 'this', 'that', 'what', 'how', 'can', 'you',
}
