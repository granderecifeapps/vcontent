import hashlib
import secrets
from datetime import timedelta

import bcrypt
import jwt

from app.config import settings, utcnow


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_secret() -> str:
    return secrets.token_urlsafe(48)


def create_access_token(user_id: str, role: str) -> str:
    now = utcnow()
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def create_file_token(file_id: str, hours: int = 6) -> str:
    now = utcnow()
    payload = {"fid": file_id, "type": "file", "iat": int(now.timestamp()), "exp": int((now + timedelta(hours=hours)).timestamp())}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_file_token(token: str) -> dict:
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    if payload.get("type") != "file" or not payload.get("fid"):
        raise jwt.InvalidTokenError("tipo inválido")
    return payload


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("tipo inválido")
    return payload
