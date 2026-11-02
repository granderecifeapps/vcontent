import logging
import os
import uuid
from datetime import date, time

from sqlalchemy import false, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.config import settings, utcnow
from app.errors import AppError
from app.models import (
    ApprovalHistory,
    AuditLog,
    Client,
    ClientUser,
    ContentComment,
    ContentFormat,
    ContentItem,
    Notification,
    Platform,
    User,
)

logger = logging.getLogger("vcontent")

AWAITING = ("pending_approval", "resubmitted")
LOCKED = ("published", "cancelled")
IMAGE_EXT = {"jpg", "jpeg", "png", "webp"}
VIDEO_EXT = {"mp4", "mov"}


def clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def commit_session(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raw = str(getattr(exc, "orig", exc)).lower()
        if "email" in raw:
            raise AppError("Este e-mail já está em uso.", 409) from exc
        raise AppError("Não foi possível salvar por conflito de dados.", 409) from exc


def client_ip(request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    if request.client:
        return request.client.host
    return None


def audit(db: Session, *, actor_id, action: str, entity_type: str, entity_id=None, details=None, ip=None) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            details=details or {},
            ip=ip,
        )
    )


def notify(db: Session, *, user_id, type_: str, title: str, body: str, data: dict | None = None) -> Notification:
    item = Notification(
        user_id=user_id,
        type=type_,
        title=title,
        body=body,
        data=data or {},
        channels=["in_app"],
    )
    db.add(item)
    dispatch_external(item)
    return item


def dispatch_external(notification: Notification) -> None:
    """Extensão para e-mail e WhatsApp. A notificação interna já fica gravada."""
    logger.info(
        "canal externo pendente type=%s user=%s channels=%s",
        notification.type,
        notification.user_id,
        notification.channels,
    )


def admin_users(db: Session) -> list[User]:
    return list(
        db.scalars(select(User).where(User.role == "admin", User.is_active.is_(True), User.deleted_at.is_(None))).all()
    )


def client_user_ids(db: Session, client_id) -> list:
    return list(db.scalars(select(ClientUser.user_id).where(ClientUser.client_id == client_id)).all())


def linked_client_ids(db: Session, user: User) -> list:
    return list(db.scalars(select(ClientUser.client_id).where(ClientUser.user_id == user.id)).all())


def owned_client(db: Session, user: User) -> Client | None:
    link = db.scalar(select(ClientUser).where(ClientUser.user_id == user.id).options(joinedload(ClientUser.client)))
    if not link:
        return None
    return link.client


def content_loader(stmt):
    return stmt.options(
        joinedload(ContentItem.client),
        joinedload(ContentItem.platform),
        joinedload(ContentItem.format),
        joinedload(ContentItem.created_by),
        selectinload(ContentItem.media),
        selectinload(ContentItem.history).joinedload(ApprovalHistory.actor),
        selectinload(ContentItem.comments).joinedload(ContentComment.author),
    )


def visible_content_filters(db: Session, user: User) -> list:
    filters = [ContentItem.deleted_at.is_(None)]
    if user.role != "admin":
        ids = linked_client_ids(db, user)
        filters.append(ContentItem.client_id.in_(ids) if ids else false())
        filters.append(ContentItem.status != "draft")
    return filters


def get_content(db: Session, user: User, content_id) -> ContentItem:
    stmt = content_loader(select(ContentItem).where(ContentItem.id == content_id, ContentItem.deleted_at.is_(None)))
    if user.role != "admin":
        ids = linked_client_ids(db, user)
        stmt = stmt.where(ContentItem.client_id.in_(ids) if ids else false())
        stmt = stmt.where(ContentItem.status != "draft")
    item = db.scalars(stmt).unique().first()
    if not item:
        raise AppError("Conteúdo não encontrado.", 404)
    return item


def get_client_or_404(db: Session, client_id) -> Client:
    client = db.get(Client, client_id)
    if not client or client.deleted_at is not None:
        raise AppError("Cliente não encontrado.", 404)
    return client


def resolve_format(db: Session, platform_id, format_id) -> tuple[Platform, ContentFormat]:
    platform = db.get(Platform, platform_id)
    fmt = db.get(ContentFormat, format_id)
    if not platform or not platform.is_active or not fmt:
        raise AppError("Plataforma ou formato inválido.", 422)
    if fmt.platform_id != platform.id:
        raise AppError("O formato não pertence à plataforma escolhida.", 422)
    return platform, fmt


def apply_hashtags(fmt: ContentFormat, hashtags: str | None) -> str | None:
    if not fmt.allows_hashtags:
        return None
    return clean(hashtags)


def sniff_media(data: bytes, extension: str) -> str:
    ext = extension.lower()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and ext == "png":
        return "image/png"
    if data.startswith(b"\xff\xd8\xff") and ext in {"jpg", "jpeg"}:
        return "image/jpeg"
    if len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP" and ext == "webp":
        return "image/webp"
    if len(data) > 12 and data[4:8] == b"ftyp" and ext == "mp4":
        return "video/mp4"
    if len(data) > 12 and data[4:8] == b"ftyp" and ext == "mov":
        return "video/quicktime"
    raise AppError("Arquivo inválido. Use JPG, JPEG, PNG, WEBP, MP4 ou MOV.", 422)


def safe_filename(name: str | None) -> str:
    base = os.path.basename(name or "arquivo").replace("\x00", "")
    return base[:180] or "arquivo"


def extension_of(name: str | None) -> str:
    filename = safe_filename(name)
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def ensure_media_kind(fmt: ContentFormat, mime: str, existing: list) -> None:
    is_image = mime.startswith("image/")
    is_video = mime.startswith("video/")
    images = [item for item in existing if item.mime_type.startswith("image/")]
    videos = [item for item in existing if item.mime_type.startswith("video/")]
    if fmt.media_type == "single_image":
        if not is_image:
            raise AppError("Este formato aceita apenas imagem.", 422)
        if images or videos:
            raise AppError("Este formato aceita apenas uma imagem. Remova a atual para substituir.", 422)
    elif fmt.media_type == "multi_image":
        if not is_image:
            raise AppError("O carrossel aceita apenas imagens.", 422)
        if len(images) >= fmt.max_files:
            raise AppError(f"O carrossel aceita no máximo {fmt.max_files} imagens.", 422)
    elif fmt.media_type == "video":
        if not is_video:
            raise AppError("Este formato aceita apenas vídeo.", 422)
        if images or videos:
            raise AppError("Este formato aceita apenas um vídeo. Remova o atual para substituir.", 422)
    elif fmt.media_type == "image_or_video":
        if not is_image and not is_video:
            raise AppError("Stories aceita uma imagem ou um vídeo.", 422)
        if existing:
            raise AppError("Stories aceita apenas um arquivo. Remova o atual para substituir.", 422)


def assert_submittable(content: ContentItem) -> None:
    if content.client.status != "active" or content.client.deleted_at is not None:
        raise AppError("O cliente está inativo.", 409)
    if not content.title.strip():
        raise AppError("Informe o título.", 422)
    if not content.scheduled_date:
        raise AppError("Informe a data programada antes de enviar para aprovação.", 422)
    caption = (content.caption or "").strip()
    copy = (content.copy_text or "").strip()
    if content.format.slug == "stories":
        if not caption and not copy:
            raise AppError("Stories precisa de texto ou legenda.", 422)
    else:
        if not caption:
            raise AppError("Informe a legenda.", 422)
        if not copy:
            raise AppError("Informe a copy.", 422)
    media = content.active_media
    images = [item for item in media if item.mime_type.startswith("image/")]
    videos = [item for item in media if item.mime_type.startswith("video/")]
    fmt = content.format
    if fmt.media_type == "single_image" and (len(images) != 1 or videos):
        raise AppError("Este formato exige exatamente uma imagem.", 422)
    if fmt.media_type == "multi_image" and (videos or not (fmt.min_files <= len(images) <= fmt.max_files)):
        raise AppError(f"O carrossel exige de {fmt.min_files} a {fmt.max_files} imagens.", 422)
    if fmt.media_type == "video" and (len(videos) != 1 or images):
        raise AppError("Este formato exige exatamente um vídeo.", 422)
    if fmt.media_type == "image_or_video" and len(media) != 1:
        raise AppError("Stories exige uma imagem ou um vídeo.", 422)


def add_history(db: Session, content: ContentItem, action: str, actor_id, reason: str | None = None) -> None:
    from app.models import ApprovalHistory

    db.add(
        ApprovalHistory(
            content_id=content.id,
            action=action,
            actor_user_id=actor_id,
            reason=clean(reason),
            version=content.version,
            created_at=utcnow(),
        )
    )


def touch(entity) -> None:
    entity.updated_at = utcnow()


def unread_count(db: Session, user_id) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None))
        )
        or 0
    )


def parse_date(value: date | None) -> date | None:
    return value


def parse_time(value: time | None) -> time | None:
    return value


def ensure_admin(db: Session) -> None:
    email = settings.admin_email.strip().lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        return
    from app.security import hash_password

    db.add(
        User(
            email=email,
            password_hash=hash_password(settings.admin_password),
            full_name=settings.admin_name,
            role="admin",
            is_active=True,
        )
    )
    commit_session(db)
    logger.info("administradora inicial criada: %s", email)


def new_id() -> uuid.UUID:
    return uuid.uuid4()
