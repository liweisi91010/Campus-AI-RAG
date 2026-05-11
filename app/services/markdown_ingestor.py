from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import jieba.analyse
from sqlalchemy import delete
from sqlmodel import Session

from app.core.config import get_settings
from app.db.session import create_db_and_tables
from app.models.knowledge import KnowledgeChunk
from app.services.keyword_service import CampusKeywordService
from app.services.milvus_store import MilvusKnowledgeStore
from app.services.embedding_service import EmbeddingService


@dataclass
class ParsedChunk:
    id: str
    source_file: str
    doc_title: str
    section_title: str
    chunk_index: int
    intent: str
    keywords: list[str]
    content: str


@dataclass
class IngestSummary:
    files_seen: int = 0
    chunks_parsed: int = 0
    chunks_inserted: int = 0
    chunks_skipped_existing: int = 0
    milvus_inserted: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


class MarkdownIngestor:
    def __init__(self, session: Session) -> None:
        self.settings = get_settings()
        self.session = session
        self.keyword_service = CampusKeywordService()
        self.embedding = EmbeddingService()
        self.milvus = MilvusKnowledgeStore()

    def ingest_directory(self, directory: Path, rebuild: bool = False) -> IngestSummary:
        files = sorted(directory.rglob('*.md'))
        return self.ingest_files(files, rebuild=rebuild)

    def ingest_files(self, files: Iterable[Path], rebuild: bool = False) -> IngestSummary:
        create_db_and_tables()
        summary = IngestSummary()
        files = [Path(f) for f in files]
        summary.files_seen = len(files)

        if rebuild:
            self.milvus.ensure_collection(recreate=True)
            self.session.exec(delete(KnowledgeChunk))
            self.session.commit()
        else:
            self.milvus.ensure_collection(recreate=False)

        chunks: list[ParsedChunk] = []
        for file in files:
            if not file.exists() or file.suffix.lower() != '.md':
                continue
            chunks.extend(self.parse_markdown_file(file))
        summary.chunks_parsed = len(chunks)

        new_chunks = []
        for chunk in chunks:
            if not rebuild and self.session.get(KnowledgeChunk, chunk.id):
                summary.chunks_skipped_existing += 1
                continue
            new_chunks.append(chunk)

        batch_size = 32
        for start in range(0, len(new_chunks), batch_size):
            batch = new_chunks[start:start + batch_size]
            vectors = self.embedding.embed_texts([embedding_input(c) for c in batch])
            milvus_rows = []
            for chunk, vector in zip(batch, vectors):
                milvus_rows.append({
                    'id': chunk.id,
                    'vector': vector,
                    'doc_title': chunk.doc_title[:500],
                    'source_file': chunk.source_file[:500],
                    'section_title': chunk.section_title[:500],
                    'intent': chunk.intent[:120],
                    'keywords': json.dumps(chunk.keywords, ensure_ascii=False)[:1900],
                    'content': chunk.content[:6000],
                })
            inserted = self.milvus.insert_chunks(milvus_rows)
            summary.milvus_inserted += inserted
            for chunk in batch:
                self.session.add(KnowledgeChunk(
                    id=chunk.id,
                    source_file=chunk.source_file,
                    doc_title=chunk.doc_title,
                    section_title=chunk.section_title,
                    chunk_index=chunk.chunk_index,
                    intent=chunk.intent,
                    keywords_json=json.dumps(chunk.keywords, ensure_ascii=False),
                    content=chunk.content,
                ))
            self.session.commit()
            summary.chunks_inserted += len(batch)

        return summary

    def parse_markdown_file(self, file: Path) -> list[ParsedChunk]:
        text = file.read_text(encoding='utf-8')
        text = strip_frontmatter(text)
        sections = split_by_headings(text)
        if not sections:
            sections = [(file.stem, text)]
        doc_title = guess_doc_title(text) or file.stem
        chunks: list[ParsedChunk] = []
        idx = 0
        for section_title, section_body in sections:
            for content in chunk_text(section_body, self.settings.chunk_max_chars, self.settings.chunk_overlap_chars):
                clean = normalize_md_text(content)
                if len(clean) < 20:
                    continue
                keyword_info = self.keyword_service.keyword_json(clean)
                jieba_terms = jieba.analyse.extract_tags(clean, topK=8)
                keywords = merge_unique(keyword_info.get('keywords', []), jieba_terms)
                chunk_id = make_chunk_id(file, section_title, idx, clean)
                chunks.append(ParsedChunk(
                    id=chunk_id,
                    source_file=str(file),
                    doc_title=doc_title,
                    section_title=section_title,
                    chunk_index=idx,
                    intent=keyword_info.get('intent', '其他'),
                    keywords=keywords,
                    content=clean,
                ))
                idx += 1
        return chunks


def strip_frontmatter(text: str) -> str:
    if text.startswith('---'):
        end = text.find('\n---', 3)
        if end != -1:
            return text[end + 4:]
    return text


def guess_doc_title(text: str) -> str:
    for line in text.splitlines():
        m = re.match(r'^#\s+(.+)$', line.strip())
        if m:
            return m.group(1).strip()
    return ''


def split_by_headings(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_title = '正文'
    current_lines: list[str] = []
    for line in lines:
        m = re.match(r'^(#{1,4})\s+(.+)$', line.strip())
        if m:
            if current_lines:
                sections.append((current_title, current_lines))
            current_title = m.group(2).strip()
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_title, current_lines))
    return [(title, '\n'.join(body)) for title, body in sections]


def normalize_md_text(text: str) -> str:
    text = re.sub(r'```.*?```', ' ', text, flags=re.DOTALL)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'!\[[^\]]*\]\([^\)]*\)', ' ', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]*\)', r'\1', text)
    text = re.sub(r'^[#>\-\*\s]+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def chunk_text(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    chunks: list[str] = []
    current = ''
    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current = f'{current}\n\n{para}'.strip()
        else:
            if current:
                chunks.append(current)
            if len(para) <= max_chars:
                current = para
            else:
                # Hard split very long paragraphs.
                pos = 0
                while pos < len(para):
                    end = pos + max_chars
                    chunks.append(para[pos:end])
                    pos = max(end - overlap_chars, pos + 1)
                current = ''
    if current:
        chunks.append(current)
    if overlap_chars <= 0 or len(chunks) <= 1:
        return chunks
    with_overlap = [chunks[0]]
    for prev, cur in zip(chunks, chunks[1:]):
        prefix = prev[-overlap_chars:]
        with_overlap.append(f'{prefix}\n{cur}')
    return with_overlap


def make_chunk_id(file: Path, section_title: str, idx: int, content: str) -> str:
    raw = f'{file.as_posix()}::{section_title}::{idx}::{content}'.encode('utf-8')
    return hashlib.sha1(raw).hexdigest()


def merge_unique(*seqs: Iterable[str]) -> list[str]:
    seen = set()
    out = []
    for seq in seqs:
        for item in seq:
            item = str(item).strip()
            if len(item) < 2 or item in seen:
                continue
            seen.add(item)
            out.append(item)
    return out[:20]


def embedding_input(chunk: ParsedChunk) -> str:
    """Build the text used for vectorization.

    Putting title, section, intent and school-specific keywords in the vector input makes
    local_hash retrieval much more effective for handbook-style Markdown documents.
    """
    keywords = ' '.join(chunk.keywords)
    return (
        f'文档标题：{chunk.doc_title}\n'
        f'章节：{chunk.section_title}\n'
        f'意图：{chunk.intent}\n'
        f'关键词：{keywords}\n'
        f'正文：{chunk.content}'
    )
