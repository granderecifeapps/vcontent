from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.config import utcnow
from app.errors import AppError
from app.models import Client, ClientUser, ContentItem, User
from app.security import hash_password
from app.services.auth import revoke_all
from app.services.common import audit, clean, client_user_ids, commit_session, extension_of, get_client_or_404, linked_client_ids, notify, sniff_media, touch
from app.services.serializers import client_dict, contract_payload
from app.storage import get_storage, new_key


def access_payload(db: Session, client: Client) -> dict | None:
    link = db.scalar(select(ClientUser).where(ClientUser.client_id == client.id).options(joinedload(ClientUser.user)))
    if not link or not link.user:
        return None
    user = link.user
    return {
        "user_id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
    }


def create_client(db: Session, actor: User, data, ip: str | None) -> Client:
    if data.status not in {"active", "inactive"}:
        raise AppError("Status inválido.", 422)
    client = Client(
        company_name=data.company_name.strip(),
        contact_name=data.contact_name.strip(),
        email=data.email.strip().lower(),
        phone=clean(data.phone),
        description=clean(data.description),
        internal_notes=clean(data.internal_notes),
        status=data.status,
    )
    db.add(client)
    db.flush()
    user = User(
        email=data.access_email.strip().lower(),
        password_hash=hash_password(data.access_password),
        full_name=data.access_name.strip(),
        role="client",
        phone=clean(data.phone),
        is_active=data.status == "active",
    )
    db.add(user)
    db.flush()
    db.add(ClientUser(client_id=client.id, user_id=user.id))
    audit(db, actor_id=actor.id, action="client_created", entity_type="client", entity_id=client.id, details={"company": client.company_name}, ip=ip)
    commit_session(db)
    return client


def update_client(db: Session, actor: User, client_id, data, ip: str | None) -> Client:
    client = get_client_or_404(db, client_id)
    fields = data.model_dump(exclude_unset=True)
    if "status" in fields and fields["status"] not in {"active", "inactive"}:
        raise AppError("Status inválido.", 422)
    for key in ("company_name", "contact_name"):
        if key in fields and fields[key] is not None:
            setattr(client, key, fields[key].strip())
    if "email" in fields and fields["email"] is not None:
        client.email = str(fields["email"]).strip().lower()
    if "phone" in fields:
        client.phone = clean(fields["phone"])
    if "description" in fields:
        client.description = clean(fields["description"])
    if "internal_notes" in fields:
        client.internal_notes = clean(fields["internal_notes"])
    if "status" in fields and fields["status"]:
        client.status = fields["status"]
    link = db.scalar(select(ClientUser).where(ClientUser.client_id == client.id).options(joinedload(ClientUser.user)))
    if link and link.user:
        user = link.user
        if fields.get("access_email"):
            user.email = str(fields["access_email"]).strip().lower()
        if fields.get("access_name"):
            user.full_name = fields["access_name"].strip()
        if fields.get("access_password"):
            user.password_hash = hash_password(fields["access_password"])
            revoke_all(db, user.id)
        if client.status != "active":
            user.is_active = False
        elif "access_active" in fields and fields["access_active"] is not None:
            user.is_active = bool(fields["access_active"])
        elif "status" in fields and fields["status"] == "active":
            user.is_active = True
        user.updated_at = client.updated_at
    touch(client)
    audit(db, actor_id=actor.id, action="client_updated", entity_type="client", entity_id=client.id, ip=ip)
    commit_session(db)
    return client


def delete_client(db: Session, actor: User, client_id, ip: str | None) -> None:
    client = get_client_or_404(db, client_id)
    client.deleted_at = client.updated_at
    touch(client)
    client.deleted_at = client.updated_at
    client.status = "inactive"
    link = db.scalar(select(ClientUser).where(ClientUser.client_id == client.id))
    if link:
        user = db.get(User, link.user_id)
        if user:
            user.is_active = False
            user.updated_at = client.updated_at
            revoke_all(db, user.id)
    audit(
        db,
        actor_id=actor.id,
        action="client_deleted",
        entity_type="client",
        entity_id=client.id,
        details={"mode": "soft"},
        ip=ip,
    )
    commit_session(db)


def list_clients(db: Session, *, q: str | None, status: str | None, page: int, page_size: int) -> dict:
    filters = [Client.deleted_at.is_(None)]
    if status in {"active", "inactive"}:
        filters.append(Client.status == status)
    if q:
        term = f"%{q.strip()}%"
        filters.append(
            Client.company_name.ilike(term) | Client.contact_name.ilike(term) | Client.email.ilike(term)
        )
    total = int(db.scalar(select(func.count()).select_from(Client).where(*filters)) or 0)
    rows = db.scalars(
        select(Client).where(*filters).order_by(Client.company_name.asc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [client_dict(row, access_payload(db, row)) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def client_detail(db: Session, client_id) -> dict:
    client = get_client_or_404(db, client_id)
    counts = dict(
        db.execute(
            select(ContentItem.status, func.count())
            .where(ContentItem.client_id == client.id, ContentItem.deleted_at.is_(None))
            .group_by(ContentItem.status)
        ).all()
    )
    payload = client_dict(client, access_payload(db, client))
    payload["stats"] = {key: int(value) for key, value in counts.items()}
    payload["content_total"] = sum(payload["stats"].values())
    return payload


def save_logo(db: Session, actor: User, client_id, filename: str, data: bytes, ip: str | None) -> dict:
    if len(data) > 5 * 1024 * 1024:
        raise AppError("O logotipo pode ter no máximo 5 MB.", 413)
    ext = extension_of(filename)
    mime = sniff_media(data, ext)
    if not mime.startswith("image/"):
        raise AppError("O logotipo precisa ser uma imagem.", 422)
    client = get_client_or_404(db, client_id)
    key = new_key(f"clients/{client.id}", ext)
    storage = get_storage()
    stored = storage.upload(key, data, mime)
    previous = client.logo_key
    client.logo_key = stored
    touch(client)
    audit(db, actor_id=actor.id, action="client_logo_updated", entity_type="client", entity_id=client.id, ip=ip)
    try:
        commit_session(db)
    except Exception:
        storage.delete(stored)
        raise
    if previous:
        try:
            storage.delete(previous)
        except Exception:
            pass
    return client_dict(client, access_payload(db, client))


def remove_logo(db: Session, actor: User, client_id, ip: str | None) -> dict:
    client = get_client_or_404(db, client_id)
    previous = client.logo_key
    client.logo_key = None
    touch(client)
    audit(db, actor_id=actor.id, action="client_logo_removed", entity_type="client", entity_id=client.id, ip=ip)
    commit_session(db)
    if previous:
        try:
            get_storage().delete(previous)
        except Exception:
            pass
    return client_dict(client, access_payload(db, client))


def _pdf(filename: str, data: bytes) -> None:
    if len(data) > 20 * 1024 * 1024:
        raise AppError("O contrato pode ter no máximo 20 MB.", 413)
    if extension_of(filename) != "pdf" or not data.startswith(b"%PDF-"):
        raise AppError("Envie um arquivo PDF.", 422)


def _contract_name(name: str | None) -> str:
    base = (name or "contrato.pdf").replace("\\", "/").split("/")[-1].replace("\x00", "")
    return base[:180] or "contrato.pdf"


def save_contract(db: Session, actor: User, client_id, filename: str, data: bytes, ip: str | None) -> dict:
    _pdf(filename, data)
    client = get_client_or_404(db, client_id)
    key = new_key(f"clients/{client.id}/contract", "pdf")
    storage = get_storage()
    stored = storage.upload(key, data, "application/pdf")
    previous = client.contract_key
    client.contract_key = stored
    client.contract_filename = _contract_name(filename)
    client.contract_uploaded_at = utcnow()
    touch(client)
    for user_id in client_user_ids(db, client.id):
        user = db.get(User, user_id)
        if user and user.is_active and user.deleted_at is None:
            notify(
                db,
                user_id=user.id,
                type_="contract_available",
                title="Contrato disponível",
                body=f"O contrato de {client.company_name} está disponível para leitura.",
                data={"client_id": str(client.id)},
            )
    audit(db, actor_id=actor.id, action="client_contract_updated", entity_type="client", entity_id=client.id, ip=ip)
    try:
        commit_session(db)
    except Exception:
        storage.delete(stored)
        raise
    if previous:
        try:
            storage.delete(previous)
        except Exception:
            pass
    return client_dict(client, access_payload(db, client))


def remove_contract(db: Session, actor: User, client_id, ip: str | None) -> dict:
    client = get_client_or_404(db, client_id)
    previous = client.contract_key
    client.contract_key = None
    client.contract_filename = None
    client.contract_uploaded_at = None
    touch(client)
    audit(db, actor_id=actor.id, action="client_contract_removed", entity_type="client", entity_id=client.id, ip=ip)
    commit_session(db)
    if previous:
        try:
            get_storage().delete(previous)
        except Exception:
            pass
    return client_dict(client, access_payload(db, client))


def own_contract(db: Session, user: User) -> dict:
    if user.role != "client":
        raise AppError("O contrato é lido no portal do cliente.", 403)
    ids = linked_client_ids(db, user)
    if not ids:
        raise AppError("Contrato não encontrado.", 404)
    client = get_client_or_404(db, ids[0])
    return {"company_name": client.company_name, "contract": contract_payload(client, file_path="/api/contract/file")}


def _contract_file(client: Client) -> tuple[bytes, str]:
    if not client.contract_key:
        raise AppError("Contrato não encontrado.", 404)
    try:
        data = get_storage().download(client.contract_key)
    except Exception as exc:
        raise AppError("Não foi possível abrir o contrato.", 404) from exc
    return data, client.contract_filename or "contrato.pdf"


def contract_file_for_admin(db: Session, client_id) -> tuple[bytes, str]:
    return _contract_file(get_client_or_404(db, client_id))


def contract_file_for_client(db: Session, user: User) -> tuple[bytes, str]:
    if user.role != "client":
        raise AppError("O contrato é lido no portal do cliente.", 403)
    ids = linked_client_ids(db, user)
    if not ids:
        raise AppError("Contrato não encontrado.", 404)
    return _contract_file(get_client_or_404(db, ids[0]))
