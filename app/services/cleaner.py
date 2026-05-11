import re
from pathlib import Path

import yaml

from app.core.config import get_settings


class TextCleaner:
    def __init__(self, typo_file: Path | None = None) -> None:
        settings = get_settings()
        self.typo_file = typo_file or settings.typo_file
        self.typo_map = self._load_typo_map(self.typo_file)

    @staticmethod
    def _load_typo_map(path: Path) -> dict[str, str]:
        if not path.exists():
            return {}
        data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        if not isinstance(data, dict):
            return {}
        return {str(k): str(v) for k, v in data.items()}

    def clean(self, text: str) -> str:
        text = text.strip()
        text = text.replace('\u3000', ' ')
        text = re.sub(r'\s+', ' ', text)
        for wrong, right in self.typo_map.items():
            text = text.replace(wrong, right)
        # Keep the original meaning. Do not aggressively rewrite student questions.
        return text.strip()
