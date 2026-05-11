import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv('STREAMLIT_API_BASE', 'http://127.0.0.1:8000').rstrip('/')
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', 'change_this_admin_token')


def admin_headers() -> dict[str, str]:
    return {'x-admin-token': ADMIN_TOKEN}


def post_json(path: str, data: dict[str, Any], admin: bool = False, timeout: int = 120) -> dict[str, Any]:
    headers = admin_headers() if admin else None
    r = requests.post(f'{API_BASE}{path}', json=data, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json()


def get_json(path: str, params: dict[str, Any] | None = None, admin: bool = False, timeout: int = 60) -> Any:
    headers = admin_headers() if admin else None
    r = requests.get(f'{API_BASE}{path}', params=params, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json()
