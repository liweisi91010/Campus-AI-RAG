from typing import Annotated

from fastapi import Header, HTTPException

from app.core.config import get_settings


def verify_admin_token(x_admin_token: Annotated[str | None, Header()] = None) -> None:
    settings = get_settings()
    if not settings.admin_token:
        return
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail='Invalid admin token')
