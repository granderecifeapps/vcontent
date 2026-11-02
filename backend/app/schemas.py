import uuid
from datetime import date, time
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if "@" not in email or any(char.isspace() for char in email):
        raise ValueError("E-mail inválido.")
    local, domain = email.rsplit("@", 1)
    if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise ValueError("E-mail inválido.")
    return email


EmailAddress = Annotated[str, Field(max_length=255), AfterValidator(normalize_email)]


class LoginIn(BaseModel):
    email: EmailAddress
    password: str = Field(min_length=1, max_length=128)


class ForgotIn(BaseModel):
    email: EmailAddress


class ResetIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    new_password: str = Field(min_length=8, max_length=128)


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class ProfileIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=40)


class ClientCreate(BaseModel):
    company_name: str = Field(min_length=2, max_length=160)
    contact_name: str = Field(min_length=2, max_length=160)
    email: EmailAddress
    phone: str | None = Field(default=None, max_length=40)
    description: str | None = None
    internal_notes: str | None = None
    status: str = "active"
    access_email: EmailAddress
    access_name: str = Field(min_length=2, max_length=160)
    access_password: str = Field(min_length=8, max_length=128)


class ClientUpdate(BaseModel):
    company_name: str | None = Field(default=None, min_length=2, max_length=160)
    contact_name: str | None = Field(default=None, min_length=2, max_length=160)
    email: EmailAddress | None = None
    phone: str | None = Field(default=None, max_length=40)
    description: str | None = None
    internal_notes: str | None = None
    status: str | None = None
    access_email: EmailAddress | None = None
    access_name: str | None = Field(default=None, min_length=2, max_length=160)
    access_password: str | None = Field(default=None, min_length=8, max_length=128)
    access_active: bool | None = None


class ContentWrite(BaseModel):
    client_id: uuid.UUID
    platform_id: uuid.UUID
    format_id: uuid.UUID
    title: str = Field(min_length=1, max_length=180)
    internal_description: str | None = None
    scheduled_date: date | None = None
    scheduled_time: time | None = None
    caption: str | None = None
    copy_text: str | None = None
    hashtags: str | None = None
    waiting_note: str | None = None
    internal_notes: str | None = None


class ContentUpdate(BaseModel):
    client_id: uuid.UUID | None = None
    platform_id: uuid.UUID | None = None
    format_id: uuid.UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=180)
    internal_description: str | None = None
    scheduled_date: date | None = None
    scheduled_time: time | None = None
    caption: str | None = None
    copy_text: str | None = None
    hashtags: str | None = None
    waiting_note: str | None = None
    internal_notes: str | None = None


class HoldIn(BaseModel):
    waiting_note: str = Field(min_length=3, max_length=2000)


class ChangesIn(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class MediaOrderIn(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1)
