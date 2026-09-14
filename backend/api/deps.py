from fastapi import Header, HTTPException

from backend.core.config import settings


def require_admin(x_admin_token: str = Header(default="")) -> None:
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="invalid admin token")
