import base64

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
HEADERS = {"X-Requested-With": "vcontent"}


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"


def test_login_and_me(client):
    denied = client.post("/api/auth/login", json={"email": "admin@vcontent.local", "password": "errada"}, headers=HEADERS)
    assert denied.status_code == 401
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@vcontent.local", "password": "Admin!2026"},
        headers=HEADERS,
    )
    assert response.status_code == 200
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "admin"
    assert "password" not in me.text


def test_csrf_blocks_cookie_post_without_header(client):
    client.post("/api/auth/login", json={"email": "admin@vcontent.local", "password": "Admin!2026"}, headers=HEADERS)
    response = client.post("/api/auth/logout")
    assert response.status_code == 403


def _platforms(client):
    response = client.get("/api/platforms")
    assert response.status_code == 200
    data = {item["slug"]: item for item in response.json()}
    return data


def _client_payload(name, email):
    return {
        "company_name": name,
        "contact_name": "Responsável",
        "email": email,
        "phone": "11999999999",
        "description": "Marca de teste",
        "internal_notes": "nota interna",
        "status": "active",
        "access_email": email,
        "access_name": "Responsável",
        "access_password": "Cliente!2026",
    }


def test_full_approval_flow_and_isolation(client):
    client.post("/api/auth/login", json={"email": "admin@vcontent.local", "password": "Admin!2026"}, headers=HEADERS)
    alpha = client.post("/api/clients", json=_client_payload("Alpha", "alpha@cliente.test"), headers=HEADERS)
    beta = client.post("/api/clients", json=_client_payload("Beta", "beta@cliente.test"), headers=HEADERS)
    assert alpha.status_code == 201, alpha.text
    assert beta.status_code == 201, beta.text
    alpha_id = alpha.json()["id"]
    beta_id = beta.json()["id"]

    platforms = _platforms(client)
    tiktok = platforms["tiktok"]
    static = next(item for item in tiktok["formats"] if item["slug"] == "static")
    instagram = platforms["instagram"]
    post = next(item for item in instagram["formats"] if item["slug"] == "post")

    created = client.post(
        "/api/contents",
        headers=HEADERS,
        json={
            "client_id": alpha_id,
            "platform_id": tiktok["id"],
            "format_id": static["id"],
            "title": "Lançamento Alpha",
            "caption": "Legenda do vídeo estático",
            "copy_text": "Copy principal",
            "hashtags": "#alpha #vcontent",
            "scheduled_date": "2026-12-01",
            "scheduled_time": "10:30",
            "internal_notes": "não mostrar ao cliente",
        },
    )
    assert created.status_code == 201, created.text
    content_id = created.json()["id"]
    assert created.json()["hashtags"] == "#alpha #vcontent"
    assert created.json()["status"] == "draft"

    hidden = client.post(
        "/api/contents",
        headers=HEADERS,
        json={
            "client_id": beta_id,
            "platform_id": instagram["id"],
            "format_id": post["id"],
            "title": "Post Beta",
            "caption": "Legenda beta",
            "copy_text": "Copy beta",
            "hashtags": "#nao-deve-salvar",
            "scheduled_date": "2026-12-02",
        },
    )
    assert hidden.status_code == 201, hidden.text
    assert hidden.json()["hashtags"] is None

    missing_media = client.post(f"/api/contents/{content_id}/submit", headers=HEADERS)
    assert missing_media.status_code == 422

    uploaded = client.post(
        f"/api/contents/{content_id}/media",
        headers=HEADERS,
        files={"file": ("foto.png", PNG, "image/png")},
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["media"][0]["mime_type"] == "image/png"
    assert uploaded.json()["media"][0]["url"]

    submitted = client.post(f"/api/contents/{content_id}/submit", headers=HEADERS)
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "pending_approval"

    client.post("/api/auth/logout", headers=HEADERS)
    client.post("/api/auth/login", json={"email": "beta@cliente.test", "password": "Cliente!2026"}, headers=HEADERS)
    forbidden = client.get(f"/api/contents/{content_id}")
    assert forbidden.status_code == 404
    assert client.get("/api/clients").status_code == 403
    listing = client.get("/api/contents")
    assert listing.status_code == 200
    assert all(item["client_id"] == beta_id for item in listing.json()["items"])
    assert "internal_notes" not in listing.text

    client.post("/api/auth/logout", headers=HEADERS)
    client.post("/api/auth/login", json={"email": "alpha@cliente.test", "password": "Cliente!2026"}, headers=HEADERS)
    queue = client.get("/api/approvals/queue")
    assert queue.status_code == 200
    assert [item["id"] for item in queue.json()] == [content_id]
    seen = client.get(f"/api/contents/{content_id}")
    assert seen.status_code == 200
    assert "internal_notes" not in seen.json()
    no_reason = client.post(f"/api/approvals/{content_id}/changes", headers=HEADERS, json={"reason": "x"})
    assert no_reason.status_code == 422
    approved = client.post(f"/api/approvals/{content_id}/approve", headers=HEADERS)
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    history = client.get(f"/api/contents/{content_id}/history")
    assert any(item["action"] == "approved" for item in history.json())

    client.post("/api/auth/logout", headers=HEADERS)
    client.post("/api/auth/login", json={"email": "admin@vcontent.local", "password": "Admin!2026"}, headers=HEADERS)
    published = client.post(f"/api/contents/{content_id}/publish", headers=HEADERS)
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    notes = client.get("/api/notifications")
    assert notes.status_code == 200
    assert notes.json()["unread_count"] >= 1


def test_change_request_and_resubmit(client):
    client.post("/api/auth/login", json={"email": "admin@vcontent.local", "password": "Admin!2026"}, headers=HEADERS)
    created_client = client.post("/api/clients", json=_client_payload("Gamma", "gamma@cliente.test"), headers=HEADERS)
    client_id = created_client.json()["id"]
    platforms = _platforms(client)
    tiktok = platforms["tiktok"]
    video = next(item for item in tiktok["formats"] if item["slug"] == "static")
    content = client.post(
        "/api/contents",
        headers=HEADERS,
        json={
            "client_id": client_id,
            "platform_id": tiktok["id"],
            "format_id": video["id"],
            "title": "Ajuste de copy",
            "caption": "Legenda original",
            "copy_text": "Copy original",
            "hashtags": "#gamma",
            "scheduled_date": "2026-12-10",
        },
    )
    content_id = content.json()["id"]
    client.post(f"/api/contents/{content_id}/media", headers=HEADERS, files={"file": ("foto.png", PNG, "image/png")})
    client.post(f"/api/contents/{content_id}/submit", headers=HEADERS)

    client.post("/api/auth/logout", headers=HEADERS)
    client.post("/api/auth/login", json={"email": "gamma@cliente.test", "password": "Cliente!2026"}, headers=HEADERS)
    changed = client.post(
        f"/api/approvals/{content_id}/changes",
        headers=HEADERS,
        json={"reason": "A cor do fundo precisa ficar mais clara."},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["status"] == "changes_requested"
    assert "mais clara" in (changed.json()["latest_reason"] or "")

    client.post("/api/auth/logout", headers=HEADERS)
    client.post("/api/auth/login", json={"email": "admin@vcontent.local", "password": "Admin!2026"}, headers=HEADERS)
    edited = client.patch(
        f"/api/contents/{content_id}",
        headers=HEADERS,
        json={"copy_text": "Copy revisada"},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["status"] == "in_review"
    resent = client.post(f"/api/contents/{content_id}/resubmit", headers=HEADERS)
    assert resent.status_code == 200, resent.text
    assert resent.json()["status"] == "resubmitted"
    assert resent.json()["version"] == 2

    client.post("/api/auth/logout", headers=HEADERS)
    client.post("/api/auth/login", json={"email": "gamma@cliente.test", "password": "Cliente!2026"}, headers=HEADERS)
    queue = client.get("/api/approvals/queue")
    assert content_id in [item["id"] for item in queue.json()]
    notes = client.get("/api/notifications")
    assert any(item["type"] == "content_resubmitted" for item in notes.json()["items"])
    history = client.get(f"/api/contents/{content_id}/history")
    actions = [item["action"] for item in history.json()]
    assert "changes_requested" in actions
    assert "resubmitted" in actions


def test_password_reset(client):
    client.post("/api/auth/login", json={"email": "admin@vcontent.local", "password": "Admin!2026"}, headers=HEADERS)
    client.post("/api/clients", json=_client_payload("Delta", "delta@cliente.test"), headers=HEADERS)
    client.post("/api/auth/logout", headers=HEADERS)
    forgot = client.post("/api/auth/forgot-password", json={"email": "delta@cliente.test"}, headers=HEADERS)
    assert forgot.status_code == 200
    url = forgot.json()["dev_reset_url"]
    token = url.split("token=")[1]
    reset = client.post("/api/auth/reset-password", json={"token": token, "new_password": "NovaSenha!2026"}, headers=HEADERS)
    assert reset.status_code == 200, reset.text
    old = client.post("/api/auth/login", json={"email": "delta@cliente.test", "password": "Cliente!2026"}, headers=HEADERS)
    assert old.status_code == 401
    new = client.post("/api/auth/login", json={"email": "delta@cliente.test", "password": "NovaSenha!2026"}, headers=HEADERS)
    assert new.status_code == 200


PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def test_contract_and_in_progress(client):
    client.post("/api/auth/login", json={"email": "admin@vcontent.local", "password": "Admin!2026"}, headers=HEADERS)
    created = client.post("/api/clients", json=_client_payload("Gama", "gama@cliente.test"), headers=HEADERS)
    assert created.status_code == 201, created.text
    client_id = created.json()["id"]
    other = client.post("/api/clients", json=_client_payload("Delta", "delta@cliente.test"), headers=HEADERS)
    assert other.status_code == 201, other.text

    rejected = client.post(
        f"/api/clients/{client_id}/contract",
        headers=HEADERS,
        files={"file": ("contrato.txt", b"nao e pdf", "text/plain")},
    )
    assert rejected.status_code == 422
    uploaded = client.post(
        f"/api/clients/{client_id}/contract",
        headers=HEADERS,
        files={"file": ("contrato.pdf", PDF, "application/pdf")},
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["contract"]["filename"] == "contrato.pdf"
    assert uploaded.json()["contract"]["url"]

    platforms = _platforms(client)
    tiktok = platforms["tiktok"]
    static = next(item for item in tiktok["formats"] if item["slug"] == "static")
    piece = client.post(
        "/api/contents",
        headers=HEADERS,
        json={
            "client_id": client_id,
            "platform_id": tiktok["id"],
            "format_id": static["id"],
            "title": "Reels de dezembro",
        },
    )
    assert piece.status_code == 201, piece.text
    content_id = piece.json()["id"]
    short = client.post(f"/api/contents/{content_id}/hold", headers=HEADERS, json={"waiting_note": "ok"})
    assert short.status_code == 422
    held = client.post(
        f"/api/contents/{content_id}/hold",
        headers=HEADERS,
        json={"waiting_note": "Aguardando o envio dos vídeos gravados."},
    )
    assert held.status_code == 200, held.text
    assert held.json()["status"] == "in_progress"
    assert held.json()["waiting_note"] == "Aguardando o envio dos vídeos gravados."
    blocked = client.post(f"/api/contents/{content_id}/submit", headers=HEADERS)
    assert blocked.status_code == 422

    client.post("/api/auth/logout", headers=HEADERS)
    client.post("/api/auth/login", json={"email": "delta@cliente.test", "password": "Cliente!2026"}, headers=HEADERS)
    assert client.get(f"/api/contents/{content_id}").status_code == 404
    foreign = client.get("/api/contract")
    assert foreign.status_code == 200
    assert foreign.json()["contract"] is None
    assert client.get("/api/contract/file").status_code == 404
    assert all(item["id"] != content_id for item in client.get("/api/contents").json()["items"])

    client.post("/api/auth/logout", headers=HEADERS)
    client.post("/api/auth/login", json={"email": "gama@cliente.test", "password": "Cliente!2026"}, headers=HEADERS)
    mine = client.get("/api/contract")
    assert mine.status_code == 200, mine.text
    assert mine.json()["contract"]["filename"] == "contrato.pdf"
    assert mine.json()["contract"]["url"] == "/api/contract/file"
    opened = client.get("/api/contract/file")
    assert opened.status_code == 200, opened.text
    assert opened.content.startswith(b"%PDF")
    assert opened.headers["content-type"].startswith("application/pdf")
    assert client.get(f"/api/clients/{client_id}/contract/file").status_code == 403
    assert client.post(f"/api/clients/{client_id}/contract", headers=HEADERS, files={"file": ("contrato.pdf", PDF, "application/pdf")}).status_code == 403
    listing = client.get("/api/contents?status=in_progress")
    assert listing.status_code == 200
    assert listing.json()["items"][0]["id"] == content_id
    assert listing.json()["items"][0]["waiting_note"].startswith("Aguardando")
    queue = client.get("/api/approvals/queue")
    assert all(item["id"] != content_id for item in queue.json())
    dash = client.get("/api/dashboard")
    assert dash.json()["in_progress"] == 1


def test_deactivate_client_blocks_login(client):
    client.post("/api/auth/login", json={"email": "admin@vcontent.local", "password": "Admin!2026"}, headers=HEADERS)
    created = client.post("/api/clients", json=_client_payload("Epsilon", "epsilon@cliente.test"), headers=HEADERS)
    client_id = created.json()["id"]
    updated = client.patch(f"/api/clients/{client_id}", headers=HEADERS, json={"status": "inactive"})
    assert updated.status_code == 200
    client.post("/api/auth/logout", headers=HEADERS)
    blocked = client.post("/api/auth/login", json={"email": "epsilon@cliente.test", "password": "Cliente!2026"}, headers=HEADERS)
    assert blocked.status_code == 403
