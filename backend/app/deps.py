from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import AppError
from app.models import User
from app.services.auth import user_from_access_token


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("vc_access")
    if not token:
        header = request.headers.get("authorization") or ""
        if header.lower().startswith("bearer "):
            token = header[7:].strip()
    if not token:
        raise AppError("Não autenticado.", 401)
    return user_from_access_token(db, token)


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise AppError("Acesso restrito à administração.", 403)
    return user
