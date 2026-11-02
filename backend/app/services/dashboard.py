from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import ApprovalHistory, Client, ContentItem, User
from app.services.common import AWAITING, linked_client_ids
from app.services.serializers import content_dict
from app.services.common import content_loader


def admin_dashboard(db: Session) -> dict:
    alive_clients = [Client.deleted_at.is_(None), Client.status == "active"]
    alive_contents = [ContentItem.deleted_at.is_(None)]

    def contents(*statuses: str) -> int:
        filters = list(alive_contents)
        if statuses:
            filters.append(ContentItem.status.in_(statuses))
        return int(db.scalar(select(func.count()).select_from(ContentItem).where(*filters)) or 0)

    recent = db.scalars(
        content_loader(select(ContentItem).where(*alive_contents).order_by(ContentItem.created_at.desc()).limit(6))
    ).unique().all()
    approvals = db.scalars(
        select(ApprovalHistory)
        .where(ApprovalHistory.action == "approved")
        .options(joinedload(ApprovalHistory.actor), joinedload(ApprovalHistory.content))
        .order_by(ApprovalHistory.created_at.desc())
        .limit(6)
    ).unique().all()
    changes = db.scalars(
        select(ApprovalHistory)
        .where(ApprovalHistory.action == "changes_requested")
        .options(joinedload(ApprovalHistory.actor), joinedload(ApprovalHistory.content))
        .order_by(ApprovalHistory.created_at.desc())
        .limit(6)
    ).unique().all()
    pending_clients = db.execute(
        select(Client.id, Client.company_name, func.count(ContentItem.id))
        .join(ContentItem, ContentItem.client_id == Client.id)
        .where(
            Client.deleted_at.is_(None),
            ContentItem.deleted_at.is_(None),
            ContentItem.status.in_(AWAITING),
        )
        .group_by(Client.id, Client.company_name)
        .order_by(func.count(ContentItem.id).desc())
        .limit(6)
    ).all()
    return {
        "role": "admin",
        "active_clients": int(db.scalar(select(func.count()).select_from(Client).where(*alive_clients)) or 0),
        "total_contents": contents(),
        "pending": contents(*AWAITING),
        "approved": contents("approved"),
        "changes_requested": contents("changes_requested", "in_review"),
        "in_progress": contents("in_progress"),
        "scheduled": int(
            db.scalar(
                select(func.count())
                .select_from(ContentItem)
                .where(
                    *alive_contents,
                    ContentItem.scheduled_date.is_not(None),
                    ContentItem.status.in_(("pending_approval", "approved", "changes_requested", "in_review", "resubmitted", "in_progress")),
                )
            )
            or 0
        ),
        "published": contents("published"),
        "recent_contents": [content_dict(item, admin=True) for item in recent],
        "recent_approvals": [_event(item) for item in approvals],
        "recent_changes": [_event(item) for item in changes],
        "clients_with_pending": [
            {"id": str(row[0]), "company_name": row[1], "pending": int(row[2])} for row in pending_clients
        ],
    }


def client_dashboard(db: Session, user: User) -> dict:
    ids = linked_client_ids(db, user)
    base = [ContentItem.deleted_at.is_(None), ContentItem.client_id.in_(ids) if ids else ContentItem.id.is_(None)]

    def count(*statuses: str) -> int:
        return int(
            db.scalar(select(func.count()).select_from(ContentItem).where(*base, ContentItem.status.in_(statuses))) or 0
        )

    today = date.today()
    upcoming = db.scalars(
        content_loader(
            select(ContentItem)
            .where(
                *base,
                ContentItem.scheduled_date.is_not(None),
                ContentItem.scheduled_date >= today,
                ContentItem.status.in_(("pending_approval", "resubmitted", "approved", "changes_requested", "in_review", "in_progress")),
            )
            .order_by(ContentItem.scheduled_date.asc(), ContentItem.scheduled_time.asc().nulls_last())
            .limit(5)
        )
    ).unique().all()
    return {
        "role": "client",
        "pending": count(*AWAITING),
        "approved": count("approved", "published"),
        "changes_requested": count("changes_requested", "in_review"),
        "in_progress": count("in_progress"),
        "upcoming": [content_dict(item, admin=False) for item in upcoming],
    }


def _event(item: ApprovalHistory) -> dict:
    content = item.content
    return {
        "id": str(item.id),
        "action": item.action,
        "reason": item.reason,
        "actor_name": item.actor.full_name if item.actor else "Sistema",
        "content_id": str(item.content_id),
        "content_title": content.title if content and content.deleted_at is None else "Conteúdo removido",
        "client_name": content.client.company_name if content and content.client else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }
