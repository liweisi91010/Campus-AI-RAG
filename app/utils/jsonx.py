import json
from typing import Any


def dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def loads(text: str, default: Any) -> Any:
    try:
        if not text:
            return default
        return json.loads(text)
    except Exception:
        return default
