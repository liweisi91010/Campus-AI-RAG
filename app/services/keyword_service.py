from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import jieba
import jieba.analyse
import yaml

from app.core.config import get_settings


@dataclass
class KeywordMatch:
    intent: str
    keywords: list[str]
    aliases: dict[str, str]
    score: float


class CampusKeywordService:
    """Rule-based keyword service for one specific university.

    Edit data/campus_keywords.yml to make it your own school's vocabulary.
    """

    def __init__(self, keyword_file: Path | None = None) -> None:
        settings = get_settings()
        self.keyword_file = keyword_file or settings.keyword_file
        self.config = self._load_config(self.keyword_file)
        self.intents: dict[str, list[str]] = self.config.get('intents', {}) or {}
        self.aliases: dict[str, str] = self.config.get('aliases', {}) or {}
        self.global_keywords: list[str] = self.config.get('global_keywords', []) or []
        for word in self.global_keywords:
            if isinstance(word, str) and word.strip():
                jieba.add_word(word.strip())
        for words in self.intents.values():
            for word in words:
                if isinstance(word, str) and word.strip():
                    jieba.add_word(word.strip())
        for a, b in self.aliases.items():
            jieba.add_word(str(a))
            jieba.add_word(str(b))

    @staticmethod
    def _load_config(path: Path) -> dict:
        if not path.exists():
            return {'intents': {}, 'aliases': {}, 'global_keywords': []}
        data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        return data if isinstance(data, dict) else {}

    def normalize_aliases(self, text: str) -> tuple[str, dict[str, str]]:
        replacements: dict[str, str] = {}
        normalized = text
        for alias, canonical in self.aliases.items():
            alias = str(alias)
            canonical = str(canonical)
            if alias and alias in normalized:
                normalized = normalized.replace(alias, canonical)
                replacements[alias] = canonical
        return normalized, replacements

    def extract_terms(self, text: str, top_k: int = 12) -> list[str]:
        normalized, _ = self.normalize_aliases(text)
        exact_terms = []
        all_terms = set(self.global_keywords)
        for words in self.intents.values():
            all_terms.update(words)
        for word in all_terms:
            if word and str(word) in normalized:
                exact_terms.append(str(word))
        tags = [w for w in jieba.analyse.extract_tags(normalized, topK=top_k) if len(w.strip()) >= 2]
        seen = set()
        merged = []
        for w in exact_terms + tags:
            if w not in seen:
                merged.append(w)
                seen.add(w)
        return merged[:top_k]

    def detect_intent(self, text: str) -> KeywordMatch:
        normalized, aliases = self.normalize_aliases(text)
        best_intent = '其他'
        best_hits: list[str] = []
        best_score = 0.0
        for intent, words in self.intents.items():
            hits = [str(w) for w in words if str(w) and str(w) in normalized]
            if not hits:
                continue
            score = len(hits) / max(len(words), 1)
            # Give exact multi-keyword hits an extra push.
            score += min(len(hits) * 0.08, 0.32)
            if score > best_score:
                best_intent = str(intent)
                best_hits = hits
                best_score = score
        if best_intent == '其他':
            best_hits = self.extract_terms(normalized, top_k=6)
        return KeywordMatch(intent=best_intent, keywords=best_hits, aliases=aliases, score=round(best_score, 4))

    def keyword_json(self, text: str) -> dict:
        m = self.detect_intent(text)
        return {
            'intent': m.intent,
            'keywords': m.keywords,
            'aliases': m.aliases,
            'score': m.score,
        }

    @staticmethod
    def overlap_score(query_terms: Iterable[str], chunk_terms: Iterable[str]) -> float:
        q = {x for x in query_terms if x}
        c = {x for x in chunk_terms if x}
        if not q or not c:
            return 0.0
        return len(q & c) / len(q | c)


def parse_keywords_json(text: str) -> list[str]:
    try:
        obj = json.loads(text or '[]')
        if isinstance(obj, list):
            return [str(x) for x in obj]
        return []
    except Exception:
        return []
