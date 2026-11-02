import logging
from datetime import timedelta

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings, utcnow
from app.errors import AppError
from app.models import ClientUser, PasswordResetToken, RefreshToken, User
from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_token,
    new_secret,
    verify_password,
)
from app.services.common import audit, commit_session, owned_client

logger = logging.getLogger("vcontent.auth")


def authenticate(db: Session, email: str, password: str, ip: str | None) -> User:
    normalized = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized, User.deleted_at.is_(None)))
    if not user or not verify_password(password, user.password_hash):
        audit(db, actor_id=user.id if user else None, action="login_failed", entity_type="user", entity_id=user.id if user else None, details={"email": normalized}, ip=ip)
        commit_session(db)
        raise AppError("E-mail ou senha inválidos.", 401)
    if not user.is_active:
        raise AppError("Esta conta está desativada. Fale com a agência.", 403)
    if user.role == "client":
        client = owned_client(db, user)
        if not client or client.deleted_at is not None or client.status != "active":
            raise AppError("Esta conta está desativada. Fale com a agência.", 403)
    audit(db, actor_id=user.id, action="login", entity_type="user", entity_id=user.id, ip=ip)
    commit_session(db)
    return user


def issue_session(db: Session, user: User, ip: str | None, user_agent: str | None) -> tuple[str, str]:
    raw_refresh = new_secret()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            expires_at=utcnow() + timedelta(days=settings.refresh_token_days),
            ip=ip,
            user_agent=(user_agent or "")[:300] or None,
        )
    )
    commit_session(db)
    access = create_access_token(str(user.id), user.role)
    return access, raw_refresh


def rotate_session(db: Session, raw_refresh: str, ip: str | None, user_agent: str | None) -> tuple[User, str, str]:
    if not raw_refresh:
        raise AppError("Sessão expirada.", 401)
    token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_refresh)))
    if not token:
        raise AppError("Sessão expirada.", 401)
    if token.revoked_at is not None:
        revoke_all(db, token.user_id)
        commit_session(db)
        raise AppError("Sessão encerrada por segurança. Entre novamente.", 401)
    if token.expires_at < utcnow():
        raise AppError("Sessão expirada.", 401)
    user = db.get(User, token.user_id)
    if not user or not user.is_active or user.deleted_at is not None:
        raise AppError("Sessão expirada.", 401)
    token.revoked_at = utcnow()
    access, refresh = issue_session(db, user, ip, user_agent)
    return user, access, refresh


def revoke_refresh(db: Session, raw_refresh: str | None) -> None:
    if not raw_refresh:
        return
    token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_refresh)))
    if token and token.revoked_at is None:
        token.revoked_at = utcnow()
        commit_session(db)


def revoke_all(db: Session, user_id) -> None:
    tokens = db.scalars(select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))).all()
    now = utcnow()
    for token in tokens:
        token.revoked_at = now


def user_from_access_token(db: Session, token: str) -> User:
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
    except jwt.PyJWTError as exc:
        raise AppError("Sessão expirada.", 401) from exc
    user = db.get(User, user_id)
    if not user or not user.is_active or user.deleted_at is not None:
        raise AppError("Não autenticado.", 401)
    return user


def request_password_reset(db: Session, email: str, ip: str | None) -> str | None:
    normalized = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized, User.deleted_at.is_(None), User.is_active.is_(True)))
    raw = None
    if user:
        raw = new_secret()
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(raw),
                expires_at=utcnow() + timedelta(hours=1),
            )
        )
        audit(db, actor_id=user.id, action="password_reset_requested", entity_type="user", entity_id=user.id, ip=ip)
        commit_session(db)
        logger.info("recuperação de senha solicitada para %s", normalized)
    return raw


def reset_password(db: Session, raw_token: str, new_password: str, ip: str | None) -> None:
    token = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(raw_token)))
    if not token or token.used_at is not None or token.expires_at < utcnow():
        raise AppError("Link de recuperação inválido ou expirado.", 400)
    user = db.get(User, token.user_id)
    if not user or not user.is_active or user.deleted_at is not None:
        raise AppError("Link de recuperação inválido ou expirado.", 400)
    user.password_hash = hash_password(new_password)
    user.updated_at = utcnow()
    token.used_at = utcnow()
    revoke_all(db, user.id)
    audit(db, actor_id=user.id, action="password_reset", entity_type="user", entity_id=user.id, ip=ip)
    commit_session(db)


def change_password(db: Session, user: User, current_password: str, new_password: str, ip: str | None) -> None:
    if not verify_password(current_password, user.password_hash):
        raise AppError("A senha atual não confere.", 400)
    user.password_hash = hash_password(new_password)
    user.updated_at = utcnow()
    revoke_all(db, user.id)
    audit(db, actor_id=user.id, action="password_changed", entity_type="user", entity_id=user.id, ip=ip)
    commit_session(db)


def update_profile(db: Session, user: User, full_name: str, phone: str | None, ip: str | None) -> User:
    user.full_name = full_name.strip()
    user.phone = phone.strip() if phone else None
    user.updated_at = utcnow()
    audit(db, actor_id=user.id, action="profile_updated", entity_type="user", entity_id=user.id, ip=ip)
    commit_session(db)
    return user


def me_payload(db: Session, user: User) -> dict:
    from app.services.common import unread_count
    from app.services.serializers import user_dict

    payload = user_dict(user)
    payload["unread_count"] = unread_count(db, user.id)
    if user.role == "client":
        link = db.scalar(select(ClientUser).where(ClientUser.user_id == user.id))
        client = owned_client(db, user) if link else None
        payload["client"] = (
            {"id": str(client.id), "company_name": client.company_name, "status": client.status} if client else None
        )
    else:
        payload["client"] = None
    return payload
