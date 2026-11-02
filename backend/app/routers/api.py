import uuid

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, joinedload, selectinload

from app.config import settings, utcnow
from app.database import get_db
from app.deps import get_current_user, require_admin
from app.errors import AppError
from app.limits import limiter
from app.models import AuditLog, Notification, Platform, User
from app.schemas import (
    ChangePasswordIn,
    ChangesIn,
    ClientCreate,
    ClientUpdate,
    ContentUpdate,
    ContentWrite,
    ForgotIn,
    LoginIn,
    HoldIn,
    MediaOrderIn,
    ProfileIn,
    ResetIn,
)
from app.security import create_access_token
from app.services.auth import (
    authenticate,
    change_password,
    issue_session,
    me_payload,
    request_password_reset,
    reset_password,
    revoke_refresh,
    rotate_session,
    update_profile,
)
from app.services.clients import (
    client_detail,
    create_client,
    delete_client,
    list_clients,
    contract_file_for_admin,
    contract_file_for_client,
    own_contract,
    remove_contract,
    remove_logo,
    save_contract,
    save_logo,
    update_client,
)
from app.services.common import client_ip, commit_session
from app.services.contents import (
    activity,
    add_media,
    approval_queue,
    approve_content,
    calendar_items,
    cancel_content,
    content_history,
    create_content,
    delete_content,
    hold_content,
    list_contents,
    order_media,
    publish_content,
    remove_media,
    request_changes,
    resubmit_content,
    start_review,
    submit_content,
    update_content,
)
from app.services.contents import get_content
from app.services.dashboard import admin_dashboard, client_dashboard
from app.services.serializers import content_dict
from app.storage import get_storage

router = APIRouter(prefix="/api")


def set_auth_cookies(response: Response, access: str, refresh: str, role: str) -> None:
    secure = settings.cookie_secure
    response.set_cookie(
        "vc_access",
        access,
        max_age=settings.access_token_minutes * 60,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        "vc_refresh",
        refresh,
        max_age=settings.refresh_token_days * 86400,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        "vc_role",
        role,
        max_age=settings.refresh_token_days * 86400,
        httponly=False,
        secure=secure,
        samesite="lax",
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    for name in ("vc_access", "vc_refresh", "vc_role"):
        response.delete_cookie(name, path="/")


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    storage_ok = False
    try:
        storage_ok = get_storage().health()
    except Exception:
        storage_ok = False
    return {"status": "ok", "database": "ok", "storage": "ok" if storage_ok else "unavailable", "version": settings.app_version}


@router.post("/auth/login")
@limiter.limit("10/minute")
def login(request: Request, payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = authenticate(db, payload.email, payload.password, client_ip(request))
    access, refresh = issue_session(db, user, client_ip(request), request.headers.get("user-agent"))
    set_auth_cookies(response, access, refresh, user.role)
    return {"user": me_payload(db, user)}


@router.post("/auth/refresh")
@limiter.limit("30/minute")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    user, access, new_refresh = rotate_session(
        db,
        request.cookies.get("vc_refresh", ""),
        client_ip(request),
        request.headers.get("user-agent"),
    )
    set_auth_cookies(response, access, new_refresh, user.role)
    return {"user": me_payload(db, user)}


@router.post("/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    revoke_refresh(db, request.cookies.get("vc_refresh"))
    clear_auth_cookies(response)
    return {"ok": True}


@router.get("/auth/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return me_payload(db, user)


@router.post("/auth/upload-token")
def upload_token(user: User = Depends(get_current_user)):
    return {"access_token": create_access_token(str(user.id), user.role)}


@router.post("/auth/forgot-password")
@limiter.limit("5/minute")
def forgot(request: Request, payload: ForgotIn, db: Session = Depends(get_db)):
    raw = request_password_reset(db, payload.email, client_ip(request))
    body = {"detail": "Se o e-mail estiver cadastrado, enviamos as instruções de recuperação."}
    if raw and settings.expose_dev_reset:
        body["dev_reset_url"] = f"{settings.frontend_url}/reset-password?token={raw}"
    return body


@router.post("/auth/reset-password")
@limiter.limit("10/minute")
def reset(request: Request, payload: ResetIn, db: Session = Depends(get_db)):
    reset_password(db, payload.token, payload.new_password, client_ip(request))
    return {"detail": "Senha atualizada. Entre com a nova senha."}


@router.post("/auth/change-password")
def change(request: Request, payload: ChangePasswordIn, response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    change_password(db, user, payload.current_password, payload.new_password, client_ip(request))
    access, refresh = issue_session(db, user, client_ip(request), request.headers.get("user-agent"))
    set_auth_cookies(response, access, refresh, user.role)
    return {"detail": "Senha atualizada."}


@router.patch("/auth/profile")
def profile(request: Request, payload: ProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    update_profile(db, user, payload.full_name, payload.phone, client_ip(request))
    return me_payload(db, user)


@router.get("/platforms")
def platforms(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Platform).where(Platform.is_active.is_(True)).options(selectinload(Platform.formats)).order_by(Platform.sort_order.asc())
    ).all()
    return [
        {
            "id": str(item.id),
            "slug": item.slug,
            "name": item.name,
            "formats": [
                {
                    "id": str(fmt.id),
                    "slug": fmt.slug,
                    "name": fmt.name,
                    "media_type": fmt.media_type,
                    "allows_hashtags": fmt.allows_hashtags,
                    "min_files": fmt.min_files,
                    "max_files": fmt.max_files,
                }
                for fmt in sorted(item.formats, key=lambda fmt: fmt.sort_order)
            ],
        }
        for item in rows
    ]


@router.get("/dashboard")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == "admin":
        return admin_dashboard(db)
    return client_dashboard(db, user)


@router.get("/clients")
def clients_list(
    q: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return list_clients(db, q=q, status=status, page=page, page_size=page_size)


@router.post("/clients", status_code=201)
def clients_create(request: Request, payload: ClientCreate, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    client = create_client(db, user, payload, client_ip(request))
    return client_detail(db, client.id)


@router.get("/clients/{client_id}")
def clients_get(client_id: uuid.UUID, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return client_detail(db, client_id)


@router.patch("/clients/{client_id}")
def clients_update(client_id: uuid.UUID, request: Request, payload: ClientUpdate, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    update_client(db, user, client_id, payload, client_ip(request))
    return client_detail(db, client_id)


@router.delete("/clients/{client_id}")
def clients_delete(client_id: uuid.UUID, request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    delete_client(db, user, client_id, client_ip(request))
    return {"ok": True}


@router.post("/clients/{client_id}/logo")
@limiter.limit("30/minute")
async def clients_logo(
    client_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = await file.read()
    return save_logo(db, user, client_id, file.filename or "logo", data, client_ip(request))


@router.delete("/clients/{client_id}/logo")
def clients_logo_delete(client_id: uuid.UUID, request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return remove_logo(db, user, client_id, client_ip(request))


@router.post("/clients/{client_id}/contract")
@limiter.limit("20/minute")
async def clients_contract(
    client_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = await file.read()
    return save_contract(db, user, client_id, file.filename or "contrato.pdf", data, client_ip(request))


@router.delete("/clients/{client_id}/contract")
def clients_contract_delete(client_id: uuid.UUID, request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return remove_contract(db, user, client_id, client_ip(request))


@router.get("/contract")
def contract_mine(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return own_contract(db, user)


def _pdf_response(data: bytes, filename: str) -> Response:
    safe = (filename or "contrato.pdf").replace('"', "").replace("\r", "").replace("\n", "")
    return Response(content=data, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{safe}"'})


@router.get("/clients/{client_id}/contract/file")
def clients_contract_file(client_id: uuid.UUID, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    data, filename = contract_file_for_admin(db, client_id)
    return _pdf_response(data, filename)


@router.get("/contract/file")
def contract_file(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data, filename = contract_file_for_client(db, user)
    return _pdf_response(data, filename)


@router.get("/contents")
def contents_list(
    q: str | None = None,
    status: str | None = None,
    client_id: uuid.UUID | None = None,
    platform_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_contents(
        db,
        user,
        q=q,
        status=status,
        client_id=client_id,
        platform_id=platform_id,
        page=page,
        page_size=page_size,
    )


@router.post("/contents", status_code=201)
def contents_create(request: Request, payload: ContentWrite, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return create_content(db, user, payload, client_ip(request))


@router.get("/contents/{content_id}")
def contents_get(content_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return content_dict(get_content(db, user, content_id), admin=user.role == "admin")


@router.patch("/contents/{content_id}")
def contents_update(content_id: uuid.UUID, request: Request, payload: ContentUpdate, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return update_content(db, user, content_id, payload, client_ip(request))


@router.delete("/contents/{content_id}")
def contents_delete(content_id: uuid.UUID, request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    delete_content(db, user, content_id, client_ip(request))
    return {"ok": True}


@router.post("/contents/{content_id}/media")
@limiter.limit("60/minute")
async def contents_media(
    content_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = await file.read()
    return add_media(db, user, content_id, file.filename or "arquivo", data, client_ip(request))


@router.delete("/contents/{content_id}/media/{media_id}")
def contents_media_delete(
    content_id: uuid.UUID,
    media_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return remove_media(db, user, content_id, media_id, client_ip(request))


@router.put("/contents/{content_id}/media/order")
def contents_media_order(
    content_id: uuid.UUID,
    request: Request,
    payload: MediaOrderIn,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return order_media(db, user, content_id, payload.ids, client_ip(request))


@router.post("/contents/{content_id}/hold")
def contents_hold(content_id: uuid.UUID, request: Request, payload: HoldIn, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return hold_content(db, user, content_id, payload.waiting_note, client_ip(request))


@router.post("/contents/{content_id}/submit")
def contents_submit(content_id: uuid.UUID, request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return submit_content(db, user, content_id, client_ip(request))


@router.post("/contents/{content_id}/resubmit")
def contents_resubmit(content_id: uuid.UUID, request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return resubmit_content(db, user, content_id, client_ip(request))


@router.post("/contents/{content_id}/review")
def contents_review(content_id: uuid.UUID, request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return start_review(db, user, content_id, client_ip(request))


@router.post("/contents/{content_id}/publish")
def contents_publish(content_id: uuid.UUID, request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return publish_content(db, user, content_id, client_ip(request))


@router.post("/contents/{content_id}/cancel")
def contents_cancel(content_id: uuid.UUID, request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return cancel_content(db, user, content_id, client_ip(request))


@router.get("/contents/{content_id}/history")
def contents_history(content_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return content_history(db, user, content_id)


@router.get("/approvals/queue")
def approvals_queue(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return approval_queue(db, user)


@router.post("/approvals/{content_id}/approve")
def approvals_approve(content_id: uuid.UUID, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return approve_content(db, user, content_id, client_ip(request))


@router.post("/approvals/{content_id}/changes")
def approvals_changes(
    content_id: uuid.UUID,
    request: Request,
    payload: ChangesIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return request_changes(db, user, content_id, payload.reason, client_ip(request))


@router.get("/calendar")
def calendar(
    start: str,
    end: str,
    client_id: uuid.UUID | None = None,
    platform_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        start_date = utcnow().date().__class__.fromisoformat(start)
        end_date = utcnow().date().__class__.fromisoformat(end)
    except ValueError as exc:
        raise AppError("Informe o período no formato AAAA-MM-DD.", 422) from exc
    if end_date < start_date:
        raise AppError("O período do calendário é inválido.", 422)
    return calendar_items(db, user, start_date, end_date, client_id, platform_id)


@router.get("/history")
def history(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    client_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return activity(db, user, page, page_size, client_id)


@router.get("/notifications")
def notifications(
    unread: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filters = [Notification.user_id == user.id]
    if unread:
        filters.append(Notification.read_at.is_(None))
    total = int(db.scalar(select(func.count()).select_from(Notification).where(*filters)) or 0)
    rows = db.scalars(
        select(Notification).where(*filters).order_by(Notification.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [
            {
                "id": str(item.id),
                "type": item.type,
                "title": item.title,
                "body": item.body,
                "data": item.data,
                "read_at": item.read_at.isoformat() if item.read_at else None,
                "created_at": item.created_at.isoformat(),
            }
            for item in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "unread_count": int(
            db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None)))
            or 0
        ),
    }


@router.post("/notifications/{notification_id}/read")
def notifications_read(notification_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(Notification, notification_id)
    if not item or item.user_id != user.id:
        raise AppError("Notificação não encontrada.", 404)
    if item.read_at is None:
        item.read_at = utcnow()
        commit_session(db)
    return {"ok": True}


@router.post("/notifications/read-all")
def notifications_read_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None))).all()
    now = utcnow()
    for item in rows:
        item.read_at = now
    commit_session(db)
    return {"ok": True}


@router.get("/audit")
def audit(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    total = int(db.scalar(select(func.count()).select_from(AuditLog)) or 0)
    rows = db.scalars(
        select(AuditLog)
        .options(joinedload(AuditLog.actor))
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).unique().all()
    return {
        "items": [
            {
                "id": str(item.id),
                "action": item.action,
                "entity_type": item.entity_type,
                "entity_id": item.entity_id,
                "actor_name": item.actor.full_name if item.actor else None,
                "details": item.details,
                "ip": item.ip,
                "created_at": item.created_at.isoformat(),
            }
            for item in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/system")
def system(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    storage_ok = False
    try:
        storage_ok = get_storage().health()
    except Exception:
        storage_ok = False
    return {
        "version": settings.app_version,
        "environment": settings.app_env,
        "database": "ok",
        "storage": "ok" if storage_ok else "unavailable",
        "external_notifications": ["in_app"],
        "prepared_channels": ["email", "whatsapp"],
    }
