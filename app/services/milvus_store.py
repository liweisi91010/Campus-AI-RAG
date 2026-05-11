from __future__ import annotations

import logging
from typing import Any

from pymilvus import DataType, MilvusClient

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class MilvusKnowledgeStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        kwargs: dict[str, Any] = {'uri': self.settings.milvus_uri}
        if self.settings.milvus_token:
            kwargs['token'] = self.settings.milvus_token
        self.client = MilvusClient(**kwargs)
        self.collection = self.settings.milvus_collection

    def ensure_collection(self, recreate: bool = False) -> None:
        if recreate and self.client.has_collection(self.collection):
            self.client.drop_collection(self.collection)
        if self.client.has_collection(self.collection):
            try:
                self.client.load_collection(self.collection)
            except Exception:
                pass
            return

        schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field(field_name='id', datatype=DataType.VARCHAR, is_primary=True, max_length=96)
        schema.add_field(field_name='vector', datatype=DataType.FLOAT_VECTOR, dim=self.settings.milvus_dimension)
        schema.add_field(field_name='doc_title', datatype=DataType.VARCHAR, max_length=512)
        schema.add_field(field_name='source_file', datatype=DataType.VARCHAR, max_length=512)
        schema.add_field(field_name='section_title', datatype=DataType.VARCHAR, max_length=512)
        schema.add_field(field_name='intent', datatype=DataType.VARCHAR, max_length=128)
        schema.add_field(field_name='keywords', datatype=DataType.VARCHAR, max_length=2048)
        schema.add_field(field_name='content', datatype=DataType.VARCHAR, max_length=20000)

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name='vector',
            index_type='AUTOINDEX',
            metric_type=self.settings.milvus_metric,
        )
        self.client.create_collection(
            collection_name=self.collection,
            schema=schema,
            index_params=index_params,
        )
        try:
            self.client.load_collection(self.collection)
        except Exception:
            logger.exception('Failed to load collection right after creation')

    def insert_chunks(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        self.ensure_collection(recreate=False)
        res = self.client.insert(collection_name=self.collection, data=rows)
        try:
            self.client.flush(collection_name=self.collection)
        except Exception:
            pass
        if isinstance(res, dict):
            return int(res.get('insert_count') or res.get('insertCount') or len(rows))
        return len(rows)

    def search(self, vector: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        self.ensure_collection(recreate=False)
        res = self.client.search(
            collection_name=self.collection,
            data=[vector],
            anns_field='vector',
            limit=top_k,
            search_params={'metric_type': self.settings.milvus_metric},
            output_fields=['doc_title', 'source_file', 'section_title', 'intent', 'keywords', 'content'],
        )
        hits: list[dict[str, Any]] = []
        if not res:
            return hits
        first = res[0] if isinstance(res, list) else res
        for item in first:
            entity = item.get('entity') or {}
            score = item.get('score')
            if score is None:
                score = item.get('distance')
            hits.append({
                'id': str(item.get('id') or entity.get('id') or ''),
                'score': float(score or 0.0),
                'doc_title': entity.get('doc_title', ''),
                'source_file': entity.get('source_file', ''),
                'section_title': entity.get('section_title', ''),
                'intent': entity.get('intent', ''),
                'keywords': entity.get('keywords', ''),
                'content': entity.get('content', ''),
                'match_type': 'vector',
            })
        return hits
