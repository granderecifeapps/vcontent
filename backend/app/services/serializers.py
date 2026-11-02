import logging

from app.config import utcnow
from app.models import ContentItem, ContentMedia
from app.storage import get_storage

logger = logging.getLogger("vcontent.serializers")


def iso(value) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def user_dict(user) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "phone": user.phone,
        "is_active": user.is_active,
    }


def media_dict(media: ContentMedia) -> dict:
    url = None
    try:
        url = get_storage().presign(media.storage_key)
    except Exception:
        logger.exception("falha ao gerar url da mídia %s", media.id)
    return {
        "id": str(media.id),
        "url": url,
        "filename": media.original_filename,
        "mime_type": media.mime_type,
        "size_bytes": media.size_bytes,
        "sort_order": media.sort_order,
        "created_at": iso(media.created_at),
    }


def latest_reason(content: ContentItem) -> str | None:
    reasoned = [item for item in content.history if item.reason and item.action == "changes_requested"]
    if not reasoned:
        return None
    latest = max(reasoned, key=lambda item: item.created_at or utcnow())
    return latest.reason


def content_dict(content: ContentItem, *, admin: bool) -> dict:
    payload = {
        "id": str(content.id),
        "client_id": str(content.client_id),
        "client_name": content.client.company_name if content.client else None,
        "platform": {
            "id": str(content.platform.id),
            "slug": content.platform.slug,
            "name": content.platform.name,
        },
        "format": {
            "id": str(content.format.id),
            "slug": content.format.slug,
            "name": content.format.name,
            "media_type": content.format.media_type,
            "allows_hashtags": content.format.allows_hashtags,
            "min_files": content.format.min_files,
            "max_files": content.format.max_files,
        },
        "title": content.title,
        "scheduled_date": iso(content.scheduled_date),
        "scheduled_time": content.scheduled_time.strftime("%H:%M") if content.scheduled_time else None,
        "caption": content.caption,
        "copy_text": content.copy_text,
        "hashtags": content.hashtags,
        "waiting_note": content.waiting_note,
        "status": content.status,
        "version": content.version,
        "latest_reason": latest_reason(content),
        "media": [media_dict(item) for item in content.active_media],
        "created_by_name": content.created_by.full_name if content.created_by else None,
        "published_at": iso(content.published_at),
        "created_at": iso(content.created_at),
        "updated_at": iso(content.updated_at),
    }
    if admin:
        payload["internal_description"] = content.internal_description
        payload["internal_notes"] = content.internal_notes
    return payload


def contract_payload(client, *, file_path: str | None = None) -> dict | None:
    if not client.contract_key:
        return None
    return {
        "filename": client.contract_filename,
        "url": file_path or f"/api/clients/{client.id}/contract/file",
        "uploaded_at": iso(client.contract_uploaded_at),
    }


def client_dict(client, access=None, *, admin: bool = True) -> dict:
    logo_url = None
    if client.logo_key:
        try:
            logo_url = get_storage().presign(client.logo_key)
        except Exception:
            logger.exception("falha ao gerar url do logo %s", client.id)
    payload = {
        "id": str(client.id),
        "company_name": client.company_name,
        "contact_name": client.contact_name,
        "email": client.email,
        "phone": client.phone,
        "logo_url": logo_url,
        "description": client.description,
        "status": client.status,
        "created_at": iso(client.created_at),
        "updated_at": iso(client.updated_at),
    }
    if admin:
        payload["internal_notes"] = client.internal_notes
        payload["access"] = access
        payload["contract"] = contract_payload(client)
    return payload


def history_dict(event, content: ContentItem | None = None) -> dict:
    return {
        "id": str(event.id),
        "kind": "approval",
        "content_id": str(event.content_id),
        "content_title": content.title if content else (event.content.title if getattr(event, "content", None) else None),
        "action": event.action,
        "reason": event.reason,
        "actor_name": event.actor.full_name if event.actor else "Sistema",
        "version": event.version,
        "created_at": iso(event.created_at),
    }
