from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.config import settings, utcnow
from app.errors import AppError
from app.models import ApprovalHistory, ContentComment, ContentItem, ContentMedia, User
from app.services.common import (
    AWAITING,
    LOCKED,
    add_history,
    admin_users,
    apply_hashtags,
    assert_submittable,
    audit,
    clean,
    client_user_ids,
    commit_session,
    linked_client_ids,
    content_loader,
    ensure_media_kind,
    extension_of,
    get_client_or_404,
    get_content,
    notify,
    resolve_format,
    safe_filename,
    sniff_media,
    touch,
    visible_content_filters,
)
from app.services.serializers import content_dict, history_dict
from app.storage import get_storage, new_key

FACING = {"title", "scheduled_date", "scheduled_time", "caption", "copy_text", "hashtags", "platform_id", "format_id", "client_id"}


def _reload(db: Session, user: User, content_id) -> dict:
    db.expire_all()
    content = get_content(db, user, content_id)
    return content_dict(content, admin=user.role == "admin")


def _guard_locked(content: ContentItem, facing_changed: bool) -> None:
    if facing_changed and content.status in LOCKED:
        raise AppError("Conteúdo publicado ou cancelado não pode ter o material alterado.", 409)


def _open_review(db: Session, content: ContentItem, actor_id) -> None:
    if content.status in ("pending_approval", "resubmitted", "approved", "changes_requested"):
        content.status = "in_review"
        add_history(db, content, "review_started", actor_id)


def _fit_current_media(content: ContentItem) -> None:
    media = content.active_media
    if not media:
        return
    fmt = content.format
    images = [item for item in media if item.mime_type.startswith("image/")]
    videos = [item for item in media if item.mime_type.startswith("video/")]
    if fmt.media_type in {"single_image", "multi_image"} and videos:
        raise AppError("Remova os vídeos antes de usar um formato de imagem.", 422)
    if fmt.media_type == "video" and images:
        raise AppError("Remova as imagens antes de usar um formato de vídeo.", 422)
    if fmt.media_type == "single_image" and len(media) > 1:
        raise AppError("Remova as imagens extras antes de usar foto única.", 422)
    if fmt.media_type == "video" and len(videos) > 1:
        raise AppError("Este formato aceita apenas um vídeo.", 422)
    if fmt.media_type == "image_or_video" and len(media) > 1:
        raise AppError("Stories aceita apenas um arquivo. Remova os extras antes de trocar o formato.", 422)


def _notify_clients(db: Session, content: ContentItem, type_: str, title: str, body: str) -> None:
    for user_id in client_user_ids(db, content.client_id):
        user = db.get(User, user_id)
        if user and user.is_active and user.deleted_at is None:
            notify(db, user_id=user.id, type_=type_, title=title, body=body, data={"content_id": str(content.id)})


def _notify_admins(db: Session, content: ContentItem, type_: str, title: str, body: str) -> None:
    for admin in admin_users(db):
        notify(
            db,
            user_id=admin.id,
            type_=type_,
            title=title,
            body=body,
            data={"content_id": str(content.id), "client_id": str(content.client_id)},
        )


def create_content(db: Session, actor: User, data, ip: str | None) -> dict:
    client = get_client_or_404(db, data.client_id)
    _platform, fmt = resolve_format(db, data.platform_id, data.format_id)
    title = data.title.strip()
    if not title:
        raise AppError("Informe o título.", 422)
    content = ContentItem(
        client_id=client.id,
        platform_id=data.platform_id,
        format_id=data.format_id,
        title=title,
        internal_description=clean(data.internal_description),
        scheduled_date=data.scheduled_date,
        scheduled_time=data.scheduled_time,
        caption=clean(data.caption),
        copy_text=clean(data.copy_text),
        hashtags=apply_hashtags(fmt, data.hashtags),
        waiting_note=clean(data.waiting_note),
        internal_notes=clean(data.internal_notes),
        status="draft",
        version=1,
        created_by_id=actor.id,
    )
    db.add(content)
    db.flush()
    add_history(db, content, "created", actor.id)
    audit(db, actor_id=actor.id, action="content_created", entity_type="content", entity_id=content.id, details={"title": title}, ip=ip)
    commit_session(db)
    return _reload(db, actor, content.id)


def update_content(db: Session, actor: User, content_id, data, ip: str | None) -> dict:
    content = get_content(db, actor, content_id)
    fields = data.model_dump(exclude_unset=True)
    facing_changed = False
    if "client_id" in fields and fields["client_id"] and fields["client_id"] != content.client_id:
        content.client = get_client_or_404(db, fields["client_id"])
        content.client_id = content.client.id
        facing_changed = True
    if "platform_id" in fields or "format_id" in fields:
        platform_id = fields.get("platform_id") or content.platform_id
        format_id = fields.get("format_id") or content.format_id
        platform, fmt = resolve_format(db, platform_id, format_id)
        if platform.id != content.platform_id or fmt.id != content.format_id:
            facing_changed = True
        content.platform = platform
        content.format = fmt
        content.platform_id = platform.id
        content.format_id = fmt.id
    if "hashtags" in fields or "format_id" in fields or "platform_id" in fields:
        incoming = fields["hashtags"] if "hashtags" in fields else content.hashtags
        updated = apply_hashtags(content.format, incoming)
        if updated != content.hashtags:
            facing_changed = True
        content.hashtags = updated
    for field in ("title", "internal_description", "scheduled_date", "scheduled_time", "caption", "copy_text", "waiting_note", "internal_notes"):
        if field not in fields:
            continue
        value = fields[field]
        if isinstance(value, str):
            value = value.strip()
            if field == "title" and not value:
                raise AppError("Informe o título.", 422)
            if field != "title":
                value = value or None
        if field in FACING and getattr(content, field) != value:
            facing_changed = True
        setattr(content, field, value)
    _guard_locked(content, facing_changed)
    _fit_current_media(content)
    if facing_changed:
        _open_review(db, content, actor.id)
    touch(content)
    audit(db, actor_id=actor.id, action="content_updated", entity_type="content", entity_id=content.id, ip=ip)
    commit_session(db)
    return _reload(db, actor, content.id)


def delete_content(db: Session, actor: User, content_id, ip: str | None) -> None:
    content = get_content(db, actor, content_id)
    content.deleted_at = utcnow()
    touch(content)
    add_history(db, content, "deleted", actor.id)
    audit(db, actor_id=actor.id, action="content_deleted", entity_type="content", entity_id=content.id, ip=ip)
    commit_session(db)


def list_contents(db: Session, user: User, *, q, status, client_id, platform_id, page: int, page_size: int) -> dict:
    filters = visible_content_filters(db, user)
    if status:
        wanted = [item.strip() for item in status.split(",") if item.strip()]
        filters.append(ContentItem.status.in_(wanted))
    if client_id:
        filters.append(ContentItem.client_id == client_id)
    if platform_id:
        filters.append(ContentItem.platform_id == platform_id)
    if q:
        term = f"%{q.strip()}%"
        filters.append(or_(ContentItem.title.ilike(term), ContentItem.caption.ilike(term), ContentItem.copy_text.ilike(term)))
    total = int(db.scalar(select(func.count()).select_from(ContentItem).where(*filters)) or 0)
    rows = db.scalars(
        content_loader(
            select(ContentItem)
            .where(*filters)
            .order_by(ContentItem.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).unique().all()
    return {
        "items": [content_dict(row, admin=user.role == "admin") for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def add_media(db: Session, actor: User, content_id, filename: str, data: bytes, ip: str | None) -> dict:
    if not data:
        raise AppError("Arquivo vazio.", 422)
    content = get_content(db, actor, content_id)
    if content.status in LOCKED:
        raise AppError("Não é possível alterar a mídia deste conteúdo.", 409)
    ext = extension_of(filename)
    mime = sniff_media(data, ext)
    limit_mb = settings.max_video_mb if mime.startswith("video/") else settings.max_image_mb
    if len(data) > limit_mb * 1024 * 1024:
        raise AppError(f"O arquivo excede o limite de {limit_mb} MB.", 413)
    ensure_media_kind(content.format, mime, content.active_media)
    key = new_key(f"contents/{content.id}", ext)
    storage = get_storage()
    stored = storage.upload(key, data, mime)
    order = max((item.sort_order for item in content.active_media), default=-1) + 1
    media = ContentMedia(
        content_id=content.id,
        storage_key=stored,
        original_filename=safe_filename(filename),
        mime_type=mime,
        size_bytes=len(data),
        sort_order=order,
    )
    db.add(media)
    db.flush()
    _open_review(db, content, actor.id)
    touch(content)
    audit(db, actor_id=actor.id, action="media_uploaded", entity_type="content", entity_id=content.id, details={"filename": media.original_filename}, ip=ip)
    try:
        commit_session(db)
    except Exception:
        storage.delete(stored)
        raise
    return _reload(db, actor, content.id)


def remove_media(db: Session, actor: User, content_id, media_id, ip: str | None) -> dict:
    content = get_content(db, actor, content_id)
    if content.status in LOCKED:
        raise AppError("Não é possível alterar a mídia deste conteúdo.", 409)
    media = next((item for item in content.active_media if item.id == media_id), None)
    if not media:
        raise AppError("Arquivo não encontrado.", 404)
    media.deleted_at = utcnow()
    _open_review(db, content, actor.id)
    touch(content)
    audit(db, actor_id=actor.id, action="media_removed", entity_type="content", entity_id=content.id, ip=ip)
    commit_session(db)
    try:
        get_storage().delete(media.storage_key)
    except Exception:
        pass
    return _reload(db, actor, content.id)


def order_media(db: Session, actor: User, content_id, ids: list, ip: str | None) -> dict:
    content = get_content(db, actor, content_id)
    if content.status in LOCKED:
        raise AppError("Não é possível alterar a mídia deste conteúdo.", 409)
    current = {item.id: item for item in content.active_media}
    if set(ids) != set(current) or len(ids) != len(current):
        raise AppError("A ordem precisa incluir exatamente os arquivos atuais.", 422)
    changed = any(current[media_id].sort_order != index for index, media_id in enumerate(ids))
    for index, media_id in enumerate(ids):
        current[media_id].sort_order = index
    if changed:
        _open_review(db, content, actor.id)
    touch(content)
    audit(db, actor_id=actor.id, action="media_reordered", entity_type="content", entity_id=content.id, ip=ip)
    commit_session(db)
    return _reload(db, actor, content.id)


def hold_content(db: Session, actor: User, content_id, note: str, ip: str | None) -> dict:
    content = get_content(db, actor, content_id)
    if content.status not in {"draft", "in_progress"}:
        raise AppError("Só um rascunho pode ficar em andamento.", 409)
    text = clean(note)
    if not text or len(text) < 3:
        raise AppError("Descreva o que está aguardando do cliente.", 422)
    first = content.status != "in_progress"
    content.waiting_note = text
    content.status = "in_progress"
    touch(content)
    add_history(db, content, "held" if first else "waiting_updated", actor.id, text)
    _notify_clients(
        db,
        content,
        "content_waiting",
        "Publicação em andamento",
        f"{content.title}: {text}",
    )
    audit(db, actor_id=actor.id, action="content_held", entity_type="content", entity_id=content.id, details={"note": text}, ip=ip)
    commit_session(db)
    return _reload(db, actor, content.id)


def submit_content(db: Session, actor: User, content_id, ip: str | None) -> dict:
    content = get_content(db, actor, content_id)
    if content.status not in {"draft", "in_progress"}:
        raise AppError("Apenas rascunhos ou conteúdos em andamento podem ser enviados. Para uma nova rodada, use reenviar.", 409)
    assert_submittable(content)
    content.status = "pending_approval"
    touch(content)
    add_history(db, content, "submitted", actor.id)
    _notify_clients(
        db,
        content,
        "content_submitted",
        "Novo conteúdo para aprovar",
        f"{content.client.company_name}: {content.title} está aguardando a sua aprovação.",
    )
    audit(db, actor_id=actor.id, action="content_submitted", entity_type="content", entity_id=content.id, ip=ip)
    commit_session(db)
    return _reload(db, actor, content.id)


def resubmit_content(db: Session, actor: User, content_id, ip: str | None) -> dict:
    content = get_content(db, actor, content_id)
    if content.status not in {"in_review", "changes_requested"}:
        raise AppError("Este conteúdo não está pronto para ser reenviado.", 409)
    assert_submittable(content)
    content.version += 1
    content.status = "resubmitted"
    touch(content)
    add_history(db, content, "resubmitted", actor.id)
    _notify_clients(
        db,
        content,
        "content_resubmitted",
        "Conteúdo ajustado para nova aprovação",
        f"{content.title} foi atualizado e voltou para a sua aprovação.",
    )
    audit(db, actor_id=actor.id, action="content_resubmitted", entity_type="content", entity_id=content.id, ip=ip)
    commit_session(db)
    return _reload(db, actor, content.id)


def start_review(db: Session, actor: User, content_id, ip: str | None) -> dict:
    content = get_content(db, actor, content_id)
    if content.status != "changes_requested":
        raise AppError("Só é possível iniciar a revisão quando há ajustes solicitados.", 409)
    content.status = "in_review"
    touch(content)
    add_history(db, content, "review_started", actor.id)
    audit(db, actor_id=actor.id, action="review_started", entity_type="content", entity_id=content.id, ip=ip)
    commit_session(db)
    return _reload(db, actor, content.id)


def publish_content(db: Session, actor: User, content_id, ip: str | None) -> dict:
    content = get_content(db, actor, content_id)
    if content.status != "approved":
        raise AppError("Somente conteúdos aprovados podem ser marcados como publicados.", 409)
    content.status = "published"
    content.published_at = utcnow()
    touch(content)
    add_history(db, content, "published", actor.id)
    audit(db, actor_id=actor.id, action="content_published", entity_type="content", entity_id=content.id, ip=ip)
    commit_session(db)
    return _reload(db, actor, content.id)


def cancel_content(db: Session, actor: User, content_id, ip: str | None) -> dict:
    content = get_content(db, actor, content_id)
    if content.status == "cancelled":
        raise AppError("O conteúdo já está cancelado.", 409)
    content.status = "cancelled"
    touch(content)
    add_history(db, content, "cancelled", actor.id)
    audit(db, actor_id=actor.id, action="content_cancelled", entity_type="content", entity_id=content.id, ip=ip)
    commit_session(db)
    return _reload(db, actor, content.id)


def approve_content(db: Session, actor: User, content_id, ip: str | None) -> dict:
    if actor.role != "client":
        raise AppError("A aprovação é feita na área do cliente.", 403)
    content = get_content(db, actor, content_id)
    if content.status not in AWAITING:
        raise AppError("Este conteúdo não está aguardando aprovação.", 409)
    content.status = "approved"
    touch(content)
    add_history(db, content, "approved", actor.id)
    _notify_admins(
        db,
        content,
        "content_approved",
        "Conteúdo aprovado",
        f"{actor.full_name} aprovou {content.title}.",
    )
    db.flush()
    remaining = int(
        db.scalar(
            select(func.count())
            .select_from(ContentItem)
            .where(
                ContentItem.client_id == content.client_id,
                ContentItem.deleted_at.is_(None),
                ContentItem.status.in_(AWAITING),
            )
        )
        or 0
    )
    if remaining == 0:
        _notify_admins(
            db,
            content,
            "review_completed",
            "Fila de aprovação concluída",
            f"{content.client.company_name} não tem mais conteúdos aguardando aprovação.",
        )
    audit(db, actor_id=actor.id, action="content_approved", entity_type="content", entity_id=content.id, ip=ip)
    commit_session(db)
    return _reload(db, actor, content.id)


def request_changes(db: Session, actor: User, content_id, reason: str, ip: str | None) -> dict:
    if actor.role != "client":
        raise AppError("A solicitação de ajustes é feita na área do cliente.", 403)
    text = clean(reason) or ""
    if len(text) < 3:
        raise AppError("Informe o motivo dos ajustes.", 422)
    content = get_content(db, actor, content_id)
    if content.status not in AWAITING:
        raise AppError("Este conteúdo não está aguardando aprovação.", 409)
    content.status = "changes_requested"
    touch(content)
    add_history(db, content, "changes_requested", actor.id, text)
    db.add(ContentComment(content_id=content.id, author_id=actor.id, body=text))
    _notify_admins(
        db,
        content,
        "changes_requested",
        "Ajustes solicitados",
        f"{actor.full_name} pediu ajustes em {content.title}.",
    )
    audit(db, actor_id=actor.id, action="changes_requested", entity_type="content", entity_id=content.id, details={"reason": text}, ip=ip)
    commit_session(db)
    return _reload(db, actor, content.id)


def content_history(db: Session, user: User, content_id) -> list[dict]:
    content = get_content(db, user, content_id)
    events = [history_dict(item, content) for item in content.history]
    events.sort(key=lambda item: item["created_at"] or "")
    return events


def activity(db: Session, user: User, page: int, page_size: int, client_id=None) -> dict:
    filters = [ContentItem.deleted_at.is_(None)]
    if user.role != "admin":
        ids = linked_client_ids(db, user)
        if not ids or (client_id and client_id not in ids):
            return {"items": [], "total": 0, "page": page, "page_size": page_size}
        filters.append(ContentItem.client_id.in_(ids))
        filters.append(ContentItem.status != "draft")
    if client_id:
        filters.append(ContentItem.client_id == client_id)
    joined = select(ApprovalHistory).join(ContentItem, ApprovalHistory.content_id == ContentItem.id).where(*filters)
    total = int(db.scalar(select(func.count()).select_from(joined.order_by(None).subquery())) or 0)
    rows = db.scalars(
        joined.options(joinedload(ApprovalHistory.actor), joinedload(ApprovalHistory.content))
        .order_by(ApprovalHistory.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).unique().all()
    return {
        "items": [history_dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def calendar_items(db: Session, user: User, start: date, end: date, client_id, platform_id) -> list[dict]:
    filters = visible_content_filters(db, user)
    filters.append(ContentItem.scheduled_date.is_not(None))
    filters.append(ContentItem.scheduled_date >= start)
    filters.append(ContentItem.scheduled_date <= end)
    filters.append(ContentItem.status != "cancelled")
    if client_id:
        filters.append(ContentItem.client_id == client_id)
    if platform_id:
        filters.append(ContentItem.platform_id == platform_id)
    rows = db.scalars(
        content_loader(select(ContentItem).where(*filters).order_by(ContentItem.scheduled_date.asc(), ContentItem.scheduled_time.asc().nulls_last()))
    ).unique().all()
    return [content_dict(row, admin=user.role == "admin") for row in rows]


def approval_queue(db: Session, user: User) -> list[dict]:
    filters = visible_content_filters(db, user)
    filters.append(ContentItem.status.in_(AWAITING))
    rows = db.scalars(
        content_loader(
            select(ContentItem)
            .where(*filters)
            .order_by(ContentItem.scheduled_date.asc().nulls_last(), ContentItem.created_at.asc())
        )
    ).unique().all()
    return [content_dict(row, admin=user.role == "admin") for row in rows]
